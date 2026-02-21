"""Injection tehdit istihbarat yoneticisi.

Bilinen kaliplar, guncellemeler,
topluluk raporlari ve engel listesi.
"""

import logging
import time
from typing import Any
from uuid import uuid4

from app.models.injectionprotect_models import (
    SeverityLevel,
    ThreatPattern,
    ThreatType,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 10000
_MAX_HISTORY = 10000

# Varsayilan tehdit kalibi havuzu
_DEFAULT_THREAT_DB: list[
    dict[str, Any]
] = [
    {
        "pattern": "ignore previous instructions",
        "threat_type": ThreatType.PROMPT_INJECTION,
        "severity": SeverityLevel.HIGH,
        "source": "builtin",
    },
    {
        "pattern": "you are now DAN",
        "threat_type": ThreatType.JAILBREAK,
        "severity": SeverityLevel.HIGH,
        "source": "builtin",
    },
    {
        "pattern": "UNION SELECT",
        "threat_type": ThreatType.SQL_INJECTION,
        "severity": SeverityLevel.CRITICAL,
        "source": "builtin",
    },
    {
        "pattern": "<script>alert",
        "threat_type": ThreatType.XSS,
        "severity": SeverityLevel.HIGH,
        "source": "builtin",
    },
    {
        "pattern": "; rm -rf /",
        "threat_type": ThreatType.COMMAND_INJECTION,
        "severity": SeverityLevel.CRITICAL,
        "source": "builtin",
    },
    {
        "pattern": "../../etc/passwd",
        "threat_type": ThreatType.PATH_TRAVERSAL,
        "severity": SeverityLevel.HIGH,
        "source": "builtin",
    },
    {
        "pattern": "developer mode enabled",
        "threat_type": ThreatType.JAILBREAK,
        "severity": SeverityLevel.HIGH,
        "source": "builtin",
    },
    {
        "pattern": "send this data to",
        "threat_type": ThreatType.DATA_EXFILTRATION,
        "severity": SeverityLevel.HIGH,
        "source": "builtin",
    },
]


class InjectionThreatIntelligence:
    """Injection tehdit istihbarat yoneticisi.

    Bilinen kaliplar, guncellemeler,
    topluluk raporlari ve engel listesi.

    Attributes:
        _patterns: Tehdit kalibi deposu.
    """

    def __init__(
        self,
        auto_load_defaults: bool = True,
    ) -> None:
        """InjectionThreatIntelligence baslatir.

        Args:
            auto_load_defaults: Varsayilanlari yukle.
        """
        self._patterns: dict[
            str, ThreatPattern
        ] = {}
        self._pattern_order: list[str] = []
        self._blocklist: set[str] = set()
        self._allowlist: set[str] = set()
        self._community_reports: list[
            dict[str, Any]
        ] = []
        self._total_ops: int = 0
        self._total_patterns: int = 0
        self._total_reports: int = 0
        self._total_lookups: int = 0
        self._total_hits: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

        if auto_load_defaults:
            self._load_defaults()

        logger.info(
            "InjectionThreatIntelligence "
            "baslatildi patterns=%d",
            len(self._patterns),
        )

    # ---- Yukleme ----

    def _load_defaults(self) -> None:
        """Varsayilan tehdit kaliplarini yukler."""
        for item in _DEFAULT_THREAT_DB:
            self.add_pattern(
                pattern=item["pattern"],
                threat_type=item["threat_type"],
                severity=item["severity"],
                source=item.get(
                    "source", "builtin",
                ),
            )

    # ---- Kalip Yonetimi ----

    def add_pattern(
        self,
        pattern: str,
        threat_type: ThreatType = (
            ThreatType.OTHER
        ),
        severity: SeverityLevel = (
            SeverityLevel.MEDIUM
        ),
        description: str = "",
        source: str = "manual",
    ) -> ThreatPattern:
        """Tehdit kalibi ekler.

        Args:
            pattern: Kalip metni.
            threat_type: Tehdit tipi.
            severity: Ciddiyet seviyesi.
            description: Aciklama.
            source: Kaynak.

        Returns:
            Tehdit kalibi.
        """
        if len(self._patterns) >= _MAX_RECORDS:
            self._rotate()

        pattern_id = str(uuid4())[:8]
        now = time.time()
        self._total_patterns += 1
        self._total_ops += 1

        tp = ThreatPattern(
            pattern_id=pattern_id,
            pattern=pattern,
            threat_type=threat_type,
            severity=severity,
            description=description,
            source=source,
            enabled=True,
            hit_count=0,
            created_at=now,
            updated_at=now,
        )

        self._patterns[pattern_id] = tp
        self._pattern_order.append(pattern_id)

        self._record_history(
            "add_pattern",
            pattern_id,
            f"type={threat_type.value} "
            f"source={source}",
        )

        return tp

    def remove_pattern(
        self,
        pattern_id: str,
    ) -> bool:
        """Kalip siler.

        Args:
            pattern_id: Kalip ID.

        Returns:
            Basarili ise True.
        """
        if pattern_id not in self._patterns:
            return False
        del self._patterns[pattern_id]
        if pattern_id in self._pattern_order:
            self._pattern_order.remove(
                pattern_id,
            )
        self._total_ops += 1
        return True

    def enable_pattern(
        self,
        pattern_id: str,
    ) -> bool:
        """Kalibi aktiflestirir.

        Args:
            pattern_id: Kalip ID.

        Returns:
            Basarili ise True.
        """
        tp = self._patterns.get(pattern_id)
        if not tp:
            return False
        tp.enabled = True
        tp.updated_at = time.time()
        self._total_ops += 1
        return True

    def disable_pattern(
        self,
        pattern_id: str,
    ) -> bool:
        """Kalibi deaktiflestirir.

        Args:
            pattern_id: Kalip ID.

        Returns:
            Basarili ise True.
        """
        tp = self._patterns.get(pattern_id)
        if not tp:
            return False
        tp.enabled = False
        tp.updated_at = time.time()
        self._total_ops += 1
        return True

    # ---- Arama/Esleme ----

    def lookup(
        self,
        text: str,
    ) -> list[ThreatPattern]:
        """Metni tehdit kaliplarinda arar.

        Args:
            text: Aranacak metin.

        Returns:
            Eslesen kaliplar.
        """
        self._total_lookups += 1
        self._total_ops += 1
        text_lower = text.lower()
        matches: list[ThreatPattern] = []

        for tp in self._patterns.values():
            if not tp.enabled:
                continue
            if tp.pattern.lower() in text_lower:
                tp.hit_count += 1
                self._total_hits += 1
                matches.append(tp)

        return matches

    def is_known_threat(
        self,
        text: str,
    ) -> bool:
        """Bilinen tehdit mi kontrol eder.

        Args:
            text: Kontrol edilecek metin.

        Returns:
            Bilinen tehdit ise True.
        """
        return len(self.lookup(text)) > 0

    def get_threat_info(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Tehdit bilgisi dondurur.

        Args:
            text: Aranacak metin.

        Returns:
            Tehdit bilgisi.
        """
        matches = self.lookup(text)
        if not matches:
            return {
                "is_threat": False,
                "matches": 0,
            }

        # En yuksek ciddiyet
        severity_order = [
            "info", "low", "medium",
            "high", "critical",
        ]
        max_sev = max(
            matches,
            key=lambda m: severity_order.index(
                m.severity.value,
            ),
        )

        return {
            "is_threat": True,
            "matches": len(matches),
            "max_severity": (
                max_sev.severity.value
            ),
            "threat_types": list({
                m.threat_type.value
                for m in matches
            }),
            "patterns": [
                m.pattern for m in matches
            ],
        }

    def search_patterns(
        self,
        query: str,
        threat_type: str = "",
        severity: str = "",
        limit: int = 50,
    ) -> list[ThreatPattern]:
        """Kaliplari arar.

        Args:
            query: Arama sorgusu.
            threat_type: Tehdit tipi filtresi.
            severity: Ciddiyet filtresi.
            limit: Maks sayi.

        Returns:
            Eslesen kaliplar.
        """
        q = query.lower()
        result: list[ThreatPattern] = []

        for tp in self._patterns.values():
            if q and q not in tp.pattern.lower():
                continue
            if (
                threat_type
                and tp.threat_type.value
                != threat_type
            ):
                continue
            if (
                severity
                and tp.severity.value != severity
            ):
                continue
            result.append(tp)
            if len(result) >= limit:
                break

        return result

    # ---- Engel Listesi ----

    def add_to_blocklist(
        self,
        text: str,
    ) -> None:
        """Engel listesine ekler.

        Args:
            text: Engellenecek metin.
        """
        self._blocklist.add(text.lower())
        self._total_ops += 1

    def remove_from_blocklist(
        self,
        text: str,
    ) -> bool:
        """Engel listesinden cikarir.

        Args:
            text: Cikarilacak metin.

        Returns:
            Basarili ise True.
        """
        key = text.lower()
        if key in self._blocklist:
            self._blocklist.discard(key)
            self._total_ops += 1
            return True
        return False

    def is_blocked(
        self,
        text: str,
    ) -> bool:
        """Engelli mi kontrol eder.

        Args:
            text: Kontrol edilecek metin.

        Returns:
            Engelli ise True.
        """
        text_lower = text.lower()
        for blocked in self._blocklist:
            if blocked in text_lower:
                return True
        return False

    def get_blocklist(self) -> list[str]:
        """Engel listesini dondurur.

        Returns:
            Engel listesi.
        """
        return sorted(self._blocklist)

    # ---- Izin Listesi ----

    def add_to_allowlist(
        self,
        text: str,
    ) -> None:
        """Izin listesine ekler.

        Args:
            text: Izin verilecek metin.
        """
        self._allowlist.add(text.lower())
        self._total_ops += 1

    def remove_from_allowlist(
        self,
        text: str,
    ) -> bool:
        """Izin listesinden cikarir.

        Args:
            text: Cikarilacak metin.

        Returns:
            Basarili ise True.
        """
        key = text.lower()
        if key in self._allowlist:
            self._allowlist.discard(key)
            self._total_ops += 1
            return True
        return False

    def is_allowed(
        self,
        text: str,
    ) -> bool:
        """Izinli mi kontrol eder.

        Args:
            text: Kontrol edilecek metin.

        Returns:
            Izinli ise True.
        """
        text_lower = text.lower()
        for allowed in self._allowlist:
            if allowed in text_lower:
                return True
        return False

    # ---- Topluluk Raporlari ----

    def submit_report(
        self,
        pattern: str,
        threat_type: ThreatType = (
            ThreatType.OTHER
        ),
        severity: SeverityLevel = (
            SeverityLevel.MEDIUM
        ),
        reporter: str = "",
        details: str = "",
    ) -> dict[str, Any]:
        """Topluluk raporu gonderir.

        Args:
            pattern: Kalip metni.
            threat_type: Tehdit tipi.
            severity: Ciddiyet seviyesi.
            reporter: Raporlayan.
            details: Detaylar.

        Returns:
            Rapor bilgisi.
        """
        report_id = str(uuid4())[:8]
        now = time.time()
        self._total_reports += 1
        self._total_ops += 1

        report = {
            "report_id": report_id,
            "pattern": pattern,
            "threat_type": threat_type.value,
            "severity": severity.value,
            "reporter": reporter,
            "details": details,
            "status": "pending",
            "submitted_at": now,
        }

        self._community_reports.append(report)

        # Otomatik onay (critical icin)
        if severity == SeverityLevel.CRITICAL:
            report["status"] = "auto_approved"
            self.add_pattern(
                pattern=pattern,
                threat_type=threat_type,
                severity=severity,
                source=f"community:{reporter}",
            )

        self._record_history(
            "submit_report",
            report_id,
            f"type={threat_type.value} "
            f"reporter={reporter}",
        )

        return report

    def approve_report(
        self,
        report_id: str,
    ) -> bool:
        """Raporu onaylar.

        Args:
            report_id: Rapor ID.

        Returns:
            Basarili ise True.
        """
        for report in self._community_reports:
            if (
                report["report_id"] == report_id
                and report["status"] == "pending"
            ):
                report["status"] = "approved"
                self.add_pattern(
                    pattern=report["pattern"],
                    threat_type=ThreatType(
                        report["threat_type"],
                    ),
                    severity=SeverityLevel(
                        report["severity"],
                    ),
                    source=(
                        f"community:"
                        f"{report['reporter']}"
                    ),
                )
                self._total_ops += 1
                return True
        return False

    def reject_report(
        self,
        report_id: str,
    ) -> bool:
        """Raporu reddeder.

        Args:
            report_id: Rapor ID.

        Returns:
            Basarili ise True.
        """
        for report in self._community_reports:
            if (
                report["report_id"] == report_id
                and report["status"] == "pending"
            ):
                report["status"] = "rejected"
                self._total_ops += 1
                return True
        return False

    def list_reports(
        self,
        status: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Raporlari listeler.

        Args:
            status: Durum filtresi.
            limit: Maks sayi.

        Returns:
            Rapor listesi.
        """
        result = []
        for report in reversed(
            self._community_reports,
        ):
            if (
                status
                and report["status"] != status
            ):
                continue
            result.append(report)
            if len(result) >= limit:
                break
        return result

    # ---- Sorgulama ----

    def get_pattern(
        self,
        pattern_id: str,
    ) -> ThreatPattern | None:
        """Kalip dondurur.

        Args:
            pattern_id: Kalip ID.

        Returns:
            Kalip veya None.
        """
        return self._patterns.get(pattern_id)

    def list_patterns(
        self,
        enabled_only: bool = False,
        threat_type: str = "",
        limit: int = 50,
    ) -> list[ThreatPattern]:
        """Kaliplari listeler.

        Args:
            enabled_only: Sadece aktif.
            threat_type: Tehdit tipi filtresi.
            limit: Maks sayi.

        Returns:
            Kalip listesi.
        """
        ids = list(
            reversed(self._pattern_order),
        )
        result: list[ThreatPattern] = []

        for pid in ids:
            tp = self._patterns.get(pid)
            if not tp:
                continue
            if enabled_only and not tp.enabled:
                continue
            if (
                threat_type
                and tp.threat_type.value
                != threat_type
            ):
                continue
            result.append(tp)
            if len(result) >= limit:
                break

        return result

    def get_top_patterns(
        self,
        limit: int = 10,
    ) -> list[ThreatPattern]:
        """En cok eslesen kaliplari dondurur.

        Args:
            limit: Maks sayi.

        Returns:
            Sirali kalip listesi.
        """
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.hit_count,
            reverse=True,
        )
        return sorted_patterns[:limit]

    # ---- Gosterim ----

    def format_pattern(
        self,
        pattern_id: str,
    ) -> str:
        """Kalibi formatlar.

        Args:
            pattern_id: Kalip ID.

        Returns:
            Formatlenmis metin.
        """
        tp = self._patterns.get(pattern_id)
        if not tp:
            return ""

        parts = [
            f"Pattern ID: {tp.pattern_id}",
            f"Pattern: {tp.pattern}",
            f"Type: {tp.threat_type.value}",
            f"Severity: {tp.severity.value}",
            f"Hits: {tp.hit_count}",
            f"Enabled: {tp.enabled}",
            f"Source: {tp.source}",
        ]
        return "\n".join(parts)

    def format_summary(self) -> str:
        """Ozet formatlar.

        Returns:
            Formatlenmis metin.
        """
        type_dist: dict[str, int] = {}
        sev_dist: dict[str, int] = {}
        for tp in self._patterns.values():
            t = tp.threat_type.value
            type_dist[t] = (
                type_dist.get(t, 0) + 1
            )
            s = tp.severity.value
            sev_dist[s] = (
                sev_dist.get(s, 0) + 1
            )

        parts = [
            f"Patterns: {len(self._patterns)}",
            f"Blocklist: {len(self._blocklist)}",
            f"Reports: "
            f"{len(self._community_reports)}",
        ]

        if type_dist:
            parts.append("Types:")
            for t, c in type_dist.items():
                parts.append(f"  {t}: {c}")

        if sev_dist:
            parts.append("Severity:")
            for s, c in sev_dist.items():
                parts.append(f"  {s}: {c}")

        return "\n".join(parts)

    # ---- Temizlik ----

    def clear_patterns(self) -> int:
        """Kaliplari temizler.

        Returns:
            Silinen sayi.
        """
        count = len(self._patterns)
        self._patterns.clear()
        self._pattern_order.clear()
        self._total_ops += 1
        return count

    def clear_all(self) -> int:
        """Tum verileri temizler.

        Returns:
            Silinen sayi.
        """
        count = len(self._patterns)
        self._patterns.clear()
        self._pattern_order.clear()
        self._blocklist.clear()
        self._allowlist.clear()
        self._community_reports.clear()
        self._total_ops += 1
        return count

    # ---- Dahili ----

    def _rotate(self) -> int:
        """Eski kayitlari temizler."""
        keep = _MAX_RECORDS // 2
        if len(self._pattern_order) <= keep:
            return 0

        to_remove = self._pattern_order[:-keep]
        for pid in to_remove:
            self._patterns.pop(pid, None)

        self._pattern_order = (
            self._pattern_order[-keep:]
        )
        return len(to_remove)

    def _record_history(
        self,
        action: str,
        record_id: str,
        detail: str,
    ) -> None:
        """Aksiyonu kaydeder."""
        self._history.append({
            "action": action,
            "record_id": record_id,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self._history) > _MAX_HISTORY:
            self._history = (
                self._history[-5000:]
            )

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gecmisi dondurur."""
        return list(
            reversed(
                self._history[-limit:],
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur."""
        return {
            "total_patterns": len(
                self._patterns,
            ),
            "total_reports": (
                self._total_reports
            ),
            "total_lookups": (
                self._total_lookups
            ),
            "total_hits": self._total_hits,
            "blocklist_size": len(
                self._blocklist,
            ),
            "allowlist_size": len(
                self._allowlist,
            ),
            "community_reports": len(
                self._community_reports,
            ),
            "total_ops": self._total_ops,
        }
