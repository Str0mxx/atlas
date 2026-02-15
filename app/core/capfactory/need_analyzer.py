"""ATLAS İhtiyaç Analizcisi modülü.

İstek analizi, yetenek eşleme,
boşluk tespiti, karmaşıklık tahmini,
fizibilite kontrolü.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NeedAnalyzer:
    """İhtiyaç analizcisi.

    Gelen istekleri analiz edip yetenek ihtiyaçlarını belirler.

    Attributes:
        _analyses: Analiz kayıtları.
        _capability_map: Mevcut yetenek haritası.
    """

    def __init__(self) -> None:
        """Analizcisi başlatır."""
        self._analyses: list[dict[str, Any]] = []
        self._capability_map: dict[
            str, dict[str, Any]
        ] = {}
        self._complexity_keywords: dict[
            str, list[str]
        ] = {
            "trivial": [
                "log", "print", "format", "convert",
            ],
            "simple": [
                "filter", "sort", "validate", "parse",
            ],
            "moderate": [
                "integrate", "transform", "sync",
                "schedule",
            ],
            "complex": [
                "ml", "predict", "optimize",
                "distribute",
            ],
            "extreme": [
                "realtime", "distributed", "consensus",
                "blockchain",
            ],
        }
        self._counter = 0
        self._stats = {
            "analyses": 0,
            "gaps_found": 0,
            "feasible": 0,
        }

        logger.info("NeedAnalyzer baslatildi")

    def analyze_request(
        self,
        request: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """İsteği analiz eder.

        Args:
            request: İstek metni.
            context: Bağlam bilgisi.

        Returns:
            Analiz sonucu.
        """
        self._counter += 1
        aid = f"analysis_{self._counter}"

        keywords = self._extract_keywords(request)
        complexity = self._estimate_complexity(
            request,
        )
        capabilities = self._map_capabilities(
            keywords,
        )
        gaps = self._identify_gaps(capabilities)
        feasible = self._check_feasibility(
            complexity, gaps,
        )

        analysis = {
            "analysis_id": aid,
            "request": request,
            "context": context or {},
            "keywords": keywords,
            "complexity": complexity,
            "required_capabilities": capabilities,
            "gaps": gaps,
            "feasible": feasible,
            "timestamp": time.time(),
        }
        self._analyses.append(analysis)
        self._stats["analyses"] += 1
        if gaps:
            self._stats["gaps_found"] += len(gaps)
        if feasible:
            self._stats["feasible"] += 1

        return analysis

    def _extract_keywords(
        self,
        request: str,
    ) -> list[str]:
        """Anahtar kelimeler çıkarır."""
        words = request.lower().split()
        stop_words = {
            "the", "a", "an", "is", "are", "was",
            "be", "to", "of", "and", "in", "that",
            "for", "it", "with", "as", "on", "at",
            "by", "i", "we", "need", "want", "can",
        }
        return [
            w for w in words
            if w not in stop_words and len(w) > 2
        ]

    def _estimate_complexity(
        self,
        request: str,
    ) -> str:
        """Karmaşıklık tahmin eder.

        Args:
            request: İstek metni.

        Returns:
            Karmaşıklık seviyesi.
        """
        request_lower = request.lower()

        for level in [
            "extreme", "complex", "moderate",
            "simple", "trivial",
        ]:
            for kw in self._complexity_keywords[level]:
                if kw in request_lower:
                    return level

        word_count = len(request.split())
        if word_count > 30:
            return "complex"
        if word_count > 15:
            return "moderate"
        if word_count > 5:
            return "simple"
        return "trivial"

    def _map_capabilities(
        self,
        keywords: list[str],
    ) -> list[str]:
        """Yetenek eşlemesi yapar."""
        capabilities = []
        for kw in keywords:
            for cap_name, cap_info in (
                self._capability_map.items()
            ):
                cap_keywords = cap_info.get(
                    "keywords", [],
                )
                if kw in cap_keywords:
                    if cap_name not in capabilities:
                        capabilities.append(cap_name)
        return capabilities

    def _identify_gaps(
        self,
        required: list[str],
    ) -> list[str]:
        """Boşlukları tespit eder."""
        gaps = []
        for cap in required:
            cap_info = self._capability_map.get(cap)
            if not cap_info or not cap_info.get(
                "available", False,
            ):
                gaps.append(cap)
        return gaps

    def _check_feasibility(
        self,
        complexity: str,
        gaps: list[str],
    ) -> bool:
        """Fizibilite kontrol eder."""
        infeasible_complexity = {"extreme"}
        if complexity in infeasible_complexity:
            if len(gaps) > 3:
                return False

        return len(gaps) <= 5

    def register_capability(
        self,
        name: str,
        keywords: list[str],
        available: bool = True,
    ) -> dict[str, Any]:
        """Yetenek kaydeder.

        Args:
            name: Yetenek adı.
            keywords: Anahtar kelimeler.
            available: Müsait mi.

        Returns:
            Kayıt bilgisi.
        """
        self._capability_map[name] = {
            "keywords": keywords,
            "available": available,
            "registered_at": time.time(),
        }
        return {"name": name, "registered": True}

    def get_analysis(
        self,
        analysis_id: str,
    ) -> dict[str, Any]:
        """Analiz getirir.

        Args:
            analysis_id: Analiz ID.

        Returns:
            Analiz bilgisi.
        """
        for a in self._analyses:
            if a["analysis_id"] == analysis_id:
                return dict(a)
        return {"error": "analysis_not_found"}

    def get_analyses(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Analizleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Analiz listesi.
        """
        return list(self._analyses[-limit:])

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats["analyses"]

    @property
    def gap_count(self) -> int:
        """Bulunan boşluk sayısı."""
        return self._stats["gaps_found"]
