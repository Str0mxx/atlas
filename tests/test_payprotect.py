"""
Payment & Financial Data Protector testleri.
"""

import pytest

from app.core.payprotect.card_tokenizer import (
    CardTokenizer,
)
from app.core.payprotect.chargeback_protector import (
    ChargebackProtector,
)
from app.core.payprotect.dual_approval_gate import (
    DualApprovalGate,
)
from app.core.payprotect.financial_data_isolator import (
    FinancialDataIsolator,
)
from app.core.payprotect.payment_anomaly_detector import (
    PaymentAnomalyDetector,
)
from app.core.payprotect.payprotect_orchestrator import (
    PayProtectOrchestrator,
)
from app.core.payprotect.pci_dss_enforcer import (
    PCIDSSEnforcer,
)
from app.core.payprotect.secure_payment_gateway import (
    SecurePaymentGateway,
)
from app.core.payprotect.transaction_limiter import (
    TransactionLimiter,
)


# ============================================================
# CardTokenizer Tests
# ============================================================
class TestCardTokenizer:
    """CardTokenizer testleri."""

    def setup_method(self) -> None:
        self.t = CardTokenizer()

    def test_init(self) -> None:
        assert self.t.token_count == 0
        assert len(self.t.CARD_TYPES) == 7

    def test_tokenize_valid(self) -> None:
        r = self.t.tokenize(
            card_number="4111111111111111",
            card_type="visa",
            holder_name="Test User",
            expiry_month=12,
            expiry_year=2030,
        )
        assert r["tokenized"] is True
        assert "token_id" in r
        assert r["last_four"] == "1111"
        assert r["card_type"] == "visa"
        assert "masked_pan" in r

    def test_tokenize_short_number(self) -> None:
        r = self.t.tokenize(
            card_number="1234",
        )
        assert r["tokenized"] is False

    def test_mask_pan(self) -> None:
        m = self.t._mask_pan(
            "4111111111111111"
        )
        assert m.startswith("4111")
        assert m.endswith("1111")
        assert "****" in m

    def test_mask_pan_short(self) -> None:
        m = self.t._mask_pan("1234")
        assert m == "****"

    def test_detokenize(self) -> None:
        r = self.t.tokenize(
            card_number="5500000000000004",
            card_type="mastercard",
            holder_name="MC User",
        )
        tid = r["token_id"]
        d = self.t.detokenize(
            token_id=tid,
        )
        assert d["found"] is True
        assert d["last_four"] == "0004"
        assert d["card_type"] == "mastercard"

    def test_detokenize_not_found(self) -> None:
        r = self.t.detokenize(
            token_id="nonexistent",
        )
        assert r["found"] is False

    def test_revoke_token(self) -> None:
        r = self.t.tokenize(
            card_number="4111111111111111",
        )
        tid = r["token_id"]
        rv = self.t.revoke_token(
            token_id=tid,
            reason="test",
        )
        assert rv["revoked"] is True

        # Detokenize fails for revoked
        d = self.t.detokenize(
            token_id=tid,
        )
        assert d["found"] is False

    def test_revoke_not_found(self) -> None:
        r = self.t.revoke_token(
            token_id="nonexistent",
        )
        assert r["revoked"] is False

    def test_get_token_info(self) -> None:
        r = self.t.tokenize(
            card_number="4111111111111111",
        )
        tid = r["token_id"]
        info = self.t.get_token_info(
            token_id=tid,
        )
        assert info["found"] is True
        assert info["status"] == "active"

    def test_get_token_info_not_found(self) -> None:
        r = self.t.get_token_info(
            token_id="nonexistent",
        )
        assert r["found"] is False

    def test_token_count(self) -> None:
        self.t.tokenize(
            card_number="4111111111111111",
        )
        self.t.tokenize(
            card_number="5500000000000004",
        )
        assert self.t.token_count == 2

    def test_get_summary(self) -> None:
        self.t.tokenize(
            card_number="4111111111111111",
            card_type="visa",
        )
        s = self.t.get_summary()
        assert s["retrieved"] is True
        assert s["total_tokens"] == 1
        assert "by_type" in s

    def test_usage_count_increments(self) -> None:
        r = self.t.tokenize(
            card_number="4111111111111111",
        )
        tid = r["token_id"]
        self.t.detokenize(token_id=tid)
        self.t.detokenize(token_id=tid)
        info = self.t.get_token_info(
            token_id=tid,
        )
        assert info["usage_count"] == 2


# ============================================================
# PCIDSSEnforcer Tests
# ============================================================
class TestPCIDSSEnforcer:
    """PCIDSSEnforcer testleri."""

    def setup_method(self) -> None:
        self.e = PCIDSSEnforcer()

    def test_init(self) -> None:
        assert self.e.violation_count == 0
        assert len(
            self.e.PCI_REQUIREMENTS
        ) == 12

    def test_default_rules(self) -> None:
        s = self.e.get_summary()
        assert s["total_rules"] == 4

    def test_add_rule(self) -> None:
        r = self.e.add_rule(
            name="test_rule",
            description="Test",
            requirement="req_1_firewall",
            severity="high",
        )
        assert r["created"] is True

    def test_check_data_storage_pan_unprotected(self) -> None:
        r = self.e.check_data_storage(
            data_type="pan",
            is_encrypted=False,
            is_tokenized=False,
            is_masked=False,
        )
        assert r["checked"] is True
        assert r["compliant"] is False
        assert r["violations"] > 0

    def test_check_data_storage_pan_encrypted(self) -> None:
        r = self.e.check_data_storage(
            data_type="pan",
            is_encrypted=True,
        )
        assert r["compliant"] is True

    def test_check_data_storage_cvv(self) -> None:
        r = self.e.check_data_storage(
            data_type="cvv",
        )
        assert r["compliant"] is False

    def test_check_data_storage_general(self) -> None:
        r = self.e.check_data_storage(
            data_type="address",
        )
        assert r["compliant"] is True

    def test_check_transmission_encrypted(self) -> None:
        r = self.e.check_transmission(
            protocol="https",
            is_encrypted=True,
            tls_version="1.3",
        )
        assert r["checked"] is True
        assert r["compliant"] is True

    def test_check_transmission_unencrypted(self) -> None:
        r = self.e.check_transmission(
            protocol="http",
            is_encrypted=False,
        )
        assert r["compliant"] is False

    def test_check_transmission_weak_tls(self) -> None:
        r = self.e.check_transmission(
            protocol="https",
            is_encrypted=True,
            tls_version="1.0",
        )
        assert r["violations"] > 0

    def test_check_access_control_compliant(self) -> None:
        r = self.e.check_access_control(
            user_id="u1",
            role="admin",
            has_mfa=True,
            access_logged=True,
        )
        assert r["compliant"] is True

    def test_check_access_control_no_mfa(self) -> None:
        r = self.e.check_access_control(
            user_id="u1",
            has_mfa=False,
            access_logged=True,
        )
        assert r["compliant"] is False

    def test_log_audit(self) -> None:
        r = self.e.log_audit(
            action="test",
            user_id="u1",
            detail="Test detail",
        )
        assert r["logged"] is True

    def test_run_compliance_scan(self) -> None:
        r = self.e.run_compliance_scan()
        assert r["scanned"] is True
        assert "requirements" in r
        assert r["total"] == 12

    def test_get_summary(self) -> None:
        s = self.e.get_summary()
        assert s["retrieved"] is True
        assert s["compliance_level"] == "level_1"


# ============================================================
# TransactionLimiter Tests
# ============================================================
class TestTransactionLimiter:
    """TransactionLimiter testleri."""

    def setup_method(self) -> None:
        self.l = TransactionLimiter()

    def test_init(self) -> None:
        assert self.l.alert_count == 0

    def test_create_limit(self) -> None:
        r = self.l.create_limit(
            name="single_max",
            limit_type="single_amount",
            max_value=5000.0,
        )
        assert r["created"] is True

    def test_create_limit_invalid_type(self) -> None:
        r = self.l.create_limit(
            name="bad",
            limit_type="invalid",
        )
        assert r["created"] is False

    def test_check_within_limit(self) -> None:
        self.l.create_limit(
            name="single",
            limit_type="single_amount",
            max_value=5000.0,
        )
        r = self.l.check_transaction(
            user_id="u1",
            amount=1000.0,
        )
        assert r["checked"] is True
        assert r["allowed"] is True

    def test_check_exceeds_limit(self) -> None:
        self.l.create_limit(
            name="single",
            limit_type="single_amount",
            max_value=5000.0,
        )
        r = self.l.check_transaction(
            user_id="u1",
            amount=6000.0,
        )
        assert r["allowed"] is False
        assert len(r["violations"]) > 0

    def test_daily_amount_limit(self) -> None:
        self.l.create_limit(
            name="daily",
            limit_type="daily_amount",
            max_value=10000.0,
        )
        self.l.check_transaction(
            user_id="u1",
            amount=6000.0,
        )
        r = self.l.check_transaction(
            user_id="u1",
            amount=5000.0,
        )
        assert r["allowed"] is False

    def test_daily_count_limit(self) -> None:
        self.l.create_limit(
            name="count",
            limit_type="daily_count",
            max_value=2,
        )
        self.l.check_transaction(
            user_id="u1",
            amount=100.0,
        )
        self.l.check_transaction(
            user_id="u1",
            amount=100.0,
        )
        r = self.l.check_transaction(
            user_id="u1",
            amount=100.0,
        )
        assert r["allowed"] is False

    def test_override_limit(self) -> None:
        r = self.l.override_limit(
            user_id="u1",
            amount=50000.0,
            reason="VIP musteri",
            approved_by="admin",
        )
        assert r["overridden"] is True

    def test_alert_count(self) -> None:
        self.l.create_limit(
            name="s",
            limit_type="single_amount",
            max_value=100.0,
        )
        self.l.check_transaction(
            user_id="u1",
            amount=500.0,
        )
        assert self.l.alert_count > 0

    def test_get_summary(self) -> None:
        s = self.l.get_summary()
        assert s["retrieved"] is True
        assert "stats" in s


# ============================================================
# PaymentAnomalyDetector Tests
# ============================================================
class TestPaymentAnomalyDetector:
    """PaymentAnomalyDetector testleri."""

    def setup_method(self) -> None:
        self.d = PaymentAnomalyDetector()

    def test_init(self) -> None:
        assert self.d.anomaly_count == 0

    def test_create_profile(self) -> None:
        r = self.d.create_profile(
            user_id="u1",
            avg_amount=500.0,
            avg_daily_count=3,
        )
        assert r["created"] is True

    def test_analyze_low_risk(self) -> None:
        r = self.d.analyze_transaction(
            user_id="u1",
            amount=100.0,
        )
        assert r["analyzed"] is True
        assert r["risk_level"] == "low"
        assert r["blocked"] is False

    def test_analyze_high_amount(self) -> None:
        r = self.d.analyze_transaction(
            user_id="u1",
            amount=10000.0,
        )
        assert r["analyzed"] is True
        assert len(r["flags"]) > 0

    def test_analyze_profile_deviation(self) -> None:
        self.d.create_profile(
            user_id="u1",
            avg_amount=100.0,
            common_merchants=["m1"],
            common_locations=["istanbul"],
        )
        r = self.d.analyze_transaction(
            user_id="u1",
            amount=500.0,
            merchant_id="m2",
            location="ankara",
        )
        assert r["analyzed"] is True
        assert r["risk_score"] > 0
        assert len(r["flags"]) >= 2

    def test_analyze_rapid_transactions(self) -> None:
        r = self.d.analyze_transaction(
            user_id="u1",
            amount=100.0,
            recent_count=10,
        )
        assert any(
            f["type"] == "rapid_transactions"
            for f in r["flags"]
        )

    def test_analyze_card_testing(self) -> None:
        r = self.d.analyze_transaction(
            user_id="u1",
            amount=0.50,
            recent_count=5,
        )
        assert any(
            f["type"] == "card_testing"
            for f in r["flags"]
        )

    def test_analyze_block(self) -> None:
        d = PaymentAnomalyDetector(
            block_threshold=0.3,
        )
        d.create_profile(
            user_id="u1",
            avg_amount=50.0,
            common_merchants=["m1"],
        )
        r = d.analyze_transaction(
            user_id="u1",
            amount=10000.0,
            merchant_id="m2",
            recent_count=10,
        )
        assert r["blocked"] is True

    def test_mark_false_positive(self) -> None:
        self.d.analyze_transaction(
            user_id="u1",
            amount=10000.0,
        )
        s = self.d.get_summary()
        anomalies = s["stats"][
            "anomalies_detected"
        ]
        assert anomalies > 0

    def test_mark_false_positive_not_found(self) -> None:
        r = self.d.mark_false_positive(
            anomaly_id="nonexistent",
        )
        assert r["marked"] is False

    def test_risk_levels(self) -> None:
        # Medium risk
        self.d.create_profile(
            user_id="u1",
            avg_amount=100.0,
        )
        r = self.d.analyze_transaction(
            user_id="u1",
            amount=10000.0,
        )
        assert r["risk_score"] > 0

    def test_get_summary(self) -> None:
        s = self.d.get_summary()
        assert s["retrieved"] is True
        assert "stats" in s


# ============================================================
# DualApprovalGate Tests
# ============================================================
class TestDualApprovalGate:
    """DualApprovalGate testleri."""

    def setup_method(self) -> None:
        self.g = DualApprovalGate(
            threshold=10000.0,
        )

    def test_init(self) -> None:
        assert self.g.pending_count == 0

    def test_requires_approval_below(self) -> None:
        assert self.g.requires_approval(
            amount=5000.0,
        ) is False

    def test_requires_approval_above(self) -> None:
        assert self.g.requires_approval(
            amount=15000.0,
        ) is True

    def test_requires_approval_high_risk(self) -> None:
        assert self.g.requires_approval(
            amount=100.0,
            request_type="data_export",
        ) is True

    def test_create_request(self) -> None:
        r = self.g.create_request(
            request_type="payment",
            amount=15000.0,
            requester_id="u1",
        )
        assert r["created"] is True
        assert r["required_approvals"] == 2

    def test_create_request_invalid_type(self) -> None:
        r = self.g.create_request(
            request_type="invalid",
        )
        assert r["created"] is False

    def test_approve_single(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            amount=15000.0,
            requester_id="u1",
        )
        rid = req["request_id"]
        r = self.g.approve(
            request_id=rid,
            approver_id="u2",
        )
        assert r["approved"] is True
        assert r["fully_approved"] is False

    def test_approve_dual(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            amount=15000.0,
            requester_id="u1",
        )
        rid = req["request_id"]
        self.g.approve(
            request_id=rid,
            approver_id="u2",
        )
        r = self.g.approve(
            request_id=rid,
            approver_id="u3",
        )
        assert r["fully_approved"] is True

    def test_approve_self_denied(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            requester_id="u1",
        )
        r = self.g.approve(
            request_id=req["request_id"],
            approver_id="u1",
        )
        assert r["approved"] is False

    def test_approve_duplicate_denied(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            requester_id="u1",
        )
        rid = req["request_id"]
        self.g.approve(
            request_id=rid,
            approver_id="u2",
        )
        r = self.g.approve(
            request_id=rid,
            approver_id="u2",
        )
        assert r["approved"] is False

    def test_reject(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            requester_id="u1",
        )
        r = self.g.reject(
            request_id=req["request_id"],
            rejector_id="u2",
            reason="Suspicious",
        )
        assert r["rejected"] is True

    def test_reject_not_found(self) -> None:
        r = self.g.reject(
            request_id="nonexistent",
        )
        assert r["rejected"] is False

    def test_override(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            requester_id="u1",
        )
        r = self.g.override(
            request_id=req["request_id"],
            overrider_id="admin",
            reason="Acil",
            authority_level="admin",
        )
        assert r["overridden"] is True

    def test_override_insufficient(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            requester_id="u1",
        )
        r = self.g.override(
            request_id=req["request_id"],
            overrider_id="user",
            authority_level="basic",
        )
        assert r["overridden"] is False

    def test_expire_pending(self) -> None:
        self.g.create_request(
            request_type="payment",
            requester_id="u1",
        )
        self.g.create_request(
            request_type="refund",
            requester_id="u2",
        )
        r = self.g.expire_pending()
        assert r["processed"] is True
        assert r["expired_count"] == 2

    def test_get_request(self) -> None:
        req = self.g.create_request(
            request_type="payment",
            requester_id="u1",
        )
        r = self.g.get_request(
            request_id=req["request_id"],
        )
        assert r["found"] is True

    def test_get_request_not_found(self) -> None:
        r = self.g.get_request(
            request_id="nonexistent",
        )
        assert r["found"] is False

    def test_get_summary(self) -> None:
        s = self.g.get_summary()
        assert s["retrieved"] is True
        assert s["threshold"] == 10000.0


# ============================================================
# FinancialDataIsolator Tests
# ============================================================
class TestFinancialDataIsolator:
    """FinancialDataIsolator testleri."""

    def setup_method(self) -> None:
        self.i = FinancialDataIsolator()

    def test_init(self) -> None:
        assert self.i.zone_count == 4

    def test_default_zones(self) -> None:
        s = self.i.get_summary()
        assert s["total_zones"] == 4

    def test_create_zone(self) -> None:
        r = self.i.create_zone(
            name="custom_zone",
            zone_type="financial",
            encryption="aes256",
        )
        assert r["created"] is True

    def test_create_zone_invalid_type(self) -> None:
        r = self.i.create_zone(
            name="bad",
            zone_type="invalid",
        )
        assert r["created"] is False

    def test_create_access_rule(self) -> None:
        r = self.i.create_access_rule(
            name="admin_read",
            zone_name="pci_zone",
            role="admin",
            data_class="card_data",
            can_read=True,
        )
        assert r["created"] is True

    def test_check_access_granted(self) -> None:
        self.i.create_access_rule(
            name="admin_read",
            zone_name="pci_zone",
            role="admin",
            data_class="card_data",
            can_read=True,
        )
        r = self.i.check_access(
            user_id="u1",
            role="admin",
            zone_name="pci_zone",
            data_class="card_data",
            operation="read",
        )
        assert r["checked"] is True
        assert r["allowed"] is True

    def test_check_access_denied(self) -> None:
        r = self.i.check_access(
            user_id="u1",
            role="viewer",
            zone_name="pci_zone",
            data_class="card_data",
            operation="read",
        )
        assert r["allowed"] is False

    def test_check_access_zone_not_found(self) -> None:
        r = self.i.check_access(
            zone_name="nonexistent",
        )
        assert r["allowed"] is False

    def test_check_access_write(self) -> None:
        self.i.create_access_rule(
            name="admin_write",
            zone_name="financial_zone",
            role="admin",
            data_class="transaction",
            can_write=True,
        )
        r = self.i.check_access(
            user_id="u1",
            role="admin",
            zone_name="financial_zone",
            data_class="transaction",
            operation="write",
        )
        assert r["allowed"] is True

    def test_encrypt_data(self) -> None:
        r = self.i.encrypt_data(
            data_id="d1",
            data_class="card_data",
            zone_name="pci_zone",
        )
        assert r["encrypted"] is True
        assert r["algorithm"] == "aes256"

    def test_encrypt_data_general_zone(self) -> None:
        r = self.i.encrypt_data(
            data_id="d2",
            zone_name="general_zone",
        )
        assert r["encrypted"] is True
        assert r["algorithm"] == "none"

    def test_get_zone_info(self) -> None:
        r = self.i.get_zone_info(
            zone_name="pci_zone",
        )
        assert r["found"] is True
        assert r["zone_type"] == "pci"

    def test_get_zone_info_not_found(self) -> None:
        r = self.i.get_zone_info(
            zone_name="nonexistent",
        )
        assert r["found"] is False

    def test_get_summary(self) -> None:
        s = self.i.get_summary()
        assert s["retrieved"] is True
        assert s["active_zones"] == 4


# ============================================================
# SecurePaymentGateway Tests
# ============================================================
class TestSecurePaymentGateway:
    """SecurePaymentGateway testleri."""

    def setup_method(self) -> None:
        self.gw = SecurePaymentGateway()

    def test_init(self) -> None:
        assert self.gw.transaction_count == 0

    def test_register_gateway(self) -> None:
        r = self.gw.register_gateway(
            name="stripe",
            gateway_type="stripe",
            api_endpoint="https://api.stripe.com",
        )
        assert r["registered"] is True

    def test_process_payment(self) -> None:
        self.gw.register_gateway(
            name="stripe",
            gateway_type="stripe",
        )
        r = self.gw.process_payment(
            amount=1000.0,
            currency="TRY",
            token_id="tok_123",
            merchant_id="m1",
            gateway_name="stripe",
        )
        assert r["processed"] is True
        assert r["status"] == "completed"

    def test_process_payment_auto_select(self) -> None:
        self.gw.register_gateway(
            name="gw1",
            priority=1,
        )
        r = self.gw.process_payment(
            amount=500.0,
        )
        assert r["processed"] is True

    def test_process_payment_no_gateway(self) -> None:
        r = self.gw.process_payment(
            amount=500.0,
        )
        assert r["processed"] is False

    def test_retry_payment(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        r = self.gw.process_payment(
            amount=100.0,
            gateway_name="gw1",
        )
        tid = r["transaction_id"]
        # Mark as failed to test retry
        self.gw._transactions[tid][
            "status"
        ] = "failed"
        ret = self.gw.retry_payment(
            transaction_id=tid,
        )
        assert ret["retried"] is True

    def test_retry_not_failed(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        r = self.gw.process_payment(
            amount=100.0,
            gateway_name="gw1",
        )
        ret = self.gw.retry_payment(
            transaction_id=r[
                "transaction_id"
            ],
        )
        assert ret["retried"] is False

    def test_retry_not_found(self) -> None:
        r = self.gw.retry_payment(
            transaction_id="nonexistent",
        )
        assert r["retried"] is False

    def test_refund_payment(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        r = self.gw.process_payment(
            amount=1000.0,
            gateway_name="gw1",
        )
        ref = self.gw.refund_payment(
            transaction_id=r[
                "transaction_id"
            ],
            reason="Customer request",
        )
        assert ref["refunded"] is True
        assert ref["refund_amount"] == 1000.0

    def test_refund_partial(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        r = self.gw.process_payment(
            amount=1000.0,
            gateway_name="gw1",
        )
        ref = self.gw.refund_payment(
            transaction_id=r[
                "transaction_id"
            ],
            amount=500.0,
        )
        assert ref["refund_amount"] == 500.0

    def test_refund_not_completed(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        r = self.gw.process_payment(
            amount=100.0,
            gateway_name="gw1",
        )
        tid = r["transaction_id"]
        self.gw._transactions[tid][
            "status"
        ] = "failed"
        ref = self.gw.refund_payment(
            transaction_id=tid,
        )
        assert ref["refunded"] is False

    def test_reconcile_matched(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        self.gw.process_payment(
            amount=1000.0,
            gateway_name="gw1",
        )
        self.gw.process_payment(
            amount=2000.0,
            gateway_name="gw1",
        )
        r = self.gw.reconcile(
            gateway_name="gw1",
            expected_total=3000.0,
        )
        assert r["reconciled"] is True
        assert r["matched"] is True

    def test_reconcile_mismatched(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        self.gw.process_payment(
            amount=1000.0,
            gateway_name="gw1",
        )
        r = self.gw.reconcile(
            gateway_name="gw1",
            expected_total=2000.0,
        )
        assert r["matched"] is False

    def test_get_transaction(self) -> None:
        self.gw.register_gateway(
            name="gw1",
        )
        r = self.gw.process_payment(
            amount=100.0,
            gateway_name="gw1",
        )
        tx = self.gw.get_transaction(
            transaction_id=r[
                "transaction_id"
            ],
        )
        assert tx["found"] is True

    def test_get_transaction_not_found(self) -> None:
        r = self.gw.get_transaction(
            transaction_id="nonexistent",
        )
        assert r["found"] is False

    def test_get_summary(self) -> None:
        s = self.gw.get_summary()
        assert s["retrieved"] is True


# ============================================================
# ChargebackProtector Tests
# ============================================================
class TestChargebackProtector:
    """ChargebackProtector testleri."""

    def setup_method(self) -> None:
        self.c = ChargebackProtector()

    def test_init(self) -> None:
        assert self.c.dispute_count == 0

    def test_open_dispute(self) -> None:
        r = self.c.open_dispute(
            transaction_id="tx_123",
            amount=1000.0,
            reason="fraud",
            customer_id="c1",
            merchant_id="m1",
        )
        assert r["opened"] is True
        assert r["status"] == "opened"

    def test_collect_evidence(self) -> None:
        d = self.c.open_dispute(
            transaction_id="tx_123",
            amount=500.0,
        )
        r = self.c.collect_evidence(
            dispute_id=d["dispute_id"],
            evidence_type="receipt",
            content="Fatura #123",
            source="system",
        )
        assert r["collected"] is True

    def test_collect_evidence_not_found(self) -> None:
        r = self.c.collect_evidence(
            dispute_id="nonexistent",
        )
        assert r["collected"] is False

    def test_submit_evidence(self) -> None:
        d = self.c.open_dispute(
            transaction_id="tx_123",
        )
        did = d["dispute_id"]
        self.c.collect_evidence(
            dispute_id=did,
            evidence_type="receipt",
            content="Test",
        )
        r = self.c.submit_evidence(
            dispute_id=did,
        )
        assert r["submitted"] is True
        assert r["evidence_count"] == 1

    def test_submit_no_evidence(self) -> None:
        d = self.c.open_dispute(
            transaction_id="tx_123",
        )
        r = self.c.submit_evidence(
            dispute_id=d["dispute_id"],
        )
        assert r["submitted"] is False

    def test_resolve_dispute_won(self) -> None:
        d = self.c.open_dispute(
            transaction_id="tx_123",
        )
        r = self.c.resolve_dispute(
            dispute_id=d["dispute_id"],
            outcome="won",
        )
        assert r["resolved"] is True
        assert r["outcome"] == "won"

    def test_resolve_dispute_lost(self) -> None:
        d = self.c.open_dispute(
            transaction_id="tx_123",
        )
        r = self.c.resolve_dispute(
            dispute_id=d["dispute_id"],
            outcome="lost",
        )
        assert r["outcome"] == "lost"

    def test_resolve_not_found(self) -> None:
        r = self.c.resolve_dispute(
            dispute_id="nonexistent",
        )
        assert r["resolved"] is False

    def test_assess_risk_low(self) -> None:
        r = self.c.assess_risk(
            merchant_id="m1",
            total_transactions=1000,
            total_disputes=5,
            total_amount=100000.0,
            dispute_amount=500.0,
        )
        assert r["assessed"] is True
        assert r["risk_level"] == "low"

    def test_assess_risk_high(self) -> None:
        r = self.c.assess_risk(
            merchant_id="m2",
            total_transactions=100,
            total_disputes=10,
            total_amount=10000.0,
            dispute_amount=5000.0,
        )
        assert r["risk_score"] > 0

    def test_assess_risk_zero_transactions(self) -> None:
        r = self.c.assess_risk(
            merchant_id="m3",
            total_transactions=0,
            total_disputes=0,
        )
        assert r["assessed"] is True
        assert r["risk_score"] == 0.0

    def test_dispute_count(self) -> None:
        self.c.open_dispute(
            transaction_id="tx_1",
        )
        self.c.open_dispute(
            transaction_id="tx_2",
        )
        assert self.c.dispute_count == 2

    def test_get_analytics(self) -> None:
        self.c.open_dispute(
            transaction_id="tx_1",
            amount=500.0,
        )
        d = self.c.open_dispute(
            transaction_id="tx_2",
            amount=300.0,
        )
        self.c.resolve_dispute(
            dispute_id=d["dispute_id"],
            outcome="won",
        )
        a = self.c.get_analytics()
        assert a["analytics"] is True
        assert a["total_disputes"] == 2
        assert a["won"] == 1

    def test_get_summary(self) -> None:
        s = self.c.get_summary()
        assert s["retrieved"] is True


# ============================================================
# PayProtectOrchestrator Tests
# ============================================================
class TestPayProtectOrchestrator:
    """PayProtectOrchestrator testleri."""

    def setup_method(self) -> None:
        self.o = PayProtectOrchestrator(
            block_threshold=0.8,
            dual_approval_threshold=10000.0,
        )

    def test_init(self) -> None:
        s = self.o.get_summary()
        assert s["retrieved"] is True

    def test_tokenize_card(self) -> None:
        r = self.o.tokenize_card(
            card_number="4111111111111111",
            card_type="visa",
            holder_name="Test",
            expiry_month=12,
            expiry_year=2030,
            merchant_id="m1",
        )
        assert r["tokenized"] is True

    def test_tokenize_card_short(self) -> None:
        r = self.o.tokenize_card(
            card_number="1234",
        )
        assert r["tokenized"] is False

    def test_process_payment_success(self) -> None:
        self.o.gateway.register_gateway(
            name="gw1",
            priority=1,
        )
        r = self.o.process_payment(
            user_id="u1",
            amount=500.0,
            token_id="tok_1",
            merchant_id="m1",
        )
        assert r["processed"] is True

    def test_process_payment_limit_blocked(self) -> None:
        self.o.limiter.create_limit(
            name="single",
            limit_type="single_amount",
            max_value=100.0,
        )
        r = self.o.process_payment(
            user_id="u1",
            amount=500.0,
        )
        assert r["processed"] is False
        assert r["reason"] == "limit_exceeded"

    def test_process_payment_anomaly_blocked(self) -> None:
        self.o.anomaly = (
            PaymentAnomalyDetector(
                block_threshold=0.1,
            )
        )
        self.o.anomaly.create_profile(
            user_id="u1",
            avg_amount=50.0,
            common_merchants=["m1"],
        )
        r = self.o.process_payment(
            user_id="u1",
            amount=10000.0,
            merchant_id="m2",
        )
        assert r["processed"] is False
        assert r["reason"] == "anomaly_blocked"

    def test_process_payment_needs_approval(self) -> None:
        self.o.gateway.register_gateway(
            name="gw1",
            priority=1,
        )
        r = self.o.process_payment(
            user_id="u1",
            amount=50000.0,
        )
        assert r["processed"] is False
        assert r["reason"] == "approval_required"

    def test_handle_chargeback(self) -> None:
        r = self.o.handle_chargeback(
            transaction_id="tx_1",
            amount=500.0,
            reason="fraud",
            customer_id="c1",
            merchant_id="m1",
        )
        assert r["opened"] is True

    def test_run_compliance_check(self) -> None:
        r = self.o.run_compliance_check()
        assert r["scanned"] is True

    def test_get_analytics(self) -> None:
        a = self.o.get_analytics()
        assert a["analytics"] is True
        assert "tokenizer" in a
        assert "pci" in a
        assert "gateway" in a

    def test_get_summary(self) -> None:
        s = self.o.get_summary()
        assert s["retrieved"] is True
        assert "active_tokens" in s
        assert "pci_violations" in s

    def test_full_pipeline(self) -> None:
        # Tokenize
        tok = self.o.tokenize_card(
            card_number="4111111111111111",
            card_type="visa",
            holder_name="Test User",
        )
        assert tok["tokenized"] is True

        # Register gateway
        self.o.gateway.register_gateway(
            name="gw1",
            priority=1,
        )

        # Process payment
        pay = self.o.process_payment(
            user_id="u1",
            amount=500.0,
            token_id=tok["token_id"],
            merchant_id="m1",
        )
        assert pay["processed"] is True

        # Summary
        s = self.o.get_summary()
        assert s["active_tokens"] >= 1
        assert s["transactions"] >= 1


# ============================================================
# PayProtect Models Tests
# ============================================================
class TestPayProtectModels:
    """PayProtect model testleri."""

    def test_card_type_enum(self) -> None:
        from app.models.payprotect_models import (
            CardType,
        )
        assert CardType.VISA == "visa"
        assert len(CardType) == 7

    def test_token_status_enum(self) -> None:
        from app.models.payprotect_models import (
            TokenStatus,
        )
        assert TokenStatus.ACTIVE == "active"

    def test_compliance_level_enum(self) -> None:
        from app.models.payprotect_models import (
            ComplianceLevel,
        )
        assert (
            ComplianceLevel.LEVEL_1
            == "level_1"
        )

    def test_limit_type_enum(self) -> None:
        from app.models.payprotect_models import (
            LimitType,
        )
        assert len(LimitType) == 6

    def test_risk_level_enum(self) -> None:
        from app.models.payprotect_models import (
            RiskLevel,
        )
        assert RiskLevel.CRITICAL == "critical"

    def test_approval_status_enum(self) -> None:
        from app.models.payprotect_models import (
            ApprovalStatus,
        )
        assert (
            ApprovalStatus.PENDING
            == "pending"
        )

    def test_dispute_status_enum(self) -> None:
        from app.models.payprotect_models import (
            DisputeStatus,
        )
        assert DisputeStatus.WON == "won"

    def test_transaction_status_enum(self) -> None:
        from app.models.payprotect_models import (
            TransactionStatus,
        )
        assert (
            TransactionStatus.COMPLETED
            == "completed"
        )

    def test_token_record(self) -> None:
        from app.models.payprotect_models import (
            TokenRecord,
        )
        r = TokenRecord(
            token_id="tok_1",
            masked_pan="4111****1111",
            last_four="1111",
        )
        assert r.token_id == "tok_1"

    def test_compliance_check(self) -> None:
        from app.models.payprotect_models import (
            ComplianceCheck,
        )
        c = ComplianceCheck(
            data_type="pan",
            is_encrypted=True,
            compliant=True,
        )
        assert c.compliant is True

    def test_transaction_limit(self) -> None:
        from app.models.payprotect_models import (
            TransactionLimit,
        )
        l = TransactionLimit(
            name="daily",
            max_value=10000.0,
        )
        assert l.max_value == 10000.0

    def test_anomaly_record(self) -> None:
        from app.models.payprotect_models import (
            AnomalyRecord,
        )
        a = AnomalyRecord(
            anomaly_id="an_1",
            risk_score=0.7,
        )
        assert a.risk_score == 0.7

    def test_approval_request(self) -> None:
        from app.models.payprotect_models import (
            ApprovalRequest,
        )
        r = ApprovalRequest(
            request_id="req_1",
            amount=15000.0,
        )
        assert r.required_approvals == 2

    def test_dispute_record(self) -> None:
        from app.models.payprotect_models import (
            DisputeRecord,
        )
        d = DisputeRecord(
            dispute_id="dp_1",
            amount=500.0,
        )
        assert d.reason == "other"

    def test_payment_transaction(self) -> None:
        from app.models.payprotect_models import (
            PaymentTransaction,
        )
        t = PaymentTransaction(
            transaction_id="tx_1",
            amount=1000.0,
        )
        assert t.currency == "TRY"

    def test_payprotect_status(self) -> None:
        from app.models.payprotect_models import (
            PayProtectStatus,
        )
        s = PayProtectStatus(
            active_tokens=5,
            transactions=10,
        )
        assert s.active_tokens == 5


# ============================================================
# Config Tests
# ============================================================
class TestPayProtectConfig:
    """PayProtect config testleri."""

    def test_payprotect_settings(self) -> None:
        from app.config import settings
        assert hasattr(
            settings, "payprotect_enabled"
        )
        assert hasattr(
            settings, "pci_dss_mode"
        )
        assert hasattr(
            settings,
            "dual_approval_threshold",
        )
        assert hasattr(
            settings, "anomaly_detection"
        )
        assert hasattr(
            settings,
            "chargeback_protection",
        )

    def test_payprotect_defaults(self) -> None:
        from app.config import settings
        assert (
            settings.payprotect_enabled
            is True
        )
        assert (
            settings.pci_dss_mode is True
        )
        assert (
            settings
            .dual_approval_threshold
            == 10000.0
        )
        assert (
            settings.anomaly_detection
            is True
        )
        assert (
            settings.chargeback_protection
            is True
        )
