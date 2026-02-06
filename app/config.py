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

    @property
    def is_production(self) -> bool:
        """Production ortaminda mi kontrol eder."""
        return self.app_env == "production"


# Tekil (singleton) settings nesnesi
settings = Settings()
