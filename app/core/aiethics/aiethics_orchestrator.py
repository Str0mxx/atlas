"""
AI Etik orkestrator modulu.

Tam etik izleme, tespit, analiz,
uyari, iyilestirme, sorumlu AI,
analitik.
"""

import logging
from typing import Any

from .bias_detector import BiasDetector
from .decision_auditor import (
    EthicsDecisionAuditor,
)
from .ethics_rule_engine import (
    EthicsRuleEngine,
)
from .ethics_violation_alert import (
    EthicsViolationAlert,
)
from .fairness_analyzer import (
    FairnessAnalyzer,
)
from .protected_class_monitor import (
    ProtectedClassMonitor,
)
from .remediation_suggester import (
    EthicsRemediationSuggester,
)
from .transparency_reporter import (
    TransparencyReporter,
)

logger = logging.getLogger(__name__)


class AIEthicsOrchestrator:
    """AI Etik orkestrator.

    Detect -> Analyze -> Alert ->
    Remediate pipeline.

    Attributes:
        _bias_detector: Onyargi tespitcisi.
        _fairness: Adalet analizcisi.
        _rule_engine: Kural motoru.
        _auditor: Karar denetcisi.
        _monitor: Korunan sinif izleyici.
        _reporter: Seffaflik raporlayici.
        _alerts: Ihlal uyarilari.
        _remediator: Iyilestirme onerici.
        _stats: Istatistikler.
    """

    def __init__(
        self,
        bias_detection: bool = True,
        fairness_metrics: bool = True,
        auto_alert: bool = True,
        transparency_reports: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            bias_detection: Onyargi tespiti.
            fairness_metrics: Adalet metrikleri.
            auto_alert: Otomatik uyari.
            transparency_reports: Raporlar.
        """
        self._bias_detection = (
            bias_detection
        )
        self._fairness_metrics = (
            fairness_metrics
        )
        self._auto_alert = auto_alert
        self._transparency_reports = (
            transparency_reports
        )

        self._bias_detector = (
            BiasDetector()
        )
        self._fairness = (
            FairnessAnalyzer()
        )
        self._rule_engine = (
            EthicsRuleEngine()
        )
        self._auditor = (
            EthicsDecisionAuditor()
        )
        self._monitor = (
            ProtectedClassMonitor()
        )
        self._reporter = (
            TransparencyReporter()
        )
        self._alerts = (
            EthicsViolationAlert(
                auto_escalate=auto_alert
            )
        )
        self._remediator = (
            EthicsRemediationSuggester()
        )

        self._stats: dict[str, int] = {
            "full_checks": 0,
            "biases_detected": 0,
            "fairness_issues": 0,
            "violations_found": 0,
            "remediations_suggested": 0,
        }

        logger.info(
            "AIEthicsOrchestrator "
            "baslatildi"
        )

    def full_ethics_check(
        self,
        dataset_id: str = "",
        predictions: list[dict]
        | None = None,
        protected_attr: str = "",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Tam etik kontrol yapar.

        Detect -> Analyze -> Alert ->
        Remediate pipeline.

        Args:
            dataset_id: Veri seti ID.
            predictions: Tahminler.
            protected_attr: Korunan ozellik.
            context: Baglam.

        Returns:
            Kontrol bilgisi.
        """
        try:
            results: dict[str, Any] = {}
            issues: list[dict] = []

            # 1. Onyargi tespiti
            if (
                self._bias_detection
                and dataset_id
            ):
                bias_result = (
                    self._bias_detector
                    .scan_for_bias(
                        dataset_id=dataset_id
                    )
                )
                results["bias"] = (
                    bias_result
                )

                if bias_result.get(
                    "scanned"
                ):
                    findings = (
                        bias_result.get(
                            "findings", []
                        )
                    )
                    if findings:
                        self._stats[
                            "biases_detected"
                        ] += len(findings)
                        for f in findings:
                            issues.append({
                                "type": (
                                    "bias"
                                ),
                                "detail": f,
                            })

            # 2. Adalet analizi
            if (
                self._fairness_metrics
                and predictions
                and protected_attr
            ):
                fair_result = (
                    self._fairness
                    .analyze_fairness(
                        predictions=(
                            predictions
                        ),
                        protected_attr=(
                            protected_attr
                        ),
                    )
                )
                results["fairness"] = (
                    fair_result
                )

                if fair_result.get(
                    "analyzed"
                ) and not fair_result.get(
                    "is_fair"
                ):
                    self._stats[
                        "fairness_issues"
                    ] += 1
                    issues.append({
                        "type": "fairness",
                        "score": (
                            fair_result.get(
                                "fairness_"
                                "score", 0
                            )
                        ),
                    })

            # 3. Kural kontrolu
            if context:
                rule_result = (
                    self._rule_engine
                    .evaluate(
                        context=context
                    )
                )
                results["rules"] = (
                    rule_result
                )

                if rule_result.get(
                    "evaluated"
                ):
                    viols = rule_result.get(
                        "violations", []
                    )
                    if viols:
                        self._stats[
                            "violations_"
                            "found"
                        ] += len(viols)
                        for v in viols:
                            issues.append({
                                "type": (
                                    "rule_"
                                    "violation"
                                ),
                                "detail": v,
                            })

            # 4. Uyari olusturma
            alerts_raised: list[str] = []
            if (
                self._auto_alert
                and issues
            ):
                for issue in issues:
                    itype = issue.get(
                        "type", ""
                    )
                    severity = (
                        "high"
                        if itype
                        == "rule_violation"
                        else "medium"
                    )
                    alert = (
                        self._alerts
                        .raise_alert(
                            violation_type=(
                                itype
                            ),
                            severity=(
                                severity
                            ),
                            title=(
                                f"Etik sorun:"
                                f" {itype}"
                            ),
                            description=(
                                str(issue)
                            ),
                            source=(
                                "full_check"
                            ),
                        )
                    )
                    if alert.get("raised"):
                        alerts_raised.append(
                            alert.get(
                                "alert_id",
                                ""
                            )
                        )

            # 5. Iyilestirme onerileri
            remediation_ids: list[
                str
            ] = []
            if issues:
                for issue in issues:
                    itype = issue.get(
                        "type", ""
                    )
                    if itype == "bias":
                        detail = issue.get(
                            "detail", {}
                        )
                        rem = (
                            self._remediator
                            .suggest_for_bias(
                                bias_type=(
                                    detail.get(
                                        "type",
                                        "",
                                    )
                                ),
                                severity=(
                                    "medium"
                                ),
                                gap=(
                                    detail.get(
                                        "gap",
                                        0,
                                    )
                                ),
                            )
                        )
                        if rem.get(
                            "suggested"
                        ):
                            remediation_ids.append(
                                rem.get(
                                    "suggestion"
                                    "_id",
                                    "",
                                )
                            )
                    elif itype == "fairness":
                        rem = (
                            self._remediator
                            .suggest_for_fairness(
                                score=(
                                    issue.get(
                                        "score",
                                        0,
                                    )
                                ),
                            )
                        )
                        if rem.get(
                            "suggested"
                        ):
                            remediation_ids.append(
                                rem.get(
                                    "suggestion"
                                    "_id",
                                    "",
                                )
                            )
                self._stats[
                    "remediations_"
                    "suggested"
                ] += len(remediation_ids)

            self._stats[
                "full_checks"
            ] += 1

            return {
                "results": results,
                "issue_count": len(
                    issues
                ),
                "issues": issues,
                "alerts_raised": (
                    alerts_raised
                ),
                "remediation_ids": (
                    remediation_ids
                ),
                "is_ethical": (
                    len(issues) == 0
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def log_and_audit_decision(
        self,
        decision_type: str = "",
        inputs: dict | None = None,
        output: Any = None,
        model_id: str = "",
        confidence: float = 1.0,
        protected_attrs: (
            dict | None
        ) = None,
    ) -> dict[str, Any]:
        """Karar kaydeder ve denetler.

        Args:
            decision_type: Karar tipi.
            inputs: Girdiler.
            output: Cikti.
            model_id: Model ID.
            confidence: Guven.
            protected_attrs: Korunan.

        Returns:
            Denetim bilgisi.
        """
        try:
            # Karar kaydet
            log_result = (
                self._auditor.log_decision(
                    decision_type=(
                        decision_type
                    ),
                    inputs=inputs,
                    output=output,
                    model_id=model_id,
                    confidence=confidence,
                    protected_attrs=(
                        protected_attrs
                    ),
                )
            )

            # Korunan ozellik izleme
            if protected_attrs:
                for attr, val in (
                    protected_attrs.items()
                ):
                    self._monitor.log_observation(
                        protected_attr=attr,
                        protected_value=(
                            str(val)
                        ),
                        outcome=output,
                    )

            return {
                "decision_id": (
                    log_result.get(
                        "decision_id"
                    )
                ),
                "logged": log_result.get(
                    "logged", False
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def generate_ethics_report(
        self,
        title: str = "",
        audience: str = "business",
    ) -> dict[str, Any]:
        """Etik raporu olusturur.

        Args:
            title: Baslik.
            audience: Hedef kitle.

        Returns:
            Rapor bilgisi.
        """
        try:
            if not self._transparency_reports:
                return {
                    "generated": False,
                    "error": (
                        "Raporlar devre disi"
                    ),
                }

            # Ozet bilgileri topla
            bias_summary = (
                self._bias_detector
                .get_summary()
            )
            fairness_summary = (
                self._fairness
                .get_summary()
            )
            alert_summary = (
                self._alerts
                .get_summary()
            )

            sections = [
                {
                    "title": (
                        "Onyargi Tespiti"
                    ),
                    "content": (
                        bias_summary
                    ),
                },
                {
                    "title": (
                        "Adalet Analizi"
                    ),
                    "content": (
                        fairness_summary
                    ),
                },
                {
                    "title": (
                        "Uyari Durumu"
                    ),
                    "content": (
                        alert_summary
                    ),
                },
            ]

            report = (
                self._reporter
                .generate_stakeholder_report(
                    title=(
                        title
                        or "Etik Raporu"
                    ),
                    audience=audience,
                    sections=sections,
                )
            )

            return report

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik bilgisi getirir."""
        try:
            return {
                "bias": (
                    self._bias_detector
                    .get_summary()
                ),
                "fairness": (
                    self._fairness
                    .get_summary()
                ),
                "rules": (
                    self._rule_engine
                    .get_summary()
                ),
                "auditor": (
                    self._auditor
                    .get_summary()
                ),
                "monitor": (
                    self._monitor
                    .get_summary()
                ),
                "alerts": (
                    self._alerts
                    .get_summary()
                ),
                "remediation": (
                    self._remediator
                    .get_summary()
                ),
                "reporter": (
                    self._reporter
                    .get_summary()
                ),
                "orchestrator_stats": (
                    dict(self._stats)
                ),
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
                "stats": dict(
                    self._stats
                ),
                "bias_detection": (
                    self._bias_detection
                ),
                "fairness_metrics": (
                    self._fairness_metrics
                ),
                "auto_alert": (
                    self._auto_alert
                ),
                "transparency_reports": (
                    self._transparency_reports
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
