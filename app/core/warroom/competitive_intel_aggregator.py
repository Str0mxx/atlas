"""ATLAS Rekabet İstihbaratı Toplayıcı.

Çoklu kaynak istihbaratı, sinyal birleştirme,
içgörü çıkarma, rapor üretimi, dağıtım.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CompetitiveIntelAggregator:
    """Rekabet istihbaratı toplayıcı.

    Çoklu kaynaklardan istihbarat toplar,
    sinyalleri birleştirir ve içgörü çıkarır.

    Attributes:
        _intel: İstihbarat kayıtları.
        _reports: Rapor kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Toplayıcıyı başlatır."""
        self._intel: list[dict] = []
        self._reports: dict[
            str, dict
        ] = {}
        self._stats = {
            "intel_collected": 0,
            "reports_generated": 0,
        }
        logger.info(
            "CompetitiveIntelAggregator "
            "baslatildi",
        )

    @property
    def intel_count(self) -> int:
        """Toplanan istihbarat sayısı."""
        return self._stats[
            "intel_collected"
        ]

    @property
    def report_count(self) -> int:
        """Üretilen rapor sayısı."""
        return self._stats[
            "reports_generated"
        ]

    def collect_intel(
        self,
        competitor_id: str,
        source: str = "news",
        content: str = "",
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """İstihbarat toplar.

        Args:
            competitor_id: Rakip kimliği.
            source: Kaynak.
            content: İçerik.
            confidence: Güven (0-1).

        Returns:
            İstihbarat bilgisi.
        """
        iid = f"intel_{str(uuid4())[:6]}"
        entry = {
            "intel_id": iid,
            "competitor_id": competitor_id,
            "source": source,
            "content": content,
            "confidence": confidence,
        }
        self._intel.append(entry)
        self._stats[
            "intel_collected"
        ] += 1

        if confidence >= 0.8:
            reliability = "verified"
        elif confidence >= 0.6:
            reliability = "probable"
        elif confidence >= 0.4:
            reliability = "possible"
        else:
            reliability = "unconfirmed"

        return {
            "intel_id": iid,
            "competitor_id": competitor_id,
            "source": source,
            "reliability": reliability,
            "collected": True,
        }

    def fuse_signals(
        self,
        competitor_id: str,
        signals: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Sinyalleri birleştirir.

        Args:
            competitor_id: Rakip kimliği.
            signals: Sinyaller
                [{source, confidence, type}].

        Returns:
            Birleştirme bilgisi.
        """
        if signals is None:
            signals = []

        if not signals:
            return {
                "competitor_id": (
                    competitor_id
                ),
                "fused_confidence": 0.0,
                "signal_count": 0,
                "fused": False,
            }

        total_conf = sum(
            s.get("confidence", 0.5)
            for s in signals
        )
        avg_conf = round(
            total_conf / len(signals),
            3,
        )

        source_types = set(
            s.get("source", "unknown")
            for s in signals
        )
        diversity_bonus = min(
            len(source_types) * 0.05,
            0.15,
        )
        fused = round(
            min(
                avg_conf + diversity_bonus,
                1.0,
            ),
            3,
        )

        return {
            "competitor_id": competitor_id,
            "fused_confidence": fused,
            "source_diversity": len(
                source_types,
            ),
            "signal_count": len(signals),
            "fused": True,
        }

    def extract_insights(
        self,
        competitor_id: str,
        intel_items: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """İçgörü çıkarır.

        Args:
            competitor_id: Rakip kimliği.
            intel_items: İstihbarat öğeleri.

        Returns:
            İçgörü bilgisi.
        """
        if intel_items is None:
            intel_items = []

        themes: dict[str, int] = {}
        for item in intel_items:
            cat = item.get(
                "category", "general",
            )
            themes[cat] = (
                themes.get(cat, 0) + 1
            )

        dominant = (
            max(themes, key=themes.get)
            if themes
            else "unknown"
        )

        high_confidence = [
            i
            for i in intel_items
            if i.get("confidence", 0)
            >= 0.7
        ]

        return {
            "competitor_id": competitor_id,
            "themes": themes,
            "dominant_theme": dominant,
            "total_items": len(intel_items),
            "high_confidence_count": len(
                high_confidence,
            ),
            "extracted": True,
        }

    def generate_report(
        self,
        competitor_id: str,
        report_type: str = "summary",
        include_sections: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Rapor üretir.

        Args:
            competitor_id: Rakip kimliği.
            report_type: Rapor tipi.
            include_sections: Bölümler.

        Returns:
            Rapor bilgisi.
        """
        if include_sections is None:
            include_sections = [
                "overview",
                "threats",
                "opportunities",
            ]

        rid = f"rpt_{str(uuid4())[:6]}"
        self._reports[rid] = {
            "competitor_id": competitor_id,
            "type": report_type,
            "sections": include_sections,
        }
        self._stats[
            "reports_generated"
        ] += 1

        return {
            "report_id": rid,
            "competitor_id": competitor_id,
            "report_type": report_type,
            "section_count": len(
                include_sections,
            ),
            "generated": True,
        }

    def distribute_intel(
        self,
        report_id: str,
        channels: list[str]
        | None = None,
        recipients: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """İstihbarat dağıtır.

        Args:
            report_id: Rapor kimliği.
            channels: Dağıtım kanalları.
            recipients: Alıcılar.

        Returns:
            Dağıtım bilgisi.
        """
        if channels is None:
            channels = ["email"]
        if recipients is None:
            recipients = []

        return {
            "report_id": report_id,
            "channels": channels,
            "recipient_count": len(
                recipients,
            ),
            "distributed": True,
        }
