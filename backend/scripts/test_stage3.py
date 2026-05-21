import asyncio
import json
from firstknock.pipeline.parsers.router import parse_file
from firstknock.pipeline.normalization.text_cleaner import clean_text
from firstknock.pipeline.extraction.extractor import extract_resume


async def main():
    with open("tests/fixtures/sample_resumes/resume.pdf", "rb") as f:
        parsed = await parse_file(f.read(), "pdf")

    cleaned = clean_text(parsed["raw_text"])
    result = await extract_resume(cleaned, embedded_links=parsed.get("embedded_links", []))

    print("=== IDENTITY ===")
    print(json.dumps(result.identity.model_dump(), indent=2))

    print("\n=== EXPERIENCE ===")
    for exp in result.experience:
        print(f"  {exp.title} @ {exp.company}")
        print(f"  Dates: {exp.start_date} -> {exp.end_date}  (current: {exp.is_current})")
        print(f"  Tech:  {exp.tech_stack}")
        print()

    print("=== PROJECTS ===")
    for p in result.projects:
        print(f"  {p.name}")
        print(f"  url:        {p.url}")
        print(f"  github_url: {p.github_url}")
        print(f"  Tech: {p.tech_stack}")
        print()

    print("=== SKILLS ===")
    print(json.dumps(result.skills.model_dump(), indent=2))

    print("\n=== EDUCATION ===")
    for e in result.education:
        print(f"  {e.degree} in {e.field} @ {e.institution} ({e.start_year} - {e.end_year})")

    print("\n=== PASS CRITERIA ===")
    print("identity.name correct:  ", result.identity.name == "Aswinthraj Devaraj")
    print("identity.email correct: ", result.identity.email == "iamaswinth@gmail.com")
    print("experience count == 2:  ", len(result.experience) == 2)
    companies = [e.company for e in result.experience]
    print("TechKareer present:     ", any("TechKareer" in c for c in companies))
    print("Praskla present:        ", any("Praskla" in c for c in companies))
    current = [e for e in result.experience if e.is_current]
    print("TechKareer is_current:  ", any("TechKareer" in e.company for e in current))
    print("projects count == 2:    ", len(result.projects) == 2)
    ai_skills = [s.lower() for s in result.skills.ai_ml]
    print("LangGraph in ai_ml:     ", any("langgraph" in s for s in ai_skills))
    print("Google ADK in ai_ml:    ", any("adk" in s for s in ai_skills))


asyncio.run(main())
