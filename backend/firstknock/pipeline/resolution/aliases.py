import json
from pathlib import Path

_aliases_path = Path(__file__).parents[3] / "data" / "skill_aliases.json"

with open(_aliases_path, encoding="utf-8") as f:
    _raw: dict[str, str] = json.load(f)

# Lowercase all keys for case-insensitive lookup
SKILL_ALIASES: dict[str, str] = {k.lower(): v for k, v in _raw.items()}
