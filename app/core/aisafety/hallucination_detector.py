"""
Halusinasyon tespitcisi modulu.

Olgusal dogrulama, guven analizi,
kaynak kontrolu, celiski tespiti,
risk puanlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class HallucinationDetector:
    """Halusinasyon tespitcisi.

    Attributes:
        _detections: Tespitler.
        _known_facts: Bilinen gercekler.
        _stats: Istatistikler.
    """

    RISK_LEVELS: list[str] = [
        "none",
        "low",
        "medium",
        "high",
        "critical",
    ]

    DETECTION_TYPES: list[str] = [
        "factual_error",
        "unsupported_claim",
        "contradiction",
        "fabrication",
        "exaggeration",
        "misattribution",
    ]

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        risk_threshold: float = 0.5,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            confidence_threshold: Guven esigi.
            risk_threshold: Risk esigi.
        """
        self._confidence_threshold = (
            confidence_threshold
        )
        self._risk_threshold = (
            risk_threshold
        )
        self._detections: dict[
            str, dict
        ] = {}
        self._known_facts: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "checks_done": 0,
            "hallucinations_found": 0,
            "high_risk_found": 0,
            "facts_registered": 0,
        }
        logger.info(
            "HallucinationDetector "
            "baslatildi"
        )

    @property
    def detection_count(self) -> int:
        """Tespit sayisi."""
        return len(self._detections)

    def register_fact(
        self,
        fact_id: str = "",
        statement: str = "",
        source: str = "",
        confidence: float = 1.0,
        category: str = "",
    ) -> dict[str, Any]:
        """Bilinen gercek kaydeder.

        Args:
            fact_id: Gercek ID.
            statement: Ifade.
            source: Kaynak.
            confidence: Guven.
            category: Kategori.

        Returns:
            Kayit bilgisi.
        """
        try:
            fid = (
                fact_id
                or f"fact_{uuid4()!s:.8}"
            )
            self._known_facts[fid] = {
                "fact_id": fid,
                "statement": statement,
                "source": source,
                "confidence": confidence,
                "category": category,
            }
            self._stats[
                "facts_registered"
            ] += 1
            return {
                "fact_id": fid,
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def check_response(
        self,
        response_text: str = "",
        context: str = "",
        sources: list[str] | None = None,
        claims: list[str] | None = None,
    ) -> dict[str, Any]:
        """Yaniti halusinasyon kontrolu.

        Args:
            response_text: Yanit metni.
            context: Baglam.
            sources: Kaynaklar.
            claims: Iddialar.

        Returns:
            Kontrol bilgisi.
        """
        try:
            did = f"hdet_{uuid4()!s:.8}"
            src_list = sources or []
            claim_list = claims or []

            findings: list[dict] = []

            # 1. Kaynak kontrolu
            if not src_list:
                findings.append({
                    "type": "unsupported_claim",
                    "detail": (
                        "Kaynak belirtilmemis"
                    ),
                    "severity": 0.3,
                })

            # 2. Iddia kontrolu
            for claim in claim_list:
                result = (
                    self._verify_claim(
                        claim
                    )
                )
                if not result["verified"]:
                    findings.append({
                        "type": result.get(
                            "type",
                            "factual_error",
                        ),
                        "claim": claim,
                        "detail": result.get(
                            "detail", ""
                        ),
                        "severity": result.get(
                            "severity", 0.5
                        ),
                    })

            # 3. Celiski kontrolu
            contradictions = (
                self._check_contradictions(
                    response_text
                )
            )
            findings.extend(contradictions)

            # 4. Guven analizi
            confidence = (
                self._analyze_confidence(
                    response_text
                )
            )

            # 5. Risk puanlama
            risk_score = (
                self._calculate_risk(
                    findings, confidence
                )
            )
            risk_level = (
                self._get_risk_level(
                    risk_score
                )
            )

            has_hallucination = (
                risk_score
                > self._risk_threshold
            )

            self._detections[did] = {
                "detection_id": did,
                "response_text": (
                    response_text[:200]
                ),
                "findings": findings,
                "confidence": confidence,
                "risk_score": round(
                    risk_score, 4
                ),
                "risk_level": risk_level,
                "has_hallucination": (
                    has_hallucination
                ),
                "checked_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "checks_done"
            ] += 1
            if has_hallucination:
                self._stats[
                    "hallucinations_found"
                ] += 1
            if risk_level in (
                "high",
                "critical",
            ):
                self._stats[
                    "high_risk_found"
                ] += 1

            return {
                "detection_id": did,
                "has_hallucination": (
                    has_hallucination
                ),
                "risk_score": round(
                    risk_score, 4
                ),
                "risk_level": risk_level,
                "confidence": round(
                    confidence, 4
                ),
                "findings_count": len(
                    findings
                ),
                "findings": findings,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _verify_claim(
        self, claim: str
    ) -> dict[str, Any]:
        """Iddia dogrular."""
        claim_lower = claim.lower()
        for fact in (
            self._known_facts.values()
        ):
            stmt = fact[
                "statement"
            ].lower()
            # Basit celiskili kontrol
            if (
                stmt in claim_lower
                or claim_lower in stmt
            ):
                return {
                    "verified": True,
                    "fact_id": (
                        fact["fact_id"]
                    ),
                }

        # Dogrulanamamis
        return {
            "verified": False,
            "type": "unsupported_claim",
            "detail": (
                "Iddia dogrulanamadi"
            ),
            "severity": 0.4,
        }

    def _check_contradictions(
        self, text: str
    ) -> list[dict]:
        """Celiskileri kontrol eder."""
        findings: list[dict] = []
        sentences = [
            s.strip()
            for s in text.split(".")
            if s.strip()
        ]

        # Basit celiski tespiti
        negations = [
            "degil",
            "yok",
            "asla",
            "hicbir",
            "not",
            "never",
            "no",
            "none",
        ]

        for i, s1 in enumerate(sentences):
            for s2 in sentences[i + 1 :]:
                s1_words = set(
                    s1.lower().split()
                )
                s2_words = set(
                    s2.lower().split()
                )
                common = (
                    s1_words & s2_words
                )

                # Ortak kelime + negasyon
                if len(common) > 2:
                    s1_neg = any(
                        n in s1.lower()
                        for n in negations
                    )
                    s2_neg = any(
                        n in s2.lower()
                        for n in negations
                    )
                    if s1_neg != s2_neg:
                        findings.append({
                            "type": (
                                "contradiction"
                            ),
                            "detail": (
                                "Olasi celiski"
                            ),
                            "sentence_1": (
                                s1[:50]
                            ),
                            "sentence_2": (
                                s2[:50]
                            ),
                            "severity": 0.6,
                        })

        return findings

    def _analyze_confidence(
        self, text: str
    ) -> float:
        """Guven analizi yapar."""
        uncertain = [
            "belki",
            "muhtemelen",
            "sanirim",
            "galiba",
            "olabilir",
            "maybe",
            "perhaps",
            "probably",
            "might",
            "could",
            "possibly",
            "i think",
            "not sure",
        ]
        text_lower = text.lower()
        count = sum(
            1
            for u in uncertain
            if u in text_lower
        )
        word_count = max(
            1, len(text.split())
        )
        uncertainty = min(
            1.0, count / (word_count * 0.1)
        )
        return round(
            1.0 - uncertainty, 4
        )

    def _calculate_risk(
        self,
        findings: list[dict],
        confidence: float,
    ) -> float:
        """Risk hesaplar."""
        if not findings:
            return 0.0

        max_sev = max(
            f.get("severity", 0)
            for f in findings
        )
        avg_sev = sum(
            f.get("severity", 0)
            for f in findings
        ) / len(findings)
        count_factor = min(
            1.0, len(findings) * 0.2
        )

        risk = (
            max_sev * 0.4
            + avg_sev * 0.3
            + count_factor * 0.3
        )

        # Dusuk guven riski arttirir
        if (
            confidence
            < self._confidence_threshold
        ):
            risk = min(
                1.0, risk * 1.2
            )

        return round(risk, 4)

    def _get_risk_level(
        self, score: float
    ) -> str:
        """Risk seviyesi dondurur."""
        if score < 0.1:
            return "none"
        if score < 0.3:
            return "low"
        if score < 0.5:
            return "medium"
        if score < 0.7:
            return "high"
        return "critical"

    def get_detection_info(
        self, detection_id: str = ""
    ) -> dict[str, Any]:
        """Tespit bilgisi getirir."""
        try:
            det = self._detections.get(
                detection_id
            )
            if not det:
                return {
                    "retrieved": False,
                    "error": (
                        "Tespit bulunamadi"
                    ),
                }
            return {
                **det,
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_detections": len(
                    self._detections
                ),
                "known_facts": len(
                    self._known_facts
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
