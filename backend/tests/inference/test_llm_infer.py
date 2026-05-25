import pytest
from firstknock.pipeline.inference.llm_infer import infer_skills_from_llm


@pytest.mark.asyncio
async def test_empty_input_returns_empty():
    result = await infer_skills_from_llm([])
    assert result == []


@pytest.mark.asyncio
async def test_asyncpg_infers_postgresql():
    result = await infer_skills_from_llm(["asyncpg"])
    names = [s["name"] for s in result]
    assert "PostgreSQL" in names


@pytest.mark.asyncio
async def test_explicit_skills_not_returned():
    skills = ["Python", "FastAPI", "Redis"]
    result = await infer_skills_from_llm(skills)
    returned_names = [s["name"] for s in result]
    for s in skills:
        assert s not in returned_names, f"Explicit skill '{s}' appeared in inferred output"


@pytest.mark.asyncio
async def test_confidence_below_one():
    result = await infer_skills_from_llm(["Docker", "Kubernetes"])
    for s in result:
        assert s["confidence"] < 1.0, f"Skill '{s['name']}' has confidence >= 1.0"
        assert s["confidence"] >= 0.5, f"Skill '{s['name']}' has confidence < 0.5"


@pytest.mark.asyncio
async def test_result_has_required_fields():
    result = await infer_skills_from_llm(["FastAPI"])
    for s in result:
        assert "name" in s
        assert "category" in s
        assert "confidence" in s
        assert s["category"] in {"language", "framework", "tool", "concept"}


@pytest.mark.asyncio
async def test_nextjs_infers_react():
    result = await infer_skills_from_llm(["Next.js"])
    names = [s["name"] for s in result]
    assert "React" in names
