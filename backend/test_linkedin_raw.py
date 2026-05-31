"""
Minimal LinkedIn/Apify raw response tester.
Needs only: httpx, pydantic-settings (both already installed)

Run:
    python test_linkedin_raw.py <linkedin_url>

Example:
    python test_linkedin_raw.py https://www.linkedin.com/in/yourprofile
"""
import asyncio
import json
import sys
import os

# Read APIFY_API_KEY from .env
def load_env_key(key: str) -> str:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(key, "")


APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID   = "harvestapi~linkedin-profile-scraper"


async def run(linkedin_url: str):
    import httpx

    api_key = load_env_key("APIFY_API_KEY")
    if not api_key:
        print("ERROR: APIFY_API_KEY not found in backend/.env")
        return

    print(f"\nStarting Apify run for: {linkedin_url}")

    async with httpx.AsyncClient(timeout=120) as client:
        # Start run
        run_resp = await client.post(
            f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
            params={"token": api_key},
            json={"urls": [linkedin_url]},
        )
        run_resp.raise_for_status()
        run_id = run_resp.json()["data"]["id"]
        print(f"Run ID: {run_id}")

        # Poll
        status = ""
        for i in range(24):
            await asyncio.sleep(5)
            status_resp = await client.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params={"token": api_key},
            )
            status_resp.raise_for_status()
            status = status_resp.json()["data"]["status"]
            print(f"  [{(i+1)*5}s] {status}")
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break

        if status != "SUCCEEDED":
            print(f"\nRun ended with: {status}")
            return

        dataset_resp = await client.get(
            f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items",
            params={"token": api_key},
        )
        dataset_resp.raise_for_status()
        items = dataset_resp.json()

    if not items:
        print("Empty dataset — Apify returned no items.")
        return

    item = items[0] if isinstance(items, list) else items

    # ── Picture keys ─────────────────────────────────────────────────────────
    print("\n=== PICTURE-RELATED KEYS ===")
    picture_keys = [k for k in item.keys() if any(
        w in k.lower() for w in ("photo", "picture", "image", "avatar", "img", "thumb")
    )]
    if picture_keys:
        for k in picture_keys:
            print(f"  {k!r}: {item[k]!r}")
    else:
        print("  NONE — this actor does not return a profile picture field.")

    # ── All top-level keys ────────────────────────────────────────────────────
    print("\n=== ALL TOP-LEVEL KEYS ===")
    print(json.dumps(list(item.keys()), indent=2))

    # ── Full raw dump ─────────────────────────────────────────────────────────
    print("\n=== FULL RAW ITEM ===")
    print(json.dumps(item, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_linkedin_raw.py <linkedin_profile_url>")
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))
