from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "ApplyWise AI"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://applywise:applywise@localhost:5432/applywise"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    scheduler_enabled: bool = False
    auth_secret_key: str = "applywise-local-auth-secret-change-me"
    auth_session_cookie_name: str = "applywise_session"
    auth_session_days: int = 7
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    google_integration_redirect_uri: str = "http://localhost:8000/api/integrations/google/callback"
    google_drive_service_account_file: str = ""
    google_drive_service_account_json: str = ""
    google_drive_folder_id: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
