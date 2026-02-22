"""Importance Scorer - heartbeat onem puanlama modulu.

Heartbeat sonuclarini analiz ederek onem seviyesi belirler ve
bildirim karari verir.
"""

import logging
import time
from typing import Optional

from app.models.heartbeat_models import (
    HeartbeatResult,
    HeartbeatStatus,
    ImportanceLevel,
    QuietHoursConfig,
)

logger = logging.getLogger(__name__)


class ImportanceScorer:
    """Heartbeat sonuclarina onem puani atar."""

    def __init__(self) -> None:
        """ImportanceScorer baslatici."""
        self._thresholds: dict[str, float] = {
            "warning_weight": 0.5,
            "critical_weight": 1.0,
            "change_weight": 0.3,
        }
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Puanlayici istatistiklerini dondurur."""
        return {"total_scores": len(self._history), "thresholds": dict(self._thresholds)}

    def score(self, heartbeat_result: HeartbeatResult) -> ImportanceLevel:
        """Heartbeat sonucuna onem puani verir."""
        status = heartbeat_result.status
        findings_count = len(heartbeat_result.findings)
        if status == HeartbeatStatus.CRITICAL:
            level = ImportanceLevel.CRITICAL
        elif status == HeartbeatStatus.WARNING:
            level = ImportanceLevel.HIGH if findings_count > 1 else ImportanceLevel.MEDIUM
        elif status == HeartbeatStatus.SILENT:
            level = ImportanceLevel.LOW
        elif status == HeartbeatStatus.SKIPPED:
            level = ImportanceLevel.NONE
        else:
            level = ImportanceLevel.LOW if findings_count > 0 else ImportanceLevel.NONE
        heartbeat_result.importance = level
        self._record_history("score", {"heartbeat_id": heartbeat_result.heartbeat_id, "importance": level.value})
        return level

    def should_notify(self, result: HeartbeatResult, quiet_hours: Optional[QuietHoursConfig] = None) -> bool:
        """Bildirim gonderilip gonderilmeyecegini belirler."""
        if result.importance in (ImportanceLevel.NONE,):
            result.should_notify = False
            return False
        if result.importance == ImportanceLevel.CRITICAL:
            result.should_notify = True
            return True
        if result.importance in (ImportanceLevel.HIGH, ImportanceLevel.MEDIUM):
            result.should_notify = True
            return True
        result.should_notify = False
        return False

    def classify_findings(self, findings: list[str]) -> dict[str, list[str]]:
        """Bulgulari ciddiyet seviyesine gore siniflandirir."""
        classified: dict[str, list[str]] = {"critical": [], "warning": [], "info": []}
        for finding in findings:
            upper = finding.upper()
            if "CRITICAL" in upper or "ERROR" in upper or "FAIL" in upper:
                classified["critical"].append(finding)
            elif "WARNING" in upper or "WARN" in upper:
                classified["warning"].append(finding)
            else:
                classified["info"].append(finding)
        self._record_history("classify_findings", {"total": len(findings)})
        return classified

    def compare_with_previous(self, current: HeartbeatResult, previous: Optional[HeartbeatResult]) -> dict:
        """Onceki sonucla karsilastirarak degisiklikleri tespit eder."""
        if not previous:
            return {"changed": False, "first_run": True, "status_change": None}
        changed = current.status != previous.status
        result = {
            "changed": changed,
            "first_run": False,
            "status_change": f"{previous.status.value} -> {current.status.value}" if changed else None,
            "new_findings": len(current.findings) - len(previous.findings),
        }
        self._record_history("compare_with_previous", result)
        return result

    def adjust_threshold(self, feedback: dict) -> None:
        """Geri bildirime gore esikleri ayarlar."""
        for key, value in feedback.items():
            if key in self._thresholds and isinstance(value, (int, float)):
                self._thresholds[key] = value
        self._record_history("adjust_threshold", {"feedback": feedback})
