"""
Kod guvenlik analizcisi modulu.

Statik analiz, OWASP kontrolleri,
enjeksiyon tespiti, guvenlik oruntuleri,
kod incelemesi.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CodeSecurityAnalyzer:
    """Kod guvenlik analizcisi.

    Attributes:
        _analyses: Analiz kayitlari.
        _findings: Bulgu kayitlari.
        _patterns: Guvenlik oruntuleri.
        _stats: Istatistikler.
    """

    OWASP_PATTERNS: list[dict] = [
        {
            "id": "A01",
            "name": "broken_access_control",
            "pattern": (
                r"(?i)(admin|root)\s*"
                r"[=:]\s*['\"]?true"
            ),
            "severity": "critical",
            "category": "Access Control",
        },
        {
            "id": "A02",
            "name": "crypto_failure",
            "pattern": (
                r"(?i)(md5|sha1)\s*\("
            ),
            "severity": "high",
            "category": "Cryptographic",
        },
        {
            "id": "A03",
            "name": "injection",
            "pattern": (
                r"(?i)(execute|query)\s*\("
                r".*['\"].*\+|\.format\("
            ),
            "severity": "critical",
            "category": "Injection",
        },
        {
            "id": "A05",
            "name": "security_misconfiguration",
            "pattern": (
                r"(?i)(verify\s*=\s*False|"
                r"check_hostname\s*=\s*False)"
            ),
            "severity": "high",
            "category": "Misconfiguration",
        },
        {
            "id": "A07",
            "name": "auth_failure",
            "pattern": (
                r"(?i)(authenticate|login)"
                r"\s*=\s*False"
            ),
            "severity": "critical",
            "category": "Authentication",
        },
        {
            "id": "A09",
            "name": "logging_failure",
            "pattern": (
                r"(?i)except\s*:\s*pass"
            ),
            "severity": "medium",
            "category": "Logging",
        },
    ]

    SECURITY_PATTERNS: list[dict] = [
        {
            "name": "eval_usage",
            "pattern": r"(?i)\beval\s*\(",
            "severity": "critical",
            "fix": "Use ast.literal_eval",
        },
        {
            "name": "pickle_usage",
            "pattern": (
                r"(?i)pickle\.(loads?|"
                r"dumps?)\s*\("
            ),
            "severity": "high",
            "fix": "Use JSON serialization",
        },
        {
            "name": "temp_file_insecure",
            "pattern": (
                r"(?i)tempfile\.(mktemp|"
                r"NamedTemporaryFile)\s*\("
            ),
            "severity": "medium",
            "fix": "Use tempfile.mkstemp",
        },
        {
            "name": "assert_in_code",
            "pattern": r"\bassert\s+",
            "severity": "low",
            "fix": (
                "Use proper validation"
            ),
        },
    ]

    def __init__(self) -> None:
        """Analizcisi baslatir."""
        self._analyses: list[dict] = []
        self._findings: list[dict] = []
        self._patterns: list[dict] = list(
            self.OWASP_PATTERNS
        ) + list(self.SECURITY_PATTERNS)
        self._stats: dict[str, int] = {
            "analyses_done": 0,
            "findings_total": 0,
            "critical_count": 0,
        }
        logger.info(
            "CodeSecurityAnalyzer baslatildi"
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._analyses)

    def analyze_code(
        self,
        code: str = "",
        source: str = "",
        language: str = "python",
    ) -> dict[str, Any]:
        """Kod analiz eder.

        Args:
            code: Analiz edilecek kod.
            source: Kaynak dosya.
            language: Programlama dili.

        Returns:
            Analiz bilgisi.
        """
        try:
            aid = f"ca_{uuid4()!s:.8}"
            findings: list[dict] = []

            for p in self._patterns:
                pattern = p.get(
                    "pattern", ""
                )
                matches = re.findall(
                    pattern, code
                )
                if matches:
                    fid = f"cf_{uuid4()!s:.8}"
                    finding = {
                        "finding_id": fid,
                        "name": p.get(
                            "name", ""
                        ),
                        "severity": p.get(
                            "severity",
                            "medium",
                        ),
                        "category": p.get(
                            "category",
                            "Security",
                        ),
                        "match_count": len(
                            matches
                        ),
                        "fix": p.get(
                            "fix",
                            p.get(
                                "category",
                                "Review code",
                            ),
                        ),
                        "source": source,
                        "resolved": False,
                    }
                    findings.append(finding)
                    self._findings.append(
                        finding
                    )
                    if (
                        p.get("severity")
                        == "critical"
                    ):
                        self._stats[
                            "critical_count"
                        ] += 1

            analysis = {
                "analysis_id": aid,
                "source": source,
                "language": language,
                "findings_count": len(
                    findings
                ),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._analyses.append(analysis)
            self._stats[
                "analyses_done"
            ] += 1
            self._stats[
                "findings_total"
            ] += len(findings)

            return {
                "analysis_id": aid,
                "findings": findings,
                "total_findings": len(
                    findings
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def check_owasp(
        self,
        code: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """OWASP kontrol eder.

        Args:
            code: Kontrol edilecek kod.
            source: Kaynak dosya.

        Returns:
            Kontrol bilgisi.
        """
        try:
            violations: list[dict] = []
            for p in self.OWASP_PATTERNS:
                matches = re.findall(
                    p["pattern"], code
                )
                if matches:
                    violations.append({
                        "owasp_id": p["id"],
                        "name": p["name"],
                        "severity": p[
                            "severity"
                        ],
                        "category": p[
                            "category"
                        ],
                        "match_count": len(
                            matches
                        ),
                    })

            return {
                "source": source,
                "violations": violations,
                "violation_count": len(
                    violations
                ),
                "compliant": len(violations)
                == 0,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def resolve_finding(
        self,
        finding_id: str = "",
        resolution: str = "",
    ) -> dict[str, Any]:
        """Bulguyu cozer.

        Args:
            finding_id: Bulgu ID.
            resolution: Cozum.

        Returns:
            Cozum bilgisi.
        """
        try:
            for f in self._findings:
                if (
                    f["finding_id"]
                    == finding_id
                ):
                    f["resolved"] = True
                    f[
                        "resolution"
                    ] = resolution
                    f[
                        "resolved_at"
                    ] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    return {
                        "finding_id": (
                            finding_id
                        ),
                        "resolved": True,
                    }

            return {
                "resolved": False,
                "error": "Bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "resolved": False,
                "error": str(e),
            }

    def get_security_score(
        self,
    ) -> dict[str, Any]:
        """Guvenlik puani getirir.

        Returns:
            Puan bilgisi.
        """
        try:
            if not self._analyses:
                return {
                    "score": 100,
                    "grade": "A",
                    "calculated": True,
                }

            unresolved = [
                f
                for f in self._findings
                if not f["resolved"]
            ]
            total = len(self._findings)
            resolved = total - len(
                unresolved
            )

            penalty = 0
            for f in unresolved:
                sev = f.get(
                    "severity", "medium"
                )
                if sev == "critical":
                    penalty += 20
                elif sev == "high":
                    penalty += 10
                elif sev == "medium":
                    penalty += 5
                else:
                    penalty += 2

            score = max(0, 100 - penalty)
            if score >= 90:
                grade = "A"
            elif score >= 70:
                grade = "B"
            elif score >= 50:
                grade = "C"
            elif score >= 30:
                grade = "D"
            else:
                grade = "F"

            return {
                "score": score,
                "grade": grade,
                "total_findings": total,
                "unresolved": len(
                    unresolved
                ),
                "resolved": resolved,
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            unresolved = [
                f
                for f in self._findings
                if not f["resolved"]
            ]
            critical = sum(
                1
                for f in unresolved
                if f["severity"] == "critical"
            )
            high = sum(
                1
                for f in unresolved
                if f["severity"] == "high"
            )

            return {
                "total_analyses": len(
                    self._analyses
                ),
                "total_findings": len(
                    self._findings
                ),
                "unresolved": len(
                    unresolved
                ),
                "critical": critical,
                "high": high,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
