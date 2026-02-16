"""ATLAS Komut Tahmincisi modülü.

Sonraki komut tahmini, bağlam bazlı öneri,
zaman bazlı kalıplar, iş akışı tahmini,
proaktif yardım.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CommandPredictor:
    """Komut tahmincisi.

    Kullanıcının sonraki komutunu tahmin eder.

    Attributes:
        _history: Komut geçmişi.
        _transitions: Geçiş tablosu.
    """

    def __init__(self) -> None:
        """Tahminciyı başlatır."""
        self._history: list[
            dict[str, Any]
        ] = []
        self._transitions: dict[
            str, dict[str, int]
        ] = {}
        self._time_patterns: dict[
            int, dict[str, int]
        ] = {}
        self._workflows: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "predictions_made": 0,
            "correct_predictions": 0,
            "suggestions_given": 0,
        }

        logger.info(
            "CommandPredictor baslatildi",
        )

    def observe(
        self,
        command: str,
        context: str = "",
        hour: int | None = None,
    ) -> dict[str, Any]:
        """Komutu gözlemler.

        Args:
            command: Komut.
            context: Bağlam.
            hour: Saat (0-23).

        Returns:
            Gözlem bilgisi.
        """
        self._counter += 1
        oid = f"obs_{self._counter}"

        now_hour = hour if hour is not None else 12

        record = {
            "observation_id": oid,
            "command": command,
            "context": context,
            "hour": now_hour,
            "timestamp": time.time(),
        }
        self._history.append(record)

        # Geçiş tablosunu güncelle
        if len(self._history) >= 2:
            prev = self._history[-2][
                "command"
            ]
            if prev not in self._transitions:
                self._transitions[prev] = {}
            self._transitions[prev][
                command
            ] = self._transitions[prev].get(
                command, 0,
            ) + 1

        # Zaman kalıbı
        if now_hour not in (
            self._time_patterns
        ):
            self._time_patterns[
                now_hour
            ] = {}
        self._time_patterns[now_hour][
            command
        ] = self._time_patterns[
            now_hour
        ].get(command, 0) + 1

        return {
            "observation_id": oid,
            "command": command,
            "observed": True,
        }

    def predict_next(
        self,
        current_command: str,
        top_n: int = 3,
    ) -> dict[str, Any]:
        """Sonraki komutu tahmin eder.

        Args:
            current_command: Mevcut komut.
            top_n: İlk N tahmin.

        Returns:
            Tahmin bilgisi.
        """
        transitions = self._transitions.get(
            current_command, {},
        )

        if not transitions:
            self._stats[
                "predictions_made"
            ] += 1
            return {
                "predictions": [],
                "confidence": 0.0,
            }

        total = sum(transitions.values())
        predictions = []
        for cmd, count in sorted(
            transitions.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]:
            predictions.append({
                "command": cmd,
                "probability": round(
                    count / total, 3,
                ),
                "count": count,
            })

        confidence = (
            predictions[0]["probability"]
            if predictions
            else 0.0
        )
        self._stats[
            "predictions_made"
        ] += 1

        return {
            "current": current_command,
            "predictions": predictions,
            "confidence": round(
                confidence, 3,
            ),
        }

    def suggest_by_context(
        self,
        context: str,
        top_n: int = 3,
    ) -> dict[str, Any]:
        """Bağlam bazlı öneri verir.

        Args:
            context: Bağlam.
            top_n: İlk N öneri.

        Returns:
            Öneri bilgisi.
        """
        context_lower = context.lower()
        freq: dict[str, int] = {}

        for record in self._history:
            if (
                context_lower
                in record.get(
                    "context", "",
                ).lower()
            ):
                cmd = record["command"]
                freq[cmd] = (
                    freq.get(cmd, 0) + 1
                )

        suggestions = []
        for cmd, count in sorted(
            freq.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]:
            suggestions.append({
                "command": cmd,
                "relevance": count,
            })

        self._stats[
            "suggestions_given"
        ] += 1

        return {
            "context": context,
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    def get_time_patterns(
        self,
        hour: int,
    ) -> dict[str, Any]:
        """Zaman bazlı kalıpları getirir.

        Args:
            hour: Saat (0-23).

        Returns:
            Kalıp bilgisi.
        """
        patterns = self._time_patterns.get(
            hour, {},
        )
        sorted_patterns = sorted(
            patterns.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "hour": hour,
            "commands": dict(
                sorted_patterns[:5],
            ),
            "total": sum(patterns.values()),
        }

    def define_workflow(
        self,
        name: str,
        commands: list[str],
    ) -> dict[str, Any]:
        """İş akışı tanımlar.

        Args:
            name: İş akışı adı.
            commands: Komut dizisi.

        Returns:
            Tanımlama bilgisi.
        """
        self._workflows[name] = commands
        return {
            "name": name,
            "steps": len(commands),
            "defined": True,
        }

    def predict_workflow(
        self,
        current_command: str,
    ) -> dict[str, Any]:
        """İş akışını tahmin eder.

        Args:
            current_command: Mevcut komut.

        Returns:
            Tahmin bilgisi.
        """
        matches = []
        for name, commands in (
            self._workflows.items()
        ):
            if current_command in commands:
                idx = commands.index(
                    current_command,
                )
                remaining = commands[idx + 1:]
                if remaining:
                    matches.append({
                        "workflow": name,
                        "next_steps": remaining,
                        "progress": round(
                            (idx + 1)
                            / len(commands),
                            2,
                        ),
                    })

        return {
            "current": current_command,
            "workflows": matches,
            "count": len(matches),
        }

    def verify_prediction(
        self,
        predicted: str,
        actual: str,
    ) -> dict[str, Any]:
        """Tahmini doğrular.

        Args:
            predicted: Tahmin edilen.
            actual: Gerçekleşen.

        Returns:
            Doğrulama bilgisi.
        """
        correct = predicted == actual
        if correct:
            self._stats[
                "correct_predictions"
            ] += 1

        total = self._stats[
            "predictions_made"
        ]
        accuracy = (
            self._stats[
                "correct_predictions"
            ]
            / max(total, 1)
        )

        return {
            "predicted": predicted,
            "actual": actual,
            "correct": correct,
            "accuracy": round(accuracy, 3),
        }

    @property
    def prediction_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats[
            "predictions_made"
        ]

    @property
    def accuracy(self) -> float:
        """Doğruluk oranı."""
        total = self._stats[
            "predictions_made"
        ]
        if total == 0:
            return 0.0
        return round(
            self._stats[
                "correct_predictions"
            ]
            / total,
            3,
        )
