"""ATLAS Akil Yurutme Izleyici modulu.

Adim-adim iz, mantik zinciri,
cikarim adimlari, kural uygulamalari, model ciktilari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReasoningTracer:
    """Akil yurutme izleyici.

    Karar surecindeki akil yurutmeyi izler.

    Attributes:
        _traces: Iz kayitlari.
        _chains: Mantik zincirleri.
    """

    def __init__(self) -> None:
        """Akil yurutme izleyiciyi baslatir."""
        self._traces: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._chains: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "traces": 0,
            "steps": 0,
        }

        logger.info(
            "ReasoningTracer baslatildi",
        )

    def start_trace(
        self,
        decision_id: str,
        reasoning_type: str = "deductive",
    ) -> dict[str, Any]:
        """Iz baslatir.

        Args:
            decision_id: Karar ID.
            reasoning_type: Akil yurutme tipi.

        Returns:
            Baslatma bilgisi.
        """
        self._traces[decision_id] = []
        self._chains[decision_id] = {
            "decision_id": decision_id,
            "reasoning_type": reasoning_type,
            "started_at": time.time(),
            "completed_at": None,
        }
        self._stats["traces"] += 1

        return {
            "decision_id": decision_id,
            "trace_started": True,
        }

    def add_step(
        self,
        decision_id: str,
        step_type: str,
        description: str,
        inputs: dict[str, Any] | None = None,
        output: str = "",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Akil yurutme adimi ekler.

        Args:
            decision_id: Karar ID.
            step_type: Adim tipi.
            description: Aciklama.
            inputs: Girdi verileri.
            output: Cikti.
            confidence: Guven skoru.

        Returns:
            Ekleme bilgisi.
        """
        if decision_id not in self._traces:
            return {"error": "trace_not_found"}

        step_num = len(
            self._traces[decision_id],
        ) + 1

        step = {
            "step_number": step_num,
            "step_type": step_type,
            "description": description,
            "inputs": inputs or {},
            "output": output,
            "confidence": confidence,
            "timestamp": time.time(),
        }

        self._traces[decision_id].append(step)
        self._stats["steps"] += 1

        return {
            "decision_id": decision_id,
            "step_number": step_num,
            "added": True,
        }

    def add_inference(
        self,
        decision_id: str,
        premise: str,
        conclusion: str,
        rule: str = "",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Cikarim adimi ekler.

        Args:
            decision_id: Karar ID.
            premise: Oncul.
            conclusion: Sonuc.
            rule: Uygulanan kural.
            confidence: Guven skoru.

        Returns:
            Ekleme bilgisi.
        """
        return self.add_step(
            decision_id,
            step_type="inference",
            description=conclusion,
            inputs={
                "premise": premise,
                "rule": rule,
            },
            output=conclusion,
            confidence=confidence,
        )

    def add_rule_application(
        self,
        decision_id: str,
        rule_name: str,
        conditions: dict[str, Any],
        result: str,
    ) -> dict[str, Any]:
        """Kural uygulamasi ekler.

        Args:
            decision_id: Karar ID.
            rule_name: Kural adi.
            conditions: Kosullar.
            result: Sonuc.

        Returns:
            Ekleme bilgisi.
        """
        return self.add_step(
            decision_id,
            step_type="rule_application",
            description=f"Rule: {rule_name}",
            inputs=conditions,
            output=result,
        )

    def add_model_output(
        self,
        decision_id: str,
        model_name: str,
        input_data: dict[str, Any],
        output: str,
        confidence: float = 0.0,
    ) -> dict[str, Any]:
        """Model ciktisi ekler.

        Args:
            decision_id: Karar ID.
            model_name: Model adi.
            input_data: Girdi verisi.
            output: Cikti.
            confidence: Guven skoru.

        Returns:
            Ekleme bilgisi.
        """
        return self.add_step(
            decision_id,
            step_type="model_output",
            description=f"Model: {model_name}",
            inputs=input_data,
            output=output,
            confidence=confidence,
        )

    def complete_trace(
        self,
        decision_id: str,
        conclusion: str = "",
    ) -> dict[str, Any]:
        """Iz tamamlar.

        Args:
            decision_id: Karar ID.
            conclusion: Sonuc.

        Returns:
            Tamamlama bilgisi.
        """
        if decision_id not in self._chains:
            return {"error": "trace_not_found"}

        chain = self._chains[decision_id]
        chain["completed_at"] = time.time()
        chain["conclusion"] = conclusion

        steps = self._traces.get(
            decision_id, [],
        )

        return {
            "decision_id": decision_id,
            "steps": len(steps),
            "reasoning_type": chain[
                "reasoning_type"
            ],
            "conclusion": conclusion,
            "completed": True,
        }

    def get_trace(
        self,
        decision_id: str,
    ) -> dict[str, Any]:
        """Iz getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            Iz bilgisi.
        """
        if decision_id not in self._traces:
            return {"error": "trace_not_found"}

        steps = self._traces[decision_id]
        chain = self._chains.get(
            decision_id, {},
        )

        return {
            "decision_id": decision_id,
            "reasoning_type": chain.get(
                "reasoning_type", "",
            ),
            "steps": list(steps),
            "step_count": len(steps),
            "conclusion": chain.get(
                "conclusion", "",
            ),
        }

    def get_logic_chain(
        self,
        decision_id: str,
    ) -> list[str]:
        """Mantik zinciri getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            Mantik adim listesi.
        """
        steps = self._traces.get(
            decision_id, [],
        )
        return [
            s["description"] for s in steps
        ]

    @property
    def trace_count(self) -> int:
        """Iz sayisi."""
        return self._stats["traces"]

    @property
    def total_steps(self) -> int:
        """Toplam adim sayisi."""
        return self._stats["steps"]
