import re
from .aliases import SKILL_ALIASES

# Matches trailing parenthetical: "AWS RDS (MySQL)" → strips " (MySQL)"
_PARENS_RE = re.compile(r'\s*\([^)]*\)\s*$')

# Matches trailing version: "Next.js 14", "Python 3.11", "React v18", "BGE-Reranker-v2"
_VERSION_RE = re.compile(r'(\s+v?\d[\d.]*|-v\d[\d.]*)$', re.IGNORECASE)


def canonicalize_skill(raw: str) -> str:
    cleaned = raw.strip()

    # Step 1 — strip parenthetical annotation
    cleaned = _PARENS_RE.sub('', cleaned).strip()

    # Step 2 — strip trailing version number
    cleaned = _VERSION_RE.sub('', cleaned).strip()

    # Step 3 — exact alias lookup (case-insensitive)
    canonical = SKILL_ALIASES.get(cleaned.lower())
    if canonical:
        return canonical

    return cleaned


def canonicalize_skill_list(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in skills:
        canonical = canonicalize_skill(raw)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result
