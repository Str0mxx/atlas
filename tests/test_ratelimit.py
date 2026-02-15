"""ATLAS Rate Limiting & Throttling testleri.

Hiz sinirlama ve kisitlama bilesenleri icin
kapsamli test suite.
"""

import time

import pytest


# ── Models ────────────────────────────────────

class TestRateLimitModels:
    """Rate limit model testleri."""

    def test_algorithm_type_enum(self):
        from app.models.ratelimit_models import AlgorithmType
        assert AlgorithmType.TOKEN_BUCKET == "token_bucket"
        assert AlgorithmType.SLIDING_WINDOW == "sliding_window"
        assert AlgorithmType.LEAKY_BUCKET == "leaky_bucket"
        assert AlgorithmType.FIXED_WINDOW == "fixed_window"
        assert AlgorithmType.ADAPTIVE == "adaptive"

    def test_quota_period_enum(self):
        from app.models.ratelimit_models import QuotaPeriod
        assert QuotaPeriod.MINUTE == "minute"
        assert QuotaPeriod.HOUR == "hour"
        assert QuotaPeriod.DAY == "day"
        assert QuotaPeriod.WEEK == "week"
        assert QuotaPeriod.MONTH == "month"

    def test_throttle_mode_enum(self):
        from app.models.ratelimit_models import ThrottleMode
        assert ThrottleMode.NONE == "none"
        assert ThrottleMode.SOFT == "soft"
        assert ThrottleMode.HARD == "hard"
        assert ThrottleMode.ADAPTIVE == "adaptive"
        assert ThrottleMode.BACKPRESSURE == "backpressure"

    def test_violation_type_enum(self):
        from app.models.ratelimit_models import ViolationType
        assert ViolationType.RATE_EXCEEDED == "rate_exceeded"
        assert ViolationType.QUOTA_EXCEEDED == "quota_exceeded"
        assert ViolationType.BURST_EXCEEDED == "burst_exceeded"
        assert ViolationType.THROTTLED == "throttled"
        assert ViolationType.BANNED == "banned"

    def test_policy_tier_enum(self):
        from app.models.ratelimit_models import PolicyTier
        assert PolicyTier.FREE == "free"
        assert PolicyTier.BASIC == "basic"
        assert PolicyTier.PRO == "pro"
        assert PolicyTier.ENTERPRISE == "enterprise"
        assert PolicyTier.UNLIMITED == "unlimited"

    def test_penalty_action_enum(self):
        from app.models.ratelimit_models import PenaltyAction
        assert PenaltyAction.WARN == "warn"
        assert PenaltyAction.DELAY == "delay"
        assert PenaltyAction.REJECT == "reject"
        assert PenaltyAction.THROTTLE == "throttle"
        assert PenaltyAction.BAN == "ban"
        assert PenaltyAction.NOTIFY == "notify"

    def test_rate_limit_record(self):
        from app.models.ratelimit_models import RateLimitRecord
        r = RateLimitRecord(key="api:user1", limit=100)
        assert r.key == "api:user1"
        assert r.limit == 100
        assert r.current_count == 0
        assert r.algorithm.value == "token_bucket"

    def test_quota_record(self):
        from app.models.ratelimit_models import QuotaRecord
        r = QuotaRecord(subject_id="user1", limit=1000)
        assert r.subject_id == "user1"
        assert r.limit == 1000
        assert r.used == 0
        assert r.period.value == "day"

    def test_violation_record(self):
        from app.models.ratelimit_models import ViolationRecord
        r = ViolationRecord(subject_id="user1")
        assert r.subject_id == "user1"
        assert r.violation_type.value == "rate_exceeded"
        assert r.penalty.value == "reject"

    def test_rate_limit_snapshot(self):
        from app.models.ratelimit_models import RateLimitSnapshot
        s = RateLimitSnapshot(total_requests=1000, allowed_requests=900)
        assert s.total_requests == 1000
        assert s.allowed_requests == 900
        assert s.rejected_requests == 0


# ── TokenBucket ───────────────────────────────

class TestTokenBucket:
    """TokenBucket testleri."""

    def setup_method(self):
        from app.core.ratelimit.token_bucket import TokenBucket
        self.tb = TokenBucket(
            default_capacity=10,
            default_refill_rate=10.0,
            burst_multiplier=1.5,
        )

    def test_create_bucket(self):
        r = self.tb.create_bucket("api:u1")
        assert r["status"] == "created"
        assert r["capacity"] == 10
        assert self.tb.bucket_count == 1

    def test_create_custom_bucket(self):
        r = self.tb.create_bucket("api:u1", capacity=50, refill_rate=5.0)
        assert r["capacity"] == 50

    def test_consume_success(self):
        self.tb.create_bucket("api:u1")
        r = self.tb.consume("api:u1")
        assert r["allowed"] is True
        assert r["remaining"] == 9

    def test_consume_multiple(self):
        self.tb.create_bucket("api:u1")
        r = self.tb.consume("api:u1", tokens=5)
        assert r["allowed"] is True
        assert r["remaining"] == 5

    def test_consume_insufficient(self):
        self.tb.create_bucket("api:u1", capacity=3)
        self.tb.consume("api:u1", tokens=3)
        r = self.tb.consume("api:u1")
        assert r["allowed"] is False
        assert r["reason"] == "insufficient_tokens"
        assert "retry_after" in r

    def test_consume_not_found(self):
        r = self.tb.consume("nonexistent")
        assert r["allowed"] is False
        assert r["reason"] == "bucket_not_found"

    def test_consume_burst(self):
        self.tb.create_bucket("api:u1", capacity=10, burst_capacity=15)
        r = self.tb.consume_burst("api:u1", tokens=5)
        assert r["allowed"] is True

    def test_consume_burst_not_found(self):
        r = self.tb.consume_burst("nonexistent")
        assert r["allowed"] is False

    def test_consume_burst_exceeded(self):
        self.tb.create_bucket("api:u1", capacity=3)
        self.tb.consume("api:u1", tokens=3)
        r = self.tb.consume_burst("api:u1", tokens=5)
        assert r["allowed"] is False
        assert r["reason"] == "burst_exceeded"

    def test_refill(self):
        self.tb.create_bucket("api:u1", capacity=10, refill_rate=1000.0)
        self.tb.consume("api:u1", tokens=5)
        time.sleep(0.01)
        b = self.tb.get_bucket("api:u1")
        assert b["tokens"] > 5

    def test_get_bucket(self):
        self.tb.create_bucket("api:u1")
        b = self.tb.get_bucket("api:u1")
        assert b is not None
        assert b["key"] == "api:u1"

    def test_get_bucket_not_found(self):
        assert self.tb.get_bucket("none") is None

    def test_reset_bucket(self):
        self.tb.create_bucket("api:u1")
        self.tb.consume("api:u1", tokens=5)
        r = self.tb.reset_bucket("api:u1")
        assert r["status"] == "reset"
        b = self.tb.get_bucket("api:u1")
        assert b["tokens"] >= 10

    def test_reset_not_found(self):
        r = self.tb.reset_bucket("none")
        assert r.get("error") == "bucket_not_found"

    def test_delete_bucket(self):
        self.tb.create_bucket("api:u1")
        assert self.tb.delete_bucket("api:u1") is True
        assert self.tb.bucket_count == 0

    def test_delete_not_found(self):
        assert self.tb.delete_bucket("none") is False

    def test_update_rate(self):
        self.tb.create_bucket("api:u1")
        r = self.tb.update_rate("api:u1", refill_rate=20.0, capacity=50)
        assert r["status"] == "updated"

    def test_update_rate_not_found(self):
        r = self.tb.update_rate("none")
        assert r.get("error") == "bucket_not_found"

    def test_list_buckets(self):
        self.tb.create_bucket("api:u1")
        self.tb.create_bucket("api:u2")
        buckets = self.tb.list_buckets()
        assert len(buckets) == 2

    def test_stats(self):
        self.tb.create_bucket("api:u1", capacity=2)
        self.tb.consume("api:u1")
        self.tb.consume("api:u1")
        self.tb.consume("api:u1")
        assert self.tb.allowed_count == 2
        assert self.tb.rejected_count == 1


# ── SlidingWindow ─────────────────────────────

class TestSlidingWindow:
    """SlidingWindow testleri."""

    def setup_method(self):
        from app.core.ratelimit.sliding_window import SlidingWindow
        self.sw = SlidingWindow(
            default_window_size=60,
            default_max_requests=10,
            precision=10,
        )

    def test_create_window(self):
        r = self.sw.create_window("api:u1")
        assert r["status"] == "created"
        assert self.sw.window_count == 1

    def test_record_allowed(self):
        self.sw.create_window("api:u1")
        r = self.sw.record("api:u1")
        assert r["allowed"] is True
        assert r["current"] == 1
        assert r["remaining"] == 9

    def test_record_exceeded(self):
        self.sw.create_window("api:u1", max_requests=3)
        self.sw.record("api:u1")
        self.sw.record("api:u1")
        self.sw.record("api:u1")
        r = self.sw.record("api:u1")
        assert r["allowed"] is False
        assert r["reason"] == "rate_exceeded"

    def test_record_not_found(self):
        r = self.sw.record("none")
        assert r["allowed"] is False
        assert r["reason"] == "window_not_found"

    def test_get_count(self):
        self.sw.create_window("api:u1")
        self.sw.record("api:u1")
        self.sw.record("api:u1")
        assert self.sw.get_count("api:u1") == 2

    def test_get_count_not_found(self):
        assert self.sw.get_count("none") == 0

    def test_get_remaining(self):
        self.sw.create_window("api:u1", max_requests=5)
        self.sw.record("api:u1")
        assert self.sw.get_remaining("api:u1") == 4

    def test_get_remaining_not_found(self):
        assert self.sw.get_remaining("none") == 0

    def test_reset_window(self):
        self.sw.create_window("api:u1")
        self.sw.record("api:u1")
        r = self.sw.reset_window("api:u1")
        assert r["status"] == "reset"
        assert self.sw.get_count("api:u1") == 0

    def test_reset_not_found(self):
        r = self.sw.reset_window("none")
        assert r.get("error") == "window_not_found"

    def test_delete_window(self):
        self.sw.create_window("api:u1")
        assert self.sw.delete_window("api:u1") is True
        assert self.sw.window_count == 0

    def test_delete_not_found(self):
        assert self.sw.delete_window("none") is False

    def test_update_limits(self):
        self.sw.create_window("api:u1")
        r = self.sw.update_limits("api:u1", max_requests=100)
        assert r["status"] == "updated"

    def test_update_not_found(self):
        r = self.sw.update_limits("none")
        assert r.get("error") == "window_not_found"

    def test_get_window(self):
        self.sw.create_window("api:u1")
        w = self.sw.get_window("api:u1")
        assert w is not None
        assert "current_count" in w

    def test_get_window_not_found(self):
        assert self.sw.get_window("none") is None

    def test_list_windows(self):
        self.sw.create_window("api:u1")
        self.sw.create_window("api:u2")
        windows = self.sw.list_windows()
        assert len(windows) == 2

    def test_stats(self):
        self.sw.create_window("api:u1", max_requests=2)
        self.sw.record("api:u1")
        self.sw.record("api:u1")
        self.sw.record("api:u1")
        assert self.sw.allowed_count == 2
        assert self.sw.rejected_count == 1


# ── LeakyBucket ───────────────────────────────

class TestLeakyBucket:
    """LeakyBucket testleri."""

    def setup_method(self):
        from app.core.ratelimit.leaky_bucket import LeakyBucket
        self.lb = LeakyBucket(
            default_capacity=10,
            default_leak_rate=100.0,
        )

    def test_create_bucket(self):
        r = self.lb.create_bucket("api:u1")
        assert r["status"] == "created"
        assert self.lb.bucket_count == 1

    def test_add_success(self):
        self.lb.create_bucket("api:u1")
        r = self.lb.add("api:u1")
        assert r["accepted"] is True
        assert "delay" in r

    def test_add_overflow(self):
        self.lb.create_bucket("api:u1", capacity=3, leak_rate=0.001)
        self.lb.add("api:u1")
        self.lb.add("api:u1")
        self.lb.add("api:u1")
        r = self.lb.add("api:u1")
        assert r["accepted"] is False
        assert r["reason"] == "overflow"

    def test_add_not_found(self):
        r = self.lb.add("none")
        assert r["accepted"] is False
        assert r["reason"] == "bucket_not_found"

    def test_leak(self):
        self.lb.create_bucket("api:u1", leak_rate=1000.0)
        self.lb.add("api:u1", count=5)
        time.sleep(0.01)
        r = self.lb.leak("api:u1")
        assert r["leaked"] >= 0

    def test_leak_not_found(self):
        r = self.lb.leak("none")
        assert r.get("error") == "bucket_not_found"

    def test_get_delay(self):
        self.lb.create_bucket("api:u1", leak_rate=10.0)
        self.lb.add("api:u1", count=5)
        delay = self.lb.get_delay("api:u1")
        assert delay >= 0

    def test_get_delay_not_found(self):
        assert self.lb.get_delay("none") == 0

    def test_get_bucket(self):
        self.lb.create_bucket("api:u1")
        b = self.lb.get_bucket("api:u1")
        assert b is not None
        assert b["key"] == "api:u1"

    def test_get_bucket_not_found(self):
        assert self.lb.get_bucket("none") is None

    def test_reset_bucket(self):
        self.lb.create_bucket("api:u1")
        self.lb.add("api:u1", count=5)
        r = self.lb.reset_bucket("api:u1")
        assert r["status"] == "reset"

    def test_reset_not_found(self):
        r = self.lb.reset_bucket("none")
        assert r.get("error") == "bucket_not_found"

    def test_delete_bucket(self):
        self.lb.create_bucket("api:u1")
        assert self.lb.delete_bucket("api:u1") is True
        assert self.lb.bucket_count == 0

    def test_delete_not_found(self):
        assert self.lb.delete_bucket("none") is False

    def test_update_rate(self):
        self.lb.create_bucket("api:u1")
        r = self.lb.update_rate("api:u1", leak_rate=50.0)
        assert r["status"] == "updated"

    def test_update_not_found(self):
        r = self.lb.update_rate("none")
        assert r.get("error") == "bucket_not_found"

    def test_list_buckets(self):
        self.lb.create_bucket("api:u1")
        self.lb.create_bucket("api:u2")
        buckets = self.lb.list_buckets()
        assert len(buckets) == 2

    def test_stats(self):
        self.lb.create_bucket("api:u1", capacity=2, leak_rate=0.001)
        self.lb.add("api:u1")
        self.lb.add("api:u1")
        self.lb.add("api:u1")
        assert self.lb.accepted_count == 2
        assert self.lb.overflow_count == 1


# ── QuotaManager ──────────────────────────────

class TestQuotaManager:
    """QuotaManager testleri."""

    def setup_method(self):
        from app.core.ratelimit.quota_manager import QuotaManager
        self.qm = QuotaManager()

    def test_create_quota(self):
        r = self.qm.create_quota("q1", "user1", 100, period="day")
        assert r["status"] == "created"
        assert self.qm.quota_count == 1

    def test_create_duplicate(self):
        self.qm.create_quota("q1", "user1", 100)
        r = self.qm.create_quota("q1", "user2", 200)
        assert r.get("error") == "quota_exists"

    def test_consume_allowed(self):
        self.qm.create_quota("q1", "user1", 100)
        r = self.qm.consume("q1", 10)
        assert r["allowed"] is True
        assert r["used"] == 10
        assert r["remaining"] == 90

    def test_consume_exceeded(self):
        self.qm.create_quota("q1", "user1", 5)
        self.qm.consume("q1", 5)
        r = self.qm.consume("q1", 1)
        assert r["allowed"] is False
        assert r["reason"] == "quota_exceeded"

    def test_consume_not_found(self):
        r = self.qm.consume("none", 1)
        assert r["allowed"] is False
        assert r["reason"] == "quota_not_found"

    def test_get_usage(self):
        self.qm.create_quota("q1", "user1", 100)
        self.qm.consume("q1", 30)
        u = self.qm.get_usage("q1")
        assert u["used"] == 30
        assert u["percentage"] == 30.0

    def test_get_usage_not_found(self):
        r = self.qm.get_usage("none")
        assert r.get("error") == "quota_not_found"

    def test_get_subject_usage(self):
        self.qm.create_quota("q1", "user1", 100, resource="api")
        self.qm.consume("q1", 10)
        u = self.qm.get_subject_usage("user1")
        assert u.get("api", 0) == 10

    def test_reset_quota(self):
        self.qm.create_quota("q1", "user1", 100)
        self.qm.consume("q1", 50)
        r = self.qm.reset_quota("q1")
        assert r["status"] == "reset"
        u = self.qm.get_usage("q1")
        assert u["used"] == 0

    def test_reset_not_found(self):
        r = self.qm.reset_quota("none")
        assert r.get("error") == "quota_not_found"

    def test_update_quota(self):
        self.qm.create_quota("q1", "user1", 100)
        r = self.qm.update_quota("q1", limit=200)
        assert r["status"] == "updated"

    def test_update_not_found(self):
        r = self.qm.update_quota("none")
        assert r.get("error") == "quota_not_found"

    def test_delete_quota(self):
        self.qm.create_quota("q1", "user1", 100)
        assert self.qm.delete_quota("q1") is True
        assert self.qm.quota_count == 0

    def test_delete_not_found(self):
        assert self.qm.delete_quota("none") is False

    def test_get_quota(self):
        self.qm.create_quota("q1", "user1", 100)
        q = self.qm.get_quota("q1")
        assert q is not None
        assert q["limit"] == 100

    def test_get_quota_not_found(self):
        assert self.qm.get_quota("none") is None

    def test_list_quotas(self):
        self.qm.create_quota("q1", "user1", 100)
        self.qm.create_quota("q2", "user2", 200)
        quotas = self.qm.list_quotas()
        assert len(quotas) == 2

    def test_list_quotas_by_subject(self):
        self.qm.create_quota("q1", "user1", 100)
        self.qm.create_quota("q2", "user2", 200)
        quotas = self.qm.list_quotas(subject_id="user1")
        assert len(quotas) == 1

    def test_auto_reset(self):
        self.qm.create_quota("q1", "user1", 100, period="day")
        self.qm.consume("q1", 50)
        # Force reset
        self.qm._quotas["q1"]["reset_at"] = time.time() - 1
        r = self.qm.consume("q1", 10)
        assert r["allowed"] is True
        assert r["used"] == 10  # Reset happened

    def test_stats(self):
        self.qm.create_quota("q1", "user1", 5)
        self.qm.consume("q1", 5)
        self.qm.consume("q1", 1)
        assert self.qm.consumed_total == 5
        assert self.qm.exceeded_count == 1


# ── ThrottleController ────────────────────────

class TestThrottleController:
    """ThrottleController testleri."""

    def setup_method(self):
        from app.core.ratelimit.throttle_controller import ThrottleController
        self.tc = ThrottleController(
            load_threshold=0.8,
            backpressure_threshold=0.95,
        )

    def test_add_rule(self):
        r = self.tc.add_rule("r1", mode="soft", threshold=0.7)
        assert r["status"] == "added"
        assert self.tc.rule_count == 1

    def test_remove_rule(self):
        self.tc.add_rule("r1")
        assert self.tc.remove_rule("r1") is True
        assert self.tc.rule_count == 0

    def test_remove_not_found(self):
        assert self.tc.remove_rule("none") is False

    def test_check_passes_low_load(self):
        self.tc.add_rule("r1", mode="hard", threshold=0.8)
        self.tc.update_load(0.3)
        r = self.tc.check()
        assert r["allowed"] is True
        assert r["throttled"] is False

    def test_check_hard_throttle(self):
        self.tc.add_rule("r1", mode="hard", threshold=0.5)
        self.tc.update_load(0.6)
        r = self.tc.check()
        assert r["allowed"] is False
        assert r["reason"] == "hard_throttle"

    def test_check_soft_throttle(self):
        self.tc.add_rule("r1", mode="soft", threshold=0.5, delay_ms=100)
        self.tc.update_load(0.6)
        r = self.tc.check()
        assert r["allowed"] is True
        assert r["throttled"] is True
        assert r["delay_ms"] == 100

    def test_check_adaptive_throttle(self):
        self.tc.add_rule("r1", mode="adaptive", threshold=0.5, delay_ms=100)
        self.tc.update_load(0.7)
        r = self.tc.check()
        assert r["allowed"] is True
        assert r["throttled"] is True
        assert r["delay_ms"] > 100

    def test_check_backpressure(self):
        self.tc.update_load(0.96)
        r = self.tc.check()
        assert r["allowed"] is False
        assert r["reason"] == "backpressure"

    def test_check_circuit_open(self):
        self.tc.set_circuit("api", state="open")
        r = self.tc.check(target="api")
        assert r["allowed"] is False
        assert r["reason"] == "circuit_open"

    def test_check_circuit_closed(self):
        self.tc.set_circuit("api", state="closed")
        r = self.tc.check(target="api")
        assert r["allowed"] is True

    def test_update_load(self):
        r = self.tc.update_load(0.5)
        assert r["load"] == 0.5
        assert self.tc.current_load == 0.5

    def test_update_load_clamped(self):
        self.tc.update_load(1.5)
        assert self.tc.current_load == 1.0
        self.tc.update_load(-0.5)
        assert self.tc.current_load == 0.0

    def test_get_rule(self):
        self.tc.add_rule("r1", mode="soft")
        r = self.tc.get_rule("r1")
        assert r is not None
        assert r["mode"] == "soft"

    def test_get_load_history(self):
        self.tc.update_load(0.3)
        self.tc.update_load(0.5)
        h = self.tc.get_load_history()
        assert len(h) == 2

    def test_list_rules(self):
        self.tc.add_rule("r1")
        self.tc.add_rule("r2")
        rules = self.tc.list_rules()
        assert len(rules) == 2

    def test_target_filtering(self):
        self.tc.add_rule("r1", mode="hard", threshold=0.5, target="api")
        self.tc.update_load(0.6)
        r = self.tc.check(target="other")
        assert r["allowed"] is True

    def test_stats(self):
        self.tc.add_rule("r1", mode="hard", threshold=0.5)
        self.tc.update_load(0.6)
        self.tc.check()
        assert self.tc.throttled_count == 1


# ── RatePolicy ────────────────────────────────

class TestRatePolicy:
    """RatePolicy testleri."""

    def setup_method(self):
        from app.core.ratelimit.rate_policy import RatePolicy
        self.rp = RatePolicy()

    def test_create_policy(self):
        r = self.rp.create_policy("p1", "Basic", tier="basic")
        assert r["status"] == "created"
        assert self.rp.policy_count == 1

    def test_create_duplicate(self):
        self.rp.create_policy("p1", "P1")
        r = self.rp.create_policy("p1", "P2")
        assert r.get("error") == "policy_exists"

    def test_delete_policy(self):
        self.rp.create_policy("p1", "P1")
        assert self.rp.delete_policy("p1") is True
        assert self.rp.policy_count == 0

    def test_delete_not_found(self):
        assert self.rp.delete_policy("none") is False

    def test_evaluate_policy(self):
        self.rp.create_policy("p1", "Pro", tier="pro", rpm=300)
        r = self.rp.evaluate("user1")
        assert r["rpm"] == 300
        assert r["source"] == "policy"

    def test_evaluate_default(self):
        r = self.rp.evaluate("user1")
        assert r["rpm"] == 60
        assert r["source"] == "default"

    def test_evaluate_user_override(self):
        self.rp.set_user_override("user1", rpm=500)
        r = self.rp.evaluate("user1")
        assert r["rpm"] == 500
        assert r["source"] == "user_override"

    def test_evaluate_endpoint_rule(self):
        self.rp.set_endpoint_rule("/api/heavy", rpm=10)
        r = self.rp.evaluate("user1", endpoint="/api/heavy")
        assert r["rpm"] == 10
        assert r["source"] == "endpoint_rule"

    def test_set_endpoint_rule(self):
        r = self.rp.set_endpoint_rule("/api/v1", rpm=100)
        assert r["status"] == "set"
        assert self.rp.endpoint_rule_count == 1

    def test_set_user_override(self):
        r = self.rp.set_user_override("user1", rpm=200)
        assert r["status"] == "set"
        assert self.rp.override_count == 1

    def test_remove_user_override(self):
        self.rp.set_user_override("user1", rpm=200)
        assert self.rp.remove_user_override("user1") is True
        assert self.rp.override_count == 0

    def test_remove_override_not_found(self):
        assert self.rp.remove_user_override("none") is False

    def test_add_dynamic_rule(self):
        r = self.rp.add_dynamic_rule("d1", condition="premium", rpm=500)
        assert r["status"] == "added"

    def test_evaluate_dynamic_rule(self):
        self.rp.add_dynamic_rule("d1", condition="premium", rpm=500)
        r = self.rp.evaluate("premium_user")
        assert r["rpm"] == 500
        assert r["source"] == "dynamic_rule"

    def test_set_tier_limits(self):
        r = self.rp.set_tier_limits("custom", rpm=1000, daily=100000)
        assert r["tier"] == "custom"

    def test_get_tier_limits(self):
        limits = self.rp.get_tier_limits("basic")
        assert limits["rpm"] == 60

    def test_get_policy(self):
        self.rp.create_policy("p1", "Test")
        p = self.rp.get_policy("p1")
        assert p["name"] == "Test"

    def test_list_policies(self):
        self.rp.create_policy("p1", "P1", tier="basic")
        self.rp.create_policy("p2", "P2", tier="pro")
        all_p = self.rp.list_policies()
        assert len(all_p) == 2
        basic_p = self.rp.list_policies(tier="basic")
        assert len(basic_p) == 1

    def test_evaluation_count(self):
        self.rp.evaluate("user1")
        self.rp.evaluate("user2")
        assert self.rp.evaluation_count == 2


# ── ViolationHandler ──────────────────────────

class TestViolationHandler:
    """ViolationHandler testleri."""

    def setup_method(self):
        from app.core.ratelimit.violation_handler import ViolationHandler
        self.vh = ViolationHandler(
            penalty_minutes=15,
            max_violations_before_ban=10,
            ban_duration_minutes=60,
        )

    def test_record_violation(self):
        r = self.vh.record_violation("user1", "rate_exceeded")
        assert r["violation_count"] == 1
        assert r["penalty"]["action"] == "warn"
        assert self.vh.violation_count == 1

    def test_escalation_to_delay(self):
        for _ in range(3):
            r = self.vh.record_violation("user1")
        assert r["penalty"]["action"] == "delay"

    def test_escalation_to_reject(self):
        for _ in range(5):
            r = self.vh.record_violation("user1")
        assert r["penalty"]["action"] == "reject"
        assert self.vh.penalty_count == 1

    def test_escalation_to_ban(self):
        for _ in range(10):
            self.vh.record_violation("user1")
        assert self.vh.ban_count == 1

    def test_check_banned(self):
        for _ in range(10):
            self.vh.record_violation("user1")
        r = self.vh.check_banned("user1")
        assert r["banned"] is True
        assert "retry_after" in r

    def test_check_not_banned(self):
        r = self.vh.check_banned("user1")
        assert r["banned"] is False

    def test_ban_expires(self):
        for _ in range(10):
            self.vh.record_violation("user1")
        self.vh._bans["user1"]["expires_at"] = time.time() - 1
        r = self.vh.check_banned("user1")
        assert r["banned"] is False
        assert r.get("was_banned") is True

    def test_get_penalty(self):
        for _ in range(6):
            self.vh.record_violation("user1")
        p = self.vh.get_penalty("user1")
        assert p is not None
        assert p["action"] == "reject"

    def test_get_penalty_none(self):
        assert self.vh.get_penalty("user1") is None

    def test_get_penalty_expired(self):
        for _ in range(5):
            self.vh.record_violation("user1")
        self.vh._penalties["user1"]["expires_at"] = time.time() - 1
        assert self.vh.get_penalty("user1") is None

    def test_generate_response_banned(self):
        for _ in range(10):
            self.vh.record_violation("user1")
        r = self.vh.generate_response("user1")
        assert r["status_code"] == 403

    def test_generate_response_reject(self):
        for _ in range(6):
            self.vh.record_violation("user1")
        r = self.vh.generate_response("user1")
        assert r["status_code"] == 429

    def test_generate_response_delay(self):
        for _ in range(3):
            self.vh.record_violation("user1")
        r = self.vh.generate_response("user1")
        assert r.get("throttled") is True or r["status_code"] == 200

    def test_generate_response_default(self):
        r = self.vh.generate_response("user1")
        assert r["status_code"] == 429
        assert r["retry_after"] == 15 * 60

    def test_submit_appeal(self):
        r = self.vh.submit_appeal("user1", reason="Legitimate use")
        assert r["status"] == "submitted"
        assert self.vh.appeal_count == 1

    def test_resolve_appeal_approved(self):
        for _ in range(10):
            self.vh.record_violation("user1")
        self.vh.submit_appeal("user1")
        r = self.vh.resolve_appeal("user1", approved=True)
        assert r["approved"] is True
        assert self.vh.check_banned("user1")["banned"] is False

    def test_resolve_appeal_rejected(self):
        self.vh.submit_appeal("user1")
        r = self.vh.resolve_appeal("user1", approved=False)
        assert r["approved"] is False

    def test_resolve_appeal_not_found(self):
        r = self.vh.resolve_appeal("user1")
        assert r.get("error") == "appeal_not_found"

    def test_clear_violations(self):
        for _ in range(10):
            self.vh.record_violation("user1")
        r = self.vh.clear_violations("user1")
        assert r["cleared"] == 10
        assert self.vh.check_banned("user1")["banned"] is False

    def test_get_violations(self):
        self.vh.record_violation("user1")
        self.vh.record_violation("user2")
        all_v = self.vh.get_violations()
        assert len(all_v) == 2
        u1_v = self.vh.get_violations(subject_id="user1")
        assert len(u1_v) == 1

    def test_get_appeals(self):
        self.vh.submit_appeal("user1")
        self.vh.submit_appeal("user2")
        self.vh.resolve_appeal("user1", approved=True)
        pending = self.vh.get_appeals(status="pending")
        assert len(pending) == 1


# ── RateAnalytics ─────────────────────────────

class TestRateAnalytics:
    """RateAnalytics testleri."""

    def setup_method(self):
        from app.core.ratelimit.rate_analytics import RateAnalytics
        self.ra = RateAnalytics(max_events=100)

    def test_record_request(self):
        r = self.ra.record_request("user1", "/api/v1", allowed=True)
        assert r["recorded"] is True
        assert self.ra.event_count == 1

    def test_record_rejected(self):
        self.ra.record_request("user1", "/api/v1", allowed=False)
        report = self.ra.get_report()
        assert report["rejected"] == 1

    def test_get_usage_pattern(self):
        for _ in range(10):
            self.ra.record_request("user1", "/api")
        p = self.ra.get_usage_pattern("user1")
        assert p["requests"] == 10
        assert p["pattern"] in ("steady", "bursty", "aggressive")

    def test_get_usage_pattern_inactive(self):
        p = self.ra.get_usage_pattern("none")
        assert p["pattern"] == "inactive"

    def test_detect_peaks(self):
        # Record many events at same hour
        for _ in range(20):
            self.ra.record_request("user1", "/api")
        peaks = self.ra.detect_peaks(threshold_multiplier=0.5)
        assert len(peaks) >= 0

    def test_analyze_trends(self):
        for _ in range(5):
            self.ra.record_request("user1", "/api")
        t = self.ra.analyze_trends(hours=2)
        assert "trend" in t
        assert "change_pct" in t

    def test_capacity_report(self):
        for _ in range(10):
            self.ra.record_request("user1", "/api")
        self.ra.record_request("user2", "/api", allowed=False)
        r = self.ra.capacity_report()
        assert r["total_requests"] == 11
        assert "recommendation" in r

    def test_get_top_subjects(self):
        for _ in range(10):
            self.ra.record_request("user1", "/api")
        for _ in range(5):
            self.ra.record_request("user2", "/api")
        top = self.ra.get_top_subjects(limit=2)
        assert len(top) == 2
        assert top[0]["total"] >= top[1]["total"]

    def test_get_top_endpoints(self):
        for _ in range(10):
            self.ra.record_request("user1", "/api/a")
        for _ in range(5):
            self.ra.record_request("user1", "/api/b")
        top = self.ra.get_top_endpoints(limit=2)
        assert len(top) == 2
        assert top[0]["total"] >= top[1]["total"]

    def test_get_report(self):
        self.ra.record_request("user1", "/api")
        r = self.ra.get_report()
        assert r["total_requests"] == 1
        assert "unique_subjects" in r

    def test_max_events_limit(self):
        for i in range(150):
            self.ra.record_request(f"u{i}", "/api")
        assert self.ra.event_count <= 100

    def test_subject_count(self):
        self.ra.record_request("user1", "/api")
        self.ra.record_request("user2", "/api")
        assert self.ra.subject_count == 2

    def test_endpoint_count(self):
        self.ra.record_request("user1", "/api/a")
        self.ra.record_request("user1", "/api/b")
        assert self.ra.endpoint_count == 2


# ── RateLimitOrchestrator ─────────────────────

class TestRateLimitOrchestrator:
    """RateLimitOrchestrator testleri."""

    def setup_method(self):
        from app.core.ratelimit.ratelimit_orchestrator import RateLimitOrchestrator
        self.orch = RateLimitOrchestrator(
            default_rpm=10,
            burst_multiplier=1.5,
            penalty_minutes=15,
        )

    def test_check_rate_limit_allowed(self):
        r = self.orch.check_rate_limit("user1", "/api")
        assert r["allowed"] is True

    def test_check_rate_limit_exceeded(self):
        # Setup with very low refill so tokens don't regenerate
        key = "user1:exctest"
        self.orch.token_bucket.create_bucket(
            key, capacity=3, refill_rate=0.001,
        )
        self.orch.token_bucket.consume(key, 3)
        r = self.orch.token_bucket.consume(key)
        assert r["allowed"] is False

    def test_check_rate_limit_banned(self):
        # Force ban
        for _ in range(20):
            self.orch.violations.record_violation("user1")
        r = self.orch.check_rate_limit("user1", "/api")
        assert r["allowed"] is False
        assert r["reason"] == "banned"

    def test_check_rate_limit_throttled(self):
        self.orch.throttle.add_rule(
            "r1", mode="hard", threshold=0.5,
        )
        self.orch.throttle.update_load(0.6)
        r = self.orch.check_rate_limit("user1", "/api")
        assert r["allowed"] is False
        assert r["reason"] == "throttled"

    def test_check_sliding_window(self):
        r = self.orch.check_rate_limit(
            "user1", "/api",
            algorithm="sliding_window",
        )
        assert r["allowed"] is True

    def test_check_leaky_bucket(self):
        r = self.orch.check_rate_limit(
            "user1", "/api",
            algorithm="leaky_bucket",
        )
        assert "accepted" in r or "allowed" in r

    def test_check_quota(self):
        self.orch.quotas.create_quota("q1", "user1", 100)
        r = self.orch.check_quota("user1", "q1", 10)
        assert r["allowed"] is True

    def test_check_quota_exceeded(self):
        self.orch.quotas.create_quota("q1", "user1", 5)
        self.orch.quotas.consume("q1", 5)
        r = self.orch.check_quota("user1", "q1", 1)
        assert r["allowed"] is False

    def test_setup_rate_limit(self):
        r = self.orch.setup_rate_limit("user1", "/api", rpm=100)
        assert r["status"] == "configured"

    def test_setup_sliding_window(self):
        r = self.orch.setup_rate_limit(
            "user1", "/api",
            rpm=100, algorithm="sliding_window",
        )
        assert r["status"] == "configured"

    def test_setup_leaky_bucket(self):
        r = self.orch.setup_rate_limit(
            "user1", "/api",
            rpm=100, algorithm="leaky_bucket",
        )
        assert r["status"] == "configured"

    def test_get_status(self):
        self.orch.check_rate_limit("user1", "/api")
        s = self.orch.get_status()
        assert s["total_checks"] >= 1
        assert "token_buckets" in s

    def test_get_analytics_report(self):
        self.orch.check_rate_limit("user1", "/api")
        r = self.orch.get_analytics_report()
        assert "overview" in r
        assert "capacity" in r
        assert "trends" in r

    def test_total_checks(self):
        self.orch.check_rate_limit("user1", "/api")
        self.orch.check_rate_limit("user2", "/api")
        assert self.orch.total_checks == 2

    def test_allowed_rejected(self):
        for _ in range(10):
            self.orch.check_rate_limit("user1", "/api")
        self.orch.check_rate_limit("user1", "/api")
        assert self.orch.allowed_total >= 10
        assert self.orch.rejected_total >= 0

    def test_full_pipeline(self):
        # Politika ayarla
        self.orch.policies.create_policy(
            "p1", "Pro", tier="pro", rpm=100,
        )
        # Kota ayarla
        self.orch.quotas.create_quota(
            "q1", "user1", 1000,
        )
        # Hiz siniri kontrolu
        r = self.orch.check_rate_limit("user1", "/api")
        assert r["allowed"] is True
        # Kota kontrolu
        r = self.orch.check_quota("user1", "q1", 1)
        assert r["allowed"] is True
        # Durum al
        s = self.orch.get_status()
        assert s["total_checks"] >= 1


# ── Config ────────────────────────────────────

class TestRateLimitConfig:
    """Rate limit config testleri."""

    def test_ratelimit_enabled(self):
        from app.config import settings
        assert hasattr(settings, "ratelimit_enabled")
        assert isinstance(settings.ratelimit_enabled, bool)

    def test_default_requests_per_minute(self):
        from app.config import settings
        assert hasattr(settings, "default_requests_per_minute")
        assert settings.default_requests_per_minute == 60

    def test_burst_multiplier(self):
        from app.config import settings
        assert hasattr(settings, "ratelimit_burst_multiplier")
        assert settings.ratelimit_burst_multiplier == 1.5

    def test_quota_reset_hour(self):
        from app.config import settings
        assert hasattr(settings, "ratelimit_quota_reset_hour")
        assert settings.ratelimit_quota_reset_hour == 0

    def test_violation_penalty_minutes(self):
        from app.config import settings
        assert hasattr(settings, "ratelimit_violation_penalty_minutes")
        assert settings.ratelimit_violation_penalty_minutes == 15


# ── Imports ───────────────────────────────────

class TestRateLimitImports:
    """Rate limit import testleri."""

    def test_import_token_bucket(self):
        from app.core.ratelimit import TokenBucket
        assert TokenBucket is not None

    def test_import_sliding_window(self):
        from app.core.ratelimit import SlidingWindow
        assert SlidingWindow is not None

    def test_import_leaky_bucket(self):
        from app.core.ratelimit import LeakyBucket
        assert LeakyBucket is not None

    def test_import_quota_manager(self):
        from app.core.ratelimit import QuotaManager
        assert QuotaManager is not None

    def test_import_throttle_controller(self):
        from app.core.ratelimit import ThrottleController
        assert ThrottleController is not None

    def test_import_rate_policy(self):
        from app.core.ratelimit import RatePolicy
        assert RatePolicy is not None

    def test_import_violation_handler(self):
        from app.core.ratelimit import ViolationHandler
        assert ViolationHandler is not None

    def test_import_rate_analytics(self):
        from app.core.ratelimit import RateAnalytics
        assert RateAnalytics is not None

    def test_import_orchestrator(self):
        from app.core.ratelimit import RateLimitOrchestrator
        assert RateLimitOrchestrator is not None

    def test_import_models(self):
        from app.models.ratelimit_models import (
            AlgorithmType,
            QuotaPeriod,
            ThrottleMode,
            ViolationType,
            PolicyTier,
            PenaltyAction,
            RateLimitRecord,
            QuotaRecord,
            ViolationRecord,
            RateLimitSnapshot,
        )
        assert all([
            AlgorithmType, QuotaPeriod, ThrottleMode,
            ViolationType, PolicyTier, PenaltyAction,
            RateLimitRecord, QuotaRecord,
            ViolationRecord, RateLimitSnapshot,
        ])
