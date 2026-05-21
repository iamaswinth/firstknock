import re

_HEADER_MAP = {
    "SUMMARY": "summary",
    "PROFESSIONAL SUMMARY": "summary",
    "ABOUT": "summary",
    "ABOUT ME": "summary",
    "WORK EXPERIENCE": "experience",
    "EXPERIENCE": "experience",
    "EMPLOYMENT": "experience",
    "EMPLOYMENT HISTORY": "experience",
    "PROFESSIONAL EXPERIENCE": "experience",
    "PROJECTS": "projects",
    "PERSONAL PROJECTS": "projects",
    "PROJECT WORK": "projects",
    "SIDE PROJECTS": "projects",
    "SKILLS": "skills",
    "TECHNICAL SKILLS": "skills",
    "CORE COMPETENCIES": "skills",
    "KEY SKILLS": "skills",
    "EDUCATION": "education",
    "ACADEMIC BACKGROUND": "education",
    "ACADEMIC QUALIFICATIONS": "education",
    "CERTIFICATIONS": "certifications",
    "CERTIFICATES": "certifications",
    "ACHIEVEMENTS": "certifications",
    "AWARDS": "certifications",
    "LANGUAGES": "languages_spoken",
    "LANGUAGES SPOKEN": "languages_spoken",
}

# Matches a line that is entirely uppercase letters and spaces, 2–40 chars
_HEADER_RE = re.compile(r'^[A-Z][A-Z\s]{1,38}[A-Z]$')


def detect_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key = "header"
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        canonical = _match_header(stripped)
        if canonical:
            _flush(sections, current_key, current_lines)
            current_key = canonical
            current_lines = []
        else:
            current_lines.append(line)

    _flush(sections, current_key, current_lines)
    return sections


def _match_header(line: str) -> str | None:
    if line in _HEADER_MAP:
        return _HEADER_MAP[line]
    if _HEADER_RE.match(line):
        return line.lower().replace(" ", "_")
    return None


def _flush(sections: dict, key: str, lines: list[str]) -> None:
    content = "\n".join(lines).strip()
    if content:
        sections[key] = content
