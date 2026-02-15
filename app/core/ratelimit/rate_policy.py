"""ATLAS Hiz Politikasi modulu.

Politika tanimlari, katman tabanli limitler,
endpoint ozel, kullanici ozel, dinamik.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Varsayilan katman limitleri
_DEFAULT_TIER_LIMITS = {
    "free": {"rpm": 10, "daily": 100},
    "basic": {"rpm": 60, "daily": 5000},
    "pro": {"rpm": 300, "daily": 50000},
    "enterprise": {"rpm": 1000, "daily": 500000},
    "unlimited": {"rpm": 0, "daily": 0},
}


class RatePolicy:
    """Hiz politikasi yoneticisi.

    Politika tabanli hiz sinirlama.

    Attributes:
        _policies: Politika kayitlari.
        _tier_limits: Katman limitleri.
    """

    def __init__(self) -> None:
        """Hiz politikasini baslatir."""
        self._policies: dict[
            str, dict[str, Any]
        ] = {}
        self._tier_limits: dict[
            str, dict[str, int]
        ] = dict(_DEFAULT_TIER_LIMITS)
        self._endpoint_rules: dict[
            str, dict[str, Any]
        ] = {}
        self._user_overrides: dict[
            str, dict[str, Any]
        ] = {}
        self._dynamic_rules: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "created": 0,
            "evaluated": 0,
            "overridden": 0,
        }

        logger.info(
            "RatePolicy baslatildi",
        )

    def create_policy(
        self,
        policy_id: str,
        name: str,
        tier: str = "basic",
        rpm: int | None = None,
        daily: int | None = None,
        burst: int | None = None,
        endpoints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Politika olusturur.

        Args:
            policy_id: Politika ID.
            name: Politika adi.
            tier: Katman.
            rpm: Dakika basina istek.
            daily: Gunluk limit.
            burst: Patlama limiti.
            endpoints: Gecerli endpoint'ler.

        Returns:
            Politika bilgisi.
        """
        if policy_id in self._policies:
            return {"error": "policy_exists"}

        tier_limits = self._tier_limits.get(
            tier, {},
        )

        self._policies[policy_id] = {
            "policy_id": policy_id,
            "name": name,
            "tier": tier,
            "rpm": rpm or tier_limits.get("rpm", 60),
            "daily": daily or tier_limits.get(
                "daily", 5000,
            ),
            "burst": burst or (
                (rpm or tier_limits.get("rpm", 60))
                * 2
            ),
            "endpoints": endpoints or ["*"],
            "enabled": True,
            "created_at": time.time(),
        }

        self._stats["created"] += 1

        return {
            "policy_id": policy_id,
            "name": name,
            "tier": tier,
            "status": "created",
        }

    def delete_policy(
        self,
        policy_id: str,
    ) -> bool:
        """Politika siler.

        Args:
            policy_id: Politika ID.

        Returns:
            Basarili mi.
        """
        if policy_id not in self._policies:
            return False
        del self._policies[policy_id]
        return True

    def evaluate(
        self,
        subject_id: str,
        endpoint: str = "*",
        policy_id: str | None = None,
    ) -> dict[str, Any]:
        """Politika degerlendirmesi.

        Args:
            subject_id: Konu ID.
            endpoint: Endpoint.
            policy_id: Politika ID (opsiyonel).

        Returns:
            Degerlendirme sonucu.
        """
        self._stats["evaluated"] += 1

        # Kullanici ozel override
        override = self._user_overrides.get(
            subject_id,
        )
        if override:
            self._stats["overridden"] += 1
            return {
                "rpm": override.get("rpm", 60),
                "daily": override.get(
                    "daily", 5000,
                ),
                "burst": override.get("burst", 120),
                "source": "user_override",
                "subject_id": subject_id,
            }

        # Endpoint ozel kural
        ep_rule = self._endpoint_rules.get(
            endpoint,
        )
        if ep_rule:
            return {
                "rpm": ep_rule.get("rpm", 60),
                "daily": ep_rule.get(
                    "daily", 5000,
                ),
                "burst": ep_rule.get("burst", 120),
                "source": "endpoint_rule",
                "endpoint": endpoint,
            }

        # Politika
        if policy_id:
            policy = self._policies.get(policy_id)
        else:
            policy = self._find_policy(
                subject_id, endpoint,
            )

        if policy:
            return {
                "rpm": policy["rpm"],
                "daily": policy["daily"],
                "burst": policy["burst"],
                "source": "policy",
                "policy_id": policy["policy_id"],
            }

        # Dinamik kurallar
        for rule in self._dynamic_rules:
            if self._matches_dynamic(
                rule, subject_id, endpoint,
            ):
                return {
                    "rpm": rule.get("rpm", 60),
                    "daily": rule.get(
                        "daily", 5000,
                    ),
                    "burst": rule.get("burst", 120),
                    "source": "dynamic_rule",
                }

        # Varsayilan
        return {
            "rpm": 60,
            "daily": 5000,
            "burst": 120,
            "source": "default",
        }

    def set_endpoint_rule(
        self,
        endpoint: str,
        rpm: int = 60,
        daily: int = 5000,
        burst: int = 120,
    ) -> dict[str, Any]:
        """Endpoint ozel kural ayarlar.

        Args:
            endpoint: Endpoint.
            rpm: Dakika basina.
            daily: Gunluk.
            burst: Patlama.

        Returns:
            Kural bilgisi.
        """
        self._endpoint_rules[endpoint] = {
            "rpm": rpm,
            "daily": daily,
            "burst": burst,
        }

        return {
            "endpoint": endpoint,
            "status": "set",
        }

    def set_user_override(
        self,
        subject_id: str,
        rpm: int = 60,
        daily: int = 5000,
        burst: int = 120,
    ) -> dict[str, Any]:
        """Kullanici ozel override ayarlar.

        Args:
            subject_id: Konu ID.
            rpm: Dakika basina.
            daily: Gunluk.
            burst: Patlama.

        Returns:
            Override bilgisi.
        """
        self._user_overrides[subject_id] = {
            "rpm": rpm,
            "daily": daily,
            "burst": burst,
        }

        return {
            "subject_id": subject_id,
            "status": "set",
        }

    def remove_user_override(
        self,
        subject_id: str,
    ) -> bool:
        """Kullanici override'ini kaldirir.

        Args:
            subject_id: Konu ID.

        Returns:
            Basarili mi.
        """
        if subject_id not in self._user_overrides:
            return False
        del self._user_overrides[subject_id]
        return True

    def add_dynamic_rule(
        self,
        rule_id: str,
        condition: str = "",
        rpm: int = 60,
        daily: int = 5000,
        burst: int = 120,
    ) -> dict[str, Any]:
        """Dinamik kural ekler.

        Args:
            rule_id: Kural ID.
            condition: Kosul.
            rpm: Dakika basina.
            daily: Gunluk.
            burst: Patlama.

        Returns:
            Kural bilgisi.
        """
        self._dynamic_rules.append({
            "rule_id": rule_id,
            "condition": condition,
            "rpm": rpm,
            "daily": daily,
            "burst": burst,
        })

        return {
            "rule_id": rule_id,
            "status": "added",
        }

    def set_tier_limits(
        self,
        tier: str,
        rpm: int,
        daily: int,
    ) -> dict[str, Any]:
        """Katman limitlerini ayarlar.

        Args:
            tier: Katman.
            rpm: Dakika basina.
            daily: Gunluk.

        Returns:
            Limit bilgisi.
        """
        self._tier_limits[tier] = {
            "rpm": rpm,
            "daily": daily,
        }

        return {
            "tier": tier,
            "rpm": rpm,
            "daily": daily,
        }

    def get_tier_limits(
        self,
        tier: str,
    ) -> dict[str, int]:
        """Katman limitlerini getirir.

        Args:
            tier: Katman.

        Returns:
            Limit bilgisi.
        """
        return dict(
            self._tier_limits.get(tier, {}),
        )

    def get_policy(
        self,
        policy_id: str,
    ) -> dict[str, Any] | None:
        """Politika bilgisi getirir.

        Args:
            policy_id: Politika ID.

        Returns:
            Politika bilgisi veya None.
        """
        return self._policies.get(policy_id)

    def list_policies(
        self,
        tier: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Politikalari listeler.

        Args:
            tier: Katman filtresi.
            limit: Limit.

        Returns:
            Politika listesi.
        """
        policies = list(self._policies.values())
        if tier:
            policies = [
                p for p in policies
                if p["tier"] == tier
            ]
        return policies[-limit:]

    def _find_policy(
        self,
        subject_id: str,
        endpoint: str,
    ) -> dict[str, Any] | None:
        """Eslesen politikayi bulur.

        Args:
            subject_id: Konu ID.
            endpoint: Endpoint.

        Returns:
            Politika veya None.
        """
        for policy in self._policies.values():
            if not policy["enabled"]:
                continue
            if "*" in policy["endpoints"]:
                return policy
            if endpoint in policy["endpoints"]:
                return policy
        return None

    def _matches_dynamic(
        self,
        rule: dict[str, Any],
        subject_id: str,
        endpoint: str,
    ) -> bool:
        """Dinamik kural eslestirmesi.

        Args:
            rule: Kural.
            subject_id: Konu ID.
            endpoint: Endpoint.

        Returns:
            Eslesiyor mu.
        """
        cond = rule.get("condition", "")
        if not cond:
            return True
        return cond in subject_id or cond in endpoint

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)

    @property
    def endpoint_rule_count(self) -> int:
        """Endpoint kural sayisi."""
        return len(self._endpoint_rules)

    @property
    def override_count(self) -> int:
        """Override sayisi."""
        return len(self._user_overrides)

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return self._stats["evaluated"]
