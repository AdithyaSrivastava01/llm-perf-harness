from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API keys — no prefix, read directly as GOOGLE_API_KEY / OPENAI_API_KEY
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # App settings — prefixed with HARNESS_
    database_url: str = Field(
        default="sqlite+aiosqlite:///./dev.db", alias="HARNESS_DATABASE_URL"
    )
    jwt_secret: str = Field(default="dev-secret-change-me", alias="HARNESS_JWT_SECRET")
    otel_endpoint: str = Field(default="", alias="HARNESS_OTEL_ENDPOINT")
    environment: str = Field(default="development", alias="HARNESS_ENVIRONMENT")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], alias="HARNESS_CORS_ORIGINS"
    )


settings = Settings()
