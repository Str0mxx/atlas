"""ATLAS Tehdit Değerlendiricisi.

Tehdit puanlama, rekabet pozisyonu,
risk analizi, erken uyarı, yanıt önceliği.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ThreatAssessor:
    """Tehdit değerlendiricisi.

    Rekabet tehditlerini değerlendirir,
    erken uyarılar oluşturur ve önceliklendirir.

    Attributes:
        _assessments: Değerlendirme kayıtları.
        _warnings: Erken uyarılar.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Değerlendiriciyi başlatır."""
        self._assessments: dict[
            str, dict
        ] = {}
        self._warnings: list[dict] = []
        self._stats = {
            "threats_scored": 0,
            "warnings_issued": 0,
        }
        logger.info(
            "ThreatAssessor baslatildi",
        )

    @property
    def assessment_count(self) -> int:
        """Değerlendirme sayısı."""
        return self._stats[
            "threats_scored"
        ]

    @property
    def warning_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "warnings_issued"
        ]

    def score_threat(
        self,
        competitor_id: str,
        market_share: float = 0.0,
        growth_rate: float = 0.0,
        innovation_score: float = 0.0,
        financial_strength: float = 0.0,
    ) -> dict[str, Any]:
        """Tehdit puanlar.

        Args:
            competitor_id: Rakip kimliği.
            market_share: Pazar payı (0-1).
            growth_rate: Büyüme oranı (0-1).
            innovation_score: İnovasyon (0-1).
            financial_strength: Finansal (0-1).

        Returns:
            Tehdit puanı bilgisi.
        """
        threat_score = round(
            market_share * 0.3
            + growth_rate * 0.3
            + innovation_score * 0.2
            + financial_strength * 0.2,
            3,
        )

        if threat_score >= 0.8:
            level = "critical"
        elif threat_score >= 0.6:
            level = "high"
        elif threat_score >= 0.4:
            level = "moderate"
        elif threat_score >= 0.2:
            level = "low"
        else:
            level = "minimal"

        self._assessments[
            competitor_id
        ] = {
            "score": threat_score,
            "level": level,
        }
        self._stats[
            "threats_scored"
        ] += 1

        return {
            "competitor_id": competitor_id,
            "threat_score": threat_score,
            "level": level,
            "scored": True,
        }

    def evaluate_position(
        self,
        our_share: float = 0.0,
        competitor_shares: dict[
            str, float
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Rekabet pozisyonunu değerlendirir.

        Args:
            our_share: Bizim pazar payı.
            competitor_shares: Rakip payları.

        Returns:
            Pozisyon bilgisi.
        """
        if competitor_shares is None:
            competitor_shares = {}

        total = our_share + sum(
            competitor_shares.values(),
        )
        our_pct = round(
            our_share
            / max(total, 0.01)
            * 100,
            1,
        )

        rank = 1
        for share in (
            competitor_shares.values()
        ):
            if share > our_share:
                rank += 1

        if rank == 1:
            position = "leader"
        elif rank <= 3:
            position = "challenger"
        else:
            position = "follower"

        return {
            "our_share_pct": our_pct,
            "rank": rank,
            "position": position,
            "competitor_count": len(
                competitor_shares,
            ),
            "evaluated": True,
        }

    def analyze_risk(
        self,
        competitor_id: str,
        threat_areas: list[
            dict[str, Any]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Risk analizi yapar.

        Args:
            competitor_id: Rakip kimliği.
            threat_areas: Tehdit alanları
                [{area, probability, impact}].

        Returns:
            Risk analizi bilgisi.
        """
        if threat_areas is None:
            threat_areas = []

        risks = []
        for ta in threat_areas:
            prob = ta.get(
                "probability", 0.5,
            )
            impact = ta.get(
                "impact", 0.5,
            )
            risk_score = round(
                prob * impact, 3,
            )
            risks.append(
                {
                    "area": ta.get(
                        "area", "",
                    ),
                    "risk_score": risk_score,
                    "critical": (
                        risk_score >= 0.5
                    ),
                },
            )

        risks.sort(
            key=lambda x: x["risk_score"],
            reverse=True,
        )

        critical_count = sum(
            1
            for r in risks
            if r["critical"]
        )

        return {
            "competitor_id": competitor_id,
            "risks": risks,
            "critical_risks": critical_count,
            "total_risks": len(risks),
            "analyzed": True,
        }

    def issue_warning(
        self,
        competitor_id: str,
        warning_type: str = "general",
        message: str = "",
        urgency: str = "medium",
    ) -> dict[str, Any]:
        """Erken uyarı çıkarır.

        Args:
            competitor_id: Rakip kimliği.
            warning_type: Uyarı tipi.
            message: Mesaj.
            urgency: Aciliyet.

        Returns:
            Uyarı bilgisi.
        """
        wid = f"wrn_{str(uuid4())[:6]}"
        warning = {
            "warning_id": wid,
            "competitor_id": competitor_id,
            "type": warning_type,
            "message": message,
            "urgency": urgency,
        }
        self._warnings.append(warning)
        self._stats[
            "warnings_issued"
        ] += 1

        return {
            "warning_id": wid,
            "competitor_id": competitor_id,
            "urgency": urgency,
            "issued": True,
        }

    def prioritize_response(
        self,
        threats: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Yanıt önceliklendirir.

        Args:
            threats: Tehditler
                [{competitor_id, score, urgency}].

        Returns:
            Önceliklendirme bilgisi.
        """
        if threats is None:
            threats = []

        urgency_weights = {
            "critical": 3.0,
            "high": 2.0,
            "medium": 1.0,
            "low": 0.5,
        }

        prioritized = []
        for t in threats:
            score = t.get("score", 0.5)
            urg = t.get(
                "urgency", "medium",
            )
            weight = urgency_weights.get(
                urg, 1.0,
            )
            priority = round(
                score * weight, 3,
            )
            prioritized.append(
                {
                    "competitor_id": t.get(
                        "competitor_id", "",
                    ),
                    "priority_score": (
                        priority
                    ),
                    "urgency": urg,
                },
            )

        prioritized.sort(
            key=lambda x: x[
                "priority_score"
            ],
            reverse=True,
        )

        return {
            "prioritized": prioritized,
            "top_priority": (
                prioritized[0][
                    "competitor_id"
                ]
                if prioritized
                else ""
            ),
            "total_threats": len(
                prioritized,
            ),
            "ranked": True,
        }
