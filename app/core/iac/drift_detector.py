"""ATLAS IaC Kayma Tespiti modulu.

Yapilandirma kaymasi, durum karsilastirma,
uyari uretimi, otomatik duzeltme
ve raporlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IaCDriftDetector:
    """IaC kayma tespitcisi.

    Yapilandirma kaymasini tespit eder.

    Attributes:
        _baselines: Temel durumlar.
        _drifts: Tespit edilen kaymalar.
    """

    def __init__(self) -> None:
        """Tespitciyi baslatir."""
        self._baselines: dict[
            str, dict[str, Any]
        ] = {}
        self._drifts: list[
            dict[str, Any]
        ] = []
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._remediation_rules: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "checks": 0,
            "drifts_found": 0,
            "remediations": 0,
        }

        logger.info(
            "IaCDriftDetector baslatildi",
        )

    def set_baseline(
        self,
        resource_key: str,
        desired_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Temel durumu ayarlar.

        Args:
            resource_key: Kaynak anahtari.
            desired_state: Istenen durum.

        Returns:
            Ayar bilgisi.
        """
        self._baselines[resource_key] = {
            "desired": dict(desired_state),
            "set_at": time.time(),
        }

        return {
            "key": resource_key,
            "status": "baseline_set",
        }

    def check(
        self,
        resource_key: str,
        actual_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Kayma kontrolu yapar.

        Args:
            resource_key: Kaynak anahtari.
            actual_state: Gercek durum.

        Returns:
            Kontrol sonucu.
        """
        self._stats["checks"] += 1

        baseline = self._baselines.get(
            resource_key,
        )
        if not baseline:
            return {
                "key": resource_key,
                "drifted": False,
                "reason": "no_baseline",
            }

        desired = baseline["desired"]
        drifted_props: list[dict[str, Any]] = []

        for prop, expected in desired.items():
            actual = actual_state.get(prop)
            if actual != expected:
                drifted_props.append({
                    "property": prop,
                    "expected": expected,
                    "actual": actual,
                })

        has_drift = len(drifted_props) > 0

        if has_drift:
            self._stats["drifts_found"] += 1

            # Ciddiyet
            if len(drifted_props) >= 5:
                severity = "critical"
            elif len(drifted_props) >= 3:
                severity = "high"
            elif len(drifted_props) >= 2:
                severity = "medium"
            else:
                severity = "low"

            drift_record = {
                "key": resource_key,
                "drifted_properties": drifted_props,
                "severity": severity,
                "detected_at": time.time(),
            }

            self._drifts.append(drift_record)

            # Uyari olustur
            self._alerts.append({
                "type": "drift_detected",
                "resource": resource_key,
                "severity": severity,
                "properties": len(drifted_props),
                "timestamp": time.time(),
            })

        return {
            "key": resource_key,
            "drifted": has_drift,
            "drifted_count": len(drifted_props),
            "details": drifted_props,
            "severity": (
                severity if has_drift else "none"
            ),
        }

    def check_all(
        self,
        actual_states: dict[
            str, dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Tum kaynaklari kontrol eder.

        Args:
            actual_states: Gercek durumlar.

        Returns:
            Toplu sonuc.
        """
        results: list[dict[str, Any]] = []
        total_drifted = 0

        for key in self._baselines:
            actual = actual_states.get(key, {})
            result = self.check(key, actual)
            results.append(result)
            if result["drifted"]:
                total_drifted += 1

        return {
            "checked": len(results),
            "drifted": total_drifted,
            "clean": len(results) - total_drifted,
            "results": results,
        }

    def add_remediation_rule(
        self,
        resource_pattern: str,
        action: str = "alert",
        auto_fix: bool = False,
    ) -> dict[str, Any]:
        """Duzeltme kurali ekler.

        Args:
            resource_pattern: Kaynak deseni.
            action: Eylem (alert/fix/ignore).
            auto_fix: Otomatik duzelt mi.

        Returns:
            Kural bilgisi.
        """
        self._remediation_rules[
            resource_pattern
        ] = {
            "action": action,
            "auto_fix": auto_fix,
        }

        return {
            "pattern": resource_pattern,
            "action": action,
        }

    def remediate(
        self,
        resource_key: str,
    ) -> dict[str, Any]:
        """Kaymayi duzeltir.

        Args:
            resource_key: Kaynak anahtari.

        Returns:
            Duzeltme bilgisi.
        """
        baseline = self._baselines.get(
            resource_key,
        )
        if not baseline:
            return {"error": "no_baseline"}

        # Kural kontrolu
        for pattern, rule in (
            self._remediation_rules.items()
        ):
            if pattern in resource_key:
                if rule["action"] == "ignore":
                    return {
                        "key": resource_key,
                        "status": "ignored",
                    }

        self._stats["remediations"] += 1

        return {
            "key": resource_key,
            "status": "remediated",
            "desired_state": baseline["desired"],
        }

    def get_drifts(
        self,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kaymalari getirir.

        Args:
            severity: Ciddiyet filtresi.
            limit: Limit.

        Returns:
            Kayma listesi.
        """
        drifts = self._drifts[-limit:]
        if severity:
            drifts = [
                d for d in drifts
                if d.get("severity") == severity
            ]
        return drifts

    def get_alerts(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Uyarilari getirir.

        Args:
            limit: Limit.

        Returns:
            Uyari listesi.
        """
        return self._alerts[-limit:]

    def get_report(self) -> dict[str, Any]:
        """Kayma raporu olusturur.

        Returns:
            Rapor.
        """
        severity_counts = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        }
        for d in self._drifts:
            sev = d.get("severity", "low")
            severity_counts[sev] = (
                severity_counts.get(sev, 0) + 1
            )

        return {
            "total_baselines": len(
                self._baselines,
            ),
            "total_checks": (
                self._stats["checks"]
            ),
            "total_drifts": (
                self._stats["drifts_found"]
            ),
            "remediations": (
                self._stats["remediations"]
            ),
            "severity_breakdown": severity_counts,
            "timestamp": time.time(),
        }

    @property
    def baseline_count(self) -> int:
        """Temel durum sayisi."""
        return len(self._baselines)

    @property
    def drift_count(self) -> int:
        """Kayma sayisi."""
        return len(self._drifts)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def check_count(self) -> int:
        """Kontrol sayisi."""
        return self._stats["checks"]
