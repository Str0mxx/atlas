"""Intrusion Detection & Prevention testleri."""

import pytest

from app.core.idsips.auto_blocker import (
    AutoBlocker,
)
from app.core.idsips.brute_force_detector import (
    BruteForceDetector,
)
from app.core.idsips.idsips_orchestrator import (
    IDSIPSOrchestrator,
)
from app.core.idsips.incident_recorder import (
    IDSIncidentRecorder,
)
from app.core.idsips.injection_guard import (
    InjectionGuard,
)
from app.core.idsips.network_analyzer import (
    NetworkAnalyzer,
)
from app.core.idsips.session_hijack_detector import (
    SessionHijackDetector,
)
from app.core.idsips.threat_intel_feed import (
    ThreatIntelFeed,
)
from app.core.idsips.xss_protector import (
    XSSProtector,
)


class TestNetworkAnalyzer:
    """NetworkAnalyzer testleri."""

    def setup_method(self) -> None:
        self.analyzer = NetworkAnalyzer()

    def test_init(self) -> None:
        assert self.analyzer is not None
        assert (
            self.analyzer.anomaly_count == 0
        )

    def test_analyze_traffic(self) -> None:
        r = self.analyzer.analyze_traffic(
            source_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            protocol="tcp",
            port=80,
            payload_size=1024,
        )
        assert r["analyzed"] is True
        assert "traffic_id" in r

    def test_analyze_traffic_suspicious(
        self,
    ) -> None:
        r = self.analyzer.analyze_traffic(
            source_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            protocol="tcp",
            port=80,
            payload_size=1024,
            description="port scan detected",
        )
        assert r["analyzed"] is True

    def test_inspect_protocol(self) -> None:
        r = self.analyzer.inspect_protocol(
            protocol="tcp",
            data="normal traffic",
        )
        assert r["inspected"] is True
        assert r["protocol"] == "tcp"

    def test_set_baseline(self) -> None:
        r = self.analyzer.set_baseline(
            metric="bandwidth",
            avg_value=100.0,
            std_dev=10.0,
            max_value=200.0,
        )
        assert r["set"] is True
        assert r["metric"] == "bandwidth"

    def test_check_anomaly_normal(
        self,
    ) -> None:
        self.analyzer.set_baseline(
            metric="bandwidth",
            avg_value=100.0,
            std_dev=10.0,
            max_value=200.0,
        )
        r = self.analyzer.check_anomaly(
            metric="bandwidth",
            current_value=105.0,
        )
        assert r["checked"] is True
        assert r["anomaly"] is False

    def test_check_anomaly_detected(
        self,
    ) -> None:
        self.analyzer.set_baseline(
            metric="bandwidth",
            avg_value=100.0,
            std_dev=10.0,
            max_value=200.0,
        )
        r = self.analyzer.check_anomaly(
            metric="bandwidth",
            current_value=500.0,
        )
        assert r["checked"] is True
        assert r["anomaly"] is True
        assert self.analyzer.anomaly_count == 1

    def test_check_anomaly_no_baseline(
        self,
    ) -> None:
        r = self.analyzer.check_anomaly(
            metric="unknown",
            current_value=100.0,
        )
        assert r["checked"] is True
        assert r["anomaly"] is False

    def test_add_pattern(self) -> None:
        r = self.analyzer.add_pattern(
            name="test_pattern",
            pattern="test.*attack",
            severity="high",
        )
        assert r["added"] is True

    def test_get_summary(self) -> None:
        r = self.analyzer.get_summary()
        assert r["retrieved"] is True
        assert "total_traffic" in r

    def test_suspicious_patterns(
        self,
    ) -> None:
        assert (
            len(
                NetworkAnalyzer.SUSPICIOUS_PATTERNS
            )
            >= 4
        )


class TestBruteForceDetector:
    """BruteForceDetector testleri."""

    def setup_method(self) -> None:
        self.detector = BruteForceDetector(
            max_attempts=3,
            lockout_minutes=15,
        )

    def test_init(self) -> None:
        assert self.detector is not None
        assert self.detector.alert_count == 0

    def test_record_attempt_success(
        self,
    ) -> None:
        r = self.detector.record_attempt(
            ip="1.2.3.4",
            username="admin",
            success=True,
            service="ssh",
        )
        assert r["recorded"] is True

    def test_record_attempt_failure(
        self,
    ) -> None:
        r = self.detector.record_attempt(
            ip="1.2.3.4",
            username="admin",
            success=False,
            service="ssh",
        )
        assert r["recorded"] is True

    def test_brute_force_alert(self) -> None:
        for _ in range(4):
            self.detector.record_attempt(
                ip="1.2.3.4",
                username="admin",
                success=False,
                service="ssh",
            )
        assert self.detector.alert_count >= 1

    def test_check_threshold(self) -> None:
        for _ in range(2):
            self.detector.record_attempt(
                ip="1.2.3.4",
                username="admin",
                success=False,
            )
        r = self.detector.check_threshold(
            ip="1.2.3.4",
            username="admin",
        )
        assert r["checked"] is True

    def test_check_threshold_exceeded(
        self,
    ) -> None:
        for _ in range(5):
            self.detector.record_attempt(
                ip="5.6.7.8",
                username="root",
                success=False,
            )
        r = self.detector.check_threshold(
            ip="5.6.7.8",
            username="root",
        )
        assert r["exceeded"] is True

    def test_block_ip(self) -> None:
        r = self.detector.block_ip(
            ip="9.8.7.6",
            reason="brute_force",
        )
        assert r["blocked"] is True
        assert self.detector.is_blocked(
            "9.8.7.6"
        )

    def test_unblock_ip(self) -> None:
        self.detector.block_ip(
            ip="9.8.7.6",
            reason="test",
        )
        r = self.detector.unblock_ip(
            ip="9.8.7.6"
        )
        assert r["unblocked"] is True
        assert not self.detector.is_blocked(
            "9.8.7.6"
        )

    def test_unblock_nonexistent(
        self,
    ) -> None:
        r = self.detector.unblock_ip(
            ip="0.0.0.0"
        )
        assert r["unblocked"] is False

    def test_lock_account(self) -> None:
        r = self.detector.lock_account(
            username="admin",
            reason="brute_force",
        )
        assert r["locked"] is True
        assert self.detector.is_locked(
            "admin"
        )

    def test_unlock_account(self) -> None:
        self.detector.lock_account(
            username="admin",
            reason="test",
        )
        r = self.detector.unlock_account(
            username="admin"
        )
        assert r["unlocked"] is True
        assert not self.detector.is_locked(
            "admin"
        )

    def test_unlock_nonexistent(
        self,
    ) -> None:
        r = self.detector.unlock_account(
            username="nobody"
        )
        assert r["unlocked"] is False

    def test_get_summary(self) -> None:
        r = self.detector.get_summary()
        assert r["retrieved"] is True


class TestInjectionGuard:
    """InjectionGuard testleri."""

    def setup_method(self) -> None:
        self.guard = InjectionGuard()

    def test_init(self) -> None:
        assert self.guard is not None
        assert (
            self.guard.detection_count == 0
        )

    def test_sql_injection_detected(
        self,
    ) -> None:
        r = self.guard.check_sql_injection(
            input_str="' OR 1=1 --",
            source="login",
        )
        assert r["detected"] is True

    def test_sql_injection_clean(
        self,
    ) -> None:
        r = self.guard.check_sql_injection(
            input_str="hello world",
            source="search",
        )
        assert r["detected"] is False

    def test_command_injection_detected(
        self,
    ) -> None:
        r = (
            self.guard.check_command_injection(
                input_str="test; rm -rf /",
                source="input",
            )
        )
        assert r["detected"] is True

    def test_command_injection_clean(
        self,
    ) -> None:
        r = (
            self.guard.check_command_injection(
                input_str="normal text",
                source="input",
            )
        )
        assert r["detected"] is False

    def test_ldap_injection_detected(
        self,
    ) -> None:
        r = self.guard.check_ldap_injection(
            input_str="*)(uid=*))(|(uid=*",
            source="search",
        )
        assert r["detected"] is True

    def test_ldap_injection_clean(
        self,
    ) -> None:
        r = self.guard.check_ldap_injection(
            input_str="john",
            source="search",
        )
        assert r["detected"] is False

    def test_xpath_injection_detected(
        self,
    ) -> None:
        r = self.guard.check_xpath_injection(
            input_str="' or '1'='1",
            source="query",
        )
        assert r["detected"] is True

    def test_xpath_injection_clean(
        self,
    ) -> None:
        r = self.guard.check_xpath_injection(
            input_str="book_title",
            source="query",
        )
        assert r["detected"] is False

    def test_check_all(self) -> None:
        r = self.guard.check_all(
            input_str="'; DROP TABLE --",
            source="api",
        )
        assert r["checked"] is True
        assert r["total_detections"] > 0

    def test_check_all_clean(self) -> None:
        r = self.guard.check_all(
            input_str="hello",
            source="api",
        )
        assert r["total_detections"] == 0

    def test_sanitize(self) -> None:
        r = self.guard.sanitize(
            input_str="te'st; dr--op"
        )
        assert r["sanitized_ok"] is True
        s = r["sanitized"]
        assert "'" not in s
        assert ";" not in s
        assert "--" not in s

    def test_get_summary(self) -> None:
        r = self.guard.get_summary()
        assert r["retrieved"] is True

    def test_patterns_exist(self) -> None:
        assert len(InjectionGuard.SQL_PATTERNS) >= 5
        assert len(InjectionGuard.CMD_PATTERNS) >= 4


class TestXSSProtector:
    """XSSProtector testleri."""

    def setup_method(self) -> None:
        self.protector = XSSProtector()

    def test_init(self) -> None:
        assert self.protector is not None
        assert (
            self.protector.detection_count
            == 0
        )

    def test_detect_xss_script(self) -> None:
        r = self.protector.detect_xss(
            input_str="<script>alert(1)</script>",
            source="form",
        )
        assert r["detected"] is True
        assert r["pattern_count"] > 0

    def test_detect_xss_event(self) -> None:
        r = self.protector.detect_xss(
            input_str='<img onerror="alert(1)">',
            source="form",
        )
        assert r["detected"] is True

    def test_detect_xss_clean(self) -> None:
        r = self.protector.detect_xss(
            input_str="hello world",
            source="form",
        )
        assert r["detected"] is False

    def test_detect_javascript_uri(
        self,
    ) -> None:
        r = self.protector.detect_xss(
            input_str="javascript:alert(1)",
        )
        assert r["detected"] is True

    def test_validate_input_valid(
        self,
    ) -> None:
        r = self.protector.validate_input(
            input_str="hello world",
        )
        assert r["valid"] is True

    def test_validate_input_xss(
        self,
    ) -> None:
        r = self.protector.validate_input(
            input_str="<script>x</script>",
        )
        assert r["valid"] is False

    def test_validate_input_too_long(
        self,
    ) -> None:
        r = self.protector.validate_input(
            input_str="a" * 20000,
            max_length=10000,
        )
        assert r["valid"] is False

    def test_encode_output(self) -> None:
        r = self.protector.encode_output(
            output_str='<div>"test"</div>',
        )
        assert r["encoded_ok"] is True
        assert "&lt;" in r["encoded"]
        assert "&gt;" in r["encoded"]
        assert "&quot;" in r["encoded"]

    def test_encode_output_no_change(
        self,
    ) -> None:
        r = self.protector.encode_output(
            output_str="hello",
        )
        assert r["modified"] is False

    def test_sanitize_html(self) -> None:
        r = self.protector.sanitize_html(
            html='<p>OK</p><script>bad</script>',
        )
        assert r["sanitized_ok"] is True
        assert "<script>" not in r["sanitized"]
        assert "<p>" in r["sanitized"]

    def test_sanitize_html_event_handler(
        self,
    ) -> None:
        r = self.protector.sanitize_html(
            html='<div onclick="alert(1)">x</div>',
        )
        assert r["sanitized_ok"] is True
        assert "onclick" not in r["sanitized"]

    def test_sanitize_html_javascript_uri(
        self,
    ) -> None:
        r = self.protector.sanitize_html(
            html='<a href="javascript:alert(1)">x</a>',
        )
        assert r["sanitized_ok"] is True
        assert "javascript:" not in r["sanitized"]

    def test_set_csp_policy(self) -> None:
        r = self.protector.set_csp_policy(
            name="strict",
        )
        assert r["set"] is True
        assert "header" in r

    def test_set_csp_policy_custom(
        self,
    ) -> None:
        r = self.protector.set_csp_policy(
            name="custom",
            directives={
                "default-src": "'none'",
                "script-src": "'self'",
            },
        )
        assert r["set"] is True
        assert "'none'" in r["header"]

    def test_get_summary(self) -> None:
        r = self.protector.get_summary()
        assert r["retrieved"] is True

    def test_patterns_exist(self) -> None:
        assert (
            len(XSSProtector.XSS_PATTERNS)
            >= 7
        )


class TestSessionHijackDetector:
    """SessionHijackDetector testleri."""

    def setup_method(self) -> None:
        self.detector = (
            SessionHijackDetector(
                max_concurrent=2
            )
        )

    def test_init(self) -> None:
        assert self.detector is not None
        assert (
            self.detector.session_count == 0
        )

    def test_register_session(self) -> None:
        r = self.detector.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.2.3.4",
            user_agent="Chrome",
            fingerprint="fp1",
        )
        assert r["registered"] is True
        assert (
            self.detector.session_count == 1
        )

    def test_check_ip_no_change(
        self,
    ) -> None:
        self.detector.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.2.3.4",
        )
        r = self.detector.check_ip_change(
            session_id="s1",
            current_ip="1.2.3.4",
        )
        assert r["ip_changed"] is False

    def test_check_ip_changed(self) -> None:
        self.detector.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.2.3.4",
        )
        r = self.detector.check_ip_change(
            session_id="s1",
            current_ip="5.6.7.8",
        )
        assert r["ip_changed"] is True

    def test_check_ip_session_not_found(
        self,
    ) -> None:
        r = self.detector.check_ip_change(
            session_id="invalid",
            current_ip="1.1.1.1",
        )
        assert r["checked"] is False

    def test_check_fingerprint_no_change(
        self,
    ) -> None:
        self.detector.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.2.3.4",
            fingerprint="fp1",
        )
        r = self.detector.check_fingerprint(
            session_id="s1",
            current_fingerprint="fp1",
        )
        assert r["fingerprint_changed"] is False

    def test_check_fingerprint_changed(
        self,
    ) -> None:
        self.detector.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.2.3.4",
            fingerprint="fp1",
        )
        r = self.detector.check_fingerprint(
            session_id="s1",
            current_fingerprint="fp2",
        )
        assert r["fingerprint_changed"] is True

    def test_check_fingerprint_not_found(
        self,
    ) -> None:
        r = self.detector.check_fingerprint(
            session_id="bad",
            current_fingerprint="fp",
        )
        assert r["checked"] is False

    def test_concurrent_sessions_ok(
        self,
    ) -> None:
        self.detector.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.1.1.1",
        )
        r = (
            self.detector.check_concurrent_sessions(
                user_id="u1"
            )
        )
        assert r["exceeded"] is False

    def test_concurrent_sessions_exceeded(
        self,
    ) -> None:
        for i in range(4):
            self.detector.register_session(
                session_id=f"s{i}",
                user_id="u1",
                ip=f"1.1.1.{i}",
            )
        r = (
            self.detector.check_concurrent_sessions(
                user_id="u1"
            )
        )
        assert r["exceeded"] is True

    def test_force_logout(self) -> None:
        self.detector.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.1.1.1",
        )
        r = self.detector.force_logout(
            session_id="s1",
            reason="hijack",
        )
        assert r["logged_out"] is True

    def test_force_logout_not_found(
        self,
    ) -> None:
        r = self.detector.force_logout(
            session_id="bad",
            reason="test",
        )
        assert r["logged_out"] is False

    def test_force_logout_user(self) -> None:
        for i in range(3):
            self.detector.register_session(
                session_id=f"s{i}",
                user_id="u1",
                ip=f"1.1.1.{i}",
            )
        r = self.detector.force_logout_user(
            user_id="u1",
            reason="security",
        )
        assert r["logged_out"] is True
        assert r["sessions_closed"] == 3

    def test_get_summary(self) -> None:
        r = self.detector.get_summary()
        assert r["retrieved"] is True


class TestAutoBlocker:
    """AutoBlocker testleri."""

    def setup_method(self) -> None:
        self.blocker = AutoBlocker()

    def test_init(self) -> None:
        assert self.blocker is not None
        assert self.blocker.blocked_count == 0

    def test_block_ip(self) -> None:
        r = self.blocker.block_ip(
            ip="1.2.3.4",
            reason="attack",
        )
        assert r["blocked"] is True
        assert self.blocker.is_blocked(
            "1.2.3.4"
        )

    def test_block_ip_permanent(
        self,
    ) -> None:
        r = self.blocker.block_ip(
            ip="5.6.7.8",
            reason="permanent ban",
            permanent=True,
        )
        assert r["permanent"] is True

    def test_block_whitelisted_ip(
        self,
    ) -> None:
        self.blocker.add_to_whitelist(
            ip="10.0.0.1"
        )
        r = self.blocker.block_ip(
            ip="10.0.0.1",
            reason="test",
        )
        assert r["blocked"] is False

    def test_unblock_ip(self) -> None:
        self.blocker.block_ip(
            ip="1.2.3.4",
            reason="test",
        )
        r = self.blocker.unblock_ip(
            ip="1.2.3.4"
        )
        assert r["unblocked"] is True
        assert not self.blocker.is_blocked(
            "1.2.3.4"
        )

    def test_unblock_not_blocked(
        self,
    ) -> None:
        r = self.blocker.unblock_ip(
            ip="0.0.0.0"
        )
        assert r["unblocked"] is False

    def test_is_blocked_blacklist(
        self,
    ) -> None:
        self.blocker.add_to_blacklist(
            ip="9.9.9.9"
        )
        assert self.blocker.is_blocked(
            "9.9.9.9"
        )

    def test_check_rate_limit(self) -> None:
        r = self.blocker.check_rate_limit(
            ip="1.1.1.1",
            max_requests=5,
        )
        assert r["checked"] is True
        assert r["exceeded"] is False

    def test_check_rate_limit_exceeded(
        self,
    ) -> None:
        for _ in range(10):
            self.blocker.check_rate_limit(
                ip="2.2.2.2",
                max_requests=5,
            )
        r = self.blocker.check_rate_limit(
            ip="2.2.2.2",
            max_requests=5,
        )
        assert r["exceeded"] is True

    def test_whitelist(self) -> None:
        r = self.blocker.add_to_whitelist(
            ip="10.0.0.1"
        )
        assert r["whitelisted"] is True

    def test_whitelist_unblocks(
        self,
    ) -> None:
        self.blocker.block_ip(
            ip="10.0.0.1",
            reason="test",
        )
        self.blocker.add_to_whitelist(
            ip="10.0.0.1"
        )
        assert not self.blocker.is_blocked(
            "10.0.0.1"
        )

    def test_remove_whitelist(self) -> None:
        self.blocker.add_to_whitelist(
            ip="10.0.0.1"
        )
        r = self.blocker.remove_from_whitelist(
            ip="10.0.0.1"
        )
        assert r["removed"] is True

    def test_blacklist(self) -> None:
        r = self.blocker.add_to_blacklist(
            ip="9.9.9.9"
        )
        assert r["blacklisted"] is True

    def test_block_country(self) -> None:
        r = self.blocker.block_country(
            country_code="cn"
        )
        assert r["geo_blocked"] is True
        assert r["country"] == "CN"
        assert (
            self.blocker.is_country_blocked(
                "CN"
            )
        )

    def test_unblock_country(self) -> None:
        self.blocker.block_country(
            country_code="cn"
        )
        r = self.blocker.unblock_country(
            country_code="cn"
        )
        assert r["unblocked"] is True
        assert not (
            self.blocker.is_country_blocked(
                "CN"
            )
        )

    def test_get_summary(self) -> None:
        r = self.blocker.get_summary()
        assert r["retrieved"] is True
        assert "blocked_ips" in r


class TestThreatIntelFeed:
    """ThreatIntelFeed testleri."""

    def setup_method(self) -> None:
        self.feed = ThreatIntelFeed()

    def test_init(self) -> None:
        assert self.feed is not None
        assert self.feed.ioc_count == 0

    def test_add_feed(self) -> None:
        r = self.feed.add_feed(
            name="test_feed",
            url="https://example.com/feed",
            feed_type="ip",
        )
        assert r["added"] is True
        assert "feed_id" in r

    def test_add_ioc(self) -> None:
        r = self.feed.add_ioc(
            ioc_type="ip",
            value="1.2.3.4",
            severity="high",
            source="test",
        )
        assert r["added"] is True
        assert self.feed.ioc_count == 1

    def test_check_ioc_match(self) -> None:
        self.feed.add_ioc(
            ioc_type="ip",
            value="1.2.3.4",
            severity="critical",
            source="blocklist",
        )
        r = self.feed.check_ioc(
            value="1.2.3.4"
        )
        assert r["matched"] is True
        assert r["match_count"] == 1

    def test_check_ioc_no_match(
        self,
    ) -> None:
        r = self.feed.check_ioc(
            value="1.1.1.1"
        )
        assert r["matched"] is False
        assert r["match_count"] == 0

    def test_set_reputation(self) -> None:
        r = self.feed.set_reputation(
            entity="1.2.3.4",
            score=20.0,
            category="malicious",
        )
        assert r["set"] is True

    def test_get_reputation_found(
        self,
    ) -> None:
        self.feed.set_reputation(
            entity="1.2.3.4",
            score=10.0,
            category="malicious",
        )
        r = self.feed.get_reputation(
            entity="1.2.3.4"
        )
        assert r["found"] is True
        assert r["score"] == 10.0

    def test_get_reputation_default(
        self,
    ) -> None:
        r = self.feed.get_reputation(
            entity="unknown"
        )
        assert r["found"] is False
        assert r["score"] == 50.0

    def test_update_feed(self) -> None:
        add_r = self.feed.add_feed(
            name="test",
            url="https://example.com",
        )
        fid = add_r["feed_id"]
        r = self.feed.update_feed(
            feed_id=fid
        )
        assert r["updated"] is True

    def test_update_feed_not_found(
        self,
    ) -> None:
        r = self.feed.update_feed(
            feed_id="invalid"
        )
        assert r["updated"] is False

    def test_get_summary(self) -> None:
        r = self.feed.get_summary()
        assert r["retrieved"] is True
        assert "total_feeds" in r


class TestIDSIncidentRecorder:
    """IDSIncidentRecorder testleri."""

    def setup_method(self) -> None:
        self.recorder = IDSIncidentRecorder()

    def test_init(self) -> None:
        assert self.recorder is not None
        assert (
            self.recorder.incident_count == 0
        )

    def test_record_incident(self) -> None:
        r = self.recorder.record_incident(
            incident_type="brute_force",
            source_ip="1.2.3.4",
            target="ssh",
            severity="high",
            description="Brute force attack",
        )
        assert r["recorded"] is True
        assert "incident_id" in r
        assert (
            self.recorder.incident_count == 1
        )

    def test_add_evidence(self) -> None:
        inc = self.recorder.record_incident(
            incident_type="injection",
            source_ip="5.6.7.8",
        )
        iid = inc["incident_id"]
        r = self.recorder.add_evidence(
            incident_id=iid,
            evidence_type="log",
            data="suspicious query",
            source="waf",
        )
        assert r["added"] is True
        assert "evidence_id" in r

    def test_add_evidence_not_found(
        self,
    ) -> None:
        r = self.recorder.add_evidence(
            incident_id="invalid",
            evidence_type="log",
            data="test",
        )
        assert r["added"] is False

    def test_get_timeline(self) -> None:
        inc = self.recorder.record_incident(
            incident_type="xss",
        )
        iid = inc["incident_id"]
        self.recorder.add_evidence(
            incident_id=iid,
            evidence_type="log",
            data="test",
        )
        r = self.recorder.get_timeline(
            incident_id=iid
        )
        assert r["retrieved"] is True
        assert r["event_count"] >= 2

    def test_get_timeline_not_found(
        self,
    ) -> None:
        r = self.recorder.get_timeline(
            incident_id="bad"
        )
        assert r["retrieved"] is False

    def test_update_severity(self) -> None:
        inc = self.recorder.record_incident(
            incident_type="test",
            severity="medium",
        )
        iid = inc["incident_id"]
        r = self.recorder.update_severity(
            incident_id=iid,
            severity="critical",
        )
        assert r["updated"] is True
        assert r["old_severity"] == "medium"
        assert r["new_severity"] == "critical"

    def test_update_severity_not_found(
        self,
    ) -> None:
        r = self.recorder.update_severity(
            incident_id="bad",
            severity="high",
        )
        assert r["updated"] is False

    def test_resolve_incident(self) -> None:
        inc = self.recorder.record_incident(
            incident_type="test",
        )
        iid = inc["incident_id"]
        r = self.recorder.resolve_incident(
            incident_id=iid,
            resolution="Fixed",
        )
        assert r["resolved"] is True

    def test_resolve_not_found(self) -> None:
        r = self.recorder.resolve_incident(
            incident_id="bad",
            resolution="test",
        )
        assert r["resolved"] is False

    def test_generate_report(self) -> None:
        inc = self.recorder.record_incident(
            incident_type="brute_force",
            source_ip="1.2.3.4",
            severity="high",
        )
        iid = inc["incident_id"]
        r = self.recorder.generate_report(
            incident_id=iid
        )
        assert r["generated"] is True
        assert r["severity"] == "high"

    def test_generate_report_not_found(
        self,
    ) -> None:
        r = self.recorder.generate_report(
            incident_id="bad"
        )
        assert r["generated"] is False

    def test_get_open_incidents(self) -> None:
        self.recorder.record_incident(
            incident_type="test1"
        )
        self.recorder.record_incident(
            incident_type="test2"
        )
        r = self.recorder.get_open_incidents()
        assert r["retrieved"] is True
        assert r["count"] == 2

    def test_get_open_after_resolve(
        self,
    ) -> None:
        inc = self.recorder.record_incident(
            incident_type="test"
        )
        self.recorder.resolve_incident(
            incident_id=inc["incident_id"],
            resolution="done",
        )
        r = self.recorder.get_open_incidents()
        assert r["count"] == 0

    def test_get_summary(self) -> None:
        self.recorder.record_incident(
            incident_type="test",
            severity="critical",
        )
        r = self.recorder.get_summary()
        assert r["retrieved"] is True
        assert r["total_incidents"] == 1
        assert r["critical"] == 1

    def test_severity_levels(self) -> None:
        assert (
            len(
                IDSIncidentRecorder.SEVERITY_LEVELS
            )
            == 5
        )


class TestIDSIPSOrchestrator:
    """IDSIPSOrchestrator testleri."""

    def setup_method(self) -> None:
        self.orch = IDSIPSOrchestrator()

    def test_init(self) -> None:
        assert self.orch is not None
        assert self.orch.network is not None
        assert (
            self.orch.brute_force is not None
        )
        assert self.orch.injection is not None
        assert self.orch.xss is not None
        assert self.orch.session is not None
        assert self.orch.blocker is not None
        assert (
            self.orch.threat_intel is not None
        )
        assert self.orch.recorder is not None

    def test_analyze_request_safe(
        self,
    ) -> None:
        r = self.orch.analyze_request(
            source_ip="10.0.0.1",
            input_data="hello world",
        )
        assert r["analyzed"] is True
        assert r["safe"] is True
        assert r["threat_count"] == 0

    def test_analyze_request_blocked_ip(
        self,
    ) -> None:
        self.orch.blocker.block_ip(
            ip="1.2.3.4",
            reason="test",
        )
        r = self.orch.analyze_request(
            source_ip="1.2.3.4",
            input_data="hello",
        )
        assert r["blocked"] is True
        assert r["safe"] is False

    def test_analyze_request_injection(
        self,
    ) -> None:
        r = self.orch.analyze_request(
            source_ip="10.0.0.1",
            input_data="' OR 1=1 --",
        )
        assert r["safe"] is False
        assert r["threat_count"] > 0

    def test_analyze_request_xss(
        self,
    ) -> None:
        r = self.orch.analyze_request(
            source_ip="10.0.0.1",
            input_data="<script>alert(1)</script>",
        )
        assert r["safe"] is False

    def test_analyze_request_threat_intel(
        self,
    ) -> None:
        self.orch.threat_intel.add_ioc(
            ioc_type="ip",
            value="9.9.9.9",
            severity="critical",
        )
        r = self.orch.analyze_request(
            source_ip="9.9.9.9",
            input_data="hello",
        )
        assert r["safe"] is False

    def test_monitor_login_success(
        self,
    ) -> None:
        r = self.orch.monitor_login(
            ip="10.0.0.1",
            username="admin",
            success=True,
            service="web",
        )
        assert r["monitored"] is True
        assert r["alert"] is False

    def test_monitor_login_brute_force(
        self,
    ) -> None:
        for _ in range(10):
            self.orch.monitor_login(
                ip="1.2.3.4",
                username="admin",
                success=False,
                service="ssh",
            )
        r = self.orch.monitor_login(
            ip="1.2.3.4",
            username="admin",
            success=False,
            service="ssh",
        )
        assert r["monitored"] is True

    def test_validate_session_valid(
        self,
    ) -> None:
        self.orch.session.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.1.1.1",
            fingerprint="fp1",
        )
        r = self.orch.validate_session(
            session_id="s1",
            current_ip="1.1.1.1",
            current_fingerprint="fp1",
        )
        assert r["validated"] is True
        assert r["valid"] is True

    def test_validate_session_ip_changed(
        self,
    ) -> None:
        self.orch.session.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.1.1.1",
            fingerprint="fp1",
        )
        r = self.orch.validate_session(
            session_id="s1",
            current_ip="9.9.9.9",
            current_fingerprint="fp1",
        )
        assert r["valid"] is False
        assert "ip_changed" in r["issues"]

    def test_validate_session_fp_changed(
        self,
    ) -> None:
        self.orch.session.register_session(
            session_id="s1",
            user_id="u1",
            ip="1.1.1.1",
            fingerprint="fp1",
        )
        r = self.orch.validate_session(
            session_id="s1",
            current_ip="1.1.1.1",
            current_fingerprint="fp_bad",
        )
        assert r["valid"] is False
        assert (
            "fingerprint_changed"
            in r["issues"]
        )

    def test_protect_input_safe(
        self,
    ) -> None:
        r = self.orch.protect_input(
            input_str="hello world",
            source="form",
        )
        assert r["protected"] is True
        assert r["threats_found"] is False

    def test_protect_input_injection(
        self,
    ) -> None:
        r = self.orch.protect_input(
            input_str="'; DROP TABLE users --",
            source="form",
        )
        assert r["protected"] is True
        assert r["threats_found"] is True
        assert (
            r["sanitized"]
            != "'; DROP TABLE users --"
        )

    def test_protect_input_xss(self) -> None:
        r = self.orch.protect_input(
            input_str="<script>alert(1)</script>",
            source="form",
        )
        assert r["protected"] is True
        assert r["threats_found"] is True

    def test_security_status(self) -> None:
        r = self.orch.security_status()
        assert r["retrieved"] is True
        assert "network" in r
        assert "brute_force" in r
        assert "injection" in r
        assert "xss" in r
        assert "session" in r
        assert "blocker" in r
        assert "threat_intel" in r
        assert "incidents" in r

    def test_get_analytics(self) -> None:
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert "network_anomalies" in r
        assert "brute_force_alerts" in r
        assert "injection_detections" in r
        assert "xss_detections" in r
        assert "blocked_ips" in r
        assert "total_incidents" in r


class TestIDSIPSModels:
    """IDS/IPS model testleri."""

    def test_detection_mode(self) -> None:
        from app.models.idsips_models import (
            DetectionMode,
        )

        assert (
            DetectionMode.ACTIVE == "active"
        )
        assert (
            DetectionMode.PASSIVE == "passive"
        )
        assert (
            DetectionMode.HYBRID == "hybrid"
        )

    def test_threat_type(self) -> None:
        from app.models.idsips_models import (
            ThreatType,
        )

        assert (
            ThreatType.BRUTE_FORCE
            == "brute_force"
        )
        assert (
            ThreatType.INJECTION
            == "injection"
        )
        assert ThreatType.XSS == "xss"

    def test_incident_severity(self) -> None:
        from app.models.idsips_models import (
            IncidentSeverity,
        )

        assert (
            IncidentSeverity.CRITICAL
            == "critical"
        )
        assert (
            IncidentSeverity.HIGH == "high"
        )

    def test_incident_status(self) -> None:
        from app.models.idsips_models import (
            IncidentStatus,
        )

        assert (
            IncidentStatus.OPEN == "open"
        )
        assert (
            IncidentStatus.RESOLVED
            == "resolved"
        )

    def test_block_reason(self) -> None:
        from app.models.idsips_models import (
            BlockReason,
        )

        assert (
            BlockReason.BRUTE_FORCE
            == "brute_force"
        )
        assert (
            BlockReason.MANUAL == "manual"
        )

    def test_ioc_type(self) -> None:
        from app.models.idsips_models import (
            IOCType,
        )

        assert IOCType.IP == "ip"
        assert IOCType.DOMAIN == "domain"

    def test_network_threat_record(
        self,
    ) -> None:
        from app.models.idsips_models import (
            NetworkThreatRecord,
        )

        r = NetworkThreatRecord(
            source_ip="1.2.3.4",
            dest_ip="5.6.7.8",
            port=80,
        )
        assert r.source_ip == "1.2.3.4"

    def test_brute_force_record(
        self,
    ) -> None:
        from app.models.idsips_models import (
            BruteForceRecord,
        )

        r = BruteForceRecord(
            ip="1.2.3.4",
            username="admin",
            attempt_count=5,
        )
        assert r.attempt_count == 5

    def test_injection_record(self) -> None:
        from app.models.idsips_models import (
            InjectionRecord,
        )

        r = InjectionRecord(
            injection_type="sql",
            pattern_count=3,
        )
        assert r.injection_type == "sql"

    def test_session_alert_record(
        self,
    ) -> None:
        from app.models.idsips_models import (
            SessionAlertRecord,
        )

        r = SessionAlertRecord(
            session_id="s1",
            alert_type="ip_change",
        )
        assert r.session_id == "s1"

    def test_block_record(self) -> None:
        from app.models.idsips_models import (
            BlockRecord,
        )

        r = BlockRecord(
            ip="1.2.3.4",
            duration_minutes=120,
            permanent=True,
        )
        assert r.permanent is True

    def test_ioc_record(self) -> None:
        from app.models.idsips_models import (
            IOCRecord,
        )

        r = IOCRecord(
            value="1.2.3.4",
            active=True,
        )
        assert r.active is True

    def test_incident_record(self) -> None:
        from app.models.idsips_models import (
            IncidentRecord,
        )

        r = IncidentRecord(
            incident_type="brute_force",
            source_ip="1.2.3.4",
            evidence_count=3,
        )
        assert r.evidence_count == 3

    def test_idsips_status(self) -> None:
        from app.models.idsips_models import (
            IDSIPSStatus,
        )

        s = IDSIPSStatus(
            total_incidents=10,
            open_incidents=3,
            blocked_ips=5,
        )
        assert s.total_incidents == 10
        assert s.blocked_ips == 5

    def test_config_settings(self) -> None:
        from app.config import settings

        assert hasattr(
            settings, "idsips_enabled"
        )
        assert hasattr(
            settings, "detection_mode"
        )
        assert hasattr(
            settings, "auto_block"
        )
        assert hasattr(
            settings, "threat_feeds"
        )
        assert hasattr(
            settings,
            "incident_retention_days",
        )
