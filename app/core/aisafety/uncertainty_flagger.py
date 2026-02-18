"""
Belirsizlik isaretleyici modulu.

Belirsizlik tespiti, cekingen dil,
bilgi boslugu, spekülasyon isaretleme,
kullanici uyarisi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class UncertaintyFlagger:
    """Belirsizlik isaretleyici.

    Attributes:
        _flags: Isaretler.
        _patterns: Kaliplar.
        _stats: Istatistikler.
    """

    FLAG_TYPES: list[str] = [
        "hedging",
        "speculation",
        "knowledge_gap",
        "vague_claim",
        "unverified",
        "approximation",
    ]

    SEVERITY_LEVELS: list[str] = [
        "info",
        "warning",
        "critical",
    ]

    def __init__(
        self,
        sensitivity: float = 0.5,
    ) -> None:
        """Isaretleyiciyi baslatir.

        Args:
            sensitivity: Hassasiyet.
        """
        self._sensitivity = sensitivity
        self._flags: dict[
            str, dict
        ] = {}
        self._patterns: dict[
            str, list[str]
        ] = {
            "hedging": [
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
                "i believe",
                "it seems",
                "apparently",
            ],
            "speculation": [
                "tahminim",
                "tahminimce",
                "olasilikla",
                "varsayarsak",
                "sanki",
                "gibi gorunuyor",
                "i guess",
                "presumably",
                "supposedly",
                "if i had to guess",
                "speculate",
                "hypothetically",
            ],
            "knowledge_gap": [
                "bilmiyorum",
                "emin degilim",
                "hatirlamiyorum",
                "tam bilgi yok",
                "i don't know",
                "not sure",
                "uncertain",
                "unclear",
                "unknown",
                "no data",
                "insufficient",
            ],
            "vague_claim": [
                "bazi",
                "bircogu",
                "genellikle",
                "cogunlukla",
                "some",
                "many",
                "often",
                "usually",
                "sometimes",
                "several",
                "various",
                "roughly",
                "about",
                "around",
            ],
            "approximation": [
                "yaklasik",
                "asagi yukari",
                "civarinda",
                "tahminen",
                "approximately",
                "roughly",
                "about",
                "around",
                "nearly",
                "almost",
                "estimated",
            ],
        }
        self._stats: dict[str, int] = {
            "texts_analyzed": 0,
            "flags_raised": 0,
            "warnings_issued": 0,
            "critical_found": 0,
        }
        logger.info(
            "UncertaintyFlagger "
            "baslatildi"
        )

    @property
    def flag_count(self) -> int:
        """Isaret sayisi."""
        return len(self._flags)

    def analyze_text(
        self,
        text: str = "",
        context: str = "",
    ) -> dict[str, Any]:
        """Metni belirsizlik icin analiz.

        Args:
            text: Metin.
            context: Baglam.

        Returns:
            Analiz bilgisi.
        """
        try:
            fid = f"uflg_{uuid4()!s:.8}"
            text_lower = text.lower()
            findings: list[dict] = []

            # Her kalip kategorisi icin
            for ftype, patterns in (
                self._patterns.items()
            ):
                matches: list[str] = []
                for p in patterns:
                    if p in text_lower:
                        matches.append(p)

                if matches:
                    severity = (
                        self._calc_severity(
                            ftype,
                            len(matches),
                            len(
                                text.split()
                            ),
                        )
                    )
                    findings.append({
                        "type": ftype,
                        "matches": matches,
                        "match_count": len(
                            matches
                        ),
                        "severity": (
                            severity
                        ),
                    })

            # Genel belirsizlik puani
            if findings:
                total_matches = sum(
                    f["match_count"]
                    for f in findings
                )
                word_count = max(
                    1, len(text.split())
                )
                density = (
                    total_matches
                    / word_count
                )
                uncertainty_score = min(
                    1.0,
                    density
                    * 10
                    * self._sensitivity,
                )
            else:
                uncertainty_score = 0.0

            level = (
                self._get_severity_level(
                    uncertainty_score
                )
            )

            self._flags[fid] = {
                "flag_id": fid,
                "text": text[:200],
                "findings": findings,
                "uncertainty_score": round(
                    uncertainty_score, 4
                ),
                "level": level,
                "analyzed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "texts_analyzed"
            ] += 1
            self._stats[
                "flags_raised"
            ] += len(findings)
            if level == "warning":
                self._stats[
                    "warnings_issued"
                ] += 1
            elif level == "critical":
                self._stats[
                    "critical_found"
                ] += 1

            return {
                "flag_id": fid,
                "findings": findings,
                "finding_count": len(
                    findings
                ),
                "uncertainty_score": round(
                    uncertainty_score, 4
                ),
                "level": level,
                "needs_warning": (
                    level != "info"
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def _calc_severity(
        self,
        flag_type: str,
        match_count: int,
        word_count: int,
    ) -> float:
        """Ciddiyet hesaplar."""
        base = {
            "hedging": 0.3,
            "speculation": 0.5,
            "knowledge_gap": 0.7,
            "vague_claim": 0.2,
            "approximation": 0.2,
            "unverified": 0.6,
        }.get(flag_type, 0.3)

        density = match_count / max(
            1, word_count
        )
        return min(
            1.0,
            base
            + density * 5 * self._sensitivity,
        )

    def _get_severity_level(
        self, score: float
    ) -> str:
        """Ciddiyet seviyesi."""
        if score < 0.3:
            return "info"
        if score < 0.6:
            return "warning"
        return "critical"

    def generate_warning(
        self,
        flag_id: str = "",
    ) -> dict[str, Any]:
        """Uyari mesaji olusturur.

        Args:
            flag_id: Isaret ID.

        Returns:
            Uyari bilgisi.
        """
        try:
            flag = self._flags.get(flag_id)
            if not flag:
                return {
                    "generated": False,
                    "error": (
                        "Isaret bulunamadi"
                    ),
                }

            warnings: list[str] = []
            for f in flag["findings"]:
                ft = f["type"]
                if ft == "hedging":
                    warnings.append(
                        "Bu yanit cekingen "
                        "ifadeler iceriyor"
                    )
                elif ft == "speculation":
                    warnings.append(
                        "Spekulatif ifadeler "
                        "tespit edildi"
                    )
                elif ft == "knowledge_gap":
                    warnings.append(
                        "Bilgi eksikligi "
                        "belirtileri var"
                    )
                elif ft == "vague_claim":
                    warnings.append(
                        "Belirsiz iddialar "
                        "iceriyor"
                    )
                elif ft == "approximation":
                    warnings.append(
                        "Yaklasik degerler "
                        "kullanilmis"
                    )

            return {
                "flag_id": flag_id,
                "warnings": warnings,
                "level": flag["level"],
                "uncertainty_score": flag[
                    "uncertainty_score"
                ],
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def add_pattern(
        self,
        flag_type: str = "",
        pattern: str = "",
    ) -> dict[str, Any]:
        """Kalip ekler.

        Args:
            flag_type: Isaret tipi.
            pattern: Kalip.

        Returns:
            Ekleme bilgisi.
        """
        try:
            if (
                flag_type
                not in self._patterns
            ):
                self._patterns[
                    flag_type
                ] = []
            if (
                pattern
                not in self._patterns[
                    flag_type
                ]
            ):
                self._patterns[
                    flag_type
                ].append(pattern)
            return {
                "flag_type": flag_type,
                "pattern": pattern,
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_flags": len(
                    self._flags
                ),
                "pattern_types": len(
                    self._patterns
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
