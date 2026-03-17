"""FastAPI entrypoint for routing optimization Stage 2."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import planning

app = FastAPI(
    title="Routing Optimization API",
    description="Stage 2 planning API backed by real routing solver",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(planning.router, prefix="/api/planning", tags=["Planning"])


@app.get("/")
async def root() -> dict:
    return {
        "service": "Routing Optimization API",
        "version": "2.0.0",
        "docs": "/api/docs",
    }


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "healthy"}
