"""ATLAS Ozellik Bayraklari modulu.

Bayrak yonetimi, kademeli dagitim,
A/B testi, kullanici hedefleme
ve kill switch.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Ozellik bayraklari yoneticisi.

    Ozellik bayraklarini yonetir.

    Attributes:
        _flags: Bayrak tanimlari.
        _overrides: Kullanici gecersiz kilmalari.
    """

    def __init__(self) -> None:
        """Ozellik bayraklarini baslatir."""
        self._flags: dict[
            str, dict[str, Any]
        ] = {}
        self._overrides: dict[
            str, dict[str, bool]
        ] = {}
        self._evaluations: list[
            dict[str, Any]
        ] = []

        logger.info("FeatureFlags baslatildi")

    def create_flag(
        self,
        name: str,
        enabled: bool = False,
        description: str = "",
        rollout_pct: float = 100.0,
    ) -> dict[str, Any]:
        """Bayrak olusturur.

        Args:
            name: Bayrak adi.
            enabled: Aktif mi.
            description: Aciklama.
            rollout_pct: Dagitim yuzdesi.

        Returns:
            Bayrak bilgisi.
        """
        flag = {
            "name": name,
            "enabled": enabled,
            "description": description,
            "rollout_pct": rollout_pct,
            "status": (
                "enabled" if enabled
                else "disabled"
            ),
            "kill_switch": False,
            "created_at": time.time(),
        }
        self._flags[name] = flag
        return {
            "name": name,
            "enabled": enabled,
        }

    def is_enabled(
        self,
        name: str,
        user_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Bayrak aktif mi kontrol eder.

        Args:
            name: Bayrak adi.
            user_id: Kullanici ID.
            context: Baglam.

        Returns:
            Aktif mi.
        """
        flag = self._flags.get(name)
        if not flag:
            return False

        # Kill switch
        if flag.get("kill_switch"):
            self._log_eval(name, user_id, False)
            return False

        # Kullanici gecersiz kilmasi
        if user_id and name in self._overrides:
            override = self._overrides[name].get(
                user_id,
            )
            if override is not None:
                self._log_eval(
                    name, user_id, override,
                )
                return override

        if not flag["enabled"]:
            self._log_eval(name, user_id, False)
            return False

        # Kademeli dagitim
        rollout = flag["rollout_pct"]
        if rollout < 100.0 and user_id:
            h = hashlib.md5(
                f"{name}:{user_id}".encode(),
            ).hexdigest()
            bucket = int(h[:8], 16) % 100
            result = bucket < rollout
            self._log_eval(
                name, user_id, result,
            )
            return result

        self._log_eval(name, user_id, True)
        return True

    def _log_eval(
        self,
        name: str,
        user_id: str,
        result: bool,
    ) -> None:
        """Degerlendirme loglar.

        Args:
            name: Bayrak adi.
            user_id: Kullanici ID.
            result: Sonuc.
        """
        self._evaluations.append({
            "flag": name,
            "user_id": user_id,
            "result": result,
            "timestamp": time.time(),
        })

    def enable(self, name: str) -> bool:
        """Bayragi aktiflestirir.

        Args:
            name: Bayrak adi.

        Returns:
            Basarili mi.
        """
        flag = self._flags.get(name)
        if flag:
            flag["enabled"] = True
            flag["status"] = "enabled"
            return True
        return False

    def disable(self, name: str) -> bool:
        """Bayragi deaktiflestirir.

        Args:
            name: Bayrak adi.

        Returns:
            Basarili mi.
        """
        flag = self._flags.get(name)
        if flag:
            flag["enabled"] = False
            flag["status"] = "disabled"
            return True
        return False

    def kill(self, name: str) -> bool:
        """Kill switch aktiflestirir.

        Args:
            name: Bayrak adi.

        Returns:
            Basarili mi.
        """
        flag = self._flags.get(name)
        if flag:
            flag["kill_switch"] = True
            flag["status"] = "killed"
            return True
        return False

    def set_rollout(
        self,
        name: str,
        pct: float,
    ) -> bool:
        """Dagitim yuzdesi ayarlar.

        Args:
            name: Bayrak adi.
            pct: Yuzde.

        Returns:
            Basarili mi.
        """
        flag = self._flags.get(name)
        if flag:
            flag["rollout_pct"] = max(
                0.0, min(100.0, pct),
            )
            return True
        return False

    def set_override(
        self,
        name: str,
        user_id: str,
        enabled: bool,
    ) -> None:
        """Kullanici gecersiz kilmasi ayarlar.

        Args:
            name: Bayrak adi.
            user_id: Kullanici ID.
            enabled: Aktif mi.
        """
        if name not in self._overrides:
            self._overrides[name] = {}
        self._overrides[name][user_id] = enabled

    def remove_override(
        self,
        name: str,
        user_id: str,
    ) -> bool:
        """Gecersiz kilmayi kaldirir.

        Args:
            name: Bayrak adi.
            user_id: Kullanici ID.

        Returns:
            Basarili mi.
        """
        if name in self._overrides:
            if user_id in self._overrides[name]:
                del self._overrides[name][user_id]
                return True
        return False

    def get_flag(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Bayrak bilgisi getirir.

        Args:
            name: Bayrak adi.

        Returns:
            Bayrak bilgisi veya None.
        """
        flag = self._flags.get(name)
        if not flag:
            return None
        return {
            "name": flag["name"],
            "enabled": flag["enabled"],
            "rollout_pct": flag["rollout_pct"],
            "status": flag["status"],
            "kill_switch": flag["kill_switch"],
        }

    def delete_flag(
        self,
        name: str,
    ) -> bool:
        """Bayragi siler.

        Args:
            name: Bayrak adi.

        Returns:
            Basarili mi.
        """
        if name in self._flags:
            del self._flags[name]
            self._overrides.pop(name, None)
            return True
        return False

    @property
    def flag_count(self) -> int:
        """Bayrak sayisi."""
        return len(self._flags)

    @property
    def enabled_count(self) -> int:
        """Aktif bayrak sayisi."""
        return sum(
            1 for f in self._flags.values()
            if f["enabled"]
            and not f.get("kill_switch")
        )

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return len(self._evaluations)
