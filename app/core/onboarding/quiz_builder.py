"""ATLAS Quiz Oluşturucu modülü.

Soru üretimi, çoklu format,
zorluk seviyeleri, rastgeleleştirme,
puanlama.
"""

import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)


class QuizBuilder:
    """Quiz oluşturucu.

    Quizler oluşturur ve puanlar.

    Attributes:
        _quizzes: Quiz kayıtları.
        _results: Sonuç kayıtları.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._quizzes: dict[
            str, dict[str, Any]
        ] = {}
        self._results: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "quizzes_created": 0,
            "quizzes_scored": 0,
        }

        logger.info(
            "QuizBuilder baslatildi",
        )

    def generate_questions(
        self,
        topic: str,
        count: int = 5,
        difficulty: str = "medium",
    ) -> dict[str, Any]:
        """Soru üretir.

        Args:
            topic: Konu.
            count: Soru sayısı.
            difficulty: Zorluk.

        Returns:
            Soru bilgisi.
        """
        self._counter += 1
        qid = f"quiz_{self._counter}"

        questions = []
        for i in range(count):
            questions.append({
                "question_id": f"q_{i+1}",
                "text": (
                    f"{topic} soru {i+1}"
                ),
                "format": "multiple_choice",
                "difficulty": difficulty,
                "options": [
                    "A", "B", "C", "D",
                ],
                "correct": "A",
            })

        self._quizzes[qid] = {
            "quiz_id": qid,
            "topic": topic,
            "questions": questions,
            "difficulty": difficulty,
            "timestamp": time.time(),
        }

        self._stats[
            "quizzes_created"
        ] += 1

        return {
            "quiz_id": qid,
            "topic": topic,
            "question_count": count,
            "difficulty": difficulty,
            "generated": True,
        }

    def create_multi_format(
        self,
        topic: str,
        formats: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Çoklu formatta quiz oluşturur.

        Args:
            topic: Konu.
            formats: Formatlar.

        Returns:
            Quiz bilgisi.
        """
        formats = formats or [
            "multiple_choice",
            "true_false",
            "short_answer",
        ]
        self._counter += 1
        qid = f"quiz_{self._counter}"

        questions = []
        for i, fmt in enumerate(formats):
            questions.append({
                "question_id": f"q_{i+1}",
                "text": (
                    f"{topic} {fmt} soru"
                ),
                "format": fmt,
                "difficulty": "medium",
            })

        self._quizzes[qid] = {
            "quiz_id": qid,
            "topic": topic,
            "questions": questions,
            "formats": formats,
            "timestamp": time.time(),
        }

        self._stats[
            "quizzes_created"
        ] += 1

        return {
            "quiz_id": qid,
            "topic": topic,
            "format_count": len(formats),
            "created": True,
        }

    def set_difficulty(
        self,
        quiz_id: str,
        difficulty: str = "medium",
    ) -> dict[str, Any]:
        """Zorluk seviyesi belirler.

        Args:
            quiz_id: Quiz kimliği.
            difficulty: Zorluk.

        Returns:
            Ayar bilgisi.
        """
        quiz = self._quizzes.get(quiz_id)
        if not quiz:
            return {
                "quiz_id": quiz_id,
                "found": False,
            }

        quiz["difficulty"] = difficulty
        for q in quiz["questions"]:
            q["difficulty"] = difficulty

        return {
            "quiz_id": quiz_id,
            "difficulty": difficulty,
            "questions_updated": len(
                quiz["questions"],
            ),
            "set": True,
        }

    def randomize(
        self,
        quiz_id: str,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Soruları rastgeleleştirir.

        Args:
            quiz_id: Quiz kimliği.
            seed: Rastgele tohum.

        Returns:
            Rastgeleleştirme bilgisi.
        """
        quiz = self._quizzes.get(quiz_id)
        if not quiz:
            return {
                "quiz_id": quiz_id,
                "found": False,
            }

        if seed is not None:
            random.seed(seed)

        questions = quiz["questions"]
        random.shuffle(questions)

        for i, q in enumerate(questions):
            q["order"] = i + 1

        return {
            "quiz_id": quiz_id,
            "question_count": len(
                questions,
            ),
            "randomized": True,
        }

    def score_quiz(
        self,
        quiz_id: str,
        answers: dict[str, str]
        | None = None,
    ) -> dict[str, Any]:
        """Quiz puanlar.

        Args:
            quiz_id: Quiz kimliği.
            answers: Yanıtlar
                {question_id: answer}.

        Returns:
            Puanlama bilgisi.
        """
        answers = answers or {}
        quiz = self._quizzes.get(quiz_id)
        if not quiz:
            return {
                "quiz_id": quiz_id,
                "found": False,
            }

        correct = 0
        total = len(quiz["questions"])

        for q in quiz["questions"]:
            qid = q["question_id"]
            if qid in answers:
                if (
                    answers[qid]
                    == q.get("correct", "")
                ):
                    correct += 1

        score = (
            (correct / total) * 100
            if total > 0
            else 0.0
        )
        passed = score >= 60

        result = {
            "quiz_id": quiz_id,
            "correct": correct,
            "total": total,
            "score": score,
            "passed": passed,
            "scored": True,
        }

        self._results.append(result)
        self._stats[
            "quizzes_scored"
        ] += 1

        return result

    @property
    def quiz_count(self) -> int:
        """Quiz sayısı."""
        return self._stats[
            "quizzes_created"
        ]

    @property
    def scored_count(self) -> int:
        """Puanlanan quiz sayısı."""
        return self._stats[
            "quizzes_scored"
        ]
