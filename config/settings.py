"""
config/settings.py

Typed, validated application settings loaded exclusively from environment
variables (or a .env file in development).  No secret is ever hardcoded.

Usage:
    from config import settings
    token = settings.telegram_bot_token
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration class.

    All fields are loaded from environment variables.
    pydantic-settings will raise a ValidationError at startup if any
    required variable is missing or has an incorrect type — fail fast.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # silently ignore unknown env vars
    )

    # ------------------------------------------------------------------
    # Telegram
    # ------------------------------------------------------------------
    telegram_bot_token: str = Field(
        ...,
        description="Telegram Bot API token from @BotFather.",
    )
    admin_ids: list[int] = Field(
        default_factory=list,
        description="Telegram IDs of admin users authorized to run admin commands.",
    )

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    supabase_url: str = Field(
        ...,
        description="Supabase project URL.",
    )
    supabase_anon_key: str = Field(
        ...,
        description="Supabase anonymous (public) API key.",
    )
    supabase_service_key: str = Field(
        ...,
        description="Supabase service role key (privileged).",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_env: str = Field(
        default="development",
        description="Runtime environment: development | staging | production",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL",
    )
    log_dir: str = Field(
        default="logs",
        description="Directory where rotating log files are written.",
    )

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------
    health_host: str = Field(
        default="0.0.0.0",
        description="Host for the health check HTTP server.",
    )
    health_port: int = Field(
        default=8080,
        description="Port for the health check HTTP server.",
    )

    # ------------------------------------------------------------------
    # Feature Flags
    # ------------------------------------------------------------------
    feature_ai_enabled: bool = Field(
        default=False,
        description="Enable AI assistant features.",
    )
    feature_ocr_enabled: bool = Field(
        default=False,
        description="Enable OCR payment verification.",
    )
    feature_support_enabled: bool = Field(
        default=False,
        description="Enable human support system.",
    )

    # ------------------------------------------------------------------
    # AI Assistant (Gemini)
    # ------------------------------------------------------------------
    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key.",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model name to use for support chat.",
    )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """True when running in the development environment."""
        return self.app_env.lower() == "development"


# Module-level singleton — import this everywhere.
settings = Settings()
