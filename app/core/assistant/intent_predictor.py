"""ATLAS Niyet Tahmincisi modulu.

Kullanicinin bir sonraki istegini tahmin eder,
proaktif oneriler sunar, davranis kaliplarini
tanir ve ongorusel aksiyonlar belirler.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import IntentCategory, IntentPrediction

logger = logging.getLogger(__name__)


class IntentPredictor:
    """Niyet tahmincisi.

    Kullanici davranislarindan ogrenip
    gelecek istekleri tahmin eder.

    Attributes:
        _predictions: Tahmin gecmisi.
        _patterns: Davranis kaliplari.
        _behavior_model: Davranis modeli.
        _sequences: Istek dizileri.
        _accuracy_log: Dogruluk kaydi.
    """

    def __init__(self) -> None:
        """Niyet tahmincisini baslatir."""
        self._predictions: list[IntentPrediction] = []
        self._patterns: dict[str, list[str]] = {}
        self._behavior_model: dict[str, dict[str, int]] = {}
        self._sequences: list[dict[str, Any]] = []
        self._accuracy_log: list[dict[str, Any]] = []
        self._correct_count = 0
        self._total_verified = 0

        logger.info("IntentPredictor baslatildi")

    def record_action(
        self,
        action: str,
        category: IntentCategory | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Aksiyon kaydeder.

        Args:
            action: Aksiyon adi.
            category: Niyet kategorisi.
            context: Baglam.
        """
        entry = {
            "action": action,
            "category": (category or IntentCategory.COMMAND).value,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._sequences.append(entry)

        # Davranis modeli guncelle
        if len(self._sequences) >= 2:
            prev = self._sequences[-2]["action"]
            curr = action
            self._behavior_model.setdefault(prev, {})
            self._behavior_model[prev][curr] = (
                self._behavior_model[prev].get(curr, 0) + 1
            )

    def predict_next(
        self,
        current_action: str,
        context: dict[str, Any] | None = None,
    ) -> IntentPrediction:
        """Bir sonraki istegi tahmin eder.

        Args:
            current_action: Mevcut aksiyon.
            context: Baglam.

        Returns:
            IntentPrediction nesnesi.
        """
        transitions = self._behavior_model.get(current_action, {})

        if not transitions:
            prediction = IntentPrediction(
                category=IntentCategory.QUERY,
                predicted_action="unknown",
                confidence=0.1,
                reasoning="Yeterli veri yok",
            )
            self._predictions.append(prediction)
            return prediction

        total = sum(transitions.values())
        best_action = max(transitions, key=transitions.get)  # type: ignore[arg-type]
        best_count = transitions[best_action]
        confidence = round(best_count / total, 3) if total > 0 else 0.1

        # Kategori tahmin et
        category = self._infer_category(best_action)

        prediction = IntentPrediction(
            category=category,
            predicted_action=best_action,
            confidence=confidence,
            reasoning=f"{best_count}/{total} gecis ({confidence:.0%})",
        )
        self._predictions.append(prediction)

        logger.info(
            "Tahmin: %s -> %s (guven=%.2f)",
            current_action, best_action, confidence,
        )
        return prediction

    def suggest_proactively(
        self,
        recent_actions: list[str],
        max_suggestions: int = 3,
    ) -> list[IntentPrediction]:
        """Proaktif oneriler sunar.

        Args:
            recent_actions: Son aksiyonlar.
            max_suggestions: Maks oneri sayisi.

        Returns:
            Oneri listesi.
        """
        suggestions: list[IntentPrediction] = []

        for action in recent_actions:
            transitions = self._behavior_model.get(action, {})
            if not transitions:
                continue

            total = sum(transitions.values())
            sorted_actions = sorted(
                transitions.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            for next_action, count in sorted_actions[:max_suggestions]:
                conf = round(count / total, 3) if total > 0 else 0.1
                if conf < 0.2:
                    continue

                suggestions.append(IntentPrediction(
                    category=self._infer_category(next_action),
                    predicted_action=next_action,
                    confidence=conf,
                    reasoning=f"Gecmis kalibina dayali ({action} sonrasi)",
                ))

        # Benzersiz, guvene gore sirali
        seen: set[str] = set()
        unique: list[IntentPrediction] = []
        for s in sorted(suggestions, key=lambda x: x.confidence, reverse=True):
            if s.predicted_action not in seen:
                seen.add(s.predicted_action)
                unique.append(s)

        return unique[:max_suggestions]

    def add_pattern(
        self,
        pattern_name: str,
        action_sequence: list[str],
    ) -> None:
        """Davranis kalibi ekler.

        Args:
            pattern_name: Kalip adi.
            action_sequence: Aksiyon dizisi.
        """
        self._patterns[pattern_name] = list(action_sequence)

        # Diziden gecisleri ogren
        for i in range(len(action_sequence) - 1):
            prev = action_sequence[i]
            curr = action_sequence[i + 1]
            self._behavior_model.setdefault(prev, {})
            self._behavior_model[prev][curr] = (
                self._behavior_model[prev].get(curr, 0) + 2
            )

    def recognize_pattern(
        self,
        recent_actions: list[str],
    ) -> dict[str, Any]:
        """Kalip tanir.

        Args:
            recent_actions: Son aksiyonlar.

        Returns:
            Taninan kalip bilgisi.
        """
        if not recent_actions:
            return {"matched": False, "pattern": None}

        best_match = ""
        best_score = 0.0

        for name, sequence in self._patterns.items():
            if len(recent_actions) < 2:
                continue

            match_count = 0
            check_len = min(len(recent_actions), len(sequence))
            for i in range(check_len):
                if recent_actions[i] == sequence[i]:
                    match_count += 1

            score = match_count / len(sequence) if sequence else 0.0
            if score > best_score:
                best_score = score
                best_match = name

        if best_score >= 0.5:
            return {
                "matched": True,
                "pattern": best_match,
                "confidence": round(best_score, 3),
                "next_expected": self._get_pattern_next(
                    best_match, len(recent_actions),
                ),
            }

        return {"matched": False, "pattern": None}

    def verify_prediction(
        self,
        prediction_id: str,
        actual_action: str,
    ) -> dict[str, Any]:
        """Tahmini dogrular.

        Args:
            prediction_id: Tahmin ID.
            actual_action: Gercek aksiyon.

        Returns:
            Dogrulama sonucu.
        """
        target = None
        for p in self._predictions:
            if p.prediction_id == prediction_id:
                target = p
                break

        if not target:
            return {"verified": False, "reason": "Tahmin bulunamadi"}

        correct = target.predicted_action == actual_action
        self._total_verified += 1
        if correct:
            self._correct_count += 1

        result = {
            "verified": True,
            "correct": correct,
            "predicted": target.predicted_action,
            "actual": actual_action,
            "accuracy": self.accuracy,
        }
        self._accuracy_log.append(result)

        return result

    def get_behavior_model(self) -> dict[str, dict[str, int]]:
        """Davranis modelini getirir.

        Returns:
            Gecis matrisi.
        """
        return {k: dict(v) for k, v in self._behavior_model.items()}

    def _infer_category(self, action: str) -> IntentCategory:
        """Aksiyondan kategori cikarir.

        Args:
            action: Aksiyon adi.

        Returns:
            IntentCategory.
        """
        action_lower = action.lower()
        if any(w in action_lower for w in ["soru", "query", "ara", "bul"]):
            return IntentCategory.QUERY
        if any(w in action_lower for w in ["devam", "sonra", "follow"]):
            return IntentCategory.FOLLOW_UP
        if any(w in action_lower for w in ["acikla", "nedir", "nasil"]):
            return IntentCategory.CLARIFICATION
        if any(w in action_lower for w in ["iyi", "kotu", "degistir"]):
            return IntentCategory.FEEDBACK
        return IntentCategory.COMMAND

    def _get_pattern_next(
        self,
        pattern_name: str,
        current_pos: int,
    ) -> str | None:
        """Kaliptaki sonraki adimi getirir.

        Args:
            pattern_name: Kalip adi.
            current_pos: Mevcut pozisyon.

        Returns:
            Sonraki aksiyon veya None.
        """
        sequence = self._patterns.get(pattern_name, [])
        if current_pos < len(sequence):
            return sequence[current_pos]
        return None

    @property
    def accuracy(self) -> float:
        """Tahmin dogrulugu."""
        if self._total_verified == 0:
            return 0.0
        return round(self._correct_count / self._total_verified, 3)

    @property
    def prediction_count(self) -> int:
        """Tahmin sayisi."""
        return len(self._predictions)

    @property
    def pattern_count(self) -> int:
        """Kalip sayisi."""
        return len(self._patterns)

    @property
    def sequence_count(self) -> int:
        """Dizi sayisi."""
        return len(self._sequences)
