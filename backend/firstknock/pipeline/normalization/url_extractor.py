import re
from urllib.parse import urlparse

_URL_RE = re.compile(r'https?://[^\s<>"{}|\\^\[\]`]+')


def extract_urls(text: str) -> dict:
    result: dict[str, list[str]] = {"github": [], "linkedin": [], "other": []}

    for match in _URL_RE.finditer(text):
        url = match.group().rstrip(".,;)")
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            continue

        if "github.com" in host:
            result["github"].append(url)
        elif "linkedin.com" in host:
            result["linkedin"].append(url)
        else:
            result["other"].append(url)

    return result
