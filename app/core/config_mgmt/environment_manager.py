"""ATLAS Ortam Yoneticisi modulu.

Ortam tespiti, ortam basi konfig,
promosyon kurallari, izolasyon
ve karsilastirma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Ortam yoneticisi.

    Ortam bazli konfigurasyon yonetir.

    Attributes:
        _environments: Ortam tanimlari.
        _configs: Ortam konfigleri.
    """

    def __init__(
        self,
        current_env: str = "development",
    ) -> None:
        """Ortam yoneticisini baslatir.

        Args:
            current_env: Mevcut ortam.
        """
        self._current_env = current_env
        self._environments: dict[
            str, dict[str, Any]
        ] = {}
        self._configs: dict[
            str, dict[str, Any]
        ] = {}
        self._promotion_rules: list[
            dict[str, Any]
        ] = []
        self._promotion_history: list[
            dict[str, Any]
        ] = []

        logger.info(
            "EnvironmentManager baslatildi: %s",
            current_env,
        )

    def register_environment(
        self,
        name: str,
        level: int = 0,
        description: str = "",
    ) -> dict[str, Any]:
        """Ortam kaydeder.

        Args:
            name: Ortam adi.
            level: Seviye (0=en dusuk).
            description: Aciklama.

        Returns:
            Kayit bilgisi.
        """
        env = {
            "name": name,
            "level": level,
            "description": description,
            "created_at": time.time(),
        }
        self._environments[name] = env
        if name not in self._configs:
            self._configs[name] = {}
        return env

    def set_config(
        self,
        env: str,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        """Ortam konfigu ayarlar.

        Args:
            env: Ortam adi.
            key: Anahtar.
            value: Deger.

        Returns:
            Kayit bilgisi.
        """
        if env not in self._configs:
            self._configs[env] = {}
        self._configs[env][key] = value
        return {"env": env, "key": key}

    def get_config(
        self,
        key: str,
        env: str | None = None,
        default: Any = None,
    ) -> Any:
        """Ortam konfigu getirir.

        Args:
            key: Anahtar.
            env: Ortam (None=mevcut).
            default: Varsayilan.

        Returns:
            Deger.
        """
        target = env or self._current_env
        env_configs = self._configs.get(
            target, {},
        )
        return env_configs.get(key, default)

    def get_all_configs(
        self,
        env: str | None = None,
    ) -> dict[str, Any]:
        """Tum ortam konfiglerini getirir.

        Args:
            env: Ortam (None=mevcut).

        Returns:
            Konfigurasyon eslesmesi.
        """
        target = env or self._current_env
        return dict(
            self._configs.get(target, {}),
        )

    def add_promotion_rule(
        self,
        from_env: str,
        to_env: str,
        require_approval: bool = True,
    ) -> dict[str, Any]:
        """Promosyon kurali ekler.

        Args:
            from_env: Kaynak ortam.
            to_env: Hedef ortam.
            require_approval: Onay gerekli mi.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "from_env": from_env,
            "to_env": to_env,
            "require_approval": require_approval,
        }
        self._promotion_rules.append(rule)
        return rule

    def promote(
        self,
        key: str,
        from_env: str,
        to_env: str,
    ) -> dict[str, Any]:
        """Konfigu terfii ettirir.

        Args:
            key: Anahtar.
            from_env: Kaynak ortam.
            to_env: Hedef ortam.

        Returns:
            Terfii sonucu.
        """
        source_configs = self._configs.get(
            from_env, {},
        )
        if key not in source_configs:
            return {
                "status": "error",
                "reason": "key_not_found",
            }

        # Kural kontrol
        allowed = False
        requires_approval = False
        for rule in self._promotion_rules:
            if (
                rule["from_env"] == from_env
                and rule["to_env"] == to_env
            ):
                allowed = True
                requires_approval = rule[
                    "require_approval"
                ]
                break

        if not self._promotion_rules:
            allowed = True

        if not allowed:
            return {
                "status": "error",
                "reason": "no_promotion_rule",
            }

        value = source_configs[key]
        if to_env not in self._configs:
            self._configs[to_env] = {}
        self._configs[to_env][key] = value

        record = {
            "key": key,
            "from_env": from_env,
            "to_env": to_env,
            "value": value,
            "requires_approval": requires_approval,
            "timestamp": time.time(),
        }
        self._promotion_history.append(record)

        return {
            "status": "promoted",
            "key": key,
            "from_env": from_env,
            "to_env": to_env,
        }

    def compare(
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
        configs_a = self._configs.get(env_a, {})
        configs_b = self._configs.get(env_b, {})
        all_keys = set(configs_a) | set(configs_b)

        only_a = []
        only_b = []
        different = []
        same = []

        for key in all_keys:
            in_a = key in configs_a
            in_b = key in configs_b
            if in_a and not in_b:
                only_a.append(key)
            elif in_b and not in_a:
                only_b.append(key)
            elif configs_a[key] != configs_b[key]:
                different.append(key)
            else:
                same.append(key)

        return {
            "env_a": env_a,
            "env_b": env_b,
            "only_a": only_a,
            "only_b": only_b,
            "different": different,
            "same": same,
            "total_keys": len(all_keys),
        }

    def detect_environment(
        self,
    ) -> str:
        """Mevcut ortami tespit eder.

        Returns:
            Ortam adi.
        """
        return self._current_env

    def switch_environment(
        self,
        env: str,
    ) -> bool:
        """Ortam degistirir.

        Args:
            env: Yeni ortam.

        Returns:
            Basarili mi.
        """
        if env in self._environments:
            self._current_env = env
            return True
        return False

    @property
    def current_env(self) -> str:
        """Mevcut ortam."""
        return self._current_env

    @property
    def environment_count(self) -> int:
        """Ortam sayisi."""
        return len(self._environments)

    @property
    def promotion_count(self) -> int:
        """Terfii sayisi."""
        return len(self._promotion_history)
