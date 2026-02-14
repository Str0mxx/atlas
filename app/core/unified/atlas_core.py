"""ATLAS Ana Cekirdek modulu.

Merkezi zeka merkezi, tum sistem entegrasyonu,
birlesik API, ana kontrol dongusu.
ATLAS'in "ruhu".
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.unified import (
    ConsciousnessLevel,
    DecisionSource,
    EntityType,
    ReasoningType,
    UnifiedSnapshot,
)

from app.core.unified.action_coordinator import ActionCoordinator
from app.core.unified.attention_manager import AttentionManager
from app.core.unified.consciousness import Consciousness
from app.core.unified.decision_integrator import DecisionIntegrator
from app.core.unified.persona_manager import PersonaManager
from app.core.unified.reasoning_engine import ReasoningEngine
from app.core.unified.reflection_module import ReflectionModule
from app.core.unified.world_model import WorldModel

logger = logging.getLogger(__name__)


class ATLASCore:
    """ATLAS ana cekirdegi.

    Tum alt sistemleri birlestiren
    merkezi zeka ve kontrol noktasi.

    Attributes:
        _consciousness: Bilinc katmani.
        _reasoning: Akil yurutme motoru.
        _attention: Dikkat yoneticisi.
        _world: Dunya modeli.
        _decisions: Karar entegratouru.
        _actions: Aksiyon koordinatoru.
        _reflection: Yansima modulu.
        _persona: Kisilik yoneticisi.
    """

    def __init__(
        self,
        consciousness_level: str = "medium",
        reasoning_depth: int = 10,
        reflection_interval: int = 3600,
        persona_consistency: float = 0.8,
    ) -> None:
        """ATLAS cekirdegini baslatir.

        Args:
            consciousness_level: Bilinc seviyesi.
            reasoning_depth: Akil yurutme derinligi.
            reflection_interval: Yansima araligi (sn).
            persona_consistency: Kisilik tutarliligi.
        """
        level_map = {
            "low": ConsciousnessLevel.LOW,
            "medium": ConsciousnessLevel.MEDIUM,
            "high": ConsciousnessLevel.HIGH,
        }
        level = level_map.get(consciousness_level, ConsciousnessLevel.MEDIUM)

        self._consciousness = Consciousness(initial_level=level)
        self._reasoning = ReasoningEngine(max_depth=reasoning_depth)
        self._attention = AttentionManager(total_capacity=1.0)
        self._world = WorldModel()
        self._decisions = DecisionIntegrator()
        self._actions = ActionCoordinator()
        self._reflection = ReflectionModule()
        self._persona = PersonaManager()

        self._reflection_interval = reflection_interval
        self._persona_consistency = persona_consistency
        self._started_at = datetime.now(timezone.utc)
        self._cycle_count = 0
        self._events: list[dict[str, Any]] = []

        # Kendini dunya modeline ekle
        self._world.add_entity(
            "ATLAS", EntityType.SYSTEM,
            properties={"role": "core", "version": "1.0"},
        )

        logger.info(
            "ATLASCore baslatildi (level=%s, depth=%d)",
            consciousness_level, reasoning_depth,
        )

    def perceive(
        self,
        source: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Algi islemi - cevreden bilgi alir.

        Args:
            source: Bilgi kaynagi.
            data: Algilanan veri.

        Returns:
            Algi sonucu.
        """
        # Cevre bilgisini guncelle
        self._consciousness.update_environment({source: data})

        # Dunya modeline varlik ekle/guncelle
        existing = self._world.find_by_state("active")
        source_entity = None
        for e in existing:
            if e.name == source:
                source_entity = e
                break

        if not source_entity:
            source_entity = self._world.add_entity(
                source, EntityType.EXTERNAL,
                properties=data,
            )
        else:
            self._world.update_entity(
                source_entity.entity_id,
                properties=data,
            )

        # Dikkat ayarla
        priority = data.get("priority", 5)
        if isinstance(priority, (int, float)):
            priority = int(min(10, max(1, priority)))
        else:
            priority = 5

        self._events.append({
            "type": "perception",
            "source": source,
            "priority": priority,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "perceived": True,
            "source": source,
            "entity_id": source_entity.entity_id,
        }

    def think(
        self,
        question: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dusunme islemi - akil yurutur.

        Args:
            question: Soru/problem.
            context: Baglam.

        Returns:
            Dusunme sonucu.
        """
        ctx = context or {}

        # Dikkat odakla
        focus = self._attention.focus_on(
            question, priority=7, capacity=0.3,
        )

        # Mantiksal akil yurutme
        premises = ctx.get("premises", [question])
        chain = self._reasoning.reason_logically(premises)

        # Ic gozlem
        introspection = self._consciousness.introspect()

        # Odagi serbest birak
        if focus:
            self._attention.release_focus(focus.focus_id)

        return {
            "question": question,
            "reasoning": {
                "chain_id": chain.chain_id,
                "conclusion": chain.conclusion,
                "confidence": chain.confidence,
            },
            "consciousness": {
                "level": introspection["level"],
                "confidence": introspection["confidence"],
            },
        }

    def decide(
        self,
        question: str,
        options: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Karar islemi - entegre karar verir.

        Args:
            question: Karar noktasi.
            options: Secenekler (source, action, confidence).

        Returns:
            Karar sonucu.
        """
        # Onerileri ekle
        for opt in options:
            source = opt.get("source", "rule_based")
            if isinstance(source, str):
                try:
                    source = DecisionSource(source)
                except ValueError:
                    source = DecisionSource.RULE_BASED

            self._decisions.add_proposal(
                question,
                source,
                opt.get("action", ""),
                opt.get("confidence", 0.5),
                opt.get("reasoning", ""),
            )

        # Sentezle
        decision = self._decisions.synthesize(question)
        if not decision:
            return {"success": False, "reason": "Sentez yapilamadi"}

        # Kisilik tutarlilik kontrolu
        consistency = self._persona.check_consistency(
            decision.chosen_action,
        )

        return {
            "success": True,
            "decision_id": decision.decision_id,
            "chosen_action": decision.chosen_action,
            "confidence": decision.confidence,
            "explanation": decision.explanation,
            "consistent": consistency["consistent"],
        }

    def act(
        self,
        action_name: str,
        target_systems: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Eylem islemi - aksiyonu koordine eder.

        Args:
            action_name: Aksiyon adi.
            target_systems: Hedef sistemler.
            parameters: Parametreler.

        Returns:
            Eylem sonucu.
        """
        action = self._actions.create_action(
            action_name,
            target_systems=target_systems,
            parameters=parameters,
        )
        result = self._actions.execute_action(action["action_id"])

        # Olay kaydet
        self._events.append({
            "type": "action",
            "name": action_name,
            "success": result["success"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return result

    def reflect(self) -> dict[str, Any]:
        """Yansima islemi - kendini degerlendirir.

        Returns:
            Yansima sonucu.
        """
        self._cycle_count += 1

        # Oz-degerlendirme
        eval_record = self._reflection.self_evaluate(
            f"Dongu {self._cycle_count}",
            criteria={
                "consciousness": min(1.0, self._consciousness.uptime / 3600),
                "attention": 1.0 - self._attention.used_capacity,
                "world_model": min(1.0, self._world.entity_count / 10),
                "decisions": min(
                    1.0, self._decisions.total_decisions / 5,
                ),
                "actions": min(
                    1.0, self._actions.completed_actions / 5,
                ),
            },
        )

        # Guven degerlendirmesi
        confidence = self._consciousness.assess_confidence()

        return {
            "cycle": self._cycle_count,
            "score": eval_record.score,
            "confidence": confidence,
            "findings": eval_record.findings,
            "overall": self._reflection.get_overall_score(),
        }

    def run_cycle(
        self,
        inputs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Ana kontrol dongusunu calistirir.

        Args:
            inputs: Girdi listesi.

        Returns:
            Dongu sonucu.
        """
        cycle_start = datetime.now(timezone.utc)
        self._cycle_count += 1

        # 1. Algi
        perceptions = []
        for inp in (inputs or []):
            p = self.perceive(
                inp.get("source", "unknown"),
                inp.get("data", {}),
            )
            perceptions.append(p)

        # 2. Bilinc guncelle
        self._consciousness.update_self_state("processing")

        # 3. Ic gozlem
        self._consciousness.introspect()

        # 4. Bilinc guncelle
        self._consciousness.update_self_state("operational")

        cycle_duration = (
            datetime.now(timezone.utc) - cycle_start
        ).total_seconds()

        return {
            "cycle": self._cycle_count,
            "perceptions": len(perceptions),
            "duration": round(cycle_duration, 4),
            "consciousness_level": self._consciousness.level.value,
        }

    def get_snapshot(self) -> UnifiedSnapshot:
        """Anlik goruntuyu getirir.

        Returns:
            UnifiedSnapshot nesnesi.
        """
        reflection_score = self._reflection.get_overall_score()

        return UnifiedSnapshot(
            consciousness_level=self._consciousness.level.value,
            active_focuses=self._attention.focus_count,
            world_entities=self._world.entity_count,
            reasoning_chains=self._reasoning.total_chains,
            decisions_made=self._decisions.total_decisions,
            reflections=self._reflection.total_records,
            uptime_seconds=round(self._consciousness.uptime, 2),
            overall_health=round(reflection_score, 3),
        )

    # Alt sistem erisimi
    @property
    def consciousness(self) -> Consciousness:
        """Bilinc katmani."""
        return self._consciousness

    @property
    def reasoning(self) -> ReasoningEngine:
        """Akil yurutme motoru."""
        return self._reasoning

    @property
    def attention(self) -> AttentionManager:
        """Dikkat yoneticisi."""
        return self._attention

    @property
    def world(self) -> WorldModel:
        """Dunya modeli."""
        return self._world

    @property
    def decisions(self) -> DecisionIntegrator:
        """Karar entegratouru."""
        return self._decisions

    @property
    def actions(self) -> ActionCoordinator:
        """Aksiyon koordinatoru."""
        return self._actions

    @property
    def reflection(self) -> ReflectionModule:
        """Yansima modulu."""
        return self._reflection

    @property
    def persona(self) -> PersonaManager:
        """Kisilik yoneticisi."""
        return self._persona

    @property
    def cycle_count(self) -> int:
        """Dongu sayisi."""
        return self._cycle_count

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._events)
