"""Centralized configuration using Pydantic Settings.

All environment variables are loaded here and validated at startup.
Access via `settings = get_settings()` or dependency injection.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL configuration."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel"
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"
    max_connections: int = 20
    socket_timeout: int = 5
    decode_responses: bool = True


class KafkaSettings(BaseSettings):
    """Apache Kafka configuration."""

    model_config = SettingsConfigDict(env_prefix="KAFKA_")

    bootstrap_servers: str = "localhost:9092"
    consumer_group: str = "sentinel-ai"

    # Topic names
    topic_incidents_created: str = "incidents.created"
    topic_incidents_updated: str = "incidents.updated"
    topic_deployments_created: str = "deployments.created"
    topic_deployments_failed: str = "deployments.failed"
    topic_ai_analysis_started: str = "ai.analysis.started"
    topic_ai_analysis_completed: str = "ai.analysis.completed"
    topic_ai_remediation_proposed: str = "ai.remediation.proposed"
    topic_notifications: str = "notifications"

    # Consumer settings
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 4096

    @property
    def is_simulation(self) -> bool:
        """Returns True if no real API keys are configured."""
        return not self.openai_api_key and not self.anthropic_api_key

    @property
    def provider(self) -> str:
        """Determines which LLM provider to use."""
        if self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"
        return "simulation"


class GitHubSettings(BaseSettings):
    """GitHub integration configuration."""

    model_config = SettingsConfigDict(env_prefix="GITHUB_")

    token: str = Field(default="", alias="GITHUB_TOKEN")
    base_url: str = "https://api.github.com"

    @property
    def is_simulation(self) -> bool:
        return not self.token


class JiraSettings(BaseSettings):
    """Jira integration configuration."""

    model_config = SettingsConfigDict(env_prefix="JIRA_")

    base_url: str = Field(default="", alias="JIRA_BASE_URL")
    api_token: str = Field(default="", alias="JIRA_API_TOKEN")

    @property
    def is_simulation(self) -> bool:
        return not self.base_url or not self.api_token


class SlackSettings(BaseSettings):
    """Slack integration configuration."""

    model_config = SettingsConfigDict(env_prefix="SLACK_")

    bot_token: str = Field(default="", alias="SLACK_BOT_TOKEN")
    channel: str = "#incidents"

    @property
    def is_simulation(self) -> bool:
        return not self.bot_token


class KubernetesSettings(BaseSettings):
    """Kubernetes cluster configuration."""

    model_config = SettingsConfigDict(env_prefix="KUBE_")

    config_path: str = Field(default="", alias="KUBE_CONFIG_PATH")
    namespace: str = "default"

    @property
    def is_simulation(self) -> bool:
        return not self.config_path


class ObservabilitySettings(BaseSettings):
    """OpenTelemetry / Prometheus configuration."""

    model_config = SettingsConfigDict(env_prefix="OTEL_")

    exporter_otlp_endpoint: str = "http://localhost:4317"
    service_name: str = "sentinel-ai"
    service_version: str = "0.1.0"
    enable_tracing: bool = True
    enable_metrics: bool = True


class Settings(BaseSettings):
    """Root application settings — aggregates all sub-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "sentinel-ai"
    app_env: str = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"

    # Sub-settings (instantiated on access)
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    kafka: KafkaSettings = KafkaSettings()
    llm: LLMSettings = LLMSettings()
    github: GitHubSettings = GitHubSettings()
    jira: JiraSettings = JiraSettings()
    slack: SlackSettings = SlackSettings()
    kubernetes: KubernetesSettings = KubernetesSettings()
    observability: ObservabilitySettings = ObservabilitySettings()

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton. Safe to call repeatedly."""
    return Settings()
