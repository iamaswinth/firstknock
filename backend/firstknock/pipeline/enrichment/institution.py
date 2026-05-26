import json
import structlog
from pathlib import Path

logger = structlog.get_logger()

_RANKINGS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "institution_rankings.json"
_rankings: dict[str, list[str]] | None = None


def _load_rankings() -> dict[str, list[str]]:
    global _rankings
    if _rankings is None:
        try:
            _rankings = json.loads(_RANKINGS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("institution_rankings_load_failed", error=str(exc))
            _rankings = {}
    return _rankings


def _lookup_tier(name: str, rankings: dict[str, list[str]]) -> str:
    name_lower = name.lower().strip()
    for tier in ("top10", "top50", "top100"):
        for entry in rankings.get(tier, []):
            if entry.lower() in name_lower or name_lower in entry.lower():
                return tier
    return "other"


def enrich_institutions(institution_names: list[str]) -> dict[str, dict]:
    """
    Lookup ranking tier for each institution from static JSON.
    Returns {institution_name: {ranking_tier}}
    """
    rankings = _load_rankings()
    results: dict[str, dict] = {}
    for name in institution_names:
        if not name:
            continue
        tier = _lookup_tier(name, rankings)
        results[name] = {"ranking_tier": tier}
        logger.info("institution_enriched", institution=name, tier=tier)
    return results
