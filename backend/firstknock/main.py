from contextlib import asynccontextmanager
from fastapi import FastAPI
from firstknock.pipeline.graph.client import close_driver
from firstknock.pipeline.graph.schema_setup import setup_graph_schema
from firstknock.api.routes.ingest import router as ingest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_graph_schema()
    yield
    await close_driver()


app = FastAPI(title="FirstKnock", lifespan=lifespan)
app.include_router(ingest_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
