"""ATLAS BDI Agent modulu.

Sense-Plan-Act dongusunu yoneten ust duzey agent.
BaseAgent'dan miras alir, belief/desire/intention modulleriyle
koordineli calisir.
"""

import asyncio
import logging
from typing import Any

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.autonomy.beliefs import BeliefBase
from app.core.autonomy.desires import DesireBase
from app.core.autonomy.intentions import IntentionBase
from app.core.decision_matrix import DecisionMatrix
from app.models.autonomy import (
    BeliefUpdate,
    CommitmentStrategy,
    Desire,
    Plan,
    PlanStatus,
)

logger = logging.getLogger("atlas.autonomy.bdi_agent")

# Varsayilan BDI dongu araligi (saniye)
DEFAULT_CYCLE_INTERVAL = 60


class BDIAgent(BaseAgent):
    """BDI mimarisine dayali otonom agent.

    Sense-Plan-Act dongusunu calistirir:
    1. Sense: Belief'leri gunceller (monitor verileri, task sonuclari)
    2. Plan: Deliberation ile hedef secer, means-ends reasoning ile plan secer
    3. Act: Plan adimlarini mevcut agent altyapisi uzerinden calistirir

    BaseAgent'dan miras alir, execute/analyze/report implement eder.

    Attributes:
        beliefs: Belief sistemi.
        desires: Desire/Goal sistemi.
        intentions: Intention sistemi.
        decision_matrix: Karar matrisi.
        commitment_strategy: Varsayilan taahhut stratejisi.
        cycle_interval: BDI dongu araligi (saniye).
        agents: Calistirmak icin kullanilabilecek agent'lar.
    """

    def __init__(
        self,
        decision_matrix: DecisionMatrix | None = None,
        commitment_strategy: CommitmentStrategy = CommitmentStrategy.SINGLE_MINDED,
        cycle_interval: int = DEFAULT_CYCLE_INTERVAL,
    ) -> None:
        """BDIAgent'i baslatir.

        Args:
            decision_matrix: Karar matrisi.
            commitment_strategy: Varsayilan taahhut stratejisi.
            cycle_interval: BDI dongu araligi (saniye).
        """
        super().__init__(name="BDIAgent")
        self.decision_matrix = decision_matrix or DecisionMatrix()
        self.beliefs = BeliefBase()
        self.desires = DesireBase(decision_matrix=self.decision_matrix)
        self.intentions = IntentionBase()
        self.commitment_strategy = commitment_strategy
        self.cycle_interval = cycle_interval
        self.agents: dict[str, BaseAgent] = {}
        self._cycle_task: asyncio.Task[None] | None = None
        self._running = False
        self._cycle_count = 0
        self.logger.info(
            "BDIAgent olusturuldu (strateji=%s)",
            commitment_strategy.value,
        )

    # === BaseAgent abstract method implementations ===

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Gorevi BDI dongusu uzerinden calistirir.

        Sense-Plan-Act dongusunun tek seferlik calistirmasi.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - description: Gorev aciklamasi
                - beliefs: (opsiyonel) Belief guncellemeleri
                - goal_name: (opsiyonel) Hedef adi
                - monitor_name: (opsiyonel) Monitor adi
                - risk/urgency: (opsiyonel) Risk/aciliyet

        Returns:
            Gorev sonucu.
        """
        # 1. SENSE
        await self._sense(task)

        # 2. DELIBERATE
        desire = await self._deliberate(task)
        if desire is None:
            return TaskResult(
                success=True,
                message="Uygun hedef bulunamadi, aksiyon gerekmiyor",
                data={
                    "cycle": "no_goal",
                    "beliefs": self.beliefs.snapshot(),
                },
            )

        # 3. MEANS-ENDS REASONING
        intention = await self._means_ends(desire)
        if intention is None:
            return TaskResult(
                success=False,
                message=f"Hedef icin plan bulunamadi: {desire.name}",
                data={
                    "desire": desire.name,
                    "beliefs": self.beliefs.snapshot(),
                },
            )

        # 4. ACT
        return await self._act(intention)

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """BDI durumunu analiz eder.

        Args:
            data: Analiz edilecek veri.

        Returns:
            BDI durum analizi.
        """
        return {
            "beliefs_count": len(self.beliefs.get_all()),
            "active_desires": len(self.desires.get_active()),
            "active_intentions": len(
                self.intentions.get_active_intentions(),
            ),
            "cycle_count": self._cycle_count,
            "beliefs_snapshot": self.beliefs.snapshot(),
            "desires_snapshot": self.desires.snapshot(),
            "intentions_snapshot": self.intentions.snapshot(),
        }

    async def report(self, result: TaskResult) -> str:
        """BDI dongu sonucunu raporlar.

        Args:
            result: Gorev sonucu.

        Returns:
            Formatlanmis rapor metni.
        """
        status_label = "BASARILI" if result.success else "BASARISIZ"
        return (
            f"[BDI] {status_label}\n"
            f"Mesaj: {result.message}\n"
            f"Belief sayisi: {len(self.beliefs.get_all())}\n"
            f"Aktif hedef: {len(self.desires.get_active())}\n"
            f"Aktif intention: "
            f"{len(self.intentions.get_active_intentions())}\n"
        )

    # === Otonom Dongu ===

    async def start_cycle(self) -> None:
        """Otonom BDI dongusunu baslatir."""
        if self._running:
            self.logger.warning("BDI dongusu zaten calisiyor")
            return
        self._running = True
        self._cycle_task = asyncio.create_task(
            self._cycle_loop(), name="bdi_cycle",
        )
        self.logger.info(
            "BDI dongusu baslatildi (aralik=%ds)",
            self.cycle_interval,
        )

    async def stop_cycle(self) -> None:
        """Otonom BDI dongusunu durdurur."""
        self._running = False
        if self._cycle_task and not self._cycle_task.done():
            self._cycle_task.cancel()
            try:
                await self._cycle_task
            except asyncio.CancelledError:
                pass
        self._cycle_task = None
        self.logger.info("BDI dongusu durduruldu")

    @property
    def is_running(self) -> bool:
        """BDI dongusu calisiyor mu."""
        return self._running

    # === Kayit Metodlari ===

    def register_agent(self, agent: BaseAgent) -> None:
        """Calistirmak icin kullanilacak alt agent kaydeder.

        Args:
            agent: Kaydedilecek agent.
        """
        self.agents[agent.name] = agent
        self.logger.info("Agent kaydedildi: %s", agent.name)

    def register_plan(self, plan: Plan) -> None:
        """Plan kutuphanesine plan ekler.

        Args:
            plan: Kaydedilecek plan.
        """
        self.intentions.register_plan(plan)

    def adopt_goal(self, desire: Desire) -> None:
        """Yeni hedef benimsetir (senkron kolaylik metodu).

        Args:
            desire: Benimsenen hedef.
        """
        self.desires.desires[desire.id] = desire
        self.logger.info("Hedef benimsendi: %s", desire.name)

    # === Internal: Sense-Plan-Act ===

    async def _sense(self, task: dict[str, Any]) -> None:
        """Sense asamasi: Belief'leri gunceller.

        Args:
            task: Gelen gorev verisi.
        """
        # Zaman bazli guven azalmasi
        await self.beliefs.decay()

        # Task'tan gelen belief guncellemeleri
        belief_updates = task.get("beliefs", [])
        for update_data in belief_updates:
            if isinstance(update_data, dict):
                update = BeliefUpdate(**update_data)
            else:
                update = update_data
            await self.beliefs.update(update)

        # Monitor verisi varsa
        if "monitor_name" in task:
            await self.beliefs.update_from_monitor(
                monitor_name=task["monitor_name"],
                risk=task.get("risk", "low"),
                urgency=task.get("urgency", "low"),
                details=task.get("details", []),
            )

    async def _deliberate(
        self,
        task: dict[str, Any],
    ) -> Desire | None:
        """Deliberation asamasi: Hangi hedefi takip edecegine karar verir.

        Args:
            task: Gelen gorev verisi.

        Returns:
            Secilen hedef veya None.
        """
        belief_snapshot = {
            b.key: b.value for b in self.beliefs.get_all()
        }

        # Task'ta belirli bir hedef istendiyse
        goal_name = task.get("goal_name")
        if goal_name:
            for desire in self.desires.get_active():
                if desire.name == goal_name:
                    return desire

        # Oncelikleri guncelle
        await self.desires.update_priorities(belief_snapshot)

        # On kosullari saglanan hedefleri al
        achievable = self.desires.get_achievable(belief_snapshot)
        if not achievable:
            return None

        # En yuksek oncelikliyi sec
        achievable.sort(key=lambda d: d.priority_score, reverse=True)
        return achievable[0]

    async def _means_ends(self, desire: Desire) -> object | None:
        """Means-ends reasoning: Hedefe ulasmak icin plan secer.

        Args:
            desire: Takip edilecek hedef.

        Returns:
            Intention veya None (plan bulunamazsa).
        """
        # Mevcut intention var mi?
        existing = self.intentions.get_intention_for_desire(desire.id)
        if existing and existing.status in (
            PlanStatus.READY,
            PlanStatus.EXECUTING,
        ):
            if self._should_reconsider(existing):
                beliefs = {
                    b.key: b.value for b in self.beliefs.get_all()
                }
                plan = await self.intentions.replan(
                    existing.id, desire, beliefs,
                )
                if plan:
                    return self.intentions.get_intention_for_desire(
                        desire.id,
                    )
                return None
            return existing

        # Yeni plan sec
        belief_snapshot = {
            b.key: b.value for b in self.beliefs.get_all()
        }
        plan = await self.intentions.select_plan(desire, belief_snapshot)
        if plan is None:
            return None

        intention = await self.intentions.commit(
            desire, plan, self.commitment_strategy,
        )
        return intention

    def _should_reconsider(self, intention: object) -> bool:
        """Mevcut intention'i yeniden degerlendirmeli mi kontrol eder.

        Args:
            intention: Mevcut intention.

        Returns:
            True ise yeniden degerlendir.
        """
        if intention.commitment == CommitmentStrategy.BLIND:
            return False
        if intention.commitment == CommitmentStrategy.OPEN_MINDED:
            return True
        # SINGLE_MINDED: sadece basarisizlik durumunda
        return intention.status == PlanStatus.FAILED

    async def _act(self, intention: object) -> TaskResult:
        """Act asamasi: Plan adimini calistirir.

        Args:
            intention: Calistirilacak intention.

        Returns:
            Adim sonucu.
        """
        step = await self.intentions.get_next_step(intention.id)
        if step is None:
            # Tum adimlar tamamlanmis
            desire = self.desires.get(intention.desire_id)
            if desire:
                await self.desires.achieve(desire.id)
            return TaskResult(
                success=True,
                message=f"Plan tamamlandi: {intention.plan_id}",
                data={
                    "intention_id": intention.id,
                    "status": "completed",
                },
            )

        # Adimi calistir
        task_dict: dict[str, Any] = {
            "description": step.description,
            **step.task_params,
        }

        if step.target_agent and step.target_agent in self.agents:
            agent = self.agents[step.target_agent]
            result = await agent.run(task_dict)
        else:
            result = TaskResult(
                success=False,
                message=f"Hedef agent bulunamadi: {step.target_agent}",
                errors=[f"Agent kayitli degil: {step.target_agent}"],
            )

        # Intention'i ilerlet
        plan_status = await self.intentions.advance(
            intention.id, result,
        )

        # Basarisiz adim sonrasi replanning
        if plan_status == PlanStatus.FAILED:
            desire = self.desires.get(intention.desire_id)
            if desire:
                beliefs = {
                    b.key: b.value for b in self.beliefs.get_all()
                }
                new_plan = await self.intentions.replan(
                    intention.id, desire, beliefs,
                )
                if new_plan is None:
                    await self.desires.drop(
                        desire.id, reason="Tum planlar basarisiz",
                    )

        return result

    async def _cycle_loop(self) -> None:
        """Otonom BDI dongu islemi."""
        self.logger.info("BDI dongu islemi baslatildi")
        while self._running:
            try:
                self._cycle_count += 1
                self.logger.info(
                    "BDI dongusu #%d baslatiliyor",
                    self._cycle_count,
                )

                belief_snapshot = {
                    b.key: b.value for b in self.beliefs.get_all()
                }
                await self.beliefs.decay()
                await self.desires.update_priorities(belief_snapshot)

                achievable = self.desires.get_achievable(belief_snapshot)
                for desire in achievable:
                    intention = await self._means_ends(desire)
                    if intention:
                        await self._act(intention)

                self.logger.info(
                    "BDI dongusu #%d tamamlandi",
                    self._cycle_count,
                )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.logger.exception("BDI dongu hatasi: %s", exc)

            try:
                await asyncio.sleep(self.cycle_interval)
            except asyncio.CancelledError:
                break

        self.logger.info("BDI dongu islemi durduruldu")

    def get_info(self) -> dict[str, Any]:
        """BDI Agent hakkinda ozet bilgi dondurur."""
        base_info = super().get_info()
        base_info.update({
            "beliefs_count": len(self.beliefs.get_all()),
            "active_desires": len(self.desires.get_active()),
            "active_intentions": len(
                self.intentions.get_active_intentions(),
            ),
            "cycle_count": self._cycle_count,
            "cycle_running": self._running,
            "commitment_strategy": self.commitment_strategy.value,
            "registered_agents": list(self.agents.keys()),
            "plan_library_size": len(self.intentions.plan_library),
        })
        return base_info
