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
    # OCR Payment Verification (Sprint 7)
    # ------------------------------------------------------------------
    ocr_receiver_name: str = Field(
        default="",
        description="Your merchant/bank account name shown on payment receipts. "
                    "Must match what appears in the screenshot (e.g. 'Rohit Kumar').",
    )
    ocr_upi_id: str = Field(
        default="",
        description="Your UPI ID (e.g. rohit@upi). Used as a soft check on receipts.",
    )
    ocr_auto_approve_threshold: float = Field(
        default=0.90,
        description="Confidence score (0.0-1.0) at or above which payments are "
                    "auto-approved without admin review.",
    )
    ocr_time_freshness_minutes: int = Field(
        default=30,
        description="Max minutes between screenshot time and current time for "
                    "the time-freshness bonus check.",
    )
    ocr_time_hard_block_hours: int = Field(
        default=2,
        description="Screenshots older than this many hours are hard-blocked "
                    "and always routed to manual review.",
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
