import asyncio
from firstknock.pipeline.persistence.postgres_writer import (
    get_or_create_user,
    save_extracted_resume,
    get_latest_resume_for_user,
)

SAMPLE_JSON = {
    "identity": {
        "name": "Aswinthraj Devaraj",
        "email": "iamaswinth@gmail.com",
        "phone": "6369585965",
        "location": "Tirupur, TamilNadu",
        "headline": "Full Stack AI Engineer",
        "github_url": "https://github.com/iamaswinth",
        "linkedin_url": "https://www.linkedin.com/in/aswinthraj-d-362a18291/",
    },
    "experience": [
        {
            "company": "TechKareer",
            "title": "Software Engineering Intern",
            "start_date": "Jan 2026",
            "end_date": "Present",
            "is_current": True,
            "tech_stack": ["Google ADK", "Next.js", "FastAPI", "LangGraph"],
        },
        {
            "company": "Praskla Technology",
            "title": "Software Engineering Intern",
            "start_date": "July 2025",
            "end_date": "Dec 2025",
            "is_current": False,
            "tech_stack": ["Electron", "React", "AWS RDS"],
        },
    ],
    "skills": {
        "languages": ["Python", "JavaScript", "SQL"],
        "frameworks": ["Next.js", "React", "FastAPI"],
        "ai_ml": ["LangGraph", "Google ADK", "Gemini Live API", "RAG"],
        "databases": ["NeonDB", "Pinecone", "PostgreSQL"],
        "devops": ["Docker", "GitHub Actions", "Azure"],
        "other": ["Blender"],
    },
}


async def main():
    print("=== PART 1: WRITE ===")
    user_id, resume_id = await save_extracted_resume(
        user_email="iamaswinth@gmail.com",
        source_type="pdf",
        raw_text="ASWINTHRAJ DEVARAJ iamaswinth@gmail.com ...",
        extracted_json=SAMPLE_JSON,
    )
    print("user_id:   ", user_id)
    print("resume_id: ", resume_id)

    print()
    print("=== PART 2: READ BACK ===")
    row = await get_latest_resume_for_user("iamaswinth@gmail.com")
    print("resume_id:          ", row.resume_id)
    print("status:             ", row.status)
    print("source_type:        ", row.source_type)
    print("extracted_json set: ", row.extracted_json is not None)
    print("name in JSON:       ", row.extracted_json["identity"]["name"])

    print()
    print("=== PART 3: UPSERT CHECK ===")
    user_id_2 = await get_or_create_user("iamaswinth@gmail.com")
    print("Same user_id on second call:", user_id == user_id_2)

    print()
    print("=== PASS CRITERIA ===")
    checks = [
        ("user_id returned",              user_id is not None),
        ("resume_id returned",            resume_id is not None),
        ("status = extracted",            row.status == "extracted"),
        ("extracted_json not null",       row.extracted_json is not None),
        ("name correct",                  row.extracted_json["identity"]["name"] == "Aswinthraj Devaraj"),
        ("upsert idempotent",             user_id == user_id_2),
    ]
    for label, passed in checks:
        print(f"  {'OK' if passed else 'FAIL'}  {label}")


asyncio.run(main())
