"""ATLAS Regulatory Orkestrator modulu.

Tam düzenleyici pipeline, karar-öncesi kontrol,
gerçek zamanlı uygulama, kural yönetimi, analitik.
"""

import logging
from typing import Any

from app.core.regulatory.compliance_checker import (
    RegulatoryComplianceChecker,
)
from app.core.regulatory.compliance_reporter import (
    RegulatoryComplianceReporter,
)
from app.core.regulatory.constraint_definer import (
    ConstraintDefiner,
)
from app.core.regulatory.exception_handler import (
    RegulatoryExceptionHandler,
)
from app.core.regulatory.jurisdiction_manager import (
    JurisdictionManager,
)
from app.core.regulatory.rate_limit_enforcer import (
    RateLimitEnforcer,
)
from app.core.regulatory.rule_repository import (
    RuleRepository,
)
from app.core.regulatory.rule_updater import (
    RuleUpdater,
)

logger = logging.getLogger(__name__)


class RegulatoryOrchestrator:
    """Regulatory orkestrator.

    Tüm düzenleyici bileşenleri koordine eder.

    Attributes:
        rules: Kural deposu.
        constraints: Kısıt tanımlayıcı.
        checker: Uyumluluk kontrolcüsü.
        jurisdictions: Yetki alanı yöneticisi.
        rate_limits: Hız limiti uygulayıcı.
        updater: Kural güncelleyici.
        exceptions: İstisna yöneticisi.
        reporter: Uyumluluk raporlayıcı.
    """

    def __init__(
        self,
        strict_mode: bool = False,
        auto_update: bool = False,
        approval_required: bool = True,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            strict_mode: Katı mod.
            auto_update: Otomatik güncelleme.
            approval_required: Onay gerekli.
        """
        self.rules = RuleRepository()
        self.constraints = ConstraintDefiner()
        self.checker = (
            RegulatoryComplianceChecker()
        )
        self.jurisdictions = (
            JurisdictionManager()
        )
        self.rate_limits = RateLimitEnforcer()
        self.updater = RuleUpdater(
            auto_update=auto_update,
        )
        self.exceptions = (
            RegulatoryExceptionHandler(
                approval_required=(
                    approval_required
                ),
            )
        )
        self.reporter = (
            RegulatoryComplianceReporter()
        )

        self._strict_mode = strict_mode
        self._stats = {
            "decisions_checked": 0,
        }

        logger.info(
            "RegulatoryOrchestrator "
            "baslatildi",
        )

    def check_decision(
        self,
        action: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Karar kontrolü yapar (tam pipeline).

        Args:
            action: Aksiyon adı.
            context: Aksiyon bağlamı.

        Returns:
            Kontrol bilgisi.
        """
        # 1) Aktif kuralları getir
        active_rules = self.rules.list_rules(
            active_only=True,
        )
        full_rules = [
            self.rules.get_rule(r["rule_id"])
            for r in active_rules
        ]

        # 2) İstisna kontrolü
        rules_to_check = []
        for rule in full_rules:
            rid = rule["rule_id"]
            exc = self.exceptions.check_exception(
                rid,
            )
            if not exc["has_exception"]:
                rules_to_check.append(rule)

        # 3) Uyumluluk kontrolü
        result = self.checker.check_action(
            action, context, rules_to_check,
        )

        # 4) Katı mod: soft ihlalleri de engelle
        allowed = result["compliant"]
        if (
            not allowed
            and not self._strict_mode
        ):
            # Katı değilse, sadece hard ihlaller engeller
            hard_violations = [
                v for v in result["violations"]
                if v.get("severity") in (
                    "critical", "high",
                )
            ]
            if not hard_violations:
                allowed = True

        self._stats["decisions_checked"] += 1

        return {
            "action": action,
            "allowed": allowed,
            "compliant": result["compliant"],
            "violations": result["violations"],
            "violation_count": result[
                "violation_count"
            ],
            "recommendations": result[
                "recommendations"
            ],
            "strict_mode": self._strict_mode,
        }

    def add_rule(
        self,
        name: str,
        category: str = "operational",
        severity: str = "medium",
        conditions: dict[str, Any] | None = None,
        jurisdiction: str = "global",
    ) -> dict[str, Any]:
        """Kural ekler.

        Args:
            name: Kural adı.
            category: Kategori.
            severity: Şiddet.
            conditions: Koşullar.
            jurisdiction: Yetki alanı.

        Returns:
            Ekleme bilgisi.
        """
        return self.rules.add_rule(
            name, category,
            severity=severity,
            conditions=conditions,
            jurisdiction=jurisdiction,
        )

    def get_compliance_report(
        self,
    ) -> dict[str, Any]:
        """Uyumluluk raporu getirir.

        Returns:
            Rapor bilgisi.
        """
        checks = self.checker.get_check_history()
        violations = (
            self.checker.get_violations()
        )
        return (
            self.reporter
            .generate_compliance_report(
                checks, violations,
            )
        )

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "total_rules": (
                self.rules.rule_count
            ),
            "active_rules": (
                self.rules.active_rule_count
            ),
            "total_constraints": (
                self.constraints
                .constraint_count
            ),
            "total_checks": (
                self.checker.check_count
            ),
            "total_violations": (
                self.checker.violation_count
            ),
            "compliance_rate": (
                self.checker.compliance_rate
            ),
            "jurisdictions": (
                self.jurisdictions
                .jurisdiction_count
            ),
            "rate_limits": (
                self.rate_limits.limit_count
            ),
            "rule_updates": (
                self.updater.update_count
            ),
            "exceptions": (
                self.exceptions.exception_count
            ),
            "active_exceptions": (
                self.exceptions
                .active_exception_count
            ),
            "reports_generated": (
                self.reporter.report_count
            ),
            "decisions_checked": (
                self._stats[
                    "decisions_checked"
                ]
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "total_rules": (
                self.rules.rule_count
            ),
            "total_checks": (
                self.checker.check_count
            ),
            "compliance_rate": (
                self.checker.compliance_rate
            ),
            "decisions_checked": (
                self._stats[
                    "decisions_checked"
                ]
            ),
        }

    @property
    def decisions_checked(self) -> int:
        """Kontrol edilen karar sayısı."""
        return self._stats[
            "decisions_checked"
        ]
