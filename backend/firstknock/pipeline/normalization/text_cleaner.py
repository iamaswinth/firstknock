import re


def clean_text(raw: str) -> str:
    text = raw

    # Remove zero-width and non-printable characters
    text = re.sub(r'[​‌‍﻿­]', '', text)

    # Fix common UTF-8 mojibake artifacts
    replacements = {
        'â€™': "'", 'â€œ': '"', 'â€': '"', 'Ã©': 'é',
        'Ã¨': 'è', 'Ã ': 'à', 'Â': '', 'â€"': '–', 'â€"': '—',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Strip standalone page numbers (line is just a number, or "Page N" / "Page N of M")
    text = re.sub(r'(?m)^\s*[Pp]age\s+\d+(\s+of\s+\d+)?\s*$', '', text)
    text = re.sub(r'(?m)^\s*\d+\s*$', '', text)

    # Normalize whitespace within each line (multiple spaces → single space)
    lines = [re.sub(r'  +', ' ', line).strip() for line in text.splitlines()]
    text = '\n'.join(lines)

    # Collapse 3+ consecutive blank lines → 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
