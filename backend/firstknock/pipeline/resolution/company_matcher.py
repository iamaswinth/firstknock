from firstknock.pipeline.resolution.entity_normalizer import _strip_company


def match_company(raw: str) -> str:
    """Synchronous suffix-strip for use at extraction/resolution time (no graph session).
    For full fuzzy resolution (Stage 2+3) at graph-write time, use resolve_company()."""
    return _strip_company(raw)
