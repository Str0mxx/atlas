"""ATLAS Regulatory & Constraint Engine testleri."""

import time

import pytest

from app.core.regulatory import (
    ConstraintDefiner,
    JurisdictionManager,
    RateLimitEnforcer,
    RegulatoryComplianceChecker,
    RegulatoryComplianceReporter,
    RegulatoryExceptionHandler,
    RegulatoryOrchestrator,
    RuleRepository,
    RuleUpdater,
)
from app.models.regulatory_models import (
    ComplianceStatus,
    ConstraintRecord,
    ConstraintType,
    ExceptionStatus,
    JurisdictionScope,
    RegulatorySnapshot,
    RuleCategory,
    RuleRecord,
    ViolationRecord,
    ViolationSeverity,
)


# ── Model Testleri ──────────────────────────


class TestRegulatoryModels:
    """Model testleri."""

    def test_rule_category_enum(self) -> None:
        assert RuleCategory.LEGAL == "legal"
        assert RuleCategory.FINANCIAL == "financial"
        assert RuleCategory.PRIVACY == "privacy"
        assert RuleCategory.OPERATIONAL == "operational"
        assert RuleCategory.PLATFORM == "platform"

    def test_constraint_type_enum(self) -> None:
        assert ConstraintType.HARD == "hard"
        assert ConstraintType.SOFT == "soft"
        assert ConstraintType.TEMPORAL == "temporal"
        assert ConstraintType.CONDITIONAL == "conditional"
        assert ConstraintType.RATE_LIMIT == "rate_limit"

    def test_violation_severity_enum(self) -> None:
        assert ViolationSeverity.CRITICAL == "critical"
        assert ViolationSeverity.HIGH == "high"
        assert ViolationSeverity.MEDIUM == "medium"
        assert ViolationSeverity.LOW == "low"
        assert ViolationSeverity.INFO == "info"

    def test_jurisdiction_scope_enum(self) -> None:
        assert JurisdictionScope.GLOBAL == "global"
        assert JurisdictionScope.REGIONAL == "regional"
        assert JurisdictionScope.NATIONAL == "national"
        assert JurisdictionScope.INDUSTRY == "industry"
        assert JurisdictionScope.PLATFORM == "platform"

    def test_exception_status_enum(self) -> None:
        assert ExceptionStatus.REQUESTED == "requested"
        assert ExceptionStatus.APPROVED == "approved"
        assert ExceptionStatus.DENIED == "denied"
        assert ExceptionStatus.EXPIRED == "expired"
        assert ExceptionStatus.REVOKED == "revoked"

    def test_compliance_status_enum(self) -> None:
        assert ComplianceStatus.COMPLIANT == "compliant"
        assert ComplianceStatus.NON_COMPLIANT == "non_compliant"
        assert ComplianceStatus.PARTIAL == "partial"
        assert ComplianceStatus.PENDING == "pending"
        assert ComplianceStatus.EXEMPT == "exempt"

    def test_rule_record(self) -> None:
        r = RuleRecord(name="Test Rule")
        assert r.name == "Test Rule"
        assert r.active is True
        assert r.rule_id

    def test_constraint_record(self) -> None:
        c = ConstraintRecord(
            name="Budget Limit",
            constraint_type=ConstraintType.HARD,
        )
        assert c.name == "Budget Limit"
        assert c.priority == 5

    def test_violation_record(self) -> None:
        v = ViolationRecord(
            rule_id="r1",
            action="delete_data",
        )
        assert v.rule_id == "r1"
        assert v.violation_id

    def test_regulatory_snapshot(self) -> None:
        s = RegulatorySnapshot(
            total_rules=10,
            compliance_rate=0.95,
        )
        assert s.total_rules == 10
        assert s.compliance_rate == 0.95


# ── RuleRepository Testleri ──────────────────


class TestRuleRepository:
    """RuleRepository testleri."""

    def test_add_rule(self) -> None:
        repo = RuleRepository()
        r = repo.add_rule("No Delete", "privacy", severity="critical")
        assert r["created"] is True
        assert r["category"] == "privacy"
        assert repo.rule_count == 1

    def test_get_rule(self) -> None:
        repo = RuleRepository()
        c = repo.add_rule("Test Rule")
        r = repo.get_rule(c["rule_id"])
        assert r["name"] == "Test Rule"
        assert r["active"] is True

    def test_get_rule_not_found(self) -> None:
        repo = RuleRepository()
        r = repo.get_rule("nonexistent")
        assert r["error"] == "rule_not_found"

    def test_update_rule(self) -> None:
        repo = RuleRepository()
        c = repo.add_rule("Old")
        r = repo.update_rule(
            c["rule_id"], {"name": "New"},
        )
        assert r["updated"] is True
        assert r["version"] == 2

    def test_activate_deactivate(self) -> None:
        repo = RuleRepository()
        c = repo.add_rule("Test")
        repo.deactivate_rule(c["rule_id"])
        r = repo.get_rule(c["rule_id"])
        assert r["active"] is False
        repo.activate_rule(c["rule_id"])
        r = repo.get_rule(c["rule_id"])
        assert r["active"] is True

    def test_list_rules(self) -> None:
        repo = RuleRepository()
        repo.add_rule("A", "privacy")
        repo.add_rule("B", "financial")
        repo.add_rule("C", "privacy")
        result = repo.list_rules(category="privacy")
        assert len(result) == 2

    def test_list_rules_active_only(self) -> None:
        repo = RuleRepository()
        c1 = repo.add_rule("A")
        repo.add_rule("B")
        repo.deactivate_rule(c1["rule_id"])
        result = repo.list_rules(active_only=True)
        assert len(result) == 1

    def test_version_history(self) -> None:
        repo = RuleRepository()
        c = repo.add_rule("Test")
        repo.update_rule(c["rule_id"], {"severity": "high"})
        repo.update_rule(c["rule_id"], {"severity": "critical"})
        h = repo.get_version_history(c["rule_id"])
        assert len(h) == 3

    def test_get_by_jurisdiction(self) -> None:
        repo = RuleRepository()
        repo.add_rule("A", jurisdiction="EU")
        repo.add_rule("B", jurisdiction="US")
        repo.add_rule("C", jurisdiction="EU")
        result = repo.get_by_jurisdiction("EU")
        assert len(result) == 2

    def test_active_rule_count(self) -> None:
        repo = RuleRepository()
        c = repo.add_rule("A")
        repo.add_rule("B")
        repo.deactivate_rule(c["rule_id"])
        assert repo.active_rule_count == 1


# ── ConstraintDefiner Testleri ───────────────


class TestConstraintDefiner:
    """ConstraintDefiner testleri."""

    def test_define_hard_constraint(self) -> None:
        cd = ConstraintDefiner()
        r = cd.define_hard_constraint(
            "No Delete", "action!=delete",
        )
        assert r["defined"] is True
        assert r["constraint_type"] == "hard"
        assert r["priority"] == 10

    def test_define_soft_constraint(self) -> None:
        cd = ConstraintDefiner()
        r = cd.define_soft_constraint(
            "Prefer Email", "channel=email", priority=3,
        )
        assert r["defined"] is True
        assert r["constraint_type"] == "soft"
        assert r["priority"] == 3

    def test_define_temporal_constraint(self) -> None:
        cd = ConstraintDefiner()
        now = time.time()
        r = cd.define_temporal_constraint(
            "Business Hours",
            "hours=business",
            start_time=now,
            end_time=now + 86400,
        )
        assert r["defined"] is True
        assert r["constraint_type"] == "temporal"

    def test_define_conditional_constraint(self) -> None:
        cd = ConstraintDefiner()
        r = cd.define_conditional_constraint(
            "Budget Check",
            "amount>1000",
            trigger="purchase",
        )
        assert r["defined"] is True
        assert r["constraint_type"] == "conditional"

    def test_get_constraint(self) -> None:
        cd = ConstraintDefiner()
        c = cd.define_hard_constraint("Test", "x=1")
        r = cd.get_constraint(c["constraint_id"])
        assert r["name"] == "Test"

    def test_evaluate_constraint_satisfied(self) -> None:
        cd = ConstraintDefiner()
        c = cd.define_hard_constraint(
            "Test", "status=active",
        )
        r = cd.evaluate_constraint(
            c["constraint_id"],
            {"status": "active"},
        )
        assert r["satisfied"] is True

    def test_evaluate_constraint_not_satisfied(self) -> None:
        cd = ConstraintDefiner()
        c = cd.define_hard_constraint(
            "Test", "status=active",
        )
        r = cd.evaluate_constraint(
            c["constraint_id"],
            {"status": "inactive"},
        )
        assert r["satisfied"] is False

    def test_evaluate_not_equal(self) -> None:
        cd = ConstraintDefiner()
        c = cd.define_hard_constraint(
            "No Admin", "role!=admin",
        )
        r = cd.evaluate_constraint(
            c["constraint_id"],
            {"role": "user"},
        )
        assert r["satisfied"] is True

    def test_evaluate_temporal_not_yet(self) -> None:
        cd = ConstraintDefiner()
        future = time.time() + 86400
        c = cd.define_temporal_constraint(
            "Future", "x=1",
            start_time=future,
        )
        r = cd.evaluate_constraint(
            c["constraint_id"], {},
        )
        assert r["satisfied"] is True
        assert r["reason"] == "not_yet_active"

    def test_evaluate_temporal_expired(self) -> None:
        cd = ConstraintDefiner()
        past = time.time() - 86400
        c = cd.define_temporal_constraint(
            "Past", "x=1",
            end_time=past,
        )
        r = cd.evaluate_constraint(
            c["constraint_id"], {},
        )
        assert r["satisfied"] is True
        assert r["reason"] == "expired"

    def test_evaluate_inactive(self) -> None:
        cd = ConstraintDefiner()
        c = cd.define_hard_constraint("Test", "x=1")
        cd.deactivate_constraint(c["constraint_id"])
        r = cd.evaluate_constraint(
            c["constraint_id"], {},
        )
        assert r["satisfied"] is True
        assert r["reason"] == "inactive"

    def test_list_constraints(self) -> None:
        cd = ConstraintDefiner()
        cd.define_hard_constraint("A", "x=1")
        cd.define_soft_constraint("B", "y=2")
        result = cd.list_constraints(constraint_type="hard")
        assert len(result) == 1

    def test_list_sorted_by_priority(self) -> None:
        cd = ConstraintDefiner()
        cd.define_soft_constraint("Low", "a=1", priority=2)
        cd.define_hard_constraint("High", "b=1")
        result = cd.list_constraints()
        assert result[0]["priority"] >= result[1]["priority"]

    def test_constraint_count(self) -> None:
        cd = ConstraintDefiner()
        cd.define_hard_constraint("A", "x=1")
        cd.define_soft_constraint("B", "y=2")
        assert cd.constraint_count == 2


# ── ComplianceChecker Testleri ───────────────


class TestComplianceChecker:
    """RegulatoryComplianceChecker testleri."""

    def test_check_action_compliant(self) -> None:
        cc = RegulatoryComplianceChecker()
        rules = [{"rule_id": "r1", "name": "Test", "active": True, "conditions": {}}]
        r = cc.check_action("read", {}, rules)
        assert r["compliant"] is True
        assert cc.check_count == 1

    def test_check_action_blocked(self) -> None:
        cc = RegulatoryComplianceChecker()
        rules = [{
            "rule_id": "r1", "name": "No Delete",
            "active": True, "severity": "critical",
            "conditions": {"blocked_actions": ["delete"]},
        }]
        r = cc.check_action("delete", {}, rules)
        assert r["compliant"] is False
        assert r["violation_count"] == 1

    def test_check_required_fields(self) -> None:
        cc = RegulatoryComplianceChecker()
        rules = [{
            "rule_id": "r1", "name": "Auth Required",
            "active": True, "severity": "high",
            "conditions": {"required_fields": ["auth_token"]},
        }]
        r = cc.check_action("api_call", {}, rules)
        assert r["compliant"] is False

    def test_check_required_fields_present(self) -> None:
        cc = RegulatoryComplianceChecker()
        rules = [{
            "rule_id": "r1", "name": "Auth",
            "active": True,
            "conditions": {"required_fields": ["auth"]},
        }]
        r = cc.check_action("api", {"auth": "tok"}, rules)
        assert r["compliant"] is True

    def test_check_limits_exceeded(self) -> None:
        cc = RegulatoryComplianceChecker()
        rules = [{
            "rule_id": "r1", "name": "Budget",
            "active": True, "severity": "high",
            "conditions": {"limits": {"amount": {"max": 1000}}},
        }]
        r = cc.check_action("purchase", {"amount": 1500}, rules)
        assert r["compliant"] is False

    def test_check_limits_below_min(self) -> None:
        cc = RegulatoryComplianceChecker()
        rules = [{
            "rule_id": "r1", "name": "Min Order",
            "active": True, "severity": "low",
            "conditions": {"limits": {"quantity": {"min": 5}}},
        }]
        r = cc.check_action("order", {"quantity": 2}, rules)
        assert r["compliant"] is False

    def test_check_inactive_rule_skipped(self) -> None:
        cc = RegulatoryComplianceChecker()
        rules = [{
            "rule_id": "r1", "name": "Blocked",
            "active": False,
            "conditions": {"blocked_actions": ["all"]},
        }]
        r = cc.check_action("all", {}, rules)
        assert r["compliant"] is True

    def test_assess_severity(self) -> None:
        cc = RegulatoryComplianceChecker()
        violations = [
            {"severity": "critical"},
            {"severity": "low"},
        ]
        r = cc.assess_severity(violations)
        assert r["overall_severity"] == "critical"
        assert r["score"] == 12

    def test_assess_severity_empty(self) -> None:
        cc = RegulatoryComplianceChecker()
        r = cc.assess_severity([])
        assert r["overall_severity"] == "none"

    def test_compliance_rate(self) -> None:
        cc = RegulatoryComplianceChecker()
        cc.check_action("a", {}, [])
        cc.check_action("b", {}, [])
        cc.check_action("c", {}, [{
            "rule_id": "r1", "name": "Block",
            "active": True, "severity": "high",
            "conditions": {"blocked_actions": ["c"]},
        }])
        assert cc.compliance_rate < 1.0

    def test_get_violations(self) -> None:
        cc = RegulatoryComplianceChecker()
        cc.check_action("del", {}, [{
            "rule_id": "r1", "name": "X",
            "active": True, "severity": "high",
            "conditions": {"blocked_actions": ["del"]},
        }])
        v = cc.get_violations()
        assert len(v) == 1

    def test_recommendations_generated(self) -> None:
        cc = RegulatoryComplianceChecker()
        r = cc.check_action("del", {}, [{
            "rule_id": "r1", "name": "NoDel",
            "active": True, "severity": "critical",
            "conditions": {"blocked_actions": ["del"]},
        }])
        assert len(r["recommendations"]) > 0
        assert "CRITICAL" in r["recommendations"][0]


# ── JurisdictionManager Testleri ─────────────


class TestJurisdictionManager:
    """JurisdictionManager testleri."""

    def test_add_jurisdiction(self) -> None:
        jm = JurisdictionManager()
        r = jm.add_jurisdiction("EU GDPR", "regional")
        assert r["added"] is True
        assert jm.jurisdiction_count == 1

    def test_map_rule(self) -> None:
        jm = JurisdictionManager()
        j = jm.add_jurisdiction("Global", "global")
        r = jm.map_rule(j["jurisdiction_id"], "rule_1")
        assert r["mapped"] is True
        assert jm.mapping_count == 1

    def test_map_rule_not_found(self) -> None:
        jm = JurisdictionManager()
        r = jm.map_rule("nonexistent", "r1")
        assert r["error"] == "jurisdiction_not_found"

    def test_get_applicable_global(self) -> None:
        jm = JurisdictionManager()
        j = jm.add_jurisdiction("Global", "global")
        jm.map_rule(j["jurisdiction_id"], "r1")
        r = jm.get_applicable_rules({})
        assert "r1" in r["rule_ids"]

    def test_get_applicable_regional(self) -> None:
        jm = JurisdictionManager()
        j = jm.add_jurisdiction(
            "EU", "regional",
            properties={"regions": ["EU"]},
        )
        jm.map_rule(j["jurisdiction_id"], "r1")
        r = jm.get_applicable_rules({"geography": "EU"})
        assert "r1" in r["rule_ids"]
        r2 = jm.get_applicable_rules({"geography": "US"})
        assert "r1" not in r2["rule_ids"]

    def test_get_applicable_industry(self) -> None:
        jm = JurisdictionManager()
        j = jm.add_jurisdiction(
            "Healthcare", "industry",
            properties={"industries": ["health"]},
        )
        jm.map_rule(j["jurisdiction_id"], "r2")
        r = jm.get_applicable_rules({"industry": "health"})
        assert "r2" in r["rule_ids"]

    def test_get_applicable_platform(self) -> None:
        jm = JurisdictionManager()
        j = jm.add_jurisdiction(
            "Google", "platform",
            properties={"platforms": ["google_ads"]},
        )
        jm.map_rule(j["jurisdiction_id"], "r3")
        r = jm.get_applicable_rules({"platform": "google_ads"})
        assert "r3" in r["rule_ids"]

    def test_check_overlaps(self) -> None:
        jm = JurisdictionManager()
        j1 = jm.add_jurisdiction("A", "global")
        j2 = jm.add_jurisdiction("B", "regional")
        jm.map_rule(j1["jurisdiction_id"], "r1")
        jm.map_rule(j2["jurisdiction_id"], "r1")
        r = jm.check_overlaps("r1")
        assert r["overlap_count"] == 1

    def test_no_duplicate_rules(self) -> None:
        jm = JurisdictionManager()
        j1 = jm.add_jurisdiction("A", "global")
        j2 = jm.add_jurisdiction("B", "global")
        jm.map_rule(j1["jurisdiction_id"], "r1")
        jm.map_rule(j2["jurisdiction_id"], "r1")
        r = jm.get_applicable_rules({})
        assert r["rule_ids"].count("r1") == 1

    def test_get_rules_for_jurisdiction(self) -> None:
        jm = JurisdictionManager()
        j = jm.add_jurisdiction("Test", "global")
        jm.map_rule(j["jurisdiction_id"], "r1")
        jm.map_rule(j["jurisdiction_id"], "r2")
        rules = jm.get_rules_for_jurisdiction(j["jurisdiction_id"])
        assert len(rules) == 2


# ── RateLimitEnforcer Testleri ───────────────


class TestRateLimitEnforcer:
    """RateLimitEnforcer testleri."""

    def test_define_limit(self) -> None:
        rle = RateLimitEnforcer()
        r = rle.define_limit("API", 100, 60)
        assert r["defined"] is True
        assert rle.limit_count == 1

    def test_check_limit_allowed(self) -> None:
        rle = RateLimitEnforcer()
        lim = rle.define_limit("API", 10, 60)
        r = rle.check_limit(lim["limit_id"])
        assert r["allowed"] is True
        assert r["remaining"] == 10

    def test_check_limit_blocked(self) -> None:
        rle = RateLimitEnforcer()
        lim = rle.define_limit("API", 3, 60)
        lid = lim["limit_id"]
        for _ in range(3):
            rle.record_usage(lid)
        r = rle.check_limit(lid)
        assert r["allowed"] is False
        assert r["remaining"] == 0

    def test_record_usage(self) -> None:
        rle = RateLimitEnforcer()
        lim = rle.define_limit("API", 10, 60)
        r = rle.record_usage(lim["limit_id"])
        assert r["recorded"] is True

    def test_record_usage_not_found(self) -> None:
        rle = RateLimitEnforcer()
        r = rle.record_usage("nonexistent")
        assert r["error"] == "limit_not_found"

    def test_quota_status(self) -> None:
        rle = RateLimitEnforcer()
        lim = rle.define_limit("API", 10, 60)
        lid = lim["limit_id"]
        rle.record_usage(lid)
        rle.record_usage(lid)
        s = rle.get_quota_status(lid)
        assert s["used"] == 2
        assert s["remaining"] == 8
        assert s["usage_percent"] == 20.0

    def test_backoff_time_no_wait(self) -> None:
        rle = RateLimitEnforcer()
        lim = rle.define_limit("API", 10, 60)
        r = rle.get_backoff_time(lim["limit_id"])
        assert r["backoff_seconds"] == 0
        assert r["strategy"] == "none"

    def test_backoff_time_not_found(self) -> None:
        rle = RateLimitEnforcer()
        r = rle.get_backoff_time("x")
        assert r["error"] == "limit_not_found"

    def test_list_limits(self) -> None:
        rle = RateLimitEnforcer()
        rle.define_limit("API1", 100, limit_type="api")
        rle.define_limit("Custom", 50, limit_type="custom")
        result = rle.list_limits(limit_type="api")
        assert len(result) == 1

    def test_blocked_count(self) -> None:
        rle = RateLimitEnforcer()
        lim = rle.define_limit("T", 1, 60)
        lid = lim["limit_id"]
        rle.record_usage(lid)
        rle.check_limit(lid)  # blocked
        assert rle.blocked_count == 1


# ── RuleUpdater Testleri ─────────────────────


class TestRuleUpdater:
    """RuleUpdater testleri."""

    def test_propose_update(self) -> None:
        ru = RuleUpdater()
        r = ru.propose_update("r1", {"severity": "high"})
        assert r["status"] == "pending"

    def test_propose_auto_update(self) -> None:
        ru = RuleUpdater(auto_update=True)
        r = ru.propose_update("r1", {"severity": "high"})
        assert r["auto_applied"] is True
        assert ru.update_count == 1

    def test_apply_update(self) -> None:
        ru = RuleUpdater()
        p = ru.propose_update("r1", {"name": "New"})
        r = ru.apply_update(p["update_id"])
        assert r["applied"] is True
        assert ru.update_count == 1

    def test_reject_update(self) -> None:
        ru = RuleUpdater()
        p = ru.propose_update("r1", {"name": "X"})
        r = ru.reject_update(p["update_id"], "Not needed")
        assert r["rejected"] is True

    def test_apply_not_found(self) -> None:
        ru = RuleUpdater()
        r = ru.apply_update("nonexistent")
        assert r["error"] == "update_not_found"

    def test_analyze_impact_low(self) -> None:
        ru = RuleUpdater()
        r = ru.analyze_impact("r1", {"description": "Updated"})
        assert r["risk_level"] == "low"
        assert r["requires_review"] is False

    def test_analyze_impact_medium(self) -> None:
        ru = RuleUpdater()
        r = ru.analyze_impact("r1", {"severity": "critical"})
        assert r["risk_level"] == "medium"

    def test_analyze_impact_high(self) -> None:
        ru = RuleUpdater()
        r = ru.analyze_impact("r1", {"conditions": {"blocked": ["x"]}})
        assert r["risk_level"] == "high"
        assert r["requires_review"] is True

    def test_notify_change(self) -> None:
        ru = RuleUpdater()
        r = ru.notify_change("r1", "updated", "Severity changed")
        assert r["notified"] is True
        assert ru.notification_count == 1

    def test_get_pending_updates(self) -> None:
        ru = RuleUpdater()
        ru.propose_update("r1", {"name": "A"})
        ru.propose_update("r2", {"name": "B"})
        pending = ru.get_pending_updates()
        assert len(pending) == 2

    def test_get_update_log(self) -> None:
        ru = RuleUpdater()
        p = ru.propose_update("r1", {"x": 1})
        ru.apply_update(p["update_id"])
        log = ru.get_update_log()
        assert len(log) == 1


# ── ExceptionHandler Testleri ────────────────


class TestExceptionHandler:
    """RegulatoryExceptionHandler testleri."""

    def test_request_exception(self) -> None:
        eh = RegulatoryExceptionHandler()
        r = eh.request_exception("r1", "Emergency")
        assert r["status"] == "requested"
        assert eh.exception_count == 1

    def test_request_auto_approved(self) -> None:
        eh = RegulatoryExceptionHandler(approval_required=False)
        r = eh.request_exception("r1", "Need it")
        assert r["auto_approved"] is True
        assert r["status"] == "approved"

    def test_approve_exception(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "Emergency")
        r = eh.approve_exception(req["exception_id"])
        assert r["approved"] is True
        assert eh.approved_count == 1

    def test_deny_exception(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "Test")
        r = eh.deny_exception(req["exception_id"], "Not valid")
        assert r["denied"] is True

    def test_approve_not_found(self) -> None:
        eh = RegulatoryExceptionHandler()
        r = eh.approve_exception("nonexistent")
        assert r["error"] == "exception_not_found"

    def test_approve_wrong_status(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "Test")
        eh.approve_exception(req["exception_id"])
        r = eh.approve_exception(req["exception_id"])
        assert r["error"] == "invalid_status"

    def test_revoke_exception(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "Test")
        eh.approve_exception(req["exception_id"])
        r = eh.revoke_exception(req["exception_id"])
        assert r["revoked"] is True

    def test_check_exception_active(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "Test", duration_hours=1)
        eh.approve_exception(req["exception_id"])
        r = eh.check_exception("r1")
        assert r["has_exception"] is True

    def test_check_exception_none(self) -> None:
        eh = RegulatoryExceptionHandler()
        r = eh.check_exception("r1")
        assert r["has_exception"] is False

    def test_cleanup_expired(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "Test", duration_hours=0)
        eh.approve_exception(req["exception_id"])
        # Force expiry
        eh._exceptions[req["exception_id"]]["expires_at"] = time.time() - 1
        r = eh.cleanup_expired()
        assert r["expired_count"] == 1

    def test_audit_trail(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "Test")
        eh.approve_exception(req["exception_id"])
        trail = eh.get_audit_trail(req["exception_id"])
        assert len(trail) == 2
        assert trail[0]["action"] == "requested"
        assert trail[1]["action"] == "approved"

    def test_active_exception_count(self) -> None:
        eh = RegulatoryExceptionHandler()
        req = eh.request_exception("r1", "A", duration_hours=24)
        eh.approve_exception(req["exception_id"])
        assert eh.active_exception_count == 1


# ── ComplianceReporter Testleri ──────────────


class TestComplianceReporter:
    """RegulatoryComplianceReporter testleri."""

    def test_compliance_report(self) -> None:
        cr = RegulatoryComplianceReporter()
        checks = [
            {"compliant": True},
            {"compliant": True},
            {"compliant": False},
        ]
        r = cr.generate_compliance_report(checks, [])
        assert r["total_checks"] == 3
        assert r["passed"] == 2
        assert r["compliance_rate"] > 0.6
        assert cr.report_count == 1

    def test_violation_report(self) -> None:
        cr = RegulatoryComplianceReporter()
        violations = [
            {"severity": "critical", "rule_id": "r1"},
            {"severity": "low", "rule_id": "r1"},
            {"severity": "medium", "rule_id": "r2"},
        ]
        r = cr.generate_violation_report(violations)
        assert r["total_violations"] == 3
        assert r["severity_distribution"]["critical"] == 1
        assert len(r["top_violated_rules"]) == 2

    def test_analyze_trends_stable(self) -> None:
        cr = RegulatoryComplianceReporter()
        now = time.time()
        violations = [
            {"timestamp": now - 20 * 86400},
            {"timestamp": now - 10 * 86400},
        ]
        r = cr.analyze_trends(violations, period_days=30)
        assert r["trend"] in ("stable", "increasing", "decreasing")

    def test_analyze_trends_increasing(self) -> None:
        cr = RegulatoryComplianceReporter()
        now = time.time()
        violations = [
            {"timestamp": now - 5 * 86400},
            {"timestamp": now - 4 * 86400},
            {"timestamp": now - 3 * 86400},
        ]
        r = cr.analyze_trends(violations, period_days=30)
        assert r["total_violations"] == 3

    def test_audit_report(self) -> None:
        cr = RegulatoryComplianceReporter()
        checks = [{"compliant": True}]
        violations = [{"severity": "low"}]
        exceptions = [{"status": "approved"}]
        r = cr.generate_audit_report(checks, violations, exceptions)
        assert r["report_type"] == "audit"
        assert r["active_exceptions"] == 1

    def test_export_report(self) -> None:
        cr = RegulatoryComplianceReporter()
        r = cr.generate_compliance_report([], [])
        exp = cr.export_report(r["report_id"])
        assert exp["exported"] is True

    def test_export_not_found(self) -> None:
        cr = RegulatoryComplianceReporter()
        r = cr.export_report("nonexistent")
        assert r["error"] == "report_not_found"

    def test_get_reports_by_type(self) -> None:
        cr = RegulatoryComplianceReporter()
        cr.generate_compliance_report([], [])
        cr.generate_violation_report([])
        cr.generate_compliance_report([], [])
        result = cr.get_reports(report_type="compliance")
        assert len(result) == 2


# ── RegulatoryOrchestrator Testleri ──────────


class TestRegulatoryOrchestrator:
    """RegulatoryOrchestrator testleri."""

    def test_check_decision_allowed(self) -> None:
        orch = RegulatoryOrchestrator()
        r = orch.check_decision("read", {})
        assert r["allowed"] is True
        assert orch.decisions_checked == 1

    def test_check_decision_blocked(self) -> None:
        orch = RegulatoryOrchestrator(strict_mode=True)
        orch.add_rule(
            "No Delete", "privacy",
            severity="critical",
            conditions={"blocked_actions": ["delete"]},
        )
        r = orch.check_decision("delete", {})
        assert r["allowed"] is False

    def test_non_strict_allows_soft_violations(self) -> None:
        orch = RegulatoryOrchestrator(strict_mode=False)
        orch.add_rule(
            "Prefer Email", "operational",
            severity="low",
            conditions={"blocked_actions": ["sms"]},
        )
        r = orch.check_decision("sms", {})
        assert r["compliant"] is False
        assert r["allowed"] is True  # Low severity → allowed in non-strict

    def test_strict_blocks_all_violations(self) -> None:
        orch = RegulatoryOrchestrator(strict_mode=True)
        orch.add_rule(
            "Low Rule", "operational",
            severity="low",
            conditions={"blocked_actions": ["sms"]},
        )
        r = orch.check_decision("sms", {})
        assert r["allowed"] is False

    def test_exception_bypasses_rule(self) -> None:
        orch = RegulatoryOrchestrator(strict_mode=True)
        rule = orch.add_rule(
            "No Delete", "privacy",
            severity="critical",
            conditions={"blocked_actions": ["delete"]},
        )
        exc = orch.exceptions.request_exception(
            rule["rule_id"], "Emergency",
        )
        orch.exceptions.approve_exception(
            exc["exception_id"],
        )
        r = orch.check_decision("delete", {})
        assert r["allowed"] is True

    def test_add_rule(self) -> None:
        orch = RegulatoryOrchestrator()
        r = orch.add_rule("Test", "legal")
        assert r["created"] is True

    def test_get_compliance_report(self) -> None:
        orch = RegulatoryOrchestrator()
        orch.check_decision("a", {})
        orch.check_decision("b", {})
        r = orch.get_compliance_report()
        assert r["total_checks"] == 2
        assert r["compliance_rate"] == 1.0

    def test_get_analytics(self) -> None:
        orch = RegulatoryOrchestrator()
        orch.add_rule("R1")
        orch.add_rule("R2")
        orch.check_decision("test", {})
        a = orch.get_analytics()
        assert a["total_rules"] == 2
        assert a["total_checks"] == 1
        assert a["decisions_checked"] == 1

    def test_get_status(self) -> None:
        orch = RegulatoryOrchestrator()
        orch.add_rule("X")
        s = orch.get_status()
        assert s["total_rules"] == 1

    def test_full_pipeline(self) -> None:
        """Tam pipeline testi."""
        orch = RegulatoryOrchestrator(strict_mode=True)

        # Kurallar ekle
        r1 = orch.add_rule(
            "Budget Limit", "financial",
            severity="high",
            conditions={"limits": {"amount": {"max": 10000}}},
        )
        r2 = orch.add_rule(
            "Auth Required", "privacy",
            severity="critical",
            conditions={"required_fields": ["auth_token"]},
        )

        # Kısıt ekle
        orch.constraints.define_hard_constraint(
            "Max Budget", "amount<=10000",
        )

        # İzin verilen aksiyon
        ok = orch.check_decision(
            "purchase",
            {"amount": 5000, "auth_token": "abc"},
        )
        assert ok["allowed"] is True

        # Bütçe aşımı
        fail = orch.check_decision(
            "purchase",
            {"amount": 15000, "auth_token": "abc"},
        )
        assert fail["allowed"] is False
        assert fail["violation_count"] >= 1

        # Auth eksik
        fail2 = orch.check_decision(
            "purchase", {"amount": 100},
        )
        assert fail2["allowed"] is False

        # Analytics
        a = orch.get_analytics()
        assert a["total_rules"] == 2
        assert a["total_checks"] == 3
        assert a["total_violations"] > 0

        # Report
        r = orch.get_compliance_report()
        assert r["compliance_rate"] < 1.0


# ── Init ve Config Testleri ──────────────────


class TestRegulatoryInit:
    """Init import testleri."""

    def test_all_imports(self) -> None:
        from app.core.regulatory import (
            ConstraintDefiner,
            JurisdictionManager,
            RateLimitEnforcer,
            RegulatoryComplianceChecker,
            RegulatoryComplianceReporter,
            RegulatoryExceptionHandler,
            RegulatoryOrchestrator,
            RuleRepository,
            RuleUpdater,
        )
        assert RuleRepository is not None
        assert ConstraintDefiner is not None
        assert RegulatoryComplianceChecker is not None
        assert JurisdictionManager is not None
        assert RateLimitEnforcer is not None
        assert RuleUpdater is not None
        assert RegulatoryExceptionHandler is not None
        assert RegulatoryComplianceReporter is not None
        assert RegulatoryOrchestrator is not None


class TestRegulatoryConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import settings
        assert hasattr(settings, "regulatory_enabled")
        assert settings.regulatory_enabled is True
        assert settings.strict_mode is False
        assert settings.auto_update_rules is False
        assert settings.violation_alert is True
        assert settings.exception_approval_required is True
