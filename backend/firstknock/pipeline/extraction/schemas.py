from pydantic import BaseModel, field_validator


class RoleRecommendation(BaseModel):
    title: str
    reason: str


def _null_if_not_url(v: str | None) -> str | None:
    if v and not v.startswith("http"):
        return None
    return v


class Identity(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.title()

    @field_validator("github_url", "linkedin_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        return _null_if_not_url(v)


class ExperienceEntry(BaseModel):
    company: str
    title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: list[str] = []
    tech_stack: list[str] = []


class ProjectEntry(BaseModel):
    name: str
    description: str
    tech_stack: list[str] = []
    url: str | None = None
    github_url: str | None = None

    @field_validator("url", "github_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        return _null_if_not_url(v)


class SkillsBlock(BaseModel):
    languages: list[str] = []
    frameworks: list[str] = []
    ai_ml: list[str] = []
    databases: list[str] = []
    devops: list[str] = []
    other: list[str] = []


class EducationEntry(BaseModel):
    institution: str
    degree: str
    field: str
    start_year: str | None = None
    end_year: str | None = None


class ResumeExtraction(BaseModel):
    identity: Identity
    experience: list[ExperienceEntry] = []
    projects: list[ProjectEntry] = []
    skills: SkillsBlock = SkillsBlock()
    education: list[EducationEntry] = []
    certifications: list[str] = []
    languages_spoken: list[str] = []
    role_recommendations: list[RoleRecommendation] = []
