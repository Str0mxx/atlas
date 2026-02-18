"""
Tutarlilik analizcisi modulu.

Ic tutarlilik, capraz tutarlilik,
mantik dogrulama, zaman tutarliligi,
celiski isaretleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ConsistencyAnalyzer:
    """Tutarlilik analizcisi.

    Attributes:
        _analyses: Analizler.
        _responses: Yanit gecmisi.
        _stats: Istatistikler.
    """

    ISSUE_TYPES: list[str] = [
        "internal_contradiction",
        "cross_response_mismatch",
        "logic_error",
        "timeline_inconsistency",
        "factual_flip",
        "tone_shift",
    ]

    def __init__(
        self,
        consistency_threshold: float = 0.7,
        history_limit: int = 100,
    ) -> None:
        """Analizcisi baslatir.

        Args:
            consistency_threshold: Esik.
            history_limit: Gecmis limiti.
        """
        self._consistency_threshold = (
            consistency_threshold
        )
        self._history_limit = (
            history_limit
        )
        self._analyses: dict[
            str, dict
        ] = {}
        self._responses: list[dict] = []
        self._stats: dict[str, int] = {
            "analyses_done": 0,
            "issues_found": 0,
            "contradictions_found": 0,
            "responses_tracked": 0,
        }
        logger.info(
            "ConsistencyAnalyzer "
            "baslatildi"
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._analyses)

    def track_response(
        self,
        response_text: str = "",
        topic: str = "",
        context: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Yanit kaydeder.

        Args:
            response_text: Yanit metni.
            topic: Konu.
            context: Baglam.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            rid = f"resp_{uuid4()!s:.8}"
            entry = {
                "response_id": rid,
                "text": response_text,
                "topic": topic,
                "context": context,
                "metadata": metadata or {},
                "tracked_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._responses.append(entry)

            # Limit asimini kes
            if (
                len(self._responses)
                > self._history_limit
            ):
                self._responses = (
                    self._responses[
                        -self._history_limit :
                    ]
                )

            self._stats[
                "responses_tracked"
            ] += 1

            return {
                "response_id": rid,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def check_internal_consistency(
        self,
        text: str = "",
    ) -> dict[str, Any]:
        """Ic tutarliligi kontrol eder.

        Args:
            text: Metin.

        Returns:
            Kontrol bilgisi.
        """
        try:
            aid = f"cona_{uuid4()!s:.8}"
            issues: list[dict] = []

            sentences = [
                s.strip()
                for s in text.split(".")
                if len(s.strip()) > 5
            ]

            # Celiski tespiti
            negations = [
                "degil",
                "yok",
                "asla",
                "hicbir",
                "not",
                "never",
                "no",
                "none",
                "isn't",
                "aren't",
                "doesn't",
                "don't",
            ]

            for i, s1 in enumerate(
                sentences
            ):
                for s2 in sentences[
                    i + 1 :
                ]:
                    s1w = set(
                        s1.lower().split()
                    )
                    s2w = set(
                        s2.lower().split()
                    )
                    common = s1w & s2w

                    if len(common) >= 3:
                        s1_neg = any(
                            n
                            in s1.lower()
                            for n in negations
                        )
                        s2_neg = any(
                            n
                            in s2.lower()
                            for n in negations
                        )
                        if s1_neg != s2_neg:
                            issues.append({
                                "type": (
                                    "internal_"
                                    "contradiction"
                                ),
                                "sentence_1": (
                                    s1[:80]
                                ),
                                "sentence_2": (
                                    s2[:80]
                                ),
                                "severity": (
                                    0.7
                                ),
                            })

            # Sayisal celiski
            import re

            numbers = re.findall(
                r"\b(\d+)\b", text
            )
            if len(numbers) != len(
                set(numbers)
            ):
                pass  # Ayni sayi tekrari ok

            score = (
                1.0
                if not issues
                else max(
                    0.0,
                    1.0
                    - len(issues) * 0.2,
                )
            )

            self._analyses[aid] = {
                "analysis_id": aid,
                "type": "internal",
                "text": text[:200],
                "issues": issues,
                "score": round(score, 4),
                "analyzed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "analyses_done"
            ] += 1
            self._stats[
                "issues_found"
            ] += len(issues)
            self._stats[
                "contradictions_found"
            ] += len(issues)

            return {
                "analysis_id": aid,
                "issues": issues,
                "issue_count": len(issues),
                "consistency_score": round(
                    score, 4
                ),
                "is_consistent": (
                    score
                    >= self._consistency_threshold
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def check_cross_consistency(
        self,
        current_text: str = "",
        topic: str = "",
    ) -> dict[str, Any]:
        """Capraz tutarliligi kontrol eder.

        Args:
            current_text: Mevcut metin.
            topic: Konu.

        Returns:
            Kontrol bilgisi.
        """
        try:
            aid = f"conx_{uuid4()!s:.8}"
            issues: list[dict] = []

            # Ayni konudaki gecmis yanitlar
            past = [
                r
                for r in self._responses
                if r["topic"] == topic
            ]

            cur_words = set(
                current_text.lower().split()
            )

            for prev in past:
                prev_words = set(
                    prev["text"]
                    .lower()
                    .split()
                )
                if not prev_words:
                    continue

                common = (
                    cur_words & prev_words
                )
                overlap = len(
                    common
                ) / max(
                    len(cur_words),
                    len(prev_words),
                )

                # Dusuk ortusmede uyari
                if (
                    overlap < 0.1
                    and len(cur_words) > 5
                    and len(prev_words) > 5
                ):
                    issues.append({
                        "type": (
                            "cross_response_"
                            "mismatch"
                        ),
                        "prev_id": prev[
                            "response_id"
                        ],
                        "overlap": round(
                            overlap, 4
                        ),
                        "severity": 0.5,
                    })

            score = (
                1.0
                if not issues
                else max(
                    0.0,
                    1.0
                    - len(issues) * 0.15,
                )
            )

            self._analyses[aid] = {
                "analysis_id": aid,
                "type": "cross",
                "topic": topic,
                "issues": issues,
                "score": round(score, 4),
                "past_responses": len(past),
                "analyzed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "analyses_done"
            ] += 1
            self._stats[
                "issues_found"
            ] += len(issues)

            return {
                "analysis_id": aid,
                "issues": issues,
                "issue_count": len(issues),
                "consistency_score": round(
                    score, 4
                ),
                "past_count": len(past),
                "is_consistent": (
                    score
                    >= self._consistency_threshold
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def check_logic(
        self,
        text: str = "",
    ) -> dict[str, Any]:
        """Mantik kontrolu yapar.

        Args:
            text: Metin.

        Returns:
            Kontrol bilgisi.
        """
        try:
            issues: list[dict] = []
            text_lower = text.lower()

            # Mantik hatalari kaliplari
            contradictory_pairs = [
                ("always", "never"),
                ("all", "none"),
                ("everyone", "nobody"),
                ("hep", "hic"),
                ("tumu", "hicbiri"),
                ("her zaman", "asla"),
            ]

            for w1, w2 in (
                contradictory_pairs
            ):
                if (
                    w1 in text_lower
                    and w2 in text_lower
                ):
                    issues.append({
                        "type": "logic_error",
                        "detail": (
                            f"Celiskili: "
                            f"'{w1}' ve '{w2}'"
                        ),
                        "severity": 0.6,
                    })

            score = (
                1.0
                if not issues
                else max(
                    0.0,
                    1.0
                    - len(issues) * 0.2,
                )
            )

            self._stats[
                "analyses_done"
            ] += 1
            self._stats[
                "issues_found"
            ] += len(issues)

            return {
                "issues": issues,
                "issue_count": len(issues),
                "logic_score": round(
                    score, 4
                ),
                "is_logical": (
                    score >= 0.7
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def check_timeline(
        self,
        text: str = "",
    ) -> dict[str, Any]:
        """Zaman tutarliligi kontrol.

        Args:
            text: Metin.

        Returns:
            Kontrol bilgisi.
        """
        try:
            import re

            issues: list[dict] = []

            # Yil cikar
            years = [
                int(y)
                for y in re.findall(
                    r"\b(1\d{3}|2\d{3})\b",
                    text,
                )
            ]

            if len(years) >= 2:
                # Kronolojik sira kontrolu
                sentences = [
                    s.strip()
                    for s in text.split(".")
                    if s.strip()
                ]
                sent_years: list[
                    tuple[int, str]
                ] = []
                for s in sentences:
                    syears = [
                        int(y)
                        for y in re.findall(
                            r"\b(1\d{3}"
                            r"|2\d{3})\b",
                            s,
                        )
                    ]
                    for y in syears:
                        sent_years.append(
                            (y, s[:50])
                        )

                # Once/sonra kontrol
                before = [
                    "once",
                    "before",
                    "oncesinde",
                    "ardi",
                ]
                after = [
                    "sonra",
                    "after",
                    "ardindan",
                ]

                for kw in before:
                    if (
                        kw in text.lower()
                        and len(sent_years)
                        >= 2
                    ):
                        if (
                            sent_years[0][0]
                            > sent_years[-1][
                                0
                            ]
                        ):
                            issues.append({
                                "type": (
                                    "timeline_"
                                    "inconsistency"
                                ),
                                "detail": (
                                    "Zaman "
                                    "sirasi "
                                    "hatasi"
                                ),
                                "severity": (
                                    0.5
                                ),
                            })
                            break

            score = (
                1.0
                if not issues
                else max(
                    0.0,
                    1.0
                    - len(issues) * 0.3,
                )
            )

            self._stats[
                "analyses_done"
            ] += 1
            self._stats[
                "issues_found"
            ] += len(issues)

            return {
                "issues": issues,
                "issue_count": len(issues),
                "timeline_score": round(
                    score, 4
                ),
                "years_found": years,
                "is_consistent": (
                    score >= 0.7
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def full_analysis(
        self,
        text: str = "",
        topic: str = "",
    ) -> dict[str, Any]:
        """Tam tutarlilik analizi.

        Args:
            text: Metin.
            topic: Konu.

        Returns:
            Tam analiz bilgisi.
        """
        try:
            aid = f"cful_{uuid4()!s:.8}"

            internal = (
                self.check_internal_consistency(
                    text
                )
            )
            cross = (
                self.check_cross_consistency(
                    text, topic
                )
            )
            logic = self.check_logic(text)
            timeline = (
                self.check_timeline(text)
            )

            scores = [
                internal.get(
                    "consistency_score", 1.0
                ),
                cross.get(
                    "consistency_score", 1.0
                ),
                logic.get(
                    "logic_score", 1.0
                ),
                timeline.get(
                    "timeline_score", 1.0
                ),
            ]
            avg = sum(scores) / len(scores)

            total_issues = (
                internal.get(
                    "issue_count", 0
                )
                + cross.get(
                    "issue_count", 0
                )
                + logic.get(
                    "issue_count", 0
                )
                + timeline.get(
                    "issue_count", 0
                )
            )

            return {
                "analysis_id": aid,
                "internal": internal,
                "cross": cross,
                "logic": logic,
                "timeline": timeline,
                "overall_score": round(
                    avg, 4
                ),
                "total_issues": (
                    total_issues
                ),
                "is_consistent": (
                    avg
                    >= self._consistency_threshold
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_analyses": len(
                    self._analyses
                ),
                "tracked_responses": len(
                    self._responses
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
