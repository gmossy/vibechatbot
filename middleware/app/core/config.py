import os
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent Chatbot Middleware"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    
    # Environment configs
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

    # If set, all /v1 routes that depend on get_current_user require
    # Authorization: Bearer <API_KEY> (match OpenWebUI OPENAI_API_KEY).
    API_KEY: str | None = None
    PUBLIC_BASE_URL: str = ""

    # Comma-separated browser Origins (e.g. OpenWebUI). Use "*" alone to allow any origin;
    # in that case allow_credentials is forced False (browser requirement).
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
    )

    # Logfire Configuration
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_PROJECT_NAME: str = "vibechatbot"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()


def build_cors_middleware_args() -> dict:
    """Safe CORS: do not combine allow_origins=['*'] with allow_credentials=True."""
    default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    raw = (settings.CORS_ORIGINS or "").strip()
    if not raw:
        origins = default_origins
        allow_credentials = True
    else:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) == 1 and parts[0] == "*":
            origins = ["*"]
            allow_credentials = False
        else:
            origins = [p for p in parts if p != "*"] or default_origins
            allow_credentials = True
    return {
        "allow_origins": origins,
        "allow_credentials": allow_credentials,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
