"""
AI Ethics & Bias Monitor modelleri.

Onyargi tespiti, adalet analizi,
etik kurallar, seffaflik raporlama
veri modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class BiasType(str, Enum):
    """Onyargi tipleri."""

    DEMOGRAPHIC = "demographic"
    REPRESENTATION = "representation"
    MEASUREMENT = "measurement"
    AGGREGATION = "aggregation"
    EVALUATION = "evaluation"
    SELECTION = "selection"
    HISTORICAL = "historical"
    LABEL = "label"


class BiasSeverity(str, Enum):
    """Onyargi ciddiyet seviyeleri."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FairnessMetric(str, Enum):
    """Adalet metrikleri."""

    DEMOGRAPHIC_PARITY = (
        "demographic_parity"
    )
    EQUAL_OPPORTUNITY = (
        "equal_opportunity"
    )
    EQUALIZED_ODDS = "equalized_odds"
    CALIBRATION = "calibration"
    PREDICTIVE_PARITY = (
        "predictive_parity"
    )
    TREATMENT_EQUALITY = (
        "treatment_equality"
    )


class RuleCategory(str, Enum):
    """Kural kategorileri."""

    FAIRNESS = "fairness"
    TRANSPARENCY = "transparency"
    ACCOUNTABILITY = "accountability"
    PRIVACY = "privacy"
    SAFETY = "safety"
    AUTONOMY = "autonomy"
    BENEFICENCE = "beneficence"
    NON_MALEFICENCE = "non_maleficence"


class RuleSeverity(str, Enum):
    """Kural ciddiyet seviyeleri."""

    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


class ComplianceLevel(str, Enum):
    """Uyumluluk seviyeleri."""

    COMPLIANT = "compliant"
    MINOR_ISSUE = "minor_issue"
    MAJOR_ISSUE = "major_issue"
    NON_COMPLIANT = "non_compliant"


class TreatmentType(str, Enum):
    """Muamele tipleri."""

    EQUAL = "equal"
    FAVORABLE = "favorable"
    UNFAVORABLE = "unfavorable"
    UNKNOWN = "unknown"


class ViolationType(str, Enum):
    """Ihlal tipleri."""

    BIAS_DETECTED = "bias_detected"
    FAIRNESS_VIOLATION = (
        "fairness_violation"
    )
    RULE_VIOLATION = "rule_violation"
    DISPARITY_ALERT = "disparity_alert"
    TRANSPARENCY_GAP = "transparency_gap"
    COMPLIANCE_ISSUE = "compliance_issue"


class AlertStatus(str, Enum):
    """Uyari durumlari."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SuggestionType(str, Enum):
    """Oneri tipleri."""

    DEBIASING = "debiasing"
    RETRAINING = "retraining"
    PROCESS_CHANGE = "process_change"
    MONITORING = "monitoring_enhancement"
    DATA_COLLECTION = "data_collection"
    MODEL_ADJUSTMENT = "model_adjustment"


class ReportType(str, Enum):
    """Rapor tipleri."""

    MODEL_CARD = "model_card"
    DECISION_EXPLANATION = (
        "decision_explanation"
    )
    STAKEHOLDER_REPORT = (
        "stakeholder_report"
    )
    PUBLIC_DISCLOSURE = "public_disclosure"
    AUDIT_REPORT = "audit_report"
    IMPACT_ASSESSMENT = "impact_assessment"


# --- Pydantic modeller ---


class BiasDetectionResult(BaseModel):
    """Onyargi tespit sonucu."""

    detection_id: str = ""
    dataset_id: str = ""
    findings: list[dict] = Field(
        default_factory=list
    )
    bias_score: float = 0.0
    severity: BiasSeverity = (
        BiasSeverity.NONE
    )
    scanned: bool = False


class FairnessAnalysisResult(BaseModel):
    """Adalet analiz sonucu."""

    analysis_id: str = ""
    metrics: dict = Field(
        default_factory=dict
    )
    is_fair: bool = True
    fairness_score: float = 1.0
    analyzed: bool = False


class EthicsRuleResult(BaseModel):
    """Etik kural sonucu."""

    evaluation_id: str = ""
    violations: list[dict] = Field(
        default_factory=list
    )
    violation_count: int = 0
    passed_count: int = 0
    compliant: bool = True
    evaluated: bool = False


class DecisionAuditResult(BaseModel):
    """Karar denetim sonucu."""

    audit_id: str = ""
    decisions_reviewed: int = 0
    findings: list[dict] = Field(
        default_factory=list
    )
    compliance: ComplianceLevel = (
        ComplianceLevel.COMPLIANT
    )
    audited: bool = False


class ProtectedClassAlert(BaseModel):
    """Korunan sinif uyarisi."""

    alert_id: str = ""
    attribute: str = ""
    gap: float = 0.0
    severity: str = "medium"
    status: AlertStatus = AlertStatus.OPEN


class EthicsViolation(BaseModel):
    """Etik ihlal."""

    alert_id: str = ""
    violation_type: ViolationType = (
        ViolationType.BIAS_DETECTED
    )
    severity: BiasSeverity = (
        BiasSeverity.MEDIUM
    )
    title: str = ""
    status: AlertStatus = AlertStatus.OPEN


class RemediationSuggestion(BaseModel):
    """Iyilestirme onerisi."""

    suggestion_id: str = ""
    suggestion_type: SuggestionType = (
        SuggestionType.DEBIASING
    )
    description: str = ""
    priority: str = "medium"


class TransparencyReport(BaseModel):
    """Seffaflik raporu."""

    report_id: str = ""
    report_type: ReportType = (
        ReportType.STAKEHOLDER_REPORT
    )
    title: str = ""
    audience: str = "business"
    generated: bool = False


class AIEthicsSummary(BaseModel):
    """AI Etik ozet."""

    full_checks: int = 0
    biases_detected: int = 0
    fairness_issues: int = 0
    violations_found: int = 0
    remediations_suggested: int = 0
    bias_detection: bool = True
    fairness_metrics: bool = True
    auto_alert: bool = True
    transparency_reports: bool = True
