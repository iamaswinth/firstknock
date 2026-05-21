import asyncio
from firstknock.pipeline.parsers.router import parse_file
from firstknock.pipeline.normalization.text_cleaner import clean_text
from firstknock.pipeline.normalization.section_detector import detect_sections
from firstknock.pipeline.normalization.url_extractor import extract_urls


async def main():
    with open("tests/fixtures/sample_resumes/resume.pdf", "rb") as f:
        parsed = await parse_file(f.read(), "pdf")

    raw = parsed["raw_text"]
    cleaned = clean_text(raw)
    sections = detect_sections(cleaned)
    urls = extract_urls(raw)

    print("=== SECTIONS DETECTED ===")
    for name, content in sections.items():
        print(f"  [{name}] — {len(content)} chars")

    print()
    print("=== URLS EXTRACTED ===")
    print("GitHub:", urls.get("github", []))
    print("LinkedIn:", urls.get("linkedin", []))
    print("Other:", urls.get("other", []))

    print()
    print("=== SIZE DELTA ===")
    print(f"Raw: {len(raw)} chars → Cleaned: {len(cleaned)} chars ({len(cleaned) - len(raw):+d})")

    print()
    print("=== PASS CRITERIA ===")
    required = {"experience", "projects", "skills", "education"}
    detected = set(sections.keys())
    missing = required - detected
    print("Required sections present:", "YES" if not missing else f"NO — missing {missing}")
    print("Summary present:", "YES" if "summary" in sections else "NO (optional)")
    print("Cleaned <= raw:", "YES" if len(cleaned) <= len(raw) else "NO — inflated!")


asyncio.run(main())
