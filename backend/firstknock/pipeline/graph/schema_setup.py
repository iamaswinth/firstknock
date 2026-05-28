import structlog
from .client import get_driver

logger = structlog.get_logger()

_INDEXES = [
    "CREATE INDEX ON :Person(person_id);",
    "CREATE INDEX ON :Skill(name);",
    "CREATE INDEX ON :Company(name);",
    "CREATE INDEX ON :Project(project_id);",
    "CREATE INDEX ON :Institution(name);",
]

_VECTOR_INDEXES = [
    (
        "person_embedding",
        """CALL vector_index.create("person_embedding", "Person", "embedding", """
        """{"dimension": 1536, "capacity": 1000, "metric": "cos"})""",
    ),
    (
        "project_embedding",
        """CALL vector_index.create("project_embedding", "Project", "embedding", """
        """{"dimension": 1536, "capacity": 5000, "metric": "cos"})""",
    ),
]


async def setup_graph_schema() -> None:
    try:
        driver = await get_driver()
        async with driver.session(database="memgraph") as session:
            for query in _INDEXES:
                result = await session.run(query)
                await result.consume()

            for name, query in _VECTOR_INDEXES:
                try:
                    result = await session.run(query)
                    await result.consume()
                    logger.info("vector_index_created", index=name)
                except Exception as exc:
                    # Memgraph raises if index already exists — safe to ignore
                    logger.debug("vector_index_skipped", index=name, reason=str(exc))

        logger.info("graph_schema_ready")
    except Exception as exc:
        logger.warning("graph_schema_setup_failed", error=str(exc))
