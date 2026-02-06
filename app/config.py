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

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # SSH
    ssh_default_host: str = ""
    ssh_default_user: str = ""
    ssh_default_key_path: str = "~/.ssh/id_rsa"

    # Master Agent
    master_agent_auto_mode: bool = False
    master_agent_max_retries: int = 3

    @property
    def is_production(self) -> bool:
        """Production ortaminda mi kontrol eder."""
        return self.app_env == "production"


# Tekil (singleton) settings nesnesi
settings = Settings()
