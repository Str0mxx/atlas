"""
Kaynak dogrulayici modulu.

Kaynak dogrulama, otorite puanlama,
guncellik kontrolu, onyargi tespiti,
atif dogrulama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SourceVerifier:
    """Kaynak dogrulayici.

    Attributes:
        _verifications: Dogrulamalar.
        _sources: Kaynak veritabani.
        _stats: Istatistikler.
    """

    AUTHORITY_LEVELS: list[str] = [
        "unknown",
        "low",
        "medium",
        "high",
        "expert",
    ]

    BIAS_TYPES: list[str] = [
        "none",
        "political",
        "commercial",
        "ideological",
        "cultural",
        "selection",
    ]

    def __init__(
        self,
        min_authority: float = 0.3,
        recency_days: int = 365,
    ) -> None:
        """Dogrulayiciyi baslatir.

        Args:
            min_authority: Min otorite esigi.
            recency_days: Guncellik gun limiti.
        """
        self._min_authority = min_authority
        self._recency_days = recency_days
        self._verifications: dict[
            str, dict
        ] = {}
        self._sources: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "sources_registered": 0,
            "verifications_done": 0,
            "citations_checked": 0,
            "bias_detected": 0,
        }
        logger.info(
            "SourceVerifier baslatildi"
        )

    @property
    def verification_count(self) -> int:
        """Dogrulama sayisi."""
        return len(self._verifications)

    def register_source(
        self,
        name: str = "",
        url: str = "",
        source_type: str = "",
        authority_score: float = 0.5,
        bias_type: str = "none",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Kaynak kaydeder.

        Args:
            name: Kaynak adi.
            url: URL.
            source_type: Kaynak tipi.
            authority_score: Otorite puani.
            bias_type: Onyargi tipi.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            sid = f"src_{uuid4()!s:.8}"
            self._sources[sid] = {
                "source_id": sid,
                "name": name,
                "url": url,
                "source_type": source_type,
                "authority_score": (
                    authority_score
                ),
                "bias_type": bias_type,
                "metadata": metadata or {},
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "sources_registered"
            ] += 1
            return {
                "source_id": sid,
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def verify_source(
        self,
        source_name: str = "",
        source_url: str = "",
        published_date: str = "",
    ) -> dict[str, Any]:
        """Kaynak dogrular.

        Args:
            source_name: Kaynak adi.
            source_url: URL.
            published_date: Yayin tarihi.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            vid = f"svrf_{uuid4()!s:.8}"

            # Otorite kontrolu
            authority = (
                self._check_authority(
                    source_name, source_url
                )
            )

            # Guncellik kontrolu
            recency = (
                self._check_recency(
                    published_date
                )
            )

            # Onyargi kontrolu
            bias = self._check_bias(
                source_name
            )

            # Genel puan
            score = (
                authority["score"] * 0.4
                + recency["score"] * 0.3
                + (1.0 - bias["score"])
                * 0.3
            )

            is_reliable = (
                score >= self._min_authority
            )

            self._verifications[vid] = {
                "verification_id": vid,
                "source_name": source_name,
                "source_url": source_url,
                "authority": authority,
                "recency": recency,
                "bias": bias,
                "overall_score": round(
                    score, 4
                ),
                "is_reliable": is_reliable,
                "verified_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "verifications_done"
            ] += 1
            if bias["detected"]:
                self._stats[
                    "bias_detected"
                ] += 1

            return {
                "verification_id": vid,
                "authority": authority,
                "recency": recency,
                "bias": bias,
                "overall_score": round(
                    score, 4
                ),
                "is_reliable": is_reliable,
                "verified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "verified": False,
                "error": str(e),
            }

    def _check_authority(
        self,
        name: str,
        url: str,
    ) -> dict[str, Any]:
        """Otorite kontrol eder."""
        # Kayitli kaynak ara
        for src in (
            self._sources.values()
        ):
            if (
                src["name"].lower()
                == name.lower()
                or (
                    url
                    and src["url"] == url
                )
            ):
                score = src[
                    "authority_score"
                ]
                level = (
                    self._get_authority_level(
                        score
                    )
                )
                return {
                    "score": score,
                    "level": level,
                    "known": True,
                    "source_id": (
                        src["source_id"]
                    ),
                }

        # Bilinmeyen kaynak
        return {
            "score": 0.3,
            "level": "low",
            "known": False,
            "source_id": None,
        }

    def _get_authority_level(
        self, score: float
    ) -> str:
        """Otorite seviyesi dondurur."""
        if score < 0.2:
            return "unknown"
        if score < 0.4:
            return "low"
        if score < 0.6:
            return "medium"
        if score < 0.8:
            return "high"
        return "expert"

    def _check_recency(
        self, published_date: str
    ) -> dict[str, Any]:
        """Guncellik kontrol eder."""
        if not published_date:
            return {
                "score": 0.5,
                "days_old": None,
                "is_recent": False,
            }

        try:
            pub = datetime.fromisoformat(
                published_date
            )
            now = datetime.now(
                timezone.utc
            )
            if pub.tzinfo is None:
                pub = pub.replace(
                    tzinfo=timezone.utc
                )
            days = (now - pub).days
            days = max(0, days)

            if days <= self._recency_days:
                score = 1.0 - (
                    days
                    / self._recency_days
                )
            else:
                score = max(
                    0.1,
                    1.0
                    - (
                        days
                        / self._recency_days
                    ),
                )

            return {
                "score": round(score, 4),
                "days_old": days,
                "is_recent": (
                    days
                    <= self._recency_days
                ),
            }
        except (ValueError, TypeError):
            return {
                "score": 0.5,
                "days_old": None,
                "is_recent": False,
            }

    def _check_bias(
        self, source_name: str
    ) -> dict[str, Any]:
        """Onyargi kontrol eder."""
        for src in (
            self._sources.values()
        ):
            if (
                src["name"].lower()
                == source_name.lower()
            ):
                bias_type = src["bias_type"]
                detected = (
                    bias_type != "none"
                )
                score = (
                    0.5 if detected else 0.0
                )
                return {
                    "detected": detected,
                    "type": bias_type,
                    "score": score,
                }

        return {
            "detected": False,
            "type": "none",
            "score": 0.0,
        }

    def verify_citation(
        self,
        claim: str = "",
        cited_source: str = "",
        cited_text: str = "",
    ) -> dict[str, Any]:
        """Atif dogrular.

        Args:
            claim: Iddia.
            cited_source: Atif kaynagi.
            cited_text: Atif metni.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            # Basit kelime eslestirme
            claim_words = set(
                claim.lower().split()
            )
            cited_words = set(
                cited_text.lower().split()
            )

            if not cited_words:
                return {
                    "match_score": 0.0,
                    "is_valid": False,
                    "reason": (
                        "Atif metni bos"
                    ),
                    "checked": True,
                }

            common = (
                claim_words & cited_words
            )
            score = len(common) / max(
                len(claim_words),
                len(cited_words),
            )

            self._stats[
                "citations_checked"
            ] += 1

            return {
                "match_score": round(
                    score, 4
                ),
                "is_valid": score >= 0.3,
                "common_terms": len(common),
                "source": cited_source,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_verifications": len(
                    self._verifications
                ),
                "registered_sources": len(
                    self._sources
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
