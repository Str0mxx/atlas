"""ATLAS Sürekli Tarayıcı modülü.

Arka plan taraması, çoklu kaynak izleme,
örüntü tespiti, değişiklik algılama, zamanlanmış taramalar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContinuousScanner:
    """Sürekli tarayıcı.

    Çoklu kaynakları arka planda tarar.

    Attributes:
        _scans: Tarama kayıtları.
        _sources: Kayıtlı kaynaklar.
        _baselines: Kaynak bazal değerleri.
        _schedules: Zamanlanmış taramalar.
    """

    def __init__(
        self,
        scan_interval: int = 300,
    ) -> None:
        """Tarayıcıyı başlatır.

        Args:
            scan_interval: Tarama aralığı (saniye).
        """
        self._scans: list[dict[str, Any]] = []
        self._sources: dict[str, dict[str, Any]] = {}
        self._baselines: dict[str, dict[str, Any]] = {}
        self._schedules: list[dict[str, Any]] = []
        self._scan_interval = scan_interval
        self._counter = 0
        self._stats = {
            "total_scans": 0,
            "findings_detected": 0,
            "patterns_found": 0,
            "changes_detected": 0,
        }

        logger.info(
            "ContinuousScanner baslatildi",
        )

    def register_source(
        self,
        name: str,
        source_type: str = "system",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tarama kaynağı kaydeder.

        Args:
            name: Kaynak adı.
            source_type: Kaynak tipi.
            config: Kaynak yapılandırması.

        Returns:
            Kayıt bilgisi.
        """
        source = {
            "name": name,
            "source_type": source_type,
            "config": config or {},
            "active": True,
            "registered_at": time.time(),
            "last_scanned": None,
            "scan_count": 0,
        }
        self._sources[name] = source

        return {
            "source": name,
            "registered": True,
        }

    def scan_source(
        self,
        name: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tek kaynağı tarar.

        Args:
            name: Kaynak adı.
            data: Tarama verisi.

        Returns:
            Tarama sonucu.
        """
        if name not in self._sources:
            return {"error": "source_not_found"}

        self._counter += 1
        sid = f"scan_{self._counter}"
        now = time.time()

        findings = self._analyze_data(
            name, data or {},
        )

        # Değişiklik tespiti
        changes = self._detect_changes(
            name, data or {},
        )

        scan = {
            "scan_id": sid,
            "source": name,
            "findings": findings,
            "changes": changes,
            "finding_count": len(findings),
            "change_count": len(changes),
            "timestamp": now,
        }
        self._scans.append(scan)
        self._sources[name]["last_scanned"] = now
        self._sources[name]["scan_count"] += 1
        self._stats["total_scans"] += 1
        self._stats["findings_detected"] += len(
            findings,
        )
        self._stats["changes_detected"] += len(
            changes,
        )

        # Bazal güncelle
        self._baselines[name] = data or {}

        return scan

    def scan_all(
        self,
        data_map: dict[str, dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Tüm kaynakları tarar.

        Args:
            data_map: Kaynak-veri eşlemesi.

        Returns:
            Toplu tarama sonucu.
        """
        data_map = data_map or {}
        results = []
        for name in self._sources:
            if self._sources[name]["active"]:
                result = self.scan_source(
                    name,
                    data_map.get(name),
                )
                results.append(result)

        total_findings = sum(
            r.get("finding_count", 0)
            for r in results
        )

        return {
            "sources_scanned": len(results),
            "total_findings": total_findings,
            "results": results,
        }

    def _analyze_data(
        self,
        source: str,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Veriyi analiz eder.

        Args:
            source: Kaynak adı.
            data: Veri.

        Returns:
            Bulgular.
        """
        findings = []

        # Eşik aşımı kontrolü
        for key, value in data.items():
            if isinstance(value, (int, float)):
                if value > 100:
                    findings.append({
                        "type": "threshold_exceeded",
                        "key": key,
                        "value": value,
                        "source": source,
                    })
                elif value < 0:
                    findings.append({
                        "type": "negative_value",
                        "key": key,
                        "value": value,
                        "source": source,
                    })

        # Hata veya uyarı kontrolü
        if data.get("error"):
            findings.append({
                "type": "error_detected",
                "detail": data["error"],
                "source": source,
            })
        if data.get("warning"):
            findings.append({
                "type": "warning_detected",
                "detail": data["warning"],
                "source": source,
            })

        return findings

    def _detect_changes(
        self,
        source: str,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Değişiklikleri tespit eder.

        Args:
            source: Kaynak adı.
            data: Yeni veri.

        Returns:
            Değişiklikler.
        """
        changes = []
        baseline = self._baselines.get(
            source, {},
        )

        for key, new_val in data.items():
            old_val = baseline.get(key)
            if old_val is not None and old_val != new_val:
                changes.append({
                    "key": key,
                    "old_value": old_val,
                    "new_value": new_val,
                    "source": source,
                })

        return changes

    def detect_patterns(
        self,
        source: str | None = None,
        min_occurrences: int = 3,
    ) -> dict[str, Any]:
        """Örüntü tespit eder.

        Args:
            source: Kaynak filtresi.
            min_occurrences: Min tekrar.

        Returns:
            Örüntü bilgisi.
        """
        scans = self._scans
        if source:
            scans = [
                s for s in scans
                if s.get("source") == source
            ]

        # Bulgu tiplerini say
        type_counts: dict[str, int] = {}
        for scan in scans:
            for finding in scan.get("findings", []):
                ftype = finding.get("type", "unknown")
                type_counts[ftype] = (
                    type_counts.get(ftype, 0) + 1
                )

        patterns = [
            {"type": t, "count": c}
            for t, c in type_counts.items()
            if c >= min_occurrences
        ]
        self._stats["patterns_found"] += len(
            patterns,
        )

        return {
            "patterns": patterns,
            "pattern_count": len(patterns),
        }

    def schedule_scan(
        self,
        source: str,
        interval_seconds: int = 300,
        priority: int = 5,
    ) -> dict[str, Any]:
        """Zamanlanmış tarama ekler.

        Args:
            source: Kaynak adı.
            interval_seconds: Tarama aralığı.
            priority: Öncelik.

        Returns:
            Zamanlama bilgisi.
        """
        schedule = {
            "source": source,
            "interval": interval_seconds,
            "priority": priority,
            "active": True,
            "created_at": time.time(),
        }
        self._schedules.append(schedule)

        return {
            "source": source,
            "scheduled": True,
            "interval": interval_seconds,
        }

    def get_scan_history(
        self,
        source: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Tarama geçmişini getirir.

        Args:
            source: Kaynak filtresi.
            limit: Maks kayıt.

        Returns:
            Tarama listesi.
        """
        results = self._scans
        if source:
            results = [
                s for s in results
                if s.get("source") == source
            ]
        return list(results[-limit:])

    @property
    def scan_count(self) -> int:
        """Toplam tarama sayısı."""
        return self._stats["total_scans"]

    @property
    def source_count(self) -> int:
        """Kaynak sayısı."""
        return len(self._sources)

    @property
    def active_source_count(self) -> int:
        """Aktif kaynak sayısı."""
        return sum(
            1 for s in self._sources.values()
            if s.get("active")
        )
