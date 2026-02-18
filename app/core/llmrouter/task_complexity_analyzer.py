"""
Gorev karmasiklik analizcisi modulu.

Karmasiklik puanlama, token tahmini,
muhakeme derinligi, alan tespiti,
kaynak tahmini.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskComplexityAnalyzer:
    """Gorev karmasiklik analizcisi.

    Attributes:
        _analyses: Analiz kayitlari.
        _domain_patterns: Alan kaliplari.
        _stats: Istatistikler.
    """

    COMPLEXITY_LEVELS: list[str] = [
        "trivial",
        "simple",
        "moderate",
        "complex",
        "expert",
    ]

    DOMAINS: list[str] = [
        "general",
        "coding",
        "math",
        "science",
        "legal",
        "medical",
        "finance",
        "creative",
        "translation",
        "analysis",
    ]

    def __init__(self) -> None:
        """Analizcivi baslatir."""
        self._analyses: dict[
            str, dict
        ] = {}
        self._domain_patterns: dict[
            str, list[str]
        ] = {
            "coding": [
                "code", "function",
                "bug", "api",
                "program", "debug",
            ],
            "math": [
                "calculate", "equation",
                "formula", "proof",
                "number", "solve",
            ],
            "legal": [
                "contract", "law",
                "regulation", "compliance",
                "legal", "clause",
            ],
            "medical": [
                "diagnosis", "treatment",
                "patient", "symptom",
                "medical", "health",
            ],
            "finance": [
                "revenue", "cost",
                "investment", "profit",
                "budget", "financial",
            ],
            "creative": [
                "write", "story",
                "design", "creative",
                "poem", "content",
            ],
        }
        self._stats: dict[str, int] = {
            "analyses_performed": 0,
            "high_complexity": 0,
            "low_complexity": 0,
        }
        logger.info(
            "TaskComplexityAnalyzer "
            "baslatildi"
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._analyses)

    def analyze_complexity(
        self,
        task_text: str = "",
        context: str = "",
        max_tokens_hint: int = 0,
    ) -> dict[str, Any]:
        """Gorev karmasikligini analiz eder.

        Args:
            task_text: Gorev metni.
            context: Baglam.
            max_tokens_hint: Token ipucu.

        Returns:
            Analiz sonucu.
        """
        try:
            aid = f"ca_{uuid4()!s:.8}"

            # Karmasiklik hesapla
            score = (
                self._calculate_complexity(
                    task_text, context
                )
            )
            level = (
                self._score_to_level(score)
            )
            domain = self._detect_domain(
                task_text
            )
            tokens = (
                self._estimate_tokens(
                    task_text,
                    score,
                    max_tokens_hint,
                )
            )
            reasoning = (
                self._estimate_reasoning(
                    score
                )
            )

            self._analyses[aid] = {
                "analysis_id": aid,
                "task_text": task_text[:200],
                "complexity_score": score,
                "complexity_level": level,
                "domain": domain,
                "estimated_tokens": tokens,
                "reasoning_depth": reasoning,
                "analyzed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "analyses_performed"
            ] += 1

            if score >= 0.7:
                self._stats[
                    "high_complexity"
                ] += 1
            elif score <= 0.3:
                self._stats[
                    "low_complexity"
                ] += 1

            return {
                "analysis_id": aid,
                "complexity_score": score,
                "complexity_level": level,
                "domain": domain,
                "estimated_tokens": tokens,
                "reasoning_depth": reasoning,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def _calculate_complexity(
        self,
        text: str,
        context: str,
    ) -> float:
        """Karmasiklik puani hesaplar."""
        score = 0.0

        # Metin uzunlugu
        words = len(text.split())
        if words > 200:
            score += 0.3
        elif words > 50:
            score += 0.2
        elif words > 10:
            score += 0.1

        # Baglam varligi
        if context:
            score += 0.1

        # Karmasiklik isaretcileri
        markers = [
            "analyze", "compare",
            "evaluate", "design",
            "optimize", "implement",
            "explain why", "complex",
            "multi-step", "trade-off",
        ]
        text_lower = text.lower()
        found = sum(
            1
            for m in markers
            if m in text_lower
        )
        score += min(found * 0.08, 0.4)

        # Soru isareti sayisi
        q_count = text.count("?")
        score += min(q_count * 0.05, 0.15)

        return min(1.0, round(score, 2))

    def _score_to_level(
        self,
        score: float,
    ) -> str:
        """Puan -> seviye donusumu."""
        if score >= 0.8:
            return "expert"
        if score >= 0.6:
            return "complex"
        if score >= 0.4:
            return "moderate"
        if score >= 0.2:
            return "simple"
        return "trivial"

    def _detect_domain(
        self,
        text: str,
    ) -> str:
        """Alan tespiti yapar."""
        text_lower = text.lower()
        best_domain = "general"
        best_score = 0

        for domain, keywords in (
            self._domain_patterns.items()
        ):
            matches = sum(
                1
                for kw in keywords
                if kw in text_lower
            )
            if matches > best_score:
                best_score = matches
                best_domain = domain

        return best_domain

    def _estimate_tokens(
        self,
        text: str,
        score: float,
        hint: int,
    ) -> int:
        """Token tahmini yapar."""
        if hint > 0:
            return hint

        base = len(text.split()) * 2
        multiplier = 1.0 + (score * 4.0)
        return max(
            256, int(base * multiplier)
        )

    def _estimate_reasoning(
        self,
        score: float,
    ) -> str:
        """Muhakeme derinligi tahmin."""
        if score >= 0.8:
            return "deep"
        if score >= 0.5:
            return "moderate"
        return "shallow"

    def predict_resources(
        self,
        analysis_id: str = "",
    ) -> dict[str, Any]:
        """Kaynak tahmini yapar.

        Args:
            analysis_id: Analiz ID.

        Returns:
            Kaynak tahmini.
        """
        try:
            a = self._analyses.get(
                analysis_id
            )
            if not a:
                return {
                    "predicted": False,
                    "error": (
                        "Analiz bulunamadi"
                    ),
                }

            score = a["complexity_score"]
            tokens = a["estimated_tokens"]

            # Tahmini sure (ms)
            latency_ms = int(
                tokens * (2.0 + score * 8.0)
            )
            # Tahmini maliyet ($)
            cost = round(
                tokens
                * (0.00001 + score * 0.0001),
                6,
            )

            return {
                "analysis_id": analysis_id,
                "estimated_latency_ms": (
                    latency_ms
                ),
                "estimated_cost": cost,
                "recommended_tier": (
                    "premium"
                    if score >= 0.6
                    else "standard"
                ),
                "predicted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "predicted": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_level: dict[str, int] = {}
            by_domain: dict[str, int] = {}
            for a in (
                self._analyses.values()
            ):
                lv = a["complexity_level"]
                by_level[lv] = (
                    by_level.get(lv, 0) + 1
                )
                dm = a["domain"]
                by_domain[dm] = (
                    by_domain.get(dm, 0) + 1
                )

            return {
                "total_analyses": len(
                    self._analyses
                ),
                "by_level": by_level,
                "by_domain": by_domain,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
