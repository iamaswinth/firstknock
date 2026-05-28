import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from firstknock.api.schemas import (
    GraphResponse, GraphNode, GraphLink, GraphCommunity,
    AnalyticsResponse, CareerEntry, BridgeSkill, InferredSkillDetail, SkillCommunity,
)
from firstknock.pipeline.graph.client import get_driver
from firstknock.pipeline.graph.queries import (
    GET_EGO_GRAPH,
    GET_ALL_SKILLS,
    GET_PERSON_SKILL_COOCCURRENCE,
    GET_INFERRED_SKILLS_DETAIL,
    GET_PERSON_NODE,
)
from firstknock.pipeline.persistence.db import get_session
from firstknock.pipeline.persistence.models import Resume, User
import uuid

router = APIRouter(tags=["graph"])
logger = structlog.get_logger()

# Palette for up to 10 communities
_COMMUNITY_COLORS = [
    "#7C3AED", "#0EA5E9", "#10B981", "#F59E0B",
    "#EF4444", "#EC4899", "#6366F1", "#14B8A6",
    "#F97316", "#84CC16",
]


def _community_name(skills: list[str]) -> str:
    return " + ".join(skills[:2]) if skills else "Misc"


# ── /graph/{user_id} ─────────────────────────────────────────────────────────

@router.get("/graph/{user_id}", response_model=GraphResponse)
async def get_graph(user_id: str):
    try:
        driver = await get_driver()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Graph database unavailable")

    # ── Ego graph edges + nodes ───────────────────────────────────────────────
    nodes: dict[str, GraphNode] = {}
    links: list[GraphLink] = []

    try:
        async with driver.session(database="memgraph") as session:
            # All HAS_SKILL rows with confidence/source
            skill_r = await session.run(GET_ALL_SKILLS, person_id=user_id)
            skill_rows = await skill_r.values()

            # Raw ego graph (person + direct neighbors + project skills)
            ego_r = await session.run(GET_EGO_GRAPH, person_id=user_id)
            ego_rows = await ego_r.data()

            # CO_OCCURS_WITH between this person's skills
            co_r = await session.run(GET_PERSON_SKILL_COOCCURRENCE, person_id=user_id)
            co_rows = await co_r.values()

            # Person node props
            pnode_r = await session.run(GET_PERSON_NODE, person_id=user_id)
            pnode = await pnode_r.single()
    except Exception as exc:
        logger.warning("graph_fetch_failed", user_id=user_id, error=str(exc))
        raise HTTPException(status_code=503, detail="Graph query failed")

    if not skill_rows and not ego_rows:
        raise HTTPException(status_code=404, detail="No graph data found for this user")

    # ── Build skill confidence + source map ───────────────────────────────────
    skill_meta: dict[str, dict] = {}
    for name, category, source, confidence, inferred_by, reason in skill_rows:
        skill_meta[name] = {
            "category": category or "concept",
            "source": source or "explicit",
            "confidence": float(confidence) if confidence is not None else 1.0,
        }

    # ── Person node ───────────────────────────────────────────────────────────
    nodes[user_id] = GraphNode(
        id=user_id,
        name="",  # filled below from ego_rows
        type="Person",
        val=20,
        properties=dict(pnode) if pnode else {},
    )

    # ── Parse ego graph rows ──────────────────────────────────────────────────
    # Use named access (row is a dict from .data()) to avoid Memgraph UNION
    # column ordering issues — driver may sort aliases alphabetically.
    for row in ego_rows:
        src_labels = row.get('src_labels') or []
        src_props  = row.get('src_props')  or {}
        rel_type   = row.get('rel_type', '')
        rel_props  = row.get('rel_props')  or {}
        tgt_labels = row.get('tgt_labels') or []
        tgt_props  = row.get('tgt_props')  or {}

        src_type = _node_type_from_labels(src_labels)
        src_id   = _node_id(src_props, src_type)

        if src_id not in nodes:
            nodes[src_id] = _make_node(src_id, src_props, src_type, skill_meta)
        elif src_type == "Person" and src_props.get("name"):
            nodes[src_id].name = src_props["name"]

        tgt_type = _node_type_from_labels(tgt_labels)
        tgt_id   = _node_id(tgt_props, tgt_type)
        if tgt_id not in nodes:
            nodes[tgt_id] = _make_node(tgt_id, tgt_props, tgt_type, skill_meta)

        link = GraphLink(
            source=src_id,
            target=tgt_id,
            type=rel_type,
            confidence=float(rel_props.get("confidence", 0)) if "confidence" in rel_props else None,
            source_type=rel_props.get("source"),
            properties={k: v for k, v in rel_props.items() if k not in ("confidence", "source")},
        )
        links.append(link)

    # ── CO_OCCURS_WITH links (between person's skills only) ───────────────────
    seen_co: set[frozenset] = set()
    for skill1, skill2, co_occ in co_rows:
        pair = frozenset([skill1, skill2])
        if pair in seen_co:
            continue
        seen_co.add(pair)
        links.append(GraphLink(
            source=f"skill-{skill1}",
            target=f"skill-{skill2}",
            type="CO_OCCURS_WITH",
            co_occurrence=int(co_occ) if co_occ else 0,
        ))

    # ── Louvain communities ───────────────────────────────────────────────────
    communities: list[GraphCommunity] = []
    try:
        async with driver.session(database="memgraph") as session:
            # Run Louvain on the full CO_OCCURS_WITH subgraph
            r = await session.run("""
                CALL community_detection.get()
                YIELD node, community_id
                WITH node.name AS name, community_id
                MATCH (p:Person {person_id: $person_id})-[:HAS_SKILL]->(s:Skill {name: name})
                RETURN name, community_id
            """, person_id=user_id)
            comm_rows = await r.values()

        community_map: dict[int, list[str]] = {}
        for skill_name, cid in comm_rows:
            cid = int(cid)
            community_map.setdefault(cid, []).append(skill_name)
            # Tag skill node with community_id
            node_id = f"skill-{skill_name}"
            if node_id in nodes:
                nodes[node_id].community_id = cid

        for i, (cid, skills) in enumerate(community_map.items()):
            communities.append(GraphCommunity(
                id=cid,
                name=_community_name(skills),
                color=_COMMUNITY_COLORS[i % len(_COMMUNITY_COLORS)],
                skills=skills,
            ))
    except Exception as exc:
        logger.debug("louvain_unavailable", error=str(exc))

    return GraphResponse(nodes=list(nodes.values()), links=links, communities=communities)


# ── /analytics/{user_id} ─────────────────────────────────────────────────────

@router.get("/analytics/{user_id}", response_model=AnalyticsResponse)
async def get_analytics(user_id: str):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # ── Career timeline from Postgres ─────────────────────────────────────────
    career_timeline: list[CareerEntry] = []
    async with get_session() as session:
        result = await session.execute(
            select(Resume, User)
            .join(User, Resume.user_id == User.user_id)
            .where(Resume.user_id == uid)
            .order_by(Resume.ingested_at.desc())
            .limit(1)
        )
        row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    resume, _ = row
    extracted = resume.extracted_json or {}
    for exp in extracted.get("experience", []):
        career_timeline.append(CareerEntry(
            company=exp.get("company", ""),
            title=exp.get("title", ""),
            start_date=exp.get("start_date"),
            end_date=exp.get("end_date"),
            months=exp.get("months"),
            is_current=exp.get("is_current", False),
        ))

    # ── Memgraph: seniority + inferred skills + MAGE analytics ───────────────
    seniority = total_months = None
    inferred_skills: list[InferredSkillDetail] = []
    skill_communities: list[SkillCommunity] | None = None
    bridge_skills: list[BridgeSkill] | None = None

    try:
        driver = await get_driver()

        async with driver.session(database="memgraph") as session:
            # Seniority
            pnode_r = await session.run(GET_PERSON_NODE, person_id=user_id)
            pnode = await pnode_r.single()
            if pnode:
                seniority = pnode["seniority"]
                total_months = pnode["total_months"]

            # Inferred skills with explanation
            inf_r = await session.run(GET_INFERRED_SKILLS_DETAIL, person_id=user_id)
            inf_rows = await inf_r.values()
            for name, category, source, confidence, inferred_by, reason in inf_rows:
                inferred_skills.append(InferredSkillDetail(
                    name=name or "",
                    category=category or "concept",
                    source=source or "inferred",
                    confidence=float(confidence) if confidence is not None else 0.5,
                    inferred_by=inferred_by,
                    reason=reason,
                ))

        # ── Louvain communities ───────────────────────────────────────────────
        try:
            async with driver.session(database="memgraph") as session:
                r = await session.run("""
                    CALL community_detection.get()
                    YIELD node, community_id
                    WITH node.name AS name, community_id
                    MATCH (p:Person {person_id: $person_id})-[:HAS_SKILL]->(s:Skill {name: name})
                    RETURN name, community_id
                    ORDER BY community_id
                """, person_id=user_id)
                comm_rows = await r.values()

            community_map: dict[int, list[str]] = {}
            for skill_name, cid in comm_rows:
                community_map.setdefault(int(cid), []).append(skill_name)

            skill_communities = [
                SkillCommunity(id=cid, name=_community_name(skills), skills=skills)
                for cid, skills in community_map.items()
            ]
        except Exception as exc:
            logger.debug("louvain_unavailable", error=str(exc))

        # ── Betweenness centrality ────────────────────────────────────────────
        try:
            async with driver.session(database="memgraph") as session:
                r = await session.run("""
                    CALL betweenness_centrality.get()
                    YIELD node, betweenness_centrality
                    WITH node.name AS name, node.category AS category,
                         betweenness_centrality
                    MATCH (p:Person {person_id: $person_id})-[:HAS_SKILL]->(s:Skill {name: name})
                    RETURN name, category, betweenness_centrality
                    ORDER BY betweenness_centrality DESC
                    LIMIT 5
                """, person_id=user_id)
                bc_rows = await r.values()

            bridge_skills = [
                BridgeSkill(
                    name=name,
                    centrality=round(float(bc), 4),
                    category=cat,
                )
                for name, cat, bc in bc_rows
            ]
        except Exception as exc:
            logger.debug("betweenness_unavailable", error=str(exc))

    except Exception as exc:
        logger.warning("analytics_graph_failed", user_id=user_id, error=str(exc))

    return AnalyticsResponse(
        user_id=user_id,
        seniority=seniority,
        total_experience_months=total_months,
        career_timeline=career_timeline,
        skill_communities=skill_communities,
        bridge_skills=bridge_skills,
        inferred_skills=inferred_skills,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _node_type_from_labels(labels: list[str]) -> str:
    for t in ("Person", "Skill", "Company", "Project", "Institution"):
        if t in labels:
            return t
    return "Unknown"


def _node_id(node: dict, node_type: str) -> str:
    if node_type == "Person":
        return str(node.get("person_id", ""))
    if node_type == "Project":
        return str(node.get("project_id", ""))
    if node_type == "Skill":
        return f"skill-{node.get('name', '')}"
    if node_type == "Company":
        return f"company-{node.get('name', '')}"
    if node_type == "Institution":
        return f"inst-{node.get('name', '')}"
    return str(node.get("name", "unknown"))


def _make_node(node_id: str, node: dict, node_type: str, skill_meta: dict) -> GraphNode:
    name = node.get("name", node_id)
    val = 5.0
    confidence = None
    source_type = None

    if node_type == "Person":
        val = 20.0
        name = node.get("name", "")
    elif node_type == "Skill":
        meta = skill_meta.get(name, {})
        confidence = meta.get("confidence", 1.0)
        source_type = meta.get("source", "explicit")
        # Size: explicit=10, inferred=5, graph_algo=3
        val = 10.0 if source_type == "explicit" else (5.0 if source_type == "inferred" else 3.0)
    elif node_type in ("Company", "Project"):
        val = 8.0
    elif node_type == "Institution":
        val = 6.0

    return GraphNode(
        id=node_id,
        name=name,
        type=node_type,
        val=val,
        confidence=confidence,
        source_type=source_type,
        properties={k: v for k, v in node.items() if k not in ("name", "person_id", "project_id")},
    )
