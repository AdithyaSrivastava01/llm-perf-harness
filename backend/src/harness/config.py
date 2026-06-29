from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "HARNESS_"}

    google_api_key: str = ""
    openai_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "dev-secret-change-me"
    otel_endpoint: str = ""
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]
    encryption_key: str = Field(
        default="dev-encryption-key-change-in-prod-32b=", alias="HARNESS_ENCRYPTION_KEY"
    )


settings = Settings()
