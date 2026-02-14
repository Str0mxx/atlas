"""ATLAS Guvenlik Duvari modulu.

IP beyaz/kara liste, hiz sinirlandirma,
istek filtreleme, DDoS koruma ve
cografi engelleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.security_hardening import FirewallAction

logger = logging.getLogger(__name__)


class Firewall:
    """Guvenlik duvari.

    Gelen istekleri filtreler
    ve koruma saglar.

    Attributes:
        _whitelist: Beyaz liste (IP).
        _blacklist: Kara liste (IP).
        _rules: Firewall kurallari.
        _blocked_requests: Engellenen istekler.
        _geo_blocks: Engellenen ulkeler.
        _request_counts: IP istek sayaclari.
    """

    def __init__(self) -> None:
        """Guvenlik duvarini baslatir."""
        self._whitelist: set[str] = set()
        self._blacklist: set[str] = set()
        self._rules: list[dict[str, Any]] = []
        self._blocked_requests: list[dict[str, Any]] = []
        self._geo_blocks: set[str] = set()
        self._request_counts: dict[str, int] = {}
        self._rate_limits: dict[str, int] = {}

        logger.info("Firewall baslatildi")

    def add_to_whitelist(self, ip: str) -> None:
        """IP'yi beyaz listeye ekler.

        Args:
            ip: IP adresi.
        """
        self._whitelist.add(ip)
        self._blacklist.discard(ip)

    def add_to_blacklist(self, ip: str) -> None:
        """IP'yi kara listeye ekler.

        Args:
            ip: IP adresi.
        """
        self._blacklist.add(ip)
        self._whitelist.discard(ip)

    def remove_from_whitelist(self, ip: str) -> bool:
        """IP'yi beyaz listeden kaldirir.

        Args:
            ip: IP adresi.

        Returns:
            Basarili ise True.
        """
        if ip in self._whitelist:
            self._whitelist.discard(ip)
            return True
        return False

    def remove_from_blacklist(self, ip: str) -> bool:
        """IP'yi kara listeden kaldirir.

        Args:
            ip: IP adresi.

        Returns:
            Basarili ise True.
        """
        if ip in self._blacklist:
            self._blacklist.discard(ip)
            return True
        return False

    def check_request(
        self,
        ip: str,
        path: str = "/",
        country: str = "",
    ) -> dict[str, Any]:
        """Istegi kontrol eder.

        Args:
            ip: Kaynak IP.
            path: Istek yolu.
            country: Ulke kodu.

        Returns:
            Kontrol sonucu.
        """
        # Beyaz liste - her zaman izin ver
        if ip in self._whitelist:
            return {
                "action": FirewallAction.ALLOW.value,
                "reason": "whitelist",
            }

        # Kara liste - her zaman engelle
        if ip in self._blacklist:
            self._record_block(ip, path, "blacklist")
            return {
                "action": FirewallAction.BLOCK.value,
                "reason": "blacklist",
            }

        # Cografi engelleme
        if country and country.upper() in self._geo_blocks:
            self._record_block(ip, path, "geo_block")
            return {
                "action": FirewallAction.BLOCK.value,
                "reason": f"geo_block:{country}",
            }

        # Rate limit
        rate_result = self._check_rate_limit(ip)
        if rate_result:
            self._record_block(ip, path, "rate_limit")
            return rate_result

        # Kural kontrolu
        for rule in self._rules:
            if self._matches_rule(rule, ip, path):
                action = rule.get(
                    "action", FirewallAction.BLOCK.value,
                )
                if action == FirewallAction.BLOCK.value:
                    self._record_block(
                        ip, path, rule.get("name", "rule"),
                    )
                return {
                    "action": action,
                    "reason": rule.get("name", "rule"),
                }

        # Istek say
        self._request_counts[ip] = (
            self._request_counts.get(ip, 0) + 1
        )

        return {
            "action": FirewallAction.ALLOW.value,
            "reason": "default_allow",
        }

    def add_rule(
        self,
        name: str,
        action: FirewallAction,
        path_pattern: str = "",
        ip_pattern: str = "",
    ) -> dict[str, Any]:
        """Firewall kurali ekler.

        Args:
            name: Kural adi.
            action: Aksiyon.
            path_pattern: Yol deseni.
            ip_pattern: IP deseni.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "action": action.value,
            "path_pattern": path_pattern,
            "ip_pattern": ip_pattern,
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._rules.append(rule)
        return rule

    def set_rate_limit(
        self,
        ip: str,
        max_requests: int,
    ) -> None:
        """IP icin rate limit ayarlar.

        Args:
            ip: IP adresi.
            max_requests: Maks istek (periyot basina).
        """
        self._rate_limits[ip] = max(1, max_requests)

    def set_global_rate_limit(
        self,
        max_requests: int,
    ) -> None:
        """Global rate limit ayarlar.

        Args:
            max_requests: Maks istek.
        """
        self._rate_limits["__global__"] = max(1, max_requests)

    def block_country(self, country_code: str) -> None:
        """Ulkeyi engeller.

        Args:
            country_code: Ulke kodu (ornek: CN, RU).
        """
        self._geo_blocks.add(country_code.upper())

    def unblock_country(self, country_code: str) -> bool:
        """Ulke engelini kaldirir.

        Args:
            country_code: Ulke kodu.

        Returns:
            Basarili ise True.
        """
        code = country_code.upper()
        if code in self._geo_blocks:
            self._geo_blocks.discard(code)
            return True
        return False

    def get_blocked_requests(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Engellenen istekleri getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Engellenen istek listesi.
        """
        return self._blocked_requests[-limit:]

    def _check_rate_limit(
        self,
        ip: str,
    ) -> dict[str, Any] | None:
        """Rate limit kontrolu yapar.

        Args:
            ip: IP adresi.

        Returns:
            Engelleme sonucu veya None.
        """
        # IP ozel limit
        limit = self._rate_limits.get(ip)
        if not limit:
            limit = self._rate_limits.get("__global__")
        if not limit:
            return None

        current = self._request_counts.get(ip, 0)
        if current >= limit:
            return {
                "action": FirewallAction.RATE_LIMIT.value,
                "reason": "rate_limit_exceeded",
                "current": current,
                "limit": limit,
            }
        return None

    def _matches_rule(
        self,
        rule: dict[str, Any],
        ip: str,
        path: str,
    ) -> bool:
        """Kuraldin eslesmesini kontrol eder.

        Args:
            rule: Kural.
            ip: IP.
            path: Yol.

        Returns:
            Eslesiyor ise True.
        """
        if not rule.get("enabled", True):
            return False

        path_pattern = rule.get("path_pattern", "")
        ip_pattern = rule.get("ip_pattern", "")

        if path_pattern and path_pattern in path:
            return True
        if ip_pattern and ip_pattern in ip:
            return True

        return False

    def _record_block(
        self,
        ip: str,
        path: str,
        reason: str,
    ) -> None:
        """Engelleme kaydeder.

        Args:
            ip: IP.
            path: Yol.
            reason: Sebep.
        """
        self._blocked_requests.append({
            "ip": ip,
            "path": path,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def reset_counters(self) -> None:
        """Istek sayaclarini sifirlar."""
        self._request_counts.clear()

    @property
    def whitelist_count(self) -> int:
        """Beyaz liste sayisi."""
        return len(self._whitelist)

    @property
    def blacklist_count(self) -> int:
        """Kara liste sayisi."""
        return len(self._blacklist)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def blocked_count(self) -> int:
        """Engellenen istek sayisi."""
        return len(self._blocked_requests)

    @property
    def geo_block_count(self) -> int:
        """Engellenen ulke sayisi."""
        return len(self._geo_blocks)
