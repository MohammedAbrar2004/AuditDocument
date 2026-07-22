from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import checklists, documents
from app.state import app_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loaded once here, never per request (v2_phase5.md SS4): BGE-M3 (2.2GB,
    # GPU) and the checklist-persistent scope (parsed items + item
    # embeddings for both checklists, Phase 3's output).
    app_state.load()
    yield


app = FastAPI(title="Audit Evidence Mapping API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(checklists.router)


@app.get("/health")
def health():
    return {"status": "ok"}
