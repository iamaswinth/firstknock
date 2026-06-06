import re
import json
from pathlib import Path

# ── Regex patterns ─────────────────────────────────────────────────────────────

_PARENS_RE = re.compile(r'\s*\([^)]*\)\s*')

# Strips common legal/descriptive suffixes from company names so that
# "Cimpress India Pvt. Ltd." and "Cimpress India" resolve to the same node.
_COMPANY_SUFFIX_RE = re.compile(
    r'\s*[,.]?\s*(?:'
    r'pvt\.?\s*ltd\.?|private\s+limited|ltd\.?|llc|inc\.?|corp\.?|co\.?|limited|'
    r'technologies|tech|solutions|software|systems|services|group'
    r')\s*\.?\s*$',
    re.IGNORECASE,
)

# ── Alias file loader ──────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


def _load_aliases(filename: str) -> dict[str, str]:
    path = _DATA_DIR / filename
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return {k.lower(): v for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)}
        except Exception:
            return {}
    return {}


_COMPANY_ALIASES: dict[str, str] = _load_aliases("company_aliases.json")
_INSTITUTION_ALIASES: dict[str, str] = _load_aliases("institution_aliases.json")

# ── Stage 1: synchronous suffix stripping ─────────────────────────────────────


def _strip_company(name: str) -> str:
    """Strip legal suffixes and parenthetical notes from a raw company name.

    Synchronous — safe to call at extraction/resolution time without a graph session.
    Idempotent: calling twice returns the same result.
    """
    n = _PARENS_RE.sub(' ', name).strip()
    # Strip suffixes repeatedly until stable (e.g. "Foo India Ltd." → "Foo India" → "Foo India")
    while True:
        stripped = _COMPANY_SUFFIX_RE.sub('', n).strip().rstrip(',').strip()
        if stripped == n or not stripped:
            break
        n = stripped
    return n or name.strip()


def _strip_institution(name: str) -> str:
    """Strip parenthetical qualifiers from a raw institution name.

    Synchronous. Does NOT strip suffixes like 'University' or 'College' because
    those are load-bearing parts of the name. Fuzzy pre-check (Stage 2) and alias
    files (Stage 3) handle abbreviation resolution.
    """
    return _PARENS_RE.sub(' ', name).strip() or name.strip()


# ── Cypher fragments (inlined here to avoid circular import with queries.py) ───

_FIND_SIMILAR_COMPANY = """
MATCH (c:Company)
WHERE size(c.name) >= 4 AND size($base) >= 4
  AND (toLower(replace(c.name, ' ', '')) CONTAINS toLower(replace($base, ' ', ''))
       OR toLower(replace($base, ' ', '')) CONTAINS toLower(replace(c.name, ' ', '')))
RETURN c.name
ORDER BY size(c.name) DESC
LIMIT 1
"""

_FIND_SIMILAR_INSTITUTION = """
MATCH (i:Institution)
WHERE size(i.name) >= 4 AND size($key) >= 4
  AND (toLower(i.name) CONTAINS toLower($key)
       OR toLower($key) CONTAINS toLower(i.name))
RETURN i.name
ORDER BY size(i.name) DESC
LIMIT 1
"""

# ── Stage 2+3: async full resolution ──────────────────────────────────────────


async def resolve_company(session, raw: str) -> str:
    """Return the canonical company name to use as a graph MERGE key.

    Stage 1 — strip legal suffixes (sync).
    Stage 2 — query existing Company nodes for a containment match (async).
    Stage 3 — fall back to company_aliases.json for entries that can't be
               matched by string containment alone.
    """
    base = _strip_company(raw)
    if len(base) >= 4:
        result = await session.run(_FIND_SIMILAR_COMPANY, base=base)
        record = await result.single()
        if record:
            return record["c.name"]
    alias = _COMPANY_ALIASES.get(base.lower())
    return alias or base


async def resolve_institution(session, raw: str) -> str:
    """Return the canonical institution name to use as a graph MERGE key.

    Stage 1 — strip parenthetical qualifiers (sync).
    Stage 2 — query existing Institution nodes for a containment match (async).
    Stage 3 — fall back to institution_aliases.json (e.g. "iit delhi" →
               "Indian Institute of Technology Delhi") without code changes.
    """
    key = _strip_institution(raw)
    if len(key) >= 4:
        result = await session.run(_FIND_SIMILAR_INSTITUTION, key=key)
        record = await result.single()
        if record:
            return record["i.name"]
    alias = _INSTITUTION_ALIASES.get(key.lower())
    return alias or key
