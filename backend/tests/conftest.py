import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sample_resumes"


@pytest.fixture
def sample_resume_pdf() -> Path:
    path = FIXTURES_DIR / "resume.pdf"
    if not path.exists():
        pytest.skip("Drop your resume PDF at tests/fixtures/sample_resumes/resume.pdf")
    return path


@pytest.fixture
def sample_resume_text() -> str:
    path = FIXTURES_DIR / "resume.txt"
    if not path.exists():
        pytest.skip("Drop a plain-text resume at tests/fixtures/sample_resumes/resume.txt")
    return path.read_text(encoding="utf-8")
