"""Sunucu saglik izleme monitor modulu.

ServerMonitorAgent'i periyodik olarak calistirip
sunucu metriklerini izler, kritik durumlarda bildirim gonderir.
"""

import logging
from typing import Any

from app.agents.server_monitor_agent import ServerMonitorAgent
from app.core.decision_matrix import DecisionMatrix
from app.models.server import MetricThresholds, ServerConfig
from app.monitors.base_monitor import BaseMonitor, MonitorResult

logger = logging.getLogger("atlas.monitor.server")


class ServerMonitor(BaseMonitor):
    """Sunucu saglik izleme monitor'u.

    ServerMonitorAgent'i periyodik olarak calistirarak
    sunucu metriklerini (CPU, RAM, Disk, servisler) izler.
    Kritik durumlarda otonom aksiyonlar alabilir.

    Attributes:
        servers: Izlenecek sunucu listesi.
        thresholds: Metrik esik degerleri.
    """

    def __init__(
        self,
        servers: list[ServerConfig] | None = None,
        thresholds: MetricThresholds | None = None,
        check_interval: int = 300,
        decision_matrix: DecisionMatrix | None = None,
        telegram_bot: Any = None,
    ) -> None:
        """ServerMonitor'u baslatir.

        Args:
            servers: Izlenecek sunucu listesi.
            thresholds: Metrik esik degerleri.
            check_interval: Kontrol araligi (saniye, varsayilan 5 dk).
            decision_matrix: Karar matrisi.
            telegram_bot: Telegram bot nesnesi.
        """
        self.servers = servers
        self.thresholds = thresholds
        agent = ServerMonitorAgent(
            servers=servers,
            thresholds=thresholds,
        )
        super().__init__(
            name="server",
            agent=agent,
            check_interval=check_interval,
            decision_matrix=decision_matrix,
            telegram_bot=telegram_bot,
        )

    async def check(self) -> MonitorResult:
        """Sunucu saglik kontrolu calistirir.

        Returns:
            Monitor kontrol sonucu.
        """
        task = {"description": "Periyodik sunucu kontrolu"}
        result = await self.agent.run(task)

        if not result.success:
            return MonitorResult(
                monitor_name=self.name,
                risk="high",
                urgency="high",
                action="immediate",
                summary=f"Sunucu kontrolu basarisiz: {result.message}",
                details=[{"error": e} for e in result.errors],
            )

        analysis = result.data.get("analysis", {})
        risk = analysis.get("risk", "low")
        urgency = analysis.get("urgency", "low")
        action = analysis.get("action", "log")
        summary = analysis.get("summary", "Sunucu kontrolu tamamlandi")
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
        """Otonom aksiyonlar calistirir.

        CLAUDE.md kurallari: servis restart ve log temizligi
        onay gerektirmez.

        Args:
            analysis: Agent analiz sonucu.
        """
        action = analysis.get("action", "log")
        details = analysis.get("details", [])

        if action in ("auto_fix", "immediate"):
            for detail in details:
                if detail.get("type") == "service_down":
                    service_name = detail.get("service", "")
                    self.logger.info(
                        "Otonom aksiyon: %s servisi restart ediliyor",
                        service_name,
                    )
