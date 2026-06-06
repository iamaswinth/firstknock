import os
import structlog
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import (
    MERGE_SKILL_IMPLIES,
    GET_GRAPH_IMPLIED_SKILLS_BY_NAMES,
    ADAMIC_ADAR_CANDIDATES_BY_NAMES,
)
from firstknock.pipeline.inference.llm_infer import infer_skills_from_llm
from firstknock.config import settings

logger = structlog.get_logger()


def _setup_langsmith() -> None:
    if settings.langchain_tracing_v2.lower() == "true" and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project


class InferenceState(TypedDict):
    user_id: str
    explicit_skills: list[dict]   # [{name, category}] — seeded by caller from extracted_json
    graph_implied: list[dict]     # [{name, category, confidence, reason, inferred_from}]
    llm_inferred: list[dict]      # [{name, category, confidence, reason, inferred_from}]
    aa_candidates: list[dict]     # [{name, category, overlap}]
    to_write: list[dict]          # merged final list with source tag
    inferred_result: dict         # assembled result saved to Postgres


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def seed_skills(state: InferenceState) -> InferenceState:
    """No-op: explicit_skills already seeded by caller from extracted_json."""
    logger.info("inference_seed_skills", person_id=state["user_id"], count=len(state["explicit_skills"]))
    return state


async def graph_implies(state: InferenceState) -> InferenceState:
    """Traverse SKILL_IMPLIES edges from known skill names — no Person node needed."""
    skill_names = [s["name"] for s in state["explicit_skills"]]
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        result = await session.run(GET_GRAPH_IMPLIED_SKILLS_BY_NAMES, skill_names=skill_names)
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
    """Co-occurrence candidates via Skill→CO_OCCURS_WITH→Skill traversal."""
    skill_names = [s["name"] for s in state["explicit_skills"]]
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        result = await session.run(
            ADAMIC_ADAR_CANDIDATES_BY_NAMES,
            skill_names=skill_names,
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
    """Write only global SKILL_IMPLIES edges to Memgraph. Per-person inferred skills go to Postgres via build_result."""
    driver = await get_driver()
    async with driver.session(database="memgraph") as session:
        for skill in state["to_write"]:
            if skill.get("source") == "llm" and skill.get("inferred_from"):
                await session.run(
                    MERGE_SKILL_IMPLIES,
                    source_skill=skill["inferred_from"],
                    implied_skill=skill["name"],
                    confidence=skill["confidence"],
                    reason=skill.get("reason", ""),
                )
    implies_count = sum(1 for s in state["to_write"] if s.get("source") == "llm" and s.get("inferred_from"))
    logger.info("inference_skill_implies_written", person_id=state["user_id"], count=implies_count)
    return state


async def build_result(state: InferenceState) -> InferenceState:
    """Assemble inferred_result dict to be saved to Postgres by the orchestrator."""
    state["inferred_result"] = {
        "skills": [
            {
                "name": s["name"],
                "category": s["category"],
                "confidence": s["confidence"],
                "source": s.get("source", ""),
                "inferred_by": s.get("inferred_from", ""),
                "reason": s.get("reason", ""),
            }
            for s in state["to_write"]
        ]
    }
    logger.info("inference_result_built", person_id=state["user_id"], count=len(state["inferred_result"]["skills"]))
    return state


# ── Conditional edge ──────────────────────────────────────────────────────────

def _has_skills(state: InferenceState) -> str:
    return "continue" if state["explicit_skills"] else "skip"


# ── Graph ─────────────────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(InferenceState)

    g.add_node("seed_skills",      seed_skills)
    g.add_node("graph_implies",    graph_implies)
    g.add_node("llm_infer",        llm_infer)
    g.add_node("adamic_adar",      adamic_adar)
    g.add_node("merge_and_filter", merge_and_filter)
    g.add_node("write_inferred",   write_inferred)
    g.add_node("build_result",     build_result)

    g.add_edge(START, "seed_skills")
    g.add_conditional_edges(
        "seed_skills",
        _has_skills,
        {"continue": "graph_implies", "skip": END},
    )
    g.add_edge("graph_implies",    "llm_infer")
    g.add_edge("llm_infer",        "adamic_adar")
    g.add_edge("adamic_adar",      "merge_and_filter")
    g.add_edge("merge_and_filter", "write_inferred")
    g.add_edge("write_inferred",   "build_result")
    g.add_edge("build_result",     END)

    return g.compile()


_graph = _build_graph()


async def run_inference(user_id: str, explicit_skills: list[dict]) -> dict:
    """
    Run the full inference pipeline for one person.

    explicit_skills: [{name, category}] from extracted_json — passed directly so
    the current user's graph need not be written before inference runs.

    Returns inferred_result dict for saving to Postgres.
    """
    _setup_langsmith()

    initial: InferenceState = {
        "user_id": user_id,
        "explicit_skills": explicit_skills,
        "graph_implied": [],
        "llm_inferred": [],
        "aa_candidates": [],
        "to_write": [],
        "inferred_result": {},
    }

    final = await _graph.ainvoke(initial)
    return final["inferred_result"]
