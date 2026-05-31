SYSTEM_PROMPT = """You are a precise resume data extractor.
Extract structured data from the resume text exactly as written.
Never infer, hallucinate, or add information not present in the text.
For dates, preserve the raw string exactly as it appears (e.g. "Jan 2026", "Present", "July 2025").
Set is_current=true only when the role end date is "Present" or explicitly ongoing.
For skill names, use the official canonical form: write "React" not "ReactJS", "Next.js" not "nextjs", \
"Kubernetes" not "k8s", "TypeScript" not "TS", "PostgreSQL" not "postgres", "JavaScript" not "JS". \
Strip version numbers from skill names (write "Next.js" not "Next.js 14", "Python" not "Python 3.11").
After extracting all resume fields, derive up to 3 role_recommendations that best describe what roles \
this person is most qualified for. Order them by confidence (highest first). Use specific, \
industry-recognized titles (e.g. "AI/ML Engineer", "Full-Stack Engineer", "MLOps Engineer", \
"Platform Engineer", "Data Engineer"). Base recommendations solely on evidence in the resume — \
skills, experience titles, projects, and seniority signals. Each reason must cite specific \
evidence from the resume in 1-2 sentences."""

EXTRACT_TOOL = {
    "name": "extract_resume",
    "description": "Extract all structured data from a resume into the defined schema.",
    "input_schema": {
        "type": "object",
        "required": ["identity", "experience", "projects", "skills", "education", "certifications", "languages_spoken", "role_recommendations"],
        "properties": {
            "identity": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name":         {"type": "string"},
                    "email":        {"type": ["string", "null"]},
                    "phone":        {"type": ["string", "null"]},
                    "location":     {"type": ["string", "null"]},
                    "headline":     {"type": ["string", "null"]},
                    "github_url":   {"type": ["string", "null"]},
                    "linkedin_url": {"type": ["string", "null"]},
                },
            },
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["company", "title", "is_current"],
                    "properties": {
                        "company":     {"type": "string"},
                        "title":       {"type": "string"},
                        "location":    {"type": ["string", "null"]},
                        "start_date":  {"type": ["string", "null"]},
                        "end_date":    {"type": ["string", "null"]},
                        "is_current":  {"type": "boolean"},
                        "description": {"type": "array", "items": {"type": "string"}},
                        "tech_stack":  {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "description"],
                    "properties": {
                        "name":        {"type": "string"},
                        "description": {"type": "string"},
                        "tech_stack":  {"type": "array", "items": {"type": "string"}},
                        "url":         {"type": ["string", "null"]},
                        "github_url":  {"type": ["string", "null"]},
                    },
                },
            },
            "skills": {
                "type": "object",
                "properties": {
                    "languages":  {"type": "array", "items": {"type": "string"}},
                    "frameworks": {"type": "array", "items": {"type": "string"}},
                    "ai_ml":      {"type": "array", "items": {"type": "string"}},
                    "databases":  {"type": "array", "items": {"type": "string"}},
                    "devops":     {"type": "array", "items": {"type": "string"}},
                    "other":      {"type": "array", "items": {"type": "string"}},
                },
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["institution", "degree", "field"],
                    "properties": {
                        "institution": {"type": "string"},
                        "degree":      {"type": "string"},
                        "field":       {"type": "string"},
                        "start_year":  {"type": ["string", "null"]},
                        "end_year":    {"type": ["string", "null"]},
                    },
                },
            },
            "certifications":   {"type": "array", "items": {"type": "string"}},
            "languages_spoken": {"type": "array", "items": {"type": "string"}},
            "role_recommendations": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["title", "reason"],
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Specific role title that best matches this person's skills and experience",
                        },
                        "reason": {
                            "type": "string",
                            "description": "1-2 sentences citing specific evidence from the resume",
                        },
                    },
                },
            },
        },
    },
}
