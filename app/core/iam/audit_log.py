"""ATLAS IAM Denetim Gunlugu modulu.

Erisim loglama, degisiklik takibi,
giris gecmisi, uyumluluk.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IAMAuditLog:
    """IAM denetim gunlugu.

    Tum IAM islemlerini kaydeder.

    Attributes:
        _entries: Gunluk kayitlari.
        _login_history: Giris gecmisi.
    """

    def __init__(
        self,
        max_entries: int = 10000,
        retention_days: int = 90,
    ) -> None:
        """Denetim gunlugunu baslatir.

        Args:
            max_entries: Maks kayit sayisi.
            retention_days: Saklama suresi (gun).
        """
        self._entries: list[dict[str, Any]] = []
        self._login_history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._change_log: list[
            dict[str, Any]
        ] = []
        self._max_entries = max_entries
        self._retention_days = retention_days
        self._stats = {
            "total_entries": 0,
            "logins": 0,
            "failures": 0,
            "changes": 0,
        }

        logger.info(
            "IAMAuditLog baslatildi",
        )

    def log_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool = True,
        ip_address: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Erisim kaydeder.

        Args:
            user_id: Kullanici ID.
            resource: Kaynak.
            action: Aksiyon.
            allowed: Izin verildi mi.
            ip_address: IP adresi.
            details: Ek detaylar.

        Returns:
            Kayit bilgisi.
        """
        entry = {
            "type": "access",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "allowed": allowed,
            "ip_address": ip_address,
            "details": details or {},
            "timestamp": time.time(),
        }

        self._add_entry(entry)

        if not allowed:
            self._stats["failures"] += 1

        return {
            "logged": True,
            "type": "access",
        }

    def log_login(
        self,
        user_id: str,
        success: bool = True,
        ip_address: str = "",
        user_agent: str = "",
        method: str = "password",
    ) -> dict[str, Any]:
        """Giris kaydeder.

        Args:
            user_id: Kullanici ID.
            success: Basarili mi.
            ip_address: IP adresi.
            user_agent: Kullanici agenti.
            method: Giris yontemi.

        Returns:
            Kayit bilgisi.
        """
        entry = {
            "type": "login",
            "user_id": user_id,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "method": method,
            "timestamp": time.time(),
        }

        self._add_entry(entry)

        # Giris gecmisi
        if user_id not in self._login_history:
            self._login_history[user_id] = []
        self._login_history[user_id].append(entry)

        self._stats["logins"] += 1
        if not success:
            self._stats["failures"] += 1

        return {
            "logged": True,
            "type": "login",
        }

    def log_change(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        old_value: Any = None,
        new_value: Any = None,
    ) -> dict[str, Any]:
        """Degisiklik kaydeder.

        Args:
            user_id: Degisikligi yapan.
            entity_type: Varlik tipi.
            entity_id: Varlik ID.
            action: Aksiyon.
            old_value: Eski deger.
            new_value: Yeni deger.

        Returns:
            Kayit bilgisi.
        """
        entry = {
            "type": "change",
            "user_id": user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": time.time(),
        }

        self._add_entry(entry)
        self._change_log.append(entry)
        self._stats["changes"] += 1

        return {
            "logged": True,
            "type": "change",
        }

    def get_login_history(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Giris gecmisini getirir.

        Args:
            user_id: Kullanici ID.
            limit: Limit.

        Returns:
            Giris gecmisi.
        """
        history = self._login_history.get(
            user_id, [],
        )
        return history[-limit:]

    def get_changes(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Degisiklikleri getirir.

        Args:
            entity_type: Varlik tipi filtresi.
            entity_id: Varlik ID filtresi.
            limit: Limit.

        Returns:
            Degisiklik listesi.
        """
        changes = self._change_log

        if entity_type:
            changes = [
                c for c in changes
                if c["entity_type"] == entity_type
            ]

        if entity_id:
            changes = [
                c for c in changes
                if c["entity_id"] == entity_id
            ]

        return changes[-limit:]

    def get_entries(
        self,
        entry_type: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kayitlari getirir.

        Args:
            entry_type: Kayit tipi filtresi.
            user_id: Kullanici ID filtresi.
            limit: Limit.

        Returns:
            Kayit listesi.
        """
        entries = self._entries

        if entry_type:
            entries = [
                e for e in entries
                if e["type"] == entry_type
            ]

        if user_id:
            entries = [
                e for e in entries
                if e.get("user_id") == user_id
            ]

        return entries[-limit:]

    def get_failed_logins(
        self,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Basarisiz girisleri getirir.

        Args:
            user_id: Kullanici ID filtresi.
            limit: Limit.

        Returns:
            Basarisiz giris listesi.
        """
        entries = [
            e for e in self._entries
            if e["type"] == "login"
            and not e.get("success", True)
        ]

        if user_id:
            entries = [
                e for e in entries
                if e.get("user_id") == user_id
            ]

        return entries[-limit:]

    def get_compliance_report(
        self,
    ) -> dict[str, Any]:
        """Uyumluluk raporu olusturur.

        Returns:
            Uyumluluk raporu.
        """
        total = len(self._entries)
        logins = self._stats["logins"]
        failures = self._stats["failures"]
        changes = self._stats["changes"]

        return {
            "total_entries": total,
            "login_events": logins,
            "failed_events": failures,
            "change_events": changes,
            "failure_rate": (
                failures / max(total, 1)
            ),
            "users_tracked": len(
                self._login_history,
            ),
            "retention_days": self._retention_days,
            "timestamp": time.time(),
        }

    def search(
        self,
        query: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kayitlarda arama yapar.

        Args:
            query: Arama sorgusu.
            limit: Limit.

        Returns:
            Eslesen kayitlar.
        """
        results = []
        q = query.lower()

        for entry in self._entries:
            text = str(entry).lower()
            if q in text:
                results.append(entry)

        return results[-limit:]

    def cleanup(
        self,
        max_age_days: int | None = None,
    ) -> int:
        """Eski kayitlari temizler.

        Args:
            max_age_days: Maks yas (gun).

        Returns:
            Temizlenen kayit sayisi.
        """
        days = max_age_days or self._retention_days
        cutoff = time.time() - (days * 86400)

        before = len(self._entries)
        self._entries = [
            e for e in self._entries
            if e.get("timestamp", 0) > cutoff
        ]
        self._change_log = [
            c for c in self._change_log
            if c.get("timestamp", 0) > cutoff
        ]

        return before - len(self._entries)

    def _add_entry(
        self,
        entry: dict[str, Any],
    ) -> None:
        """Kayit ekler.

        Args:
            entry: Kayit.
        """
        self._entries.append(entry)
        self._stats["total_entries"] += 1

        # Maks kayit limiti
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[
                -self._max_entries:
            ]

    @property
    def entry_count(self) -> int:
        """Kayit sayisi."""
        return len(self._entries)

    @property
    def login_count(self) -> int:
        """Giris kaydi sayisi."""
        return self._stats["logins"]

    @property
    def failure_count(self) -> int:
        """Basarisizlik kaydi sayisi."""
        return self._stats["failures"]

    @property
    def change_count(self) -> int:
        """Degisiklik kaydi sayisi."""
        return self._stats["changes"]
