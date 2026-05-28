from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from firstknock.pipeline.graph.client import close_driver
from firstknock.pipeline.graph.schema_setup import setup_graph_schema
from firstknock.api.routes.ingest import router as ingest_router
from firstknock.api.routes.health import router as health_router
from firstknock.api.routes.profile import router as profile_router
from firstknock.api.routes.skills import router as skills_router
from firstknock.api.routes.graph import router as graph_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_graph_schema()
    yield
    await close_driver()


app = FastAPI(title="FirstKnock", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(health_router)
app.include_router(profile_router)
app.include_router(skills_router)
app.include_router(graph_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
