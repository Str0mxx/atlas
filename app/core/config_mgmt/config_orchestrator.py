"""ATLAS Konfigurasyon Orkestratoru modulu.

Merkezi kontrol, dagitim,
izleme, analitik ve
konfigurasyon yasam dongusu.
"""

import logging
import time
from typing import Any

from app.core.config_mgmt.config_differ import (
    ConfigDiffer,
)
from app.core.config_mgmt.config_loader import (
    ConfigLoader,
)
from app.core.config_mgmt.config_store import (
    ConfigStore,
)
from app.core.config_mgmt.config_validator import (
    ConfigValidator,
)
from app.core.config_mgmt.dynamic_config import (
    DynamicConfig,
)
from app.core.config_mgmt.environment_manager import (
    EnvironmentManager,
)
from app.core.config_mgmt.feature_flags import (
    FeatureFlags,
)
from app.core.config_mgmt.secret_vault import (
    SecretVault,
)

logger = logging.getLogger(__name__)


class ConfigOrchestrator:
    """Konfigurasyon orkestratoru.

    Tum konfigurasyon yonetimini koordine eder.

    Attributes:
        store: Konfigurasyon deposu.
        loader: Konfigurasyon yukleyici.
        validator: Dogrulayici.
        flags: Ozellik bayraklari.
        vault: Gizli veri kasasi.
        env_mgr: Ortam yoneticisi.
        dynamic: Dinamik konfigurasyon.
        differ: Farklayici.
    """

    def __init__(
        self,
        current_env: str = "development",
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            current_env: Mevcut ortam.
        """
        self.store = ConfigStore()
        self.loader = ConfigLoader()
        self.validator = ConfigValidator()
        self.flags = FeatureFlags()
        self.vault = SecretVault()
        self.env_mgr = EnvironmentManager(
            current_env,
        )
        self.dynamic = DynamicConfig()
        self.differ = ConfigDiffer()

        self._audit_log: list[
            dict[str, Any]
        ] = []
        self._initialized = False

        logger.info(
            "ConfigOrchestrator baslatildi: %s",
            current_env,
        )

    def initialize(
        self,
        config_data: dict[str, Any] | None = None,
        environments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sistemi baslatir.

        Args:
            config_data: Baslangic konfigurasyonu.
            environments: Ortam listesi.

        Returns:
            Baslangic bilgisi.
        """
        # Ortamlari kaydet
        env_list = environments or [
            "development", "staging", "production",
        ]
        for i, env in enumerate(env_list):
            self.env_mgr.register_environment(
                env, level=i,
            )

        # Promosyon kurallarini ekle
        for i in range(len(env_list) - 1):
            self.env_mgr.add_promotion_rule(
                env_list[i],
                env_list[i + 1],
                require_approval=(i > 0),
            )

        # Baslangic konfigurasyonunu yukle
        if config_data:
            for key, value in config_data.items():
                self.store.set(key, value)
                self.dynamic.set(key, value, "init")

        self._initialized = True
        self._log_audit("initialize", {
            "environments": env_list,
            "configs": len(config_data or {}),
        })

        return {
            "status": "initialized",
            "environments": len(env_list),
            "configs_loaded": len(
                config_data or {},
            ),
        }

    def load_and_validate(
        self,
        json_content: str,
        schema_name: str | None = None,
    ) -> dict[str, Any]:
        """Yukler ve dogrular.

        Args:
            json_content: JSON icerigi.
            schema_name: Sema adi.

        Returns:
            Yukleme ve dogrulama sonucu.
        """
        data = self.loader.load_json(json_content)
        if "error" in data:
            return {
                "status": "error",
                "reason": "parse_error",
                "error": data["error"],
            }

        if schema_name:
            validation = self.validator.validate(
                data, schema_name,
            )
            if not validation["valid"]:
                return {
                    "status": "error",
                    "reason": "validation_error",
                    "errors": validation["errors"],
                }

        # Store'a kaydet
        stored = 0
        for key, value in data.items():
            self.store.set(key, value)
            stored += 1

        self._log_audit("load_and_validate", {
            "stored": stored,
            "schema": schema_name,
        })

        return {
            "status": "loaded",
            "stored": stored,
            "validated": schema_name is not None,
        }

    def promote_config(
        self,
        key: str,
        from_env: str,
        to_env: str,
    ) -> dict[str, Any]:
        """Konfigurasyon terfii.

        Args:
            key: Anahtar.
            from_env: Kaynak ortam.
            to_env: Hedef ortam.

        Returns:
            Terfii sonucu.
        """
        result = self.env_mgr.promote(
            key, from_env, to_env,
        )

        self._log_audit("promote", {
            "key": key,
            "from": from_env,
            "to": to_env,
            "result": result.get("status"),
        })

        return result

    def check_feature(
        self,
        flag_name: str,
        user_id: str = "",
    ) -> bool:
        """Ozellik kontrolu.

        Args:
            flag_name: Bayrak adi.
            user_id: Kullanici ID.

        Returns:
            Aktif mi.
        """
        return self.flags.is_enabled(
            flag_name, user_id,
        )

    def manage_secret(
        self,
        action: str,
        name: str,
        value: str = "",
        accessor: str = "",
    ) -> dict[str, Any]:
        """Gizli veri yonetimi.

        Args:
            action: Islem (store/retrieve/rotate).
            name: Gizli veri adi.
            value: Deger.
            accessor: Erisimci.

        Returns:
            Islem sonucu.
        """
        if action == "store":
            result = self.vault.store(name, value)
        elif action == "retrieve":
            result = self.vault.retrieve(
                name, accessor,
            )
        elif action == "rotate":
            result = self.vault.rotate(name, value)
        else:
            result = {
                "status": "error",
                "reason": "unknown_action",
            }

        self._log_audit("manage_secret", {
            "action": action,
            "name": name,
        })

        return result

    def compare_environments(
        self,
        env_a: str,
        env_b: str,
    ) -> dict[str, Any]:
        """Ortamlari karsilastirir.

        Args:
            env_a: Ortam A.
            env_b: Ortam B.

        Returns:
            Karsilastirma sonucu.
        """
        return self.env_mgr.compare(env_a, env_b)

    def diff_configs(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> dict[str, Any]:
        """Konfigurasyonlari karsilastirir.

        Args:
            source: Kaynak.
            target: Hedef.

        Returns:
            Fark sonucu.
        """
        return self.differ.diff(source, target)

    def get_snapshot(self) -> dict[str, Any]:
        """Sistem snapshot'i alir.

        Returns:
            Snapshot bilgisi.
        """
        return {
            "total_configs": (
                self.store.config_count
            ),
            "total_secrets": (
                self.vault.secret_count
            ),
            "total_flags": self.flags.flag_count,
            "environments": (
                self.env_mgr.environment_count
            ),
            "dynamic_configs": (
                self.dynamic.config_count
            ),
            "diffs": self.differ.diff_count,
            "audit_entries": len(self._audit_log),
            "current_env": (
                self.env_mgr.current_env
            ),
            "initialized": self._initialized,
            "timestamp": time.time(),
        }

    def _log_audit(
        self,
        action: str,
        details: dict[str, Any],
    ) -> None:
        """Denetim logu yazar.

        Args:
            action: Islem.
            details: Detaylar.
        """
        self._audit_log.append({
            "action": action,
            "details": details,
            "timestamp": time.time(),
        })

    def get_audit_log(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Denetim logu getirir.

        Args:
            limit: Limit.

        Returns:
            Log listesi.
        """
        return self._audit_log[-limit:]

    @property
    def audit_count(self) -> int:
        """Denetim kaydi sayisi."""
        return len(self._audit_log)

    @property
    def is_initialized(self) -> bool:
        """Baslatildi mi."""
        return self._initialized
