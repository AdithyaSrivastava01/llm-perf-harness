from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from harness.api.agui import setup_agui_endpoint
from harness.api.health import router as health_router
from harness.config import settings
from harness.meta_tools.registry import init_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_registry()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Agent-Evals Meta-Harness", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    setup_agui_endpoint(app)
    return app


app = create_app()
