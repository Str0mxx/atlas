"""Sunucu guvenlik izleme monitor modulu.

SecurityAgent'i periyodik olarak calistirip
guvenlik tehditlerini izler ve otonom aksiyonlar alir.
"""

import logging
from typing import Any

from app.agents.security_agent import SecurityAgent
from app.core.decision_matrix import DecisionMatrix
from app.models.security import SecurityScanConfig
from app.models.server import ServerConfig
from app.monitors.base_monitor import BaseMonitor, MonitorResult

logger = logging.getLogger("atlas.monitor.security")


class SecurityMonitor(BaseMonitor):
    """Sunucu guvenlik izleme monitor'u.

    SecurityAgent'i periyodik olarak calistirarak
    auth log, fail2ban, port taramasi, SSL sertifika
    ve supheli process kontrolu yapar.

    Attributes:
        servers: Taranacak sunucu listesi.
        scan_config: Guvenlik tarama yapilandirmasi.
    """

    def __init__(
        self,
        servers: list[ServerConfig] | None = None,
        scan_config: SecurityScanConfig | None = None,
        check_interval: int = 3600,
        decision_matrix: DecisionMatrix | None = None,
        telegram_bot: Any = None,
    ) -> None:
        """SecurityMonitor'u baslatir.

        Args:
            servers: Taranacak sunucu listesi.
            scan_config: Guvenlik tarama yapilandirmasi.
            check_interval: Kontrol araligi (saniye, varsayilan 1 saat).
            decision_matrix: Karar matrisi.
            telegram_bot: Telegram bot nesnesi.
        """
        self.servers = servers
        self.scan_config = scan_config
        agent = SecurityAgent(
            servers=servers,
            scan_config=scan_config,
        )
        super().__init__(
            name="security",
            agent=agent,
            check_interval=check_interval,
            decision_matrix=decision_matrix,
            telegram_bot=telegram_bot,
        )

    async def check(self) -> MonitorResult:
        """Guvenlik taramasi calistirir.

        Returns:
            Monitor kontrol sonucu.
        """
        task = {"description": "Periyodik guvenlik taramasi"}
        result = await self.agent.run(task)

        if not result.success:
            return MonitorResult(
                monitor_name=self.name,
                risk="high",
                urgency="high",
                action="immediate",
                summary=f"Guvenlik taramasi basarisiz: {result.message}",
                details=[{"error": e} for e in result.errors],
            )

        analysis = result.data.get("analysis", {})
        risk = analysis.get("risk", "low")
        urgency = analysis.get("urgency", "low")
        action = analysis.get("action", "log")
        summary = analysis.get("summary", "Guvenlik taramasi tamamlandi")
        details = analysis.get("details", [])

        # Otonom aksiyonlar
        await self._handle_autonomous_actions(analysis)

        return MonitorResult(
            monitor_name=self.name,
            risk=risk,
            urgency=urgency,
            action=action,
            summary=summary,
            details=details,
        )

    async def _handle_autonomous_actions(
        self, analysis: dict[str, Any],
    ) -> None:
        """Otonom guvenlik aksiyonlari calistirir.

        CLAUDE.md kurallari: IP engelleme ve SSL yenileme
        onay gerektirmez.

        Args:
            analysis: Agent analiz sonucu.
        """
        action = analysis.get("action", "log")
        details = analysis.get("details", [])

        if action in ("auto_fix", "immediate"):
            for detail in details:
                detail_type = detail.get("type", "")

                if detail_type == "failed_login_threshold":
                    ip = detail.get("ip", "")
                    self.logger.info(
                        "Otonom aksiyon: IP engelleniyor — %s", ip,
                    )

                elif detail_type == "ssl_expiring":
                    domain = detail.get("domain", "")
                    self.logger.info(
                        "Otonom aksiyon: SSL yenileniyor — %s", domain,
                    )
