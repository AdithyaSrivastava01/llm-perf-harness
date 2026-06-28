from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from harness.api.health import router as health_router
from harness.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Agent-Evals Meta-Harness")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    return app


app = create_app()
