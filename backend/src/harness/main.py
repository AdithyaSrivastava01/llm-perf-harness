import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from harness.config import settings

# ADK reads API keys directly from os.environ
if settings.google_api_key:
    os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

from harness.api.agui import setup_agui_endpoint  # noqa: E402
from harness.api.health import router as health_router  # noqa: E402
from harness.api.mock_agent import router as mock_router  # noqa: E402
from harness.api.quick_eval_routes import router as quick_eval_router  # noqa: E402
from harness.meta_tools.registry import init_registry  # noqa: E402


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
    app.include_router(quick_eval_router)
    app.include_router(mock_router)
    setup_agui_endpoint(app)
    return app


app = create_app()
