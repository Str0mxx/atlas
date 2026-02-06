"""ATLAS Master Agent modulu.

Tum gelen gorevleri analiz eder, karar matrisini kullanarak
uygun agent'a yonlendirir.
"""

import logging
from typing import Any

from app.agents.base_agent import AgentStatus, BaseAgent, TaskResult
from app.core.decision_matrix import (
    ActionType,
    DecisionMatrix,
    RiskLevel,
    UrgencyLevel,
)

logger = logging.getLogger(__name__)


class MasterAgent(BaseAgent):
    """Ana koordinator agent.

    Gelen gorevleri analiz eder, karar matrisine gore
    uygun alt agent'a yonlendirir veya dogrudan islem yapar.

    Attributes:
        decision_matrix: Karar matrisi.
        agents: Kayitli alt agent'lar.
    """

    def __init__(self) -> None:
        """Master Agent'i baslatir."""
        super().__init__(name="MasterAgent")
        self.decision_matrix = DecisionMatrix()
        self.agents: dict[str, BaseAgent] = {}
        self.telegram_bot: Any = None
        self.logger.info("Master Agent hazir. Kayitli agent sayisi: %d", len(self.agents))

    def register_agent(self, agent: BaseAgent) -> None:
        """Yeni bir alt agent kaydeder.

        Args:
            agent: Kaydedilecek agent.
        """
        self.agents[agent.name] = agent
        self.logger.info("Agent kaydedildi: %s", agent.name)

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Gorevi analiz edip uygun agent'a yonlendirir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - description: Gorev aciklamasi
                - risk: Risk seviyesi (low/medium/high)
                - urgency: Aciliyet seviyesi (low/medium/high)
                - target_agent: (opsiyonel) Hedef agent adi

        Returns:
            Gorev sonucu.
        """
        description = task.get("description", "tanimsiz gorev")
        risk = RiskLevel(task.get("risk", "low"))
        urgency = UrgencyLevel(task.get("urgency", "low"))

        self.logger.info("Gorev alindi: %s", description)

        # Karar matrisinden aksiyon belirle
        decision = await self.decision_matrix.evaluate(
            risk=risk,
            urgency=urgency,
            context={"detail": description},
        )

        # Aksiyona gore yonlendir
        result = await self._route_action(task, decision.action)
        return result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Gelen veriyi analiz eder.

        Args:
            data: Analiz edilecek veri.

        Returns:
            Analiz sonuclari (risk, urgency, suggested_action).
        """
        # TODO: LLM ile derin analiz yapilacak
        analysis = {
            "risk": data.get("risk", "low"),
            "urgency": data.get("urgency", "low"),
            "suggested_action": "log",
            "summary": f"Analiz tamamlandi: {data.get('description', '')}",
        }
        self.logger.info("Analiz sonucu: %s", analysis["summary"])
        return analysis

    async def report(self, result: TaskResult) -> str:
        """Gorev sonucunu formatli rapor olarak dondurur.

        Args:
            result: Raporlanacak sonuc.

        Returns:
            Formatlanmis rapor metni.
        """
        status_emoji = "OK" if result.success else "HATA"
        report_text = (
            f"[{status_emoji}] ATLAS Rapor\n"
            f"Durum: {'Basarili' if result.success else 'Basarisiz'}\n"
            f"Mesaj: {result.message}\n"
            f"Zaman: {result.timestamp.isoformat()}\n"
        )
        if result.errors:
            report_text += f"Hatalar: {', '.join(result.errors)}\n"
        return report_text

    async def _route_action(self, task: dict[str, Any], action: ActionType) -> TaskResult:
        """Aksiyona gore gorevi yonlendirir.

        Args:
            task: Gorev detaylari.
            action: Belirlenen aksiyon tipi.

        Returns:
            Yonlendirme sonucu.
        """
        self.logger.info("Yonlendirme: aksiyon=%s", action.value)

        if action == ActionType.LOG:
            return await self._handle_log(task)
        elif action == ActionType.NOTIFY:
            return await self._handle_notify(task)
        elif action == ActionType.AUTO_FIX:
            return await self._handle_auto_fix(task)
        elif action == ActionType.IMMEDIATE:
            return await self._handle_immediate(task)

        return TaskResult(success=False, message=f"Bilinmeyen aksiyon: {action}")

    async def _handle_log(self, task: dict[str, Any]) -> TaskResult:
        """Sadece kaydet aksiyonu."""
        self.logger.info("Gorev kaydedildi: %s", task.get("description", ""))
        return TaskResult(success=True, message="Gorev kaydedildi")

    async def _handle_notify(self, task: dict[str, Any]) -> TaskResult:
        """Bildirim gonder aksiyonu."""
        description = task.get("description", "")
        self.logger.info("Bildirim gonderilecek: %s", description)

        if self.telegram_bot:
            try:
                await self.telegram_bot.send_message(
                    f"ATLAS Bildirim:\n{description}",
                )
            except Exception as exc:
                self.logger.error("Telegram bildirim hatasi: %s", exc)

        return TaskResult(success=True, message="Bildirim gonderildi")

    async def _handle_auto_fix(self, task: dict[str, Any]) -> TaskResult:
        """Otomatik duzeltme aksiyonu."""
        target = task.get("target_agent")
        if target and target in self.agents:
            agent = self.agents[target]
            return await agent.run(task)

        self.logger.warning("Hedef agent bulunamadi: %s", target)
        return TaskResult(
            success=False,
            message=f"Otomatik duzeltme icin agent bulunamadi: {target}",
        )

    async def _handle_immediate(self, task: dict[str, Any]) -> TaskResult:
        """Acil mudahale aksiyonu."""
        description = task.get("description", "")
        self.logger.critical("ACIL MUDAHALE: %s", description)

        if self.telegram_bot:
            try:
                await self.telegram_bot.send_buttons(
                    text=f"ACIL MUDAHALE GEREKIYOR:\n{description}",
                    buttons=[
                        {"text": "Onayla", "callback_data": "approve_immediate"},
                        {"text": "Reddet", "callback_data": "reject_immediate"},
                    ],
                )
            except Exception as exc:
                self.logger.error("Telegram acil bildirim hatasi: %s", exc)

        # Hedef agent varsa otomatik calistir
        target = task.get("target_agent")
        if target and target in self.agents:
            agent = self.agents[target]
            return await agent.run(task)

        return TaskResult(success=True, message="Acil mudahale baslatildi")

    def get_registered_agents(self) -> list[dict[str, Any]]:
        """Kayitli agent'larin listesini dondurur."""
        return [agent.get_info() for agent in self.agents.values()]
