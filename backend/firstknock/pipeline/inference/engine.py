import os
import structlog
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import (
    DELETE_STALE_INFERRED_SKILLS,
    GET_EXPLICIT_SKILLS,
    GET_GRAPH_IMPLIED_SKILLS,
    MERGE_INFERRED_HAS_SKILL,
    MERGE_SKILL_IMPLIES,
    ADAMIC_ADAR_CANDIDATES,
)
from firstknock.pipeline.inference.llm_infer import infer_skills_from_llm
from firstknock.pipeline.inference.seniority import write_seniority
from firstknock.config import settings

logger = structlog.get_logger()


def _setup_langsmith() -> None:
    if settings.langchain_tracing_v2.lower() == "true" and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project


class InferenceState(TypedDict):
    user_id: str
    explicit_skills: list[dict]   # [{name, category}]
    graph_implied: list[dict]     # [{name, category, confidence, reason, inferred_from}]
    llm_inferred: list[dict]      # [{name, category, confidence, reason, inferred_from}]
    aa_candidates: list[dict]     # [{name, category, overlap}]
    to_write: list[dict]          # merged final list with source tag
    written_count: int


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def fetch_skills(state: InferenceState) -> InferenceState:
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        result = await session.run(GET_EXPLICIT_SKILLS, person_id=state["user_id"])
        rows = await result.values()
    state["explicit_skills"] = [{"name": r[0], "category": r[1]} for r in rows]
    logger.info("inference_fetch_skills", person_id=state["user_id"], count=len(state["explicit_skills"]))
    return state


async def graph_implies(state: InferenceState) -> InferenceState:
    """Traverse existing SKILL_IMPLIES edges before calling LLM."""
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        result = await session.run(GET_GRAPH_IMPLIED_SKILLS, person_id=state["user_id"])
        rows = await result.values()
    state["graph_implied"] = [
        {
            "inferred_from": r[0],
            "name": r[1],
            "category": r[2],
            "confidence": r[3],
            "reason": r[4],
        }
        for r in rows
    ]
    logger.info("inference_graph_implied", person_id=state["user_id"], count=len(state["graph_implied"]))
    return state


async def llm_infer(state: InferenceState) -> InferenceState:
    already_covered = {s["name"] for s in state["graph_implied"]}
    names = [s["name"] for s in state["explicit_skills"]]
    state["llm_inferred"] = await infer_skills_from_llm(names, skip=already_covered)
    return state


async def adamic_adar(state: InferenceState) -> InferenceState:
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        result = await session.run(
            ADAMIC_ADAR_CANDIDATES,
            person_id=state["user_id"],
            min_overlap=3,
            limit=15,
        )
        rows = await result.values()
    state["aa_candidates"] = [{"name": r[0], "category": r[1], "overlap": r[2]} for r in rows]
    logger.info("inference_adamic_adar", person_id=state["user_id"], candidates=len(state["aa_candidates"]))
    return state


async def merge_and_filter(state: InferenceState) -> InferenceState:
    explicit_names = {s["name"] for s in state["explicit_skills"]}
    seen: set[str] = set()
    to_write: list[dict] = []

    # graph_implied first — highest quality (already validated by prior LLM calls)
    for s in state["graph_implied"]:
        if s["name"] not in explicit_names and s["name"] not in seen:
            seen.add(s["name"])
            to_write.append({**s, "source": "graph_implied"})

    for s in state["llm_inferred"]:
        if not s.get("inferred_from"):
            continue
        if s["name"] not in explicit_names and s["name"] not in seen:
            seen.add(s["name"])
            to_write.append({**s, "source": "llm"})

    for c in state["aa_candidates"]:
        if c["name"] not in explicit_names and c["name"] not in seen:
            seen.add(c["name"])
            to_write.append({
                "name": c["name"],
                "category": c["category"],
                "confidence": round(min(0.5, c["overlap"] / 10.0), 2),
                "inferred_from": "",
                "reason": "",
                "source": "adamic_adar",
            })

    state["to_write"] = to_write
    return state


async def write_inferred(state: InferenceState) -> InferenceState:
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        await session.run(DELETE_STALE_INFERRED_SKILLS, person_id=state["user_id"])
        for skill in state["to_write"]:
            await session.run(
                MERGE_INFERRED_HAS_SKILL,
                person_id=state["user_id"],
                name=skill["name"],
                category=skill["category"],
                confidence=skill["confidence"],
                inferred_by=skill.get("inferred_from", ""),
                reason=skill.get("reason", ""),
            )
            # Write SKILL_IMPLIES only for LLM-sourced inferences with a traceable source skill
            if skill.get("source") == "llm" and skill.get("inferred_from"):
                await session.run(
                    MERGE_SKILL_IMPLIES,
                    source_skill=skill["inferred_from"],
                    implied_skill=skill["name"],
                    confidence=skill["confidence"],
                    reason=skill.get("reason", ""),
                )
    state["written_count"] = len(state["to_write"])
    logger.info("inference_written", person_id=state["user_id"], count=state["written_count"])
    return state


async def write_seniority_node(state: InferenceState) -> InferenceState:
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        await write_seniority(session, state["user_id"])
    return state


# ── Conditional edge ──────────────────────────────────────────────────────────

def _has_skills(state: InferenceState) -> str:
    return "continue" if state["explicit_skills"] else "skip"


# ── Graph ─────────────────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(InferenceState)

    g.add_node("fetch_skills",     fetch_skills)
    g.add_node("graph_implies",    graph_implies)
    g.add_node("llm_infer",        llm_infer)
    g.add_node("adamic_adar",      adamic_adar)
    g.add_node("merge_and_filter", merge_and_filter)
    g.add_node("write_inferred",   write_inferred)
    g.add_node("write_seniority",  write_seniority_node)

    g.add_edge(START, "fetch_skills")
    g.add_conditional_edges(
        "fetch_skills",
        _has_skills,
        {"continue": "graph_implies", "skip": END},
    )
    g.add_edge("graph_implies",    "llm_infer")
    g.add_edge("llm_infer",        "adamic_adar")
    g.add_edge("adamic_adar",      "merge_and_filter")
    g.add_edge("merge_and_filter", "write_inferred")
    g.add_edge("write_inferred",   "write_seniority")
    g.add_edge("write_seniority",  END)

    return g.compile()


_graph = _build_graph()


async def run_inference(user_id: str) -> int:
    """Run the full inference pipeline for one person. Returns count of inferred edges written."""
    _setup_langsmith()

    initial: InferenceState = {
        "user_id": user_id,
        "explicit_skills": [],
        "graph_implied": [],
        "llm_inferred": [],
        "aa_candidates": [],
        "to_write": [],
        "written_count": 0,
    }

    final = await _graph.ainvoke(initial)
    return final["written_count"]
