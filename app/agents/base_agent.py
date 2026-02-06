"""Tum ATLAS agent'larinin miras alacagi temel sinif."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent durum tanimlari."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"
    STOPPED = "stopped"


class TaskResult(BaseModel):
    """Agent gorev sonucu."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    errors: list[str] = Field(default_factory=list)


class BaseAgent(ABC):
    """Tum agent'larin miras alacagi soyut temel sinif.

    Her agent su temel yeteneklere sahiptir:
    - execute: Gorevi calistirir
    - analyze: Veriyi analiz eder
    - report: Sonuclari raporlar

    Attributes:
        name: Agent adi.
        status: Mevcut durum.
        logger: Agent'a ozel logger.
    """

    def __init__(self, name: str) -> None:
        """Agent'i baslatir.

        Args:
            name: Agent adi.
        """
        self.name = name
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"atlas.agent.{name}")
        self._created_at = datetime.now(timezone.utc)
        self._task_count = 0

        self.logger.info("%s agent olusturuldu", self.name)

    @abstractmethod
    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Verilen gorevi calistirir.

        Args:
            task: Gorev detaylarini iceren sozluk.

        Returns:
            Gorev sonucu.
        """

    @abstractmethod
    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Veriyi analiz eder ve sonuc dondurur.

        Args:
            data: Analiz edilecek veri.

        Returns:
            Analiz sonuclari.
        """

    @abstractmethod
    async def report(self, result: TaskResult) -> str:
        """Gorev sonucunu raporlar.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Formatlanmis rapor metni.
        """

    async def run(self, task: dict[str, Any]) -> TaskResult:
        """Gorevi guvenli sekilde calistirir (hata yakalama dahil).

        Args:
            task: Gorev detaylari.

        Returns:
            Gorev sonucu.
        """
        self.status = AgentStatus.RUNNING
        self._task_count += 1
        self.logger.info("[%s] Gorev baslatiliyor (#%d): %s",
                         self.name, self._task_count, task.get("description", ""))

        try:
            result = await self.execute(task)
            self.status = AgentStatus.IDLE
            self.logger.info("[%s] Gorev tamamlandi: basarili=%s", self.name, result.success)
            return result
        except Exception as exc:
            self.status = AgentStatus.ERROR
            self.logger.exception("[%s] Gorev hatasi: %s", self.name, exc)
            return TaskResult(
                success=False,
                message=f"Agent hatasi: {exc}",
                errors=[str(exc)],
            )

    def get_info(self) -> dict[str, Any]:
        """Agent hakkinda ozet bilgi dondurur."""
        return {
            "name": self.name,
            "status": self.status.value,
            "created_at": self._created_at.isoformat(),
            "task_count": self._task_count,
        }
