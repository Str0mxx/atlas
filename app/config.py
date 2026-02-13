"""ATLAS yapilandirma modulu.

Tum uygulama ayarlari Pydantic Settings uzerinden yonetilir.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Proje kok dizini
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Ana uygulama ayarlari."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Uygulama
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"
    app_secret_key: SecretStr = Field(default=SecretStr("change-this-secret-key"))

    # Anthropic
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))

    # Telegram
    telegram_bot_token: SecretStr = Field(default=SecretStr(""))
    telegram_admin_chat_id: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://atlas:password@localhost:5432/atlas_db"
    database_pool_size: int = 5

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10

    # Qdrant (Vektor Veritabani)
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: SecretStr | None = Field(default=None)
    qdrant_collection_prefix: str = "atlas"
    qdrant_embedding_model: str = "BAAI/bge-small-en-v1.5"
    qdrant_embedding_dimension: int = 384

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # SSH
    ssh_default_host: str = ""
    ssh_default_user: str = ""
    ssh_default_key_path: str = "~/.ssh/id_rsa"

    # Research
    tavily_api_key: SecretStr = Field(default=SecretStr(""))

    # Google Ads
    google_ads_developer_token: SecretStr = Field(default=SecretStr(""))
    google_ads_client_id: str = ""
    google_ads_client_secret: SecretStr = Field(default=SecretStr(""))
    google_ads_refresh_token: SecretStr = Field(default=SecretStr(""))
    google_ads_customer_id: str = ""

    # Gmail API
    gmail_client_id: str = ""
    gmail_client_secret: SecretStr = Field(default=SecretStr(""))
    gmail_refresh_token: SecretStr = Field(default=SecretStr(""))
    gmail_sender_email: str = ""
    gmail_sender_name: str = ""

    # Webhook
    webhook_secret: SecretStr = Field(default=SecretStr(""))

    # OpenAI (Whisper STT)
    openai_api_key: SecretStr = Field(default=SecretStr(""))

    # ElevenLabs (TTS)
    elevenlabs_api_key: SecretStr = Field(default=SecretStr(""))

    # Master Agent
    master_agent_auto_mode: bool = False
    master_agent_max_retries: int = 3

    # TaskManager
    task_manager_max_concurrent: int = 5
    task_manager_retry_backoff_base: int = 5
    task_manager_retry_backoff_max: int = 300

    # Monitor Intervals (saniye)
    server_monitor_interval: int = 300
    security_monitor_interval: int = 3600
    ads_monitor_interval: int = 3600
    opportunity_monitor_interval: int = 86400

    # Plugin sistemi
    plugins_enabled: bool = True
    plugins_dir: str = "app/plugins"
    plugins_auto_load: bool = True

    # Bootstrap / Auto-Provisioning
    bootstrap_auto_install: bool = False
    bootstrap_allowed_installers: str = "pip,npm"
    bootstrap_sandbox_mode: bool = True
    bootstrap_require_approval: bool = True

    # Self-Coding
    selfcode_enabled: bool = False
    selfcode_max_generation_attempts: int = 3
    selfcode_sandbox_timeout: int = 30
    selfcode_auto_commit: bool = False
    selfcode_require_tests: bool = True

    # Memory Palace
    memory_palace_forgetting_rate: float = 0.1
    memory_palace_consolidation_interval: int = 3600
    memory_palace_emotional_weight: float = 0.3
    memory_palace_max_working_memory: int = 7

    # Business Runner
    business_cycle_interval: int = 60
    business_max_parallel_initiatives: int = 3
    business_risk_tolerance: float = 0.5
    business_human_approval_threshold: float = 0.8

    # NLP Engine
    nlp_clarification_threshold: float = 0.4
    nlp_max_context_turns: int = 50
    nlp_execution_confirmation: bool = True
    nlp_verbosity_level: str = "normal"

    # Predictive Intelligence
    predictive_forecast_horizon: int = 7
    predictive_confidence_threshold: float = 0.6
    predictive_model_update_frequency: str = "daily"
    predictive_ensemble_strategy: str = "weighted"

    # Knowledge Graph
    knowledge_max_nodes: int = 10000
    knowledge_inference_depth: int = 5
    knowledge_fusion_strategy: str = "trust_based"
    knowledge_persistence_path: str = ""

    # Resilience / Offline
    resilience_enabled: bool = True
    offline_health_check_interval: int = 30
    offline_max_queue_size: int = 1000
    offline_sync_batch_size: int = 50
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    local_llm_provider: str = "rule_based"
    local_llm_ollama_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.2"
    state_persistence_db_path: str = "data/atlas_state.db"
    state_persistence_max_snapshots: int = 100

    @property
    def is_production(self) -> bool:
        """Production ortaminda mi kontrol eder."""
        return self.app_env == "production"


# Tekil (singleton) settings nesnesi
settings = Settings()
