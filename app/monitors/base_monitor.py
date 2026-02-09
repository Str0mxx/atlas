"""ATLAS monitor temel sinifi ve ortak modeller.

Tum monitor modulleri BaseMonitor'dan miras alir.
Monitor'lar agent'lari periyodik olarak calistirir,
sonuclari karar matrisi ile analiz eder ve bildirim gonderir.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.core.decision_matrix import ActionType, DecisionMatrix


class MonitorResult(BaseModel):
    """Monitor kontrol sonucu.

    Attributes:
        monitor_name: Monitor adi.
        check_time: Kontrol zamani.
        risk: Risk seviyesi (RiskLevel value).
        urgency: Aciliyet seviyesi (UrgencyLevel value).
        action: Aksiyon tipi (ActionType value).
        summary: Kontrol ozeti.
        details: Detayli bulgular listesi.
        alerts_sent: Gonderilen bildirim sayisi.
    """

    monitor_name: str = ""
    check_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    risk: str = "low"
    urgency: str = "low"
    action: str = "log"
    summary: str = ""
    details: list[dict[str, Any]] = Field(default_factory=list)
    alerts_sent: int = 0


class BaseMonitor(ABC):
    """Tum monitor'larin miras alacagi soyut temel sinif.

    Monitor'lar agent'lari periyodik olarak calistirir,
    karar matrisi ile sonuclari degerlendirir ve
    gerektiginde Telegram bildirimi gonderir.

    Attributes:
        name: Monitor adi.
        agent: Kullanilan agent.
        check_interval: Kontrol araligi (saniye).
        decision_matrix: Karar matrisi.
        telegram_bot: Bildirim gonderici (opsiyonel).
        logger: Monitor'a ozel logger.
    """

    def __init__(
        self,
        name: str,
        agent: BaseAgent,
        check_interval: int = 300,
        decision_matrix: DecisionMatrix | None = None,
        telegram_bot: Any = None,
    ) -> None:
        """BaseMonitor'u baslatir.

        Args:
            name: Monitor adi.
            agent: Kullanilan agent.
            check_interval: Kontrol araligi (saniye).
            decision_matrix: Karar matrisi (None ise yeni olusturulur).
            telegram_bot: Telegram bot nesnesi (opsiyonel).
        """
        self.name = name
        self.agent = agent
        self.check_interval = check_interval
        self.decision_matrix = decision_matrix or DecisionMatrix()
        self.telegram_bot = telegram_bot
        self.logger = logging.getLogger(f"atlas.monitor.{name}")
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._last_result: MonitorResult | None = None
        self._check_count = 0
        self.logger.info(
            "%s monitor olusturuldu (aralik=%ds)", self.name, self.check_interval,
        )

    @abstractmethod
    async def check(self) -> MonitorResult:
        """Tek sefer kontrol calistirir.

        Alt siniflar bu metodu implement eder.

        Returns:
            Monitor kontrol sonucu.
        """

    async def start(self) -> None:
        """Periyodik izlemeyi baslatir."""
        if self._running:
            self.logger.warning("%s zaten calisiyor", self.name)
            return
        self._running = True
        self._task = asyncio.create_task(
            self._monitor_loop(), name=f"monitor_{self.name}",
        )
        self.logger.info("%s monitor baslatildi", self.name)

    async def stop(self) -> None:
        """Izlemeyi durdurur."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self.logger.info("%s monitor durduruldu", self.name)

    @property
    def is_running(self) -> bool:
        """Monitor calisiyor mu."""
        return self._running and self._task is not None and not self._task.done()

    @property
    def last_result(self) -> MonitorResult | None:
        """Son kontrol sonucu."""
        return self._last_result

    def _should_notify(self, risk: str, urgency: str) -> bool:
        """Bildirim gerekli mi kontrolu.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.

        Returns:
            Bildirim gerekli ise True.
        """
        action = self.decision_matrix.get_action_for(risk, urgency)
        return action in (ActionType.NOTIFY, ActionType.AUTO_FIX, ActionType.IMMEDIATE)

    def _format_alert(self, result: MonitorResult) -> str:
        """Bildirim mesaji formatlar.

        Args:
            result: Monitor kontrol sonucu.

        Returns:
            Formatlanmis bildirim metni.
        """
        lines = [
            f"=== {result.monitor_name.upper()} UYARI ===",
            f"Zaman: {result.check_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"Risk: {result.risk} | Aciliyet: {result.urgency}",
            f"Aksiyon: {result.action}",
            "",
            result.summary,
        ]
        if result.details:
            lines.append("")
            for detail in result.details[:10]:
                for k, v in detail.items():
                    lines.append(f"  {k}: {v}")
                lines.append("")
        return "\n".join(lines)

    async def _monitor_loop(self) -> None:
        """Periyodik izleme dongusu."""
        self.logger.info("%s izleme dongusu baslatildi", self.name)
        while self._running:
            try:
                self._check_count += 1
                self.logger.info(
                    "[%s] Kontrol #%d baslatiliyor...",
                    self.name, self._check_count,
                )
                result = await self.check()
                self._last_result = result
                self.logger.info(
                    "[%s] Kontrol #%d tamamlandi: risk=%s, urgency=%s",
                    self.name, self._check_count, result.risk, result.urgency,
                )

                # Bildirim gerekli mi?
                if self._should_notify(result.risk, result.urgency):
                    await self._send_alert(result)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.logger.exception("[%s] Kontrol hatasi: %s", self.name, exc)

            # Sonraki kontrol icin bekle
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

        self.logger.info("%s izleme dongusu durduruldu", self.name)

    async def _send_alert(self, result: MonitorResult) -> None:
        """Telegram bildirimi gonderir.

        Args:
            result: Monitor kontrol sonucu.
        """
        if self.telegram_bot is None:
            self.logger.debug("Telegram bot yok, bildirim atlaniliyor")
            return
        try:
            alert_text = self._format_alert(result)
            await self.telegram_bot.send_message(alert_text)
            result.alerts_sent += 1
            self.logger.info("[%s] Bildirim gonderildi", self.name)
        except Exception as exc:
            self.logger.error("[%s] Bildirim gonderilemedi: %s", self.name, exc)

    def get_info(self) -> dict[str, Any]:
        """Monitor hakkinda ozet bilgi.

        Returns:
            Monitor durumu ve istatistikleri.
        """
        return {
            "name": self.name,
            "is_running": self.is_running,
            "check_interval": self.check_interval,
            "check_count": self._check_count,
            "last_check": (
                self._last_result.check_time.isoformat()
                if self._last_result else None
            ),
        }
