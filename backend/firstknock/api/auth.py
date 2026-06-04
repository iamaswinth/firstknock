import structlog
import jwt
import httpx
from collections import OrderedDict
from fastapi import HTTPException, Header
from jwt.algorithms import RSAAlgorithm
from firstknock.config import settings

logger = structlog.get_logger()

# Shared HTTP client — one connection pool for all Clerk API calls
_http_client: httpx.AsyncClient | None = None

def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=8.0)
    return _http_client

# Module-level caches — reset on process restart (fine for dev; JWKS keys rarely rotate)
_jwks_keys: list | None = None

# LRU cap: evicts oldest entry after 50k users so memory stays bounded
_MAX_EMAIL_CACHE = 50_000
_email_by_clerk_id: OrderedDict[str, str] = OrderedDict()


async def _load_jwks() -> list:
    global _jwks_keys
    if _jwks_keys is None:
        if not settings.clerk_jwks_url:
            raise HTTPException(status_code=500, detail="CLERK_JWKS_URL not configured")
        r = await _get_http_client().get(settings.clerk_jwks_url, timeout=5)
        r.raise_for_status()
        _jwks_keys = r.json()["keys"]
    return _jwks_keys


async def _email_for(clerk_id: str) -> str:
    if clerk_id in _email_by_clerk_id:
        return _email_by_clerk_id[clerk_id]
    if not settings.clerk_secret_key:
        logger.warning("clerk_secret_key_missing", clerk_id=clerk_id)
        return ""
    try:
        r = await _get_http_client().get(
            f"https://api.clerk.com/v1/users/{clerk_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        )
    except httpx.TimeoutException:
        logger.warning("clerk_api_timeout", clerk_id=clerk_id)
        return ""
    except httpx.HTTPError as exc:
        logger.warning("clerk_api_error", clerk_id=clerk_id, error=str(exc))
        return ""
    if r.status_code != 200:
        logger.warning("clerk_user_fetch_failed", clerk_id=clerk_id, status=r.status_code)
        return ""
    data = r.json()
    addrs = data.get("email_addresses", [])
    primary_id = data.get("primary_email_address_id")
    email = next(
        (e["email_address"] for e in addrs if e["id"] == primary_id),
        addrs[0]["email_address"] if addrs else "",
    )
    _email_by_clerk_id[clerk_id] = email
    if len(_email_by_clerk_id) > _MAX_EMAIL_CACHE:
        _email_by_clerk_id.popitem(last=False)
    return email


async def verify_clerk_token(authorization: str = Header(...)) -> dict:
    """
    FastAPI dependency that verifies a Clerk-issued JWT (RS256).
    Returns {"clerk_id": str, "email": str}.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'")

    token = authorization[7:]

    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Malformed JWT")

    kid = header.get("kid")
    keys = await _load_jwks()
    key_data = next((k for k in keys if k.get("kid") == kid), None)

    if key_data is None:
        # Refresh JWKS once in case of key rotation
        global _jwks_keys
        _jwks_keys = None
        keys = await _load_jwks()
        key_data = next((k for k in keys if k.get("kid") == kid), None)

    if key_data is None:
        raise HTTPException(status_code=401, detail="Unknown signing key in token header")

    public_key = RSAAlgorithm.from_jwk(key_data)

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    clerk_id: str = payload.get("sub", "")

    # Clerk session tokens don't include email by default — fetch from Clerk API
    email = payload.get("email") or await _email_for(clerk_id)

    return {"clerk_id": clerk_id, "email": email}
