"""
Rekabet pozisyonu analizcisi modülü.

Pozisyon haritalama, farklılaşma analizi,
hendek değerlendirmesi, zafiyet tespiti ve
strateji seçenekleri sunar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CompetitivePositionAnalyzer:
    """Rekabet pozisyonu analizcisi.

    Rekabet pozisyonunu haritalanır,
    farklılaşma analizi yapar, hendek
    değerlendirir ve strateji önerir.

    Attributes:
        _analyses: Analiz kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analizciciyi başlatır."""
        self._analyses: list[dict] = []
        self._stats: dict[str, int] = {
            "analyses_done": 0,
        }
        logger.info(
            "CompetitivePositionAnalyzer "
            "baslatildi"
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_done"
        ]

    def map_position(
        self,
        our_score: float = 50.0,
        market_avg: float = 50.0,
        market_share: float = 10.0,
    ) -> dict[str, Any]:
        """Pozisyon haritalama yapar.

        Args:
            our_score: Bizim skorumuz.
            market_avg: Pazar ortalaması.
            market_share: Pazar payı.

        Returns:
            Pozisyon haritası.
        """
        try:
            relative = round(
                our_score - market_avg, 2
            )

            if (
                market_share >= 30
                and relative > 0
            ):
                position = "leader"
            elif (
                market_share >= 15
                and relative > 0
            ):
                position = "challenger"
            elif market_share >= 5:
                position = "follower"
            elif relative > 10:
                position = "niche"
            else:
                position = "new_entrant"

            self._stats[
                "analyses_done"
            ] += 1

            result = {
                "our_score": our_score,
                "market_avg": market_avg,
                "market_share": market_share,
                "relative_score": relative,
                "position": position,
                "mapped": True,
            }

            logger.info(
                f"Pozisyon: {position}, "
                f"skor={relative}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Pozisyon haritalama "
                f"hatasi: {e}"
            )
            return {
                "our_score": our_score,
                "market_avg": market_avg,
                "market_share": market_share,
                "relative_score": 0.0,
                "position": "unknown",
                "mapped": False,
                "error": str(e),
            }

    def analyze_differentiation(
        self,
        our_features: list[str]
        | None = None,
        competitor_features: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Farklılaşma analizi yapar.

        Args:
            our_features: Özelliklerimiz.
            competitor_features: Rakip öz.

        Returns:
            Farklılaşma analizi.
        """
        try:
            if our_features is None:
                our_features = []
            if competitor_features is None:
                competitor_features = []

            our_set = set(our_features)
            comp_set = set(
                competitor_features
            )

            unique_ours = our_set - comp_set
            unique_theirs = (
                comp_set - our_set
            )
            shared = our_set & comp_set

            diff_score = round(
                (
                    len(unique_ours)
                    / max(len(our_set), 1)
                )
                * 100,
                1,
            )

            if diff_score >= 60:
                strength = "strong"
            elif diff_score >= 30:
                strength = "moderate"
            else:
                strength = "weak"

            self._stats[
                "analyses_done"
            ] += 1

            result = {
                "unique_ours": list(
                    unique_ours
                ),
                "unique_theirs": list(
                    unique_theirs
                ),
                "shared": list(shared),
                "differentiation_score": (
                    diff_score
                ),
                "strength": strength,
                "analyzed": True,
            }

            logger.info(
                f"Farklilasma: "
                f"skor={diff_score}, "
                f"guc={strength}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Farklilasma analizi "
                f"hatasi: {e}"
            )
            return {
                "unique_ours": [],
                "unique_theirs": [],
                "shared": [],
                "differentiation_score": 0.0,
                "strength": "unknown",
                "analyzed": False,
                "error": str(e),
            }

    def assess_moat(
        self,
        factors: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Hendek değerlendirmesi yapar.

        Args:
            factors: Hendek faktörleri ve skor.

        Returns:
            Hendek değerlendirmesi.
        """
        try:
            if factors is None:
                factors = {}

            scores = list(factors.values())
            avg_score = round(
                sum(scores)
                / max(len(scores), 1),
                1,
            )

            if avg_score >= 80:
                moat_strength = "wide"
            elif avg_score >= 50:
                moat_strength = "narrow"
            else:
                moat_strength = "none"

            strongest = (
                max(
                    factors,
                    key=factors.get,
                )
                if factors
                else "none"
            )
            weakest = (
                min(
                    factors,
                    key=factors.get,
                )
                if factors
                else "none"
            )

            self._stats[
                "analyses_done"
            ] += 1

            result = {
                "factors": factors,
                "factor_count": len(
                    factors
                ),
                "avg_score": avg_score,
                "moat_strength": (
                    moat_strength
                ),
                "strongest": strongest,
                "weakest": weakest,
                "assessed": True,
            }

            logger.info(
                f"Hendek: "
                f"guc={moat_strength}, "
                f"ort={avg_score}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Hendek degerlendirme "
                f"hatasi: {e}"
            )
            return {
                "factors": {},
                "factor_count": 0,
                "avg_score": 0.0,
                "moat_strength": "unknown",
                "strongest": "none",
                "weakest": "none",
                "assessed": False,
                "error": str(e),
            }

    def detect_vulnerabilities(
        self,
        weaknesses: list[str]
        | None = None,
        threats: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Zafiyet tespiti yapar.

        Args:
            weaknesses: Zayıf noktalar.
            threats: Tehditler.

        Returns:
            Zafiyet tespiti sonucu.
        """
        try:
            if weaknesses is None:
                weaknesses = []
            if threats is None:
                threats = []

            vuln_count = (
                len(weaknesses)
                + len(threats)
            )

            if vuln_count >= 6:
                risk_level = "critical"
            elif vuln_count >= 3:
                risk_level = "high"
            elif vuln_count >= 1:
                risk_level = "medium"
            else:
                risk_level = "low"

            self._stats[
                "analyses_done"
            ] += 1

            result = {
                "weaknesses": weaknesses,
                "threats": threats,
                "weakness_count": len(
                    weaknesses
                ),
                "threat_count": len(
                    threats
                ),
                "total_vulnerabilities": (
                    vuln_count
                ),
                "risk_level": risk_level,
                "detected": True,
            }

            logger.info(
                f"Zafiyet tespiti: "
                f"{vuln_count} zafiyet, "
                f"risk={risk_level}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Zafiyet tespiti "
                f"hatasi: {e}"
            )
            return {
                "weaknesses": [],
                "threats": [],
                "weakness_count": 0,
                "threat_count": 0,
                "total_vulnerabilities": 0,
                "risk_level": "unknown",
                "detected": False,
                "error": str(e),
            }

    def suggest_strategy(
        self,
        position: str = "follower",
        moat_strength: str = "narrow",
        risk_level: str = "medium",
    ) -> dict[str, Any]:
        """Strateji seçenekleri önerir.

        Args:
            position: Mevcut pozisyon.
            moat_strength: Hendek gücü.
            risk_level: Risk seviyesi.

        Returns:
            Strateji önerileri.
        """
        try:
            strategies: list[str] = []

            if position == "leader":
                strategies.append(
                    "defend_market_share"
                )
            elif position == "challenger":
                strategies.append(
                    "aggressive_growth"
                )
            elif position == "niche":
                strategies.append(
                    "deepen_niche"
                )
            else:
                strategies.append(
                    "find_differentiation"
                )

            if moat_strength == "none":
                strategies.append(
                    "build_competitive_moat"
                )

            if risk_level in (
                "high",
                "critical",
            ):
                strategies.append(
                    "reduce_vulnerabilities"
                )

            if not strategies:
                strategies.append(
                    "maintain_position"
                )

            if risk_level == "critical":
                urgency = "immediate"
            elif risk_level == "high":
                urgency = "high"
            else:
                urgency = "normal"

            self._stats[
                "analyses_done"
            ] += 1

            result = {
                "strategies": strategies,
                "strategy_count": len(
                    strategies
                ),
                "position": position,
                "urgency": urgency,
                "suggested": True,
            }

            logger.info(
                f"Strateji onerisi: "
                f"{len(strategies)} strateji, "
                f"aciliyet={urgency}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Strateji onerisi "
                f"hatasi: {e}"
            )
            return {
                "strategies": [],
                "strategy_count": 0,
                "position": position,
                "urgency": "unknown",
                "suggested": False,
                "error": str(e),
            }
