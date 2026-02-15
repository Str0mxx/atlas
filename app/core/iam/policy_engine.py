"""ATLAS IAM Politika Motoru modulu.

Allow/deny politikalari, kosullar,
onbellek destegi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IAMPolicyEngine:
    """IAM politika motoru.

    Politika tabanli erisim kontrolu.

    Attributes:
        _policies: Politika kayitlari.
        _cache: Karar onbellegi.
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_ttl: int = 300,
    ) -> None:
        """Politika motorunu baslatir.

        Args:
            cache_enabled: Onbellek aktif mi.
            cache_ttl: Onbellek TTL (sn).
        """
        self._policies: dict[
            str, dict[str, Any]
        ] = {}
        self._cache: dict[
            str, dict[str, Any]
        ] = {}
        self._cache_enabled = cache_enabled
        self._cache_ttl = cache_ttl
        self._stats = {
            "created": 0,
            "evaluated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        logger.info(
            "IAMPolicyEngine baslatildi",
        )

    def create_policy(
        self,
        policy_id: str,
        name: str,
        effect: str = "allow",
        resources: list[str] | None = None,
        actions: list[str] | None = None,
        subjects: list[str] | None = None,
        conditions: dict[str, Any] | None = None,
        priority: int = 0,
    ) -> dict[str, Any]:
        """Politika olusturur.

        Args:
            policy_id: Politika ID.
            name: Politika adi.
            effect: Etki (allow/deny).
            resources: Kaynaklar.
            actions: Aksiyonlar.
            subjects: Konular.
            conditions: Kosullar.
            priority: Oncelik.

        Returns:
            Politika bilgisi.
        """
        if policy_id in self._policies:
            return {"error": "policy_exists"}

        self._policies[policy_id] = {
            "policy_id": policy_id,
            "name": name,
            "effect": effect,
            "resources": resources or ["*"],
            "actions": actions or ["*"],
            "subjects": subjects or ["*"],
            "conditions": conditions or {},
            "priority": priority,
            "enabled": True,
            "created_at": time.time(),
        }

        self._invalidate_cache()
        self._stats["created"] += 1

        return {
            "policy_id": policy_id,
            "name": name,
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
        self._invalidate_cache()
        return True

    def update_policy(
        self,
        policy_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Politika gunceller.

        Args:
            policy_id: Politika ID.
            **kwargs: Guncellenecek alanlar.

        Returns:
            Guncelleme sonucu.
        """
        policy = self._policies.get(policy_id)
        if not policy:
            return {"error": "policy_not_found"}

        allowed = {
            "name", "effect", "resources",
            "actions", "subjects", "conditions",
            "priority", "enabled",
        }
        for key, value in kwargs.items():
            if key in allowed:
                policy[key] = value

        self._invalidate_cache()

        return {
            "policy_id": policy_id,
            "status": "updated",
        }

    def evaluate(
        self,
        subject: str,
        resource: str,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Politika degerlendirmesi yapar.

        Args:
            subject: Konu.
            resource: Kaynak.
            action: Aksiyon.
            context: Baglamsal bilgi.

        Returns:
            Degerlendirme sonucu.
        """
        self._stats["evaluated"] += 1
        ctx = context or {}

        # Onbellek kontrolu
        ctx_key = str(sorted(ctx.items())) if ctx else ""
        cache_key = f"{subject}:{resource}:{action}:{ctx_key}"
        if self._cache_enabled:
            cached = self._get_cache(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return cached

            self._stats["cache_misses"] += 1

        # Politikalari degerlendir
        matching = self._find_matching(
            subject, resource, action,
        )

        if not matching:
            result = {
                "allowed": False,
                "reason": "no_matching_policy",
                "policy_id": None,
            }
            self._set_cache(cache_key, result)
            return result

        # Oncelik sirasi: deny > allow
        # Ayni etki icinde yuksek oncelik kazanir
        deny_policies = [
            p for p in matching
            if p["effect"] == "deny"
        ]
        allow_policies = [
            p for p in matching
            if p["effect"] == "allow"
        ]

        # Deny varsa engelle
        for policy in deny_policies:
            if self._check_conditions(
                policy.get("conditions", {}),
                ctx,
            ):
                result = {
                    "allowed": False,
                    "reason": "explicit_deny",
                    "policy_id": policy["policy_id"],
                }
                self._set_cache(cache_key, result)
                return result

        # Allow varsa izin ver
        for policy in allow_policies:
            if self._check_conditions(
                policy.get("conditions", {}),
                ctx,
            ):
                result = {
                    "allowed": True,
                    "reason": "explicit_allow",
                    "policy_id": policy["policy_id"],
                }
                self._set_cache(cache_key, result)
                return result

        result = {
            "allowed": False,
            "reason": "conditions_not_met",
            "policy_id": None,
        }
        self._set_cache(cache_key, result)
        return result

    def get_policy(
        self,
        policy_id: str,
    ) -> dict[str, Any] | None:
        """Politika getirir.

        Args:
            policy_id: Politika ID.

        Returns:
            Politika bilgisi veya None.
        """
        return self._policies.get(policy_id)

    def list_policies(
        self,
        effect: str | None = None,
        enabled_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Politikalari listeler.

        Args:
            effect: Etki filtresi.
            enabled_only: Sadece aktifler.
            limit: Limit.

        Returns:
            Politika listesi.
        """
        policies = list(self._policies.values())

        if effect:
            policies = [
                p for p in policies
                if p["effect"] == effect
            ]

        if enabled_only:
            policies = [
                p for p in policies
                if p["enabled"]
            ]

        return policies[-limit:]

    def _find_matching(
        self,
        subject: str,
        resource: str,
        action: str,
    ) -> list[dict[str, Any]]:
        """Eslesen politikalari bulur.

        Args:
            subject: Konu.
            resource: Kaynak.
            action: Aksiyon.

        Returns:
            Eslesen politikalar (oncelik sirali).
        """
        matching = []
        for policy in self._policies.values():
            if not policy["enabled"]:
                continue

            if not self._pattern_matches(
                policy["subjects"], subject,
            ):
                continue
            if not self._pattern_matches(
                policy["resources"], resource,
            ):
                continue
            if not self._pattern_matches(
                policy["actions"], action,
            ):
                continue

            matching.append(policy)

        matching.sort(
            key=lambda p: p["priority"],
            reverse=True,
        )
        return matching

    def _pattern_matches(
        self,
        patterns: list[str],
        value: str,
    ) -> bool:
        """Desen listesi eslestirmesi.

        Args:
            patterns: Desenler.
            value: Deger.

        Returns:
            Eslesiyor mu.
        """
        for pattern in patterns:
            if pattern == "*":
                return True
            if pattern == value:
                return True
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if value.startswith(prefix):
                    return True
        return False

    def _check_conditions(
        self,
        conditions: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Kosullari kontrol eder.

        Args:
            conditions: Kosullar.
            context: Baglam.

        Returns:
            Kosullar saglanıyor mu.
        """
        if not conditions:
            return True

        for key, expected in conditions.items():
            actual = context.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True

    def _get_cache(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Onbellekten getirir.

        Args:
            key: Anahtar.

        Returns:
            Deger veya None.
        """
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() - entry["time"] > self._cache_ttl:
            del self._cache[key]
            return None
        return entry["value"]

    def _set_cache(
        self,
        key: str,
        value: dict[str, Any],
    ) -> None:
        """Onbellege yazar.

        Args:
            key: Anahtar.
            value: Deger.
        """
        if self._cache_enabled:
            self._cache[key] = {
                "value": value,
                "time": time.time(),
            }

    def _invalidate_cache(self) -> None:
        """Onbellegi temizler."""
        self._cache.clear()

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)

    @property
    def cache_size(self) -> int:
        """Onbellek boyutu."""
        return len(self._cache)

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return self._stats["evaluated"]
