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


async def setup_graph_schema() -> None:
    try:
        driver = await get_driver()
        async with driver.session(database="memgraph") as session:
            for query in _INDEXES:
                result = await session.run(query)
                await result.consume()
        logger.info("graph_schema_ready")
    except Exception as exc:
        logger.warning("graph_schema_setup_failed", error=str(exc))
