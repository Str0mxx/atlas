"""Heartbeat Engine - periyodik saglik kontrolu motoru.

Sablon tabanli heartbeat kontrollerini calistirir, zamanlar ve
yanitlari isleyerek durumu belirler.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.heartbeat_models import (
    HeartbeatConfig,
    HeartbeatResult,
    HeartbeatStatus,
    HeartbeatTemplate,
    ImportanceLevel,
)

logger = logging.getLogger(__name__)


class HeartbeatEngine:
    """Heartbeat kontrollerini yoneten ana motor."""

    def __init__(self, config: Optional[HeartbeatConfig] = None) -> None:
        """HeartbeatEngine baslatici.

        Args:
            config: Motor yapilandirmasi.
        """
        self.config = config or HeartbeatConfig()
        self._templates: dict[str, HeartbeatTemplate] = {}
        self._scheduled: dict[str, dict] = {}
        self._last_results: dict[str, HeartbeatResult] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        entry = {"action": action, "timestamp": time.time(), "details": details or {}}
        self._history.append(entry)

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Motor istatistiklerini dondurur."""
        return {
            "total_templates": len(self._templates),
            "scheduled_count": len(self._scheduled),
            "total_runs": len(self._history),
            "last_results_count": len(self._last_results),
        }

    def run_heartbeat(self, template_id: str) -> HeartbeatResult:
        """Tek bir heartbeat kontrolu calistirir.

        Args:
            template_id: Calistirilacak sablon.

        Returns:
            Heartbeat kontrol sonucu.
        """
        template = self._templates.get(template_id)
        if not template:
            result = HeartbeatResult(
                heartbeat_id=str(uuid.uuid4()), timestamp=time.time(),
                status=HeartbeatStatus.SKIPPED,
                message=f"Template not found: {template_id}",
            )
            self._record_history("run_heartbeat", {"template_id": template_id, "status": "skipped"})
            return result
        if not template.enabled:
            result = HeartbeatResult(
                heartbeat_id=str(uuid.uuid4()), timestamp=time.time(),
                status=HeartbeatStatus.SKIPPED,
                message=f"Template disabled: {template_id}",
            )
            self._record_history("run_heartbeat", {"template_id": template_id, "status": "disabled"})
            return result
        response = template.content
        result = self.process_response(response)
        result.heartbeat_id = str(uuid.uuid4())
        result.timestamp = time.time()
        if self.config.sender_metadata:
            result.metrics.update(self.config.sender_metadata)
        self._last_results[template_id] = result
        self._record_history("run_heartbeat", {"template_id": template_id, "status": result.status.value})
        logger.info(f"Heartbeat calisti: {template_id} -> {result.status.value}")
        return result

    def schedule_heartbeat(self, template_id: str, interval: Optional[int] = None) -> bool:
        """Periyodik heartbeat zamanlar."""
        if template_id not in self._templates:
            self._record_history("schedule_heartbeat", {"template_id": template_id, "error": "not_found"})
            return False
        effective_interval = interval or self.config.default_interval
        self._scheduled[template_id] = {
            "interval": effective_interval, "scheduled_at": time.time(),
            "next_run": time.time() + effective_interval * 60,
        }
        self._record_history("schedule_heartbeat", {"template_id": template_id, "interval": effective_interval})
        return True

    def cancel_heartbeat(self, template_id: str) -> bool:
        """Zamanlanmis heartbeat kontrolunu iptal eder."""
        if template_id in self._scheduled:
            del self._scheduled[template_id]
            self._record_history("cancel_heartbeat", {"template_id": template_id})
            return True
        return False

    def load_template(self, template_id: str) -> Optional[HeartbeatTemplate]:
        """Kaydedilmis sablonu yukler."""
        return self._templates.get(template_id)

    def save_template(self, template: HeartbeatTemplate) -> bool:
        """Sablonu kaydeder."""
        if not template.template_id:
            template.template_id = str(uuid.uuid4())
        self._templates[template.template_id] = template
        self._record_history("save_template", {"template_id": template.template_id})
        return True

    def list_templates(self) -> list[HeartbeatTemplate]:
        """Tum sablonlari listeler."""
        return list(self._templates.values())

    def process_response(self, response: str) -> HeartbeatResult:
        """Heartbeat yanitini isler ve durumu belirler.

        Args:
            response: Kontrol yanit metni.

        Returns:
            Islenmis heartbeat sonucu.
        """
        result = HeartbeatResult()
        if not response or not response.strip():
            result.status = HeartbeatStatus.SILENT
            result.message = "Empty response"
            return result
        cleaned = response.strip()
        if self.config.strip_response_prefix and ":" in cleaned:
            cleaned = cleaned.split(":", 1)[-1].strip()
        upper = response.strip().upper()
        for ok_resp in self.config.ok_responses:
            if ok_resp in upper:
                result.status = HeartbeatStatus.OK
                result.message = cleaned
                return result
        findings: list[str] = []
        if "WARNING" in upper or "WARN" in upper:
            result.status = HeartbeatStatus.WARNING
            findings.append("Warning detected in response")
        elif "CRITICAL" in upper or "ERROR" in upper or "FAIL" in upper:
            result.status = HeartbeatStatus.CRITICAL
            findings.append("Critical issue detected in response")
        else:
            result.status = HeartbeatStatus.OK
        result.message = cleaned
        result.findings = findings
        return result

    def inject_metadata(self, template: HeartbeatTemplate, metadata: dict) -> HeartbeatTemplate:
        """Sablona gonderi meta verisi ekler."""
        template.metadata.update(metadata)
        self._record_history("inject_metadata", {"template_id": template.template_id, "keys": list(metadata.keys())})
        return template

    def get_last_result(self, template_id: str) -> Optional[HeartbeatResult]:
        """Son heartbeat sonucunu dondurur."""
        return self._last_results.get(template_id)

    def is_healthy(self) -> bool:
        """Genel sistem saglik durumunu kontrol eder."""
        if not self._last_results:
            return True
        return all(
            r.status in (HeartbeatStatus.OK, HeartbeatStatus.SKIPPED)
            for r in self._last_results.values()
        )
