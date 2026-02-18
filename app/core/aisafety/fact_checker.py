"""
Gercek kontrolcusu modulu.

Iddia cikarma, gercek dogrulama,
kaynak esleme, guven puanlama,
duzeltme onerileri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FactChecker:
    """Gercek kontrolcusu.

    Attributes:
        _checks: Kontroller.
        _fact_db: Gercek veritabani.
        _stats: Istatistikler.
    """

    VERDICT_TYPES: list[str] = [
        "true",
        "mostly_true",
        "mixed",
        "mostly_false",
        "false",
        "unverifiable",
    ]

    def __init__(
        self,
        min_confidence: float = 0.6,
    ) -> None:
        """Kontrolcuyu baslatir.

        Args:
            min_confidence: Min guven esigi.
        """
        self._min_confidence = (
            min_confidence
        )
        self._checks: dict[
            str, dict
        ] = {}
        self._fact_db: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "checks_done": 0,
            "claims_extracted": 0,
            "facts_verified": 0,
            "corrections_suggested": 0,
        }
        logger.info(
            "FactChecker baslatildi"
        )

    @property
    def check_count(self) -> int:
        """Kontrol sayisi."""
        return len(self._checks)

    def add_fact(
        self,
        statement: str = "",
        source: str = "",
        category: str = "",
        confidence: float = 1.0,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Gercek ekler.

        Args:
            statement: Ifade.
            source: Kaynak.
            category: Kategori.
            confidence: Guven.
            metadata: Ek veri.

        Returns:
            Ekleme bilgisi.
        """
        try:
            fid = f"fdb_{uuid4()!s:.8}"
            self._fact_db[fid] = {
                "fact_id": fid,
                "statement": statement,
                "source": source,
                "category": category,
                "confidence": confidence,
                "metadata": metadata or {},
                "added_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            return {
                "fact_id": fid,
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def extract_claims(
        self,
        text: str = "",
    ) -> dict[str, Any]:
        """Iddia cikarir.

        Args:
            text: Metin.

        Returns:
            Iddia bilgisi.
        """
        try:
            sentences = [
                s.strip()
                for s in text.split(".")
                if len(s.strip()) > 10
            ]

            claims: list[dict] = []
            indicators = [
                "dir",
                "tir",
                "dır",
                "tır",
                "is",
                "are",
                "was",
                "were",
                "has",
                "have",
                "will",
                "olarak",
                "gore",
                "kadar",
                "den fazla",
                "more than",
                "less than",
                "according",
                "percent",
                "yuzde",
            ]

            for i, s in enumerate(
                sentences
            ):
                s_lower = s.lower()
                is_claim = any(
                    ind in s_lower
                    for ind in indicators
                )
                has_number = any(
                    c.isdigit()
                    for c in s
                )

                if is_claim or has_number:
                    claims.append({
                        "index": i,
                        "text": s,
                        "has_number": (
                            has_number
                        ),
                        "verifiable": True,
                    })

            self._stats[
                "claims_extracted"
            ] += len(claims)

            return {
                "total_sentences": len(
                    sentences
                ),
                "claims_found": len(
                    claims
                ),
                "claims": claims,
                "extracted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "extracted": False,
                "error": str(e),
            }

    def verify_claim(
        self,
        claim: str = "",
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """Iddia dogrular.

        Args:
            claim: Iddia.
            sources: Kaynaklar.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            claim_lower = claim.lower()
            src_list = sources or []

            # Veritabaninda ara
            matches: list[dict] = []
            for fact in (
                self._fact_db.values()
            ):
                stmt = fact[
                    "statement"
                ].lower()
                words_claim = set(
                    claim_lower.split()
                )
                words_fact = set(
                    stmt.split()
                )
                common = (
                    words_claim & words_fact
                )

                if len(common) >= 3:
                    similarity = len(
                        common
                    ) / max(
                        len(words_claim),
                        len(words_fact),
                    )
                    matches.append({
                        "fact_id": (
                            fact["fact_id"]
                        ),
                        "statement": fact[
                            "statement"
                        ],
                        "similarity": round(
                            similarity, 4
                        ),
                        "confidence": fact[
                            "confidence"
                        ],
                        "source": fact[
                            "source"
                        ],
                    })

            # En iyi eslesme
            matches.sort(
                key=lambda x: x[
                    "similarity"
                ],
                reverse=True,
            )

            if matches:
                best = matches[0]
                conf = (
                    best["similarity"]
                    * best["confidence"]
                )
                if conf >= 0.7:
                    verdict = "true"
                elif conf >= 0.5:
                    verdict = "mostly_true"
                elif conf >= 0.3:
                    verdict = "mixed"
                else:
                    verdict = "mostly_false"
            else:
                verdict = "unverifiable"
                conf = 0.0

            self._stats[
                "facts_verified"
            ] += 1

            return {
                "claim": claim,
                "verdict": verdict,
                "confidence": round(
                    conf, 4
                ),
                "matches": matches[:3],
                "sources_provided": len(
                    src_list
                ),
                "verified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "verified": False,
                "error": str(e),
            }

    def check_text(
        self,
        text: str = "",
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """Metni toplu kontrol eder.

        Args:
            text: Metin.
            sources: Kaynaklar.

        Returns:
            Kontrol bilgisi.
        """
        try:
            cid = f"fchk_{uuid4()!s:.8}"

            # Iddia cikar
            extracted = (
                self.extract_claims(text)
            )
            claims = extracted.get(
                "claims", []
            )

            results: list[dict] = []
            for c in claims:
                vr = self.verify_claim(
                    claim=c["text"],
                    sources=sources,
                )
                results.append({
                    "claim": c["text"],
                    "verdict": vr.get(
                        "verdict",
                        "unverifiable",
                    ),
                    "confidence": vr.get(
                        "confidence", 0
                    ),
                })

            # Genel skor
            if results:
                scores = {
                    "true": 1.0,
                    "mostly_true": 0.75,
                    "mixed": 0.5,
                    "mostly_false": 0.25,
                    "false": 0.0,
                    "unverifiable": 0.5,
                }
                avg = sum(
                    scores.get(
                        r["verdict"], 0.5
                    )
                    for r in results
                ) / len(results)
            else:
                avg = 1.0

            self._checks[cid] = {
                "check_id": cid,
                "text": text[:200],
                "claims_count": len(
                    claims
                ),
                "results": results,
                "overall_score": round(
                    avg, 4
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

            return {
                "check_id": cid,
                "claims_found": len(
                    claims
                ),
                "results": results,
                "overall_score": round(
                    avg, 4
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def suggest_corrections(
        self,
        check_id: str = "",
    ) -> dict[str, Any]:
        """Duzeltme onerir.

        Args:
            check_id: Kontrol ID.

        Returns:
            Oneri bilgisi.
        """
        try:
            chk = self._checks.get(
                check_id
            )
            if not chk:
                return {
                    "suggested": False,
                    "error": (
                        "Kontrol bulunamadi"
                    ),
                }

            corrections: list[dict] = []
            for r in chk["results"]:
                if r["verdict"] in (
                    "false",
                    "mostly_false",
                    "unverifiable",
                ):
                    corrections.append({
                        "claim": r["claim"],
                        "verdict": (
                            r["verdict"]
                        ),
                        "suggestion": (
                            "Bu iddiayi "
                            "dogrulayin veya "
                            "kaldirin"
                        ),
                        "action": (
                            "review"
                            if r["verdict"]
                            == "unverifiable"
                            else "correct"
                        ),
                    })

            self._stats[
                "corrections_suggested"
            ] += len(corrections)

            return {
                "check_id": check_id,
                "corrections": corrections,
                "total": len(corrections),
                "suggested": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "suggested": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_checks": len(
                    self._checks
                ),
                "fact_db_size": len(
                    self._fact_db
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
