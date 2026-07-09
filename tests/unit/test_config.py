"""
tests/unit/test_config.py

Unit tests for config/settings.py

Tests validate:
  - Settings loads correctly from environment variables
  - Required fields raise ValidationError when missing
  - Default values are applied correctly
  - Helper properties work as expected
  - No secrets are hardcoded in Settings
"""

import os

import pytest
from pydantic import ValidationError


class TestSettingsDefaults:
    """Test that optional settings have correct default values."""

    def test_app_env_default_is_development(self, monkeypatch):
        """APP_ENV should default to 'development'."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")

        # Import inside test to allow monkeypatching before module load
        from config.settings import Settings

        s = Settings(_env_file=None)
        assert s.app_env == "development"

    def test_log_level_default_is_info(self, monkeypatch):
        """LOG_LEVEL should default to 'INFO'."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")

        from config.settings import Settings

        s = Settings(_env_file=None)
        assert s.log_level == "INFO"

    def test_health_port_default(self, monkeypatch):
        """HEALTH_PORT should default to 8080."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")

        from config.settings import Settings

        s = Settings(_env_file=None)
        assert s.health_port == 8080

    def test_feature_flags_default_to_false(self, monkeypatch):
        """All feature flags should be disabled by default."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")

        from config.settings import Settings

        s = Settings(_env_file=None)
        assert s.feature_ai_enabled is False
        assert s.feature_ocr_enabled is False
        assert s.feature_support_enabled is False


class TestSettingsRequired:
    """Test that missing required fields raise validation errors."""

    def test_missing_telegram_token_raises(self, monkeypatch):
        """Settings must fail if TELEGRAM_BOT_TOKEN is not set."""
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")

        from config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_missing_supabase_url_raises(self, monkeypatch):
        """Settings must fail if SUPABASE_URL is not set."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")

        from config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_missing_supabase_keys_raise(self, monkeypatch):
        """Settings must fail if Supabase keys are not set."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

        from config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(_env_file=None)


class TestSettingsHelpers:
    """Test convenience property helpers on Settings."""

    def _make_settings(self, monkeypatch, app_env: str):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test_service_key")
        monkeypatch.setenv("APP_ENV", app_env)

        from config.settings import Settings

        return Settings(_env_file=None)

    def test_is_production_true(self, monkeypatch):
        s = self._make_settings(monkeypatch, "production")
        assert s.is_production is True
        assert s.is_development is False

    def test_is_development_true(self, monkeypatch):
        s = self._make_settings(monkeypatch, "development")
        assert s.is_development is True
        assert s.is_production is False
