"""Tests for the shared configuration module."""

from __future__ import annotations

import os

import pytest

from services.shared.config import (
    DatabaseSettings,
    KafkaSettings,
    LLMSettings,
    RedisSettings,
    Settings,
    get_settings,
)


class TestSettings:
    """Tests for the root Settings class."""

    def test_default_settings_load(self):
        """Settings can be instantiated with defaults."""
        settings = Settings()
        assert settings.app_name == "sentinel-ai"
        assert settings.app_env in ("development", "staging", "production", "test")
        assert settings.app_debug is True

    def test_settings_singleton(self):
        """get_settings() returns the same instance on repeated calls."""
        # Reset cache for clean test
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_database_settings_defaults(self):
        """DatabaseSettings has sensible defaults."""
        db = DatabaseSettings()
        assert "postgresql" in db.url
        assert db.pool_size > 0
        assert db.max_overflow >= 0

    def test_redis_settings_defaults(self):
        """RedisSettings has sensible defaults."""
        redis = RedisSettings()
        assert "redis://" in redis.url
        assert redis.max_connections > 0

    def test_kafka_settings_topics(self):
        """KafkaSettings generates topic names."""
        kafka = KafkaSettings()
        assert kafka.topic_incidents_created == "incidents.created"
        assert kafka.topic_deployments_failed == "deployments.failed"
        assert kafka.topic_ai_analysis_started == "ai.analysis.started"

    def test_llm_settings_simulation_mode(self):
        """LLM settings correctly detect simulation mode when no keys set."""
        llm = LLMSettings(openai_api_key="", anthropic_api_key="")
        assert llm.is_simulation is True
        assert llm.provider == "simulation"

    def test_llm_settings_openai_provider(self):
        """LLM settings detect OpenAI when API key is set."""
        llm = LLMSettings(openai_api_key="test-key", anthropic_api_key="")
        assert llm.is_simulation is False
        assert llm.provider == "openai"

    def test_llm_settings_anthropic_provider(self):
        """LLM settings detect Anthropic when API key is set."""
        llm = LLMSettings(openai_api_key="", anthropic_api_key="test-key")
        assert llm.is_simulation is False
        assert llm.provider == "anthropic"


class TestEnvValidation:
    """Tests for environment validation."""

    def test_valid_env_value(self):
        """Valid APP_ENV values are accepted."""
        settings = Settings(app_env="production")
        assert settings.app_env == "production"

    def test_invalid_env_value_raises(self):
        """Invalid APP_ENV values raise ValueError."""
        with pytest.raises(Exception):
            Settings(app_env="invalid_env")
