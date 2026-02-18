"""
Etik karar denetcisi modulu.

Karar loglama, denetim izi,
kalip tespiti, uyumluluk kontrolu,
raporlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class EthicsDecisionAuditor:
    """Etik karar denetcisi.

    Attributes:
        _decisions: Kararlar.
        _audits: Denetimler.
        _stats: Istatistikler.
    """

    DECISION_TYPES: list[str] = [
        "classification",
        "recommendation",
        "filtering",
        "ranking",
        "allocation",
        "prediction",
    ]

    COMPLIANCE_LEVELS: list[str] = [
        "compliant",
        "minor_issue",
        "major_issue",
        "non_compliant",
    ]

    def __init__(
        self,
        retention_limit: int = 10000,
    ) -> None:
        """Denetciyi baslatir.

        Args:
            retention_limit: Saklama limiti.
        """
        self._retention_limit = (
            retention_limit
        )
        self._decisions: list[dict] = []
        self._audits: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "decisions_logged": 0,
            "audits_done": 0,
            "patterns_found": 0,
            "non_compliant": 0,
        }
        logger.info(
            "EthicsDecisionAuditor "
            "baslatildi"
        )

    @property
    def decision_count(self) -> int:
        """Karar sayisi."""
        return len(self._decisions)

    def log_decision(
        self,
        decision_type: str = "",
        inputs: dict | None = None,
        output: Any = None,
        model_id: str = "",
        confidence: float = 1.0,
        protected_attrs: (
            dict | None
        ) = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Karar kaydeder.

        Args:
            decision_type: Karar tipi.
            inputs: Girdiler.
            output: Cikti.
            model_id: Model ID.
            confidence: Guven.
            protected_attrs: Korunan.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            did = f"dec_{uuid4()!s:.8}"
            entry = {
                "decision_id": did,
                "decision_type": (
                    decision_type
                ),
                "inputs": inputs or {},
                "output": output,
                "model_id": model_id,
                "confidence": confidence,
                "protected_attrs": (
                    protected_attrs or {}
                ),
                "metadata": metadata or {},
                "logged_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._decisions.append(entry)

            # Limit kontrol
            if (
                len(self._decisions)
                > self._retention_limit
            ):
                self._decisions = (
                    self._decisions[
                        -self._retention_limit :
                    ]
                )

            self._stats[
                "decisions_logged"
            ] += 1

            return {
                "decision_id": did,
                "logged": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def audit_decisions(
        self,
        decision_type: str = "",
        protected_attr: str = "",
        last_n: int = 100,
    ) -> dict[str, Any]:
        """Kararlari denetler.

        Args:
            decision_type: Filtre.
            protected_attr: Korunan ozellik.
            last_n: Son N karar.

        Returns:
            Denetim bilgisi.
        """
        try:
            aid = f"aud_{uuid4()!s:.8}"

            decs = self._decisions[-last_n:]
            if decision_type:
                decs = [
                    d
                    for d in decs
                    if d["decision_type"]
                    == decision_type
                ]

            findings: list[dict] = []

            # Sonuc dagilimi analizi
            if protected_attr and decs:
                groups: dict[
                    str, list
                ] = {}
                for d in decs:
                    g = str(
                        d.get(
                            "protected_attrs",
                            {},
                        ).get(
                            protected_attr,
                            "unknown",
                        )
                    )
                    groups.setdefault(
                        g, []
                    )
                    groups[g].append(d)

                # Pozitif sonuc oranlari
                rates: dict[
                    str, float
                ] = {}
                for g, recs in (
                    groups.items()
                ):
                    pos = sum(
                        1
                        for r in recs
                        if r.get("output")
                    )
                    rates[g] = (
                        pos / len(recs)
                        if recs
                        else 0
                    )

                if len(rates) >= 2:
                    max_r = max(
                        rates.values()
                    )
                    min_r = min(
                        rates.values()
                    )
                    gap = max_r - min_r

                    if gap > 0.2:
                        findings.append({
                            "type": (
                                "outcome_"
                                "disparity"
                            ),
                            "attribute": (
                                protected_attr
                            ),
                            "rates": {
                                k: round(
                                    v, 4
                                )
                                for k, v in rates.items()
                            },
                            "gap": round(
                                gap, 4
                            ),
                            "severity": (
                                "major_issue"
                                if gap > 0.4
                                else "minor_issue"
                            ),
                        })

            # Guven dagilimi
            if decs:
                avg_conf = sum(
                    d.get("confidence", 0)
                    for d in decs
                ) / len(decs)
                low_conf = sum(
                    1
                    for d in decs
                    if d.get(
                        "confidence", 1
                    )
                    < 0.5
                )
                if low_conf > len(decs) * 0.3:
                    findings.append({
                        "type": (
                            "low_confidence_"
                            "pattern"
                        ),
                        "low_count": (
                            low_conf
                        ),
                        "avg_confidence": (
                            round(
                                avg_conf, 4
                            )
                        ),
                        "severity": (
                            "minor_issue"
                        ),
                    })

            compliance = (
                "compliant"
                if not findings
                else (
                    "non_compliant"
                    if any(
                        f.get("severity")
                        == "major_issue"
                        for f in findings
                    )
                    else "minor_issue"
                )
            )

            self._audits[aid] = {
                "audit_id": aid,
                "decisions_reviewed": len(
                    decs
                ),
                "findings": findings,
                "compliance": compliance,
                "audited_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "audits_done"
            ] += 1
            self._stats[
                "patterns_found"
            ] += len(findings)
            if compliance == "non_compliant":
                self._stats[
                    "non_compliant"
                ] += 1

            return {
                "audit_id": aid,
                "decisions_reviewed": len(
                    decs
                ),
                "findings": findings,
                "finding_count": len(
                    findings
                ),
                "compliance": compliance,
                "audited": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "audited": False,
                "error": str(e),
            }

    def generate_report(
        self,
        audit_id: str = "",
    ) -> dict[str, Any]:
        """Denetim raporu olusturur.

        Args:
            audit_id: Denetim ID.

        Returns:
            Rapor bilgisi.
        """
        try:
            audit = self._audits.get(
                audit_id
            )
            if not audit:
                return {
                    "generated": False,
                    "error": (
                        "Denetim bulunamadi"
                    ),
                }

            report = {
                "audit_id": audit_id,
                "summary": {
                    "decisions_reviewed": (
                        audit[
                            "decisions_reviewed"
                        ]
                    ),
                    "findings_count": len(
                        audit["findings"]
                    ),
                    "compliance": audit[
                        "compliance"
                    ],
                },
                "findings": audit[
                    "findings"
                ],
                "recommendations": [],
            }

            for f in audit["findings"]:
                if (
                    f["type"]
                    == "outcome_disparity"
                ):
                    report[
                        "recommendations"
                    ].append(
                        "Sonuc esitsizligini "
                        "azaltmak icin model "
                        "yeniden egitilmeli"
                    )
                elif (
                    f["type"]
                    == "low_confidence_pattern"
                ):
                    report[
                        "recommendations"
                    ].append(
                        "Dusuk guvenli "
                        "kararlari inceleyin"
                    )

            return {
                **report,
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_decisions": len(
                    self._decisions
                ),
                "total_audits": len(
                    self._audits
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
