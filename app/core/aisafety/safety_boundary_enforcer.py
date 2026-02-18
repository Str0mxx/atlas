"""
Guvenlik sinir uygulayici modulu.

Icerik filtreleme, konu kisitlamalari,
cikti dogrulama, zararli icerik engelleme,
uyumluluk zorlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SafetyBoundaryEnforcer:
    """Guvenlik sinir uygulayici.

    Attributes:
        _enforcements: Uygulamalar.
        _boundaries: Sinirlar.
        _stats: Istatistikler.
    """

    ACTION_TYPES: list[str] = [
        "allow",
        "warn",
        "modify",
        "block",
        "escalate",
    ]

    BOUNDARY_CATEGORIES: list[str] = [
        "harmful_content",
        "personal_info",
        "medical_advice",
        "legal_advice",
        "financial_advice",
        "hate_speech",
        "violence",
        "adult_content",
        "misinformation",
        "manipulation",
    ]

    def __init__(
        self,
        strict_mode: bool = False,
        max_violations: int = 3,
    ) -> None:
        """Uygulayiciyi baslatir.

        Args:
            strict_mode: Siki mod.
            max_violations: Max ihlal.
        """
        self._strict_mode = strict_mode
        self._max_violations = (
            max_violations
        )
        self._enforcements: dict[
            str, dict
        ] = {}
        self._boundaries: dict[
            str, dict
        ] = {}
        self._blocked_patterns: list[
            dict
        ] = []
        self._topic_restrictions: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "checks_done": 0,
            "violations_found": 0,
            "content_blocked": 0,
            "content_modified": 0,
            "warnings_issued": 0,
        }
        self._init_default_boundaries()
        logger.info(
            "SafetyBoundaryEnforcer "
            "baslatildi"
        )

    @property
    def enforcement_count(self) -> int:
        """Uygulama sayisi."""
        return len(self._enforcements)

    def _init_default_boundaries(
        self,
    ) -> None:
        """Varsayilan sinirlar olusturur."""
        defaults = {
            "harmful_content": {
                "action": "block",
                "severity": 1.0,
                "patterns": [
                    "bomb yap",
                    "silah yap",
                    "zehir yap",
                    "hack yap",
                    "make a bomb",
                    "make a weapon",
                    "make poison",
                    "how to hack",
                ],
            },
            "personal_info": {
                "action": "warn",
                "severity": 0.7,
                "patterns": [
                    "tc kimlik",
                    "kredi karti",
                    "ssn",
                    "social security",
                    "credit card",
                    "password is",
                ],
            },
            "hate_speech": {
                "action": "block",
                "severity": 0.9,
                "patterns": [],
            },
            "misinformation": {
                "action": "warn",
                "severity": 0.6,
                "patterns": [],
            },
        }
        for cat, cfg in defaults.items():
            self._boundaries[cat] = {
                "category": cat,
                "action": cfg["action"],
                "severity": cfg["severity"],
                "patterns": cfg["patterns"],
                "active": True,
            }

    def add_boundary(
        self,
        category: str = "",
        action: str = "warn",
        severity: float = 0.5,
        patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sinir ekler.

        Args:
            category: Kategori.
            action: Aksiyon.
            severity: Ciddiyet.
            patterns: Kaliplar.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._boundaries[category] = {
                "category": category,
                "action": action,
                "severity": severity,
                "patterns": patterns or [],
                "active": True,
            }
            return {
                "category": category,
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def add_topic_restriction(
        self,
        topic: str = "",
        restriction: str = "block",
        reason: str = "",
    ) -> dict[str, Any]:
        """Konu kisitlamasi ekler.

        Args:
            topic: Konu.
            restriction: Kisitlama.
            reason: Neden.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._topic_restrictions[
                topic.lower()
            ] = {
                "topic": topic,
                "restriction": restriction,
                "reason": reason,
                "active": True,
            }
            return {
                "topic": topic,
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def check_content(
        self,
        text: str = "",
        content_type: str = "output",
    ) -> dict[str, Any]:
        """Icerigi kontrol eder.

        Args:
            text: Metin.
            content_type: Icerik tipi.

        Returns:
            Kontrol bilgisi.
        """
        try:
            eid = f"sbe_{uuid4()!s:.8}"
            text_lower = text.lower()
            violations: list[dict] = []

            # 1. Sinir kalip kontrolu
            for bnd in (
                self._boundaries.values()
            ):
                if not bnd["active"]:
                    continue
                for pattern in bnd[
                    "patterns"
                ]:
                    if (
                        pattern.lower()
                        in text_lower
                    ):
                        violations.append({
                            "category": bnd[
                                "category"
                            ],
                            "pattern": (
                                pattern
                            ),
                            "action": bnd[
                                "action"
                            ],
                            "severity": bnd[
                                "severity"
                            ],
                        })

            # 2. Konu kisitlama kontrolu
            for (
                topic,
                restr,
            ) in (
                self._topic_restrictions.items()
            ):
                if (
                    restr["active"]
                    and topic in text_lower
                ):
                    violations.append({
                        "category": (
                            "topic_restriction"
                        ),
                        "topic": topic,
                        "action": restr[
                            "restriction"
                        ],
                        "severity": 0.8,
                    })

            # 3. Ek kalip kontrolu
            for bp in (
                self._blocked_patterns
            ):
                if (
                    bp["pattern"].lower()
                    in text_lower
                ):
                    violations.append({
                        "category": bp.get(
                            "category",
                            "custom",
                        ),
                        "pattern": bp[
                            "pattern"
                        ],
                        "action": "block",
                        "severity": bp.get(
                            "severity", 0.8
                        ),
                    })

            # Karar belirle
            if not violations:
                action = "allow"
            else:
                max_sev = max(
                    v["severity"]
                    for v in violations
                )
                has_block = any(
                    v["action"] == "block"
                    for v in violations
                )

                if (
                    has_block
                    or self._strict_mode
                ):
                    action = "block"
                elif max_sev >= 0.7:
                    action = (
                        "block"
                        if self._strict_mode
                        else "warn"
                    )
                else:
                    action = "warn"

            self._enforcements[eid] = {
                "enforcement_id": eid,
                "text": text[:200],
                "content_type": (
                    content_type
                ),
                "violations": violations,
                "action": action,
                "checked_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "checks_done"
            ] += 1
            self._stats[
                "violations_found"
            ] += len(violations)
            if action == "block":
                self._stats[
                    "content_blocked"
                ] += 1
            elif action == "warn":
                self._stats[
                    "warnings_issued"
                ] += 1

            return {
                "enforcement_id": eid,
                "action": action,
                "violations": violations,
                "violation_count": len(
                    violations
                ),
                "is_safe": (
                    action == "allow"
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def validate_output(
        self,
        output_text: str = "",
        original_query: str = "",
    ) -> dict[str, Any]:
        """Ciktiyi dogrular.

        Args:
            output_text: Cikti metni.
            original_query: Orijinal sorgu.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            # Icerik kontrolu
            content_check = (
                self.check_content(
                    output_text, "output"
                )
            )

            # Ek dogrulama
            issues: list[str] = []

            # Bos cikti
            if not output_text.strip():
                issues.append(
                    "Bos cikti"
                )

            # Cok kisa cikti
            if (
                len(
                    output_text.split()
                )
                < 3
                and len(
                    original_query.split()
                )
                > 10
            ):
                issues.append(
                    "Yetersiz yanit"
                )

            is_valid = (
                content_check.get(
                    "is_safe", True
                )
                and not issues
            )

            return {
                "is_valid": is_valid,
                "content_check": (
                    content_check
                ),
                "issues": issues,
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "validated": False,
                "error": str(e),
            }

    def add_blocked_pattern(
        self,
        pattern: str = "",
        category: str = "custom",
        severity: float = 0.8,
    ) -> dict[str, Any]:
        """Engellenen kalip ekler.

        Args:
            pattern: Kalip.
            category: Kategori.
            severity: Ciddiyet.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._blocked_patterns.append({
                "pattern": pattern,
                "category": category,
                "severity": severity,
            })
            return {
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
                "total_enforcements": len(
                    self._enforcements
                ),
                "boundaries": len(
                    self._boundaries
                ),
                "topic_restrictions": len(
                    self._topic_restrictions
                ),
                "blocked_patterns": len(
                    self._blocked_patterns
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
