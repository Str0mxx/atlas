"""ATLAS Trafik Yoneticisi modulu.

Trafik bolme, canary dagitim,
mavi-yesil yonlendirme, A/B testi
ve karanlik lansman.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TrafficManager:
    """Trafik yoneticisi.

    Trafik dagitimini yonetir.

    Attributes:
        _rules: Trafik kurallari.
        _splits: Bolme tanimlari.
    """

    def __init__(self) -> None:
        """Trafik yoneticisini baslatir."""
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._splits: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._canaries: dict[
            str, dict[str, Any]
        ] = {}
        self._ab_tests: dict[
            str, dict[str, Any]
        ] = {}
        self._dark_launches: dict[
            str, dict[str, Any]
        ] = {}
        self._routing_history: list[
            dict[str, Any]
        ] = []

        logger.info(
            "TrafficManager baslatildi",
        )

    def set_traffic_split(
        self,
        service: str,
        splits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Trafik bolmesi ayarlar.

        Args:
            service: Servis adi.
            splits: Bolme tanimlari
                [{version, weight}, ...].

        Returns:
            Bolme bilgisi.
        """
        total = sum(s["weight"] for s in splits)
        normalized = []
        for s in splits:
            normalized.append({
                "version": s["version"],
                "weight": s["weight"] / total * 100,
            })
        self._splits[service] = normalized

        return {
            "service": service,
            "splits": len(normalized),
        }

    def route_request(
        self,
        service: str,
        request_id: str = "",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Istegi yonlendirir.

        Args:
            service: Servis adi.
            request_id: Istek ID.
            headers: Basliklar.

        Returns:
            Yonlendirme bilgisi.
        """
        # Canary kontrolu
        canary = self._canaries.get(service)
        if canary and canary["enabled"]:
            h = hashlib.md5(
                request_id.encode(),
            ).hexdigest()
            bucket = int(h[:8], 16) % 100
            if bucket < canary["percentage"]:
                result = {
                    "version": canary["version"],
                    "routing": "canary",
                }
                self._record_routing(
                    service, result,
                )
                return result

        # A/B test kontrolu
        ab = self._ab_tests.get(service)
        if ab and ab["enabled"]:
            h = hashlib.md5(
                request_id.encode(),
            ).hexdigest()
            bucket = int(h[:8], 16) % 100
            if bucket < ab["split_pct"]:
                version = ab["variant_b"]
            else:
                version = ab["variant_a"]
            result = {
                "version": version,
                "routing": "ab_test",
            }
            self._record_routing(service, result)
            return result

        # Trafik bolmesi
        splits = self._splits.get(service)
        if splits:
            h = hashlib.md5(
                request_id.encode(),
            ).hexdigest()
            bucket = int(h[:8], 16) % 100
            cumulative = 0.0
            for s in splits:
                cumulative += s["weight"]
                if bucket < cumulative:
                    result = {
                        "version": s["version"],
                        "routing": "split",
                    }
                    self._record_routing(
                        service, result,
                    )
                    return result

        result = {
            "version": "default",
            "routing": "default",
        }
        self._record_routing(service, result)
        return result

    def setup_canary(
        self,
        service: str,
        version: str,
        percentage: float = 10.0,
    ) -> dict[str, Any]:
        """Canary dagitim ayarlar.

        Args:
            service: Servis adi.
            version: Canary surumu.
            percentage: Yuzde.

        Returns:
            Canary bilgisi.
        """
        self._canaries[service] = {
            "version": version,
            "percentage": percentage,
            "enabled": True,
            "created_at": time.time(),
        }
        return {
            "service": service,
            "version": version,
            "percentage": percentage,
        }

    def promote_canary(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Canary'yi tam dagitima yukseltir.

        Args:
            service: Servis adi.

        Returns:
            Yukseltme bilgisi.
        """
        canary = self._canaries.get(service)
        if not canary:
            return {
                "status": "error",
                "reason": "no_canary",
            }

        canary["percentage"] = 100.0
        return {
            "status": "promoted",
            "version": canary["version"],
        }

    def rollback_canary(
        self,
        service: str,
    ) -> bool:
        """Canary'yi geri alir.

        Args:
            service: Servis adi.

        Returns:
            Basarili mi.
        """
        if service in self._canaries:
            del self._canaries[service]
            return True
        return False

    def setup_ab_test(
        self,
        service: str,
        variant_a: str,
        variant_b: str,
        split_pct: float = 50.0,
    ) -> dict[str, Any]:
        """A/B testi ayarlar.

        Args:
            service: Servis adi.
            variant_a: Varyant A.
            variant_b: Varyant B.
            split_pct: B orani (%).

        Returns:
            Test bilgisi.
        """
        self._ab_tests[service] = {
            "variant_a": variant_a,
            "variant_b": variant_b,
            "split_pct": split_pct,
            "enabled": True,
            "created_at": time.time(),
        }
        return {
            "service": service,
            "variant_a": variant_a,
            "variant_b": variant_b,
        }

    def end_ab_test(
        self,
        service: str,
        winner: str | None = None,
    ) -> dict[str, Any]:
        """A/B testini sonlandirir.

        Args:
            service: Servis adi.
            winner: Kazanan varyant.

        Returns:
            Sonlandirma bilgisi.
        """
        ab = self._ab_tests.pop(service, None)
        if not ab:
            return {
                "status": "error",
                "reason": "no_test",
            }
        return {
            "status": "ended",
            "winner": winner or ab["variant_a"],
        }

    def setup_dark_launch(
        self,
        service: str,
        version: str,
        mirror_pct: float = 100.0,
    ) -> dict[str, Any]:
        """Karanlik lansman ayarlar.

        Args:
            service: Servis adi.
            version: Surum.
            mirror_pct: Yansitma yuzdesi.

        Returns:
            Lansman bilgisi.
        """
        self._dark_launches[service] = {
            "version": version,
            "mirror_pct": mirror_pct,
            "enabled": True,
            "created_at": time.time(),
        }
        return {
            "service": service,
            "version": version,
            "mirror_pct": mirror_pct,
        }

    def should_mirror(
        self,
        service: str,
        request_id: str,
    ) -> bool:
        """Yansitilmali mi.

        Args:
            service: Servis adi.
            request_id: Istek ID.

        Returns:
            Yansitilmali mi.
        """
        dark = self._dark_launches.get(service)
        if not dark or not dark["enabled"]:
            return False
        h = hashlib.md5(
            request_id.encode(),
        ).hexdigest()
        bucket = int(h[:8], 16) % 100
        return bucket < dark["mirror_pct"]

    def _record_routing(
        self,
        service: str,
        result: dict[str, Any],
    ) -> None:
        """Yonlendirme kaydeder.

        Args:
            service: Servis adi.
            result: Yonlendirme sonucu.
        """
        self._routing_history.append({
            "service": service,
            **result,
            "timestamp": time.time(),
        })

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._splits)

    @property
    def canary_count(self) -> int:
        """Canary sayisi."""
        return len(self._canaries)

    @property
    def ab_test_count(self) -> int:
        """A/B test sayisi."""
        return len(self._ab_tests)

    @property
    def dark_launch_count(self) -> int:
        """Karanlik lansman sayisi."""
        return len(self._dark_launches)

    @property
    def routing_count(self) -> int:
        """Yonlendirme sayisi."""
        return len(self._routing_history)
