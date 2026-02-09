"""Firsat izleme monitor modulu.

ResearchAgent'i kullanarak tedarikci, fiyat ve
firma guvenilirlik izlemesi yapar.
"""

import logging
from typing import Any

from app.agents.research_agent import ResearchAgent
from app.core.decision_matrix import DecisionMatrix
from app.models.research import ResearchConfig
from app.monitors.base_monitor import BaseMonitor, MonitorResult

logger = logging.getLogger("atlas.monitor.opportunity")


class OpportunityMonitor(BaseMonitor):
    """Firsat izleme monitor'u.

    ResearchAgent'i kullanarak tedarikci fiyatlarini,
    firma guvenilirligini ve pazar firsatlarini izler.

    Attributes:
        config: Arastirma yapilandirmasi.
        watched_suppliers: Izlenecek tedarikci listesi.
        watched_companies: Izlenecek firma URL'leri.
    """

    def __init__(
        self,
        config: ResearchConfig | None = None,
        watched_suppliers: list[dict[str, str]] | None = None,
        watched_companies: list[str] | None = None,
        check_interval: int = 86400,
        decision_matrix: DecisionMatrix | None = None,
        telegram_bot: Any = None,
    ) -> None:
        """OpportunityMonitor'u baslatir.

        Args:
            config: Arastirma yapilandirmasi.
            watched_suppliers: Izlenecek tedarikci listesi.
                Her eleman {"name": "...", "url": "..."} formati.
            watched_companies: Izlenecek firma URL'leri.
            check_interval: Kontrol araligi (saniye, varsayilan 24 saat).
            decision_matrix: Karar matrisi.
            telegram_bot: Telegram bot nesnesi.
        """
        self.config = config
        self.watched_suppliers = watched_suppliers or []
        self.watched_companies = watched_companies or []
        agent = ResearchAgent(config=config)
        super().__init__(
            name="opportunity",
            agent=agent,
            check_interval=check_interval,
            decision_matrix=decision_matrix,
            telegram_bot=telegram_bot,
        )

    async def check(self) -> MonitorResult:
        """Firsat izleme kontrolu calistirir.

        Returns:
            Monitor kontrol sonucu.
        """
        task = {
            "description": "Periyodik firsat izleme",
            "research_type": "supplier_research",
            "suppliers": self.watched_suppliers,
            "companies": self.watched_companies,
        }
        result = await self.agent.run(task)

        if not result.success:
            return MonitorResult(
                monitor_name=self.name,
                risk="low",
                urgency="low",
                action="log",
                summary=f"Firsat izleme basarisiz: {result.message}",
                details=[{"error": e} for e in result.errors],
            )

        analysis = result.data.get("analysis", {})
        risk = analysis.get("risk", "low")
        urgency = analysis.get("urgency", "low")
        action = analysis.get("action", "log")
        summary = analysis.get("summary", "Firsat izleme tamamlandi")
        details = analysis.get("details", [])

        return MonitorResult(
            monitor_name=self.name,
            risk=risk,
            urgency=urgency,
            action=action,
            summary=summary,
            details=details,
        )

    async def check_on_demand(
        self, task: dict[str, Any],
    ) -> MonitorResult:
        """Tek seferlik firsat kontrolu calistirir.

        Periyodik izlemeden bagimsiz olarak
        belirli bir arastirma gorevi calistirir.

        Args:
            task: Arastirma gorev detaylari.

        Returns:
            Monitor kontrol sonucu.
        """
        result = await self.agent.run(task)

        if not result.success:
            return MonitorResult(
                monitor_name=self.name,
                risk="low",
                urgency="low",
                action="log",
                summary=f"On-demand kontrol basarisiz: {result.message}",
                details=[{"error": e} for e in result.errors],
            )

        analysis = result.data.get("analysis", {})
        return MonitorResult(
            monitor_name=self.name,
            risk=analysis.get("risk", "low"),
            urgency=analysis.get("urgency", "low"),
            action=analysis.get("action", "log"),
            summary=analysis.get("summary", "On-demand kontrol tamamlandi"),
            details=analysis.get("details", []),
        )
