"""Google Ads performans izleme monitor modulu.

MarketingAgent'i periyodik olarak calistirip
reklam kampanya performansini izler.
"""

import logging
from typing import Any

from app.agents.marketing_agent import MarketingAgent
from app.core.decision_matrix import DecisionMatrix
from app.models.marketing import MarketingConfig
from app.monitors.base_monitor import BaseMonitor, MonitorResult

logger = logging.getLogger("atlas.monitor.ads")


class AdsMonitor(BaseMonitor):
    """Google Ads performans izleme monitor'u.

    MarketingAgent'i periyodik olarak calistirarak
    kampanya performansi, anahtar kelime, reddedilen reklamlar
    ve butce analizini izler.

    Attributes:
        config: Marketing yapilandirmasi.
    """

    def __init__(
        self,
        config: MarketingConfig | None = None,
        check_interval: int = 3600,
        decision_matrix: DecisionMatrix | None = None,
        telegram_bot: Any = None,
    ) -> None:
        """AdsMonitor'u baslatir.

        Args:
            config: Marketing yapilandirmasi.
            check_interval: Kontrol araligi (saniye, varsayilan 1 saat).
            decision_matrix: Karar matrisi.
            telegram_bot: Telegram bot nesnesi.
        """
        self.config = config
        agent = MarketingAgent(config=config)
        super().__init__(
            name="ads",
            agent=agent,
            check_interval=check_interval,
            decision_matrix=decision_matrix,
            telegram_bot=telegram_bot,
        )

    async def check(self) -> MonitorResult:
        """Reklam performans kontrolu calistirir.

        Returns:
            Monitor kontrol sonucu.
        """
        task = {"description": "Periyodik reklam performans kontrolu"}
        result = await self.agent.run(task)

        if not result.success:
            return MonitorResult(
                monitor_name=self.name,
                risk="medium",
                urgency="medium",
                action="notify",
                summary=f"Reklam kontrolu basarisiz: {result.message}",
                details=[{"error": e} for e in result.errors],
            )

        analysis = result.data.get("analysis", {})
        risk = analysis.get("risk", "low")
        urgency = analysis.get("urgency", "low")
        action = analysis.get("action", "log")
        summary = analysis.get("summary", "Reklam kontrolu tamamlandi")
        details = analysis.get("details", [])

        # Reddedilen reklam varsa aciliyet yukselt
        disapprovals = analysis.get("disapprovals", [])
        if disapprovals:
            risk = "high"
            urgency = "high"
            action = "immediate"
            summary = f"Reddedilen reklam tespit edildi: {len(disapprovals)} adet"
            details = [{"disapproval": d} for d in disapprovals] + details

        return MonitorResult(
            monitor_name=self.name,
            risk=risk,
            urgency=urgency,
            action=action,
            summary=summary,
            details=details,
        )
