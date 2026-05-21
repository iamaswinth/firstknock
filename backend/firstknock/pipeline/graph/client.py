from neo4j import AsyncGraphDatabase, AsyncDriver
from firstknock.config import settings

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        auth = (settings.memgraph_user, settings.memgraph_password) if settings.memgraph_user else ("", "")
        _driver = AsyncGraphDatabase.driver(settings.memgraph_url, auth=auth)
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
