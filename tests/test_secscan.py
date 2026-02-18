"""Continuous Security Scanner testleri."""

import pytest

from app.core.secscan.vulnerability_scanner import (
    VulnerabilityScanner,
)
from app.core.secscan.dependency_auditor import (
    DependencyAuditor,
)
from app.core.secscan.config_misconfig_detector import (
    ConfigMisconfigDetector,
)
from app.core.secscan.port_scanner import (
    PortScanner,
)
from app.core.secscan.ssl_certificate_monitor import (
    SSLCertificateMonitor,
)
from app.core.secscan.code_security_analyzer import (
    CodeSecurityAnalyzer,
)
from app.core.secscan.cve_tracker import (
    CVETracker,
)
from app.core.secscan.patch_recommender import (
    PatchRecommender,
)
from app.core.secscan.secscan_orchestrator import (
    SecScanOrchestrator,
)
from app.models.secscan_models import (
    ScanType,
    SeverityLevel,
    PatchStatus,
    CertGrade,
    PortState,
    ComplianceStatus,
    VulnerabilityRecord,
    DependencyRecord,
    ConfigIssueRecord,
    PortRecord,
    CertificateRecord,
    CVERecord,
    PatchRecord,
    SecurityPosture,
)


# ─── VulnerabilityScanner ───


class TestVulnerabilityScanner:
    """VulnerabilityScanner testleri."""

    def setup_method(self) -> None:
        self.scanner = VulnerabilityScanner()

    def test_init(self) -> None:
        assert self.scanner.scan_count == 0
        assert len(self.scanner._vulnerabilities) == 0

    def test_scan_code_clean(self) -> None:
        r = self.scanner.scan_code(
            code="x = 1 + 2",
            source="test.py",
        )
        assert r["scanned"] is True
        assert r["total_findings"] == 0

    def test_scan_code_sql_injection(self) -> None:
        code = 'cursor.execute("SELECT * FROM %s" % table)'
        r = self.scanner.scan_code(
            code=code, source="db.py"
        )
        assert r["scanned"] is True
        assert r["total_findings"] >= 1

    def test_scan_code_xss(self) -> None:
        code = 'document.write("hello")'
        r = self.scanner.scan_code(
            code=code, source="app.js"
        )
        assert r["scanned"] is True
        assert r["total_findings"] >= 1

    def test_scan_code_hardcoded_secret(self) -> None:
        code = 'password = "mysuperpassword123"'
        r = self.scanner.scan_code(
            code=code, source="config.py"
        )
        assert r["scanned"] is True
        assert r["total_findings"] >= 1

    def test_scan_code_command_injection(self) -> None:
        code = 'os.system("rm -rf " + path)'
        r = self.scanner.scan_code(
            code=code, source="util.py"
        )
        assert r["scanned"] is True
        assert r["total_findings"] >= 1

    def test_scan_code_path_traversal(self) -> None:
        code = 'open("../../etc/passwd")'
        r = self.scanner.scan_code(
            code=code, source="file.py"
        )
        assert r["scanned"] is True
        assert r["total_findings"] >= 1

    def test_scan_count_increments(self) -> None:
        self.scanner.scan_code(code="x=1")
        self.scanner.scan_code(code="y=2")
        assert self.scanner.scan_count == 2

    def test_check_cve(self) -> None:
        r = self.scanner.check_cve(
            component="openssl",
            version="1.1.1",
        )
        assert r["checked"] is True
        assert r["component"] == "openssl"

    def test_mark_fixed(self) -> None:
        code = 'os.system("cmd")'
        scan = self.scanner.scan_code(
            code=code, source="t.py"
        )
        fid = scan["findings"][0]["finding_id"]
        r = self.scanner.mark_fixed(
            finding_id=fid,
            fix_details="replaced",
        )
        assert r["marked"] is True

    def test_mark_fixed_not_found(self) -> None:
        r = self.scanner.mark_fixed(
            finding_id="nope"
        )
        assert r["marked"] is False

    def test_schedule_scan(self) -> None:
        r = self.scanner.schedule_scan(
            target="repo",
            frequency="weekly",
        )
        assert r["scheduled"] is True
        assert r["frequency"] == "weekly"

    def test_get_summary(self) -> None:
        self.scanner.scan_code(
            code='os.system("x")',
            source="a.py",
        )
        r = self.scanner.get_summary()
        assert r["retrieved"] is True
        assert r["total_scans"] == 1
        assert r["unfixed"] >= 1


# ─── DependencyAuditor ───


class TestDependencyAuditor:
    """DependencyAuditor testleri."""

    def setup_method(self) -> None:
        self.auditor = DependencyAuditor()

    def test_init(self) -> None:
        assert self.auditor.package_count == 0

    def test_add_package(self) -> None:
        r = self.auditor.add_package(
            name="requests",
            version="2.28.0",
            latest_version="2.31.0",
            license_type="Apache-2.0",
        )
        assert r["added"] is True
        assert r["outdated"] is True

    def test_add_package_up_to_date(self) -> None:
        r = self.auditor.add_package(
            name="flask",
            version="3.0.0",
            latest_version="3.0.0",
        )
        assert r["added"] is True
        assert r["outdated"] is False

    def test_report_vulnerability(self) -> None:
        self.auditor.add_package(
            name="django", version="3.2.0"
        )
        r = self.auditor.report_vulnerability(
            package_name="django",
            cve_id="CVE-2023-1234",
            severity="critical",
        )
        assert r["reported"] is True

    def test_report_vulnerability_not_found(self) -> None:
        r = self.auditor.report_vulnerability(
            package_name="nonexistent",
            cve_id="CVE-X",
        )
        assert r["reported"] is False

    def test_audit_packages(self) -> None:
        self.auditor.add_package(
            name="pkg1",
            version="1.0",
            latest_version="2.0",
        )
        r = self.auditor.audit_packages()
        assert r["audited"] is True
        assert r["total"] == 1
        assert r["outdated"] == 1

    def test_get_update_recommendations(self) -> None:
        self.auditor.add_package(
            name="old",
            version="1.0",
            latest_version="2.0",
        )
        r = self.auditor.get_update_recommendations()
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_check_license_compliance(self) -> None:
        self.auditor.add_package(
            name="good",
            version="1.0",
            license_type="MIT",
        )
        r = self.auditor.check_license_compliance()
        assert r["checked"] is True
        assert r["compliant"] is True

    def test_check_license_violation(self) -> None:
        self.auditor.add_package(
            name="bad",
            version="1.0",
            license_type="GPL-3.0",
        )
        r = self.auditor.check_license_compliance()
        assert r["checked"] is True
        assert r["compliant"] is False
        assert r["violation_count"] == 1

    def test_get_vulnerable_packages(self) -> None:
        self.auditor.add_package(
            name="vuln", version="1.0"
        )
        self.auditor.report_vulnerability(
            package_name="vuln",
            cve_id="CVE-1",
        )
        r = self.auditor.get_vulnerable_packages()
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_package_count(self) -> None:
        self.auditor.add_package(
            name="a", version="1.0"
        )
        self.auditor.add_package(
            name="b", version="2.0"
        )
        assert self.auditor.package_count == 2


# ─── ConfigMisconfigDetector ───


class TestConfigMisconfigDetector:
    """ConfigMisconfigDetector testleri."""

    def setup_method(self) -> None:
        self.detector = ConfigMisconfigDetector()

    def test_init(self) -> None:
        assert self.detector.check_count == 0

    def test_check_config_clean(self) -> None:
        r = self.detector.check_config(
            config_content="port = 8080",
            source="app.conf",
        )
        assert r["checked"] is True
        assert r["total_issues"] == 0

    def test_check_config_debug(self) -> None:
        r = self.detector.check_config(
            config_content="DEBUG = true",
            source="settings.py",
        )
        assert r["checked"] is True
        assert r["total_issues"] >= 1

    def test_check_config_default_password(self) -> None:
        r = self.detector.check_config(
            config_content="password = admin",
            source=".env",
        )
        assert r["checked"] is True
        assert r["total_issues"] >= 1

    def test_check_config_exposed_port(self) -> None:
        r = self.detector.check_config(
            config_content="host = 0.0.0.0",
            source="server.conf",
        )
        assert r["checked"] is True
        assert r["total_issues"] >= 1

    def test_check_config_no_ssl(self) -> None:
        r = self.detector.check_config(
            config_content="ssl = false",
            source="nginx.conf",
        )
        assert r["checked"] is True
        assert r["total_issues"] >= 1

    def test_add_rule(self) -> None:
        r = self.detector.add_rule(
            name="test_rule",
            pattern=r"test\s*=\s*true",
            severity="low",
        )
        assert r["added"] is True

    def test_add_rule_invalid_regex(self) -> None:
        r = self.detector.add_rule(
            name="bad",
            pattern="[invalid",
        )
        assert r["added"] is False

    def test_resolve_issue(self) -> None:
        res = self.detector.check_config(
            config_content="DEBUG = true",
            source="s.py",
        )
        iid = res["issues"][0]["issue_id"]
        r = self.detector.resolve_issue(
            issue_id=iid,
            resolution="Disabled debug",
        )
        assert r["resolved"] is True

    def test_resolve_issue_not_found(self) -> None:
        r = self.detector.resolve_issue(
            issue_id="nope"
        )
        assert r["resolved"] is False

    def test_get_hardening_suggestions(self) -> None:
        self.detector.check_config(
            config_content="DEBUG = true",
            source="s.py",
        )
        r = self.detector.get_hardening_suggestions()
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_get_summary(self) -> None:
        self.detector.check_config(
            config_content="password = 123456",
            source="e.env",
        )
        r = self.detector.get_summary()
        assert r["retrieved"] is True
        assert r["total_issues"] >= 1

    def test_check_count_increments(self) -> None:
        self.detector.check_config(
            config_content="x=1"
        )
        self.detector.check_config(
            config_content="y=2"
        )
        assert self.detector.check_count == 2


# ─── PortScanner ───


class TestPortScanner:
    """PortScanner testleri."""

    def setup_method(self) -> None:
        self.scanner = PortScanner()

    def test_init(self) -> None:
        assert self.scanner.scan_count == 0

    def test_scan_ports(self) -> None:
        r = self.scanner.scan_ports(
            host="192.168.1.1"
        )
        assert r["scanned"] is True
        assert r["total_open"] > 0

    def test_scan_specific_ports(self) -> None:
        r = self.scanner.scan_ports(
            host="10.0.0.1",
            ports=[80, 443],
        )
        assert r["scanned"] is True
        assert r["total_open"] == 2

    def test_identify_service(self) -> None:
        r = self.scanner.identify_service(port=22)
        assert r["identified"] is True
        assert r["service"] == "SSH"

    def test_identify_service_unknown(self) -> None:
        r = self.scanner.identify_service(port=9999)
        assert r["identified"] is True
        assert r["service"] == "unknown"

    def test_identify_risky_port(self) -> None:
        r = self.scanner.identify_service(port=23)
        assert r["risky"] is True

    def test_check_unnecessary_services(self) -> None:
        self.scanner.scan_ports(
            host="srv1",
            ports=[22, 80, 443, 3389],
        )
        r = self.scanner.check_unnecessary_services(
            host="srv1",
            required_ports=[22, 80, 443],
        )
        assert r["checked"] is True
        assert r["count"] == 1

    def test_add_firewall_rule(self) -> None:
        r = self.scanner.add_firewall_rule(
            port=23, action="block"
        )
        assert r["added"] is True
        assert r["action"] == "block"

    def test_validate_firewall_compliant(self) -> None:
        self.scanner.scan_ports(
            host="fw1", ports=[80, 443]
        )
        self.scanner.add_firewall_rule(
            port=23, action="block"
        )
        r = self.scanner.validate_firewall(
            host="fw1"
        )
        assert r["validated"] is True
        assert r["compliant"] is True

    def test_validate_firewall_violation(self) -> None:
        self.scanner.scan_ports(
            host="fw2", ports=[23, 80]
        )
        self.scanner.add_firewall_rule(
            port=23, action="block"
        )
        r = self.scanner.validate_firewall(
            host="fw2"
        )
        assert r["validated"] is True
        assert r["compliant"] is False
        assert r["violation_count"] == 1

    def test_get_summary(self) -> None:
        self.scanner.scan_ports(
            host="s1", ports=[22, 23]
        )
        r = self.scanner.get_summary()
        assert r["retrieved"] is True
        assert r["total_scans"] == 1
        assert r["risky_ports"] >= 1

    def test_scan_count_increments(self) -> None:
        self.scanner.scan_ports(host="a")
        self.scanner.scan_ports(host="b")
        assert self.scanner.scan_count == 2


# ─── SSLCertificateMonitor ───


class TestSSLCertificateMonitor:
    """SSLCertificateMonitor testleri."""

    def setup_method(self) -> None:
        self.monitor = SSLCertificateMonitor()

    def test_init(self) -> None:
        assert self.monitor.cert_count == 0

    def test_add_certificate(self) -> None:
        r = self.monitor.add_certificate(
            domain="example.com",
            issuer="Let's Encrypt",
            expires_at="2027-06-01T00:00:00+00:00",
            cipher_suite="TLS_AES_256_GCM_SHA384",
        )
        assert r["added"] is True
        assert self.monitor.cert_count == 1

    def test_check_expiration_ok(self) -> None:
        self.monitor.add_certificate(
            domain="safe.com",
            expires_at="2027-12-31T00:00:00+00:00",
        )
        r = self.monitor.check_expiration(
            domain="safe.com"
        )
        assert r["checked"] is True
        assert r["expired"] is False
        assert r["expiring"] is False

    def test_check_expiration_expired(self) -> None:
        self.monitor.add_certificate(
            domain="old.com",
            expires_at="2020-01-01T00:00:00+00:00",
        )
        r = self.monitor.check_expiration(
            domain="old.com"
        )
        assert r["checked"] is True
        assert r["expired"] is True

    def test_check_expiration_not_found(self) -> None:
        r = self.monitor.check_expiration(
            domain="missing.com"
        )
        assert r["checked"] is False

    def test_validate_chain_valid(self) -> None:
        r = self.monitor.validate_chain(
            domain="test.com",
            chain=["leaf", "intermediate", "root"],
        )
        assert r["validated"] is True
        assert r["valid"] is True

    def test_validate_chain_missing_intermediate(self) -> None:
        r = self.monitor.validate_chain(
            domain="test.com",
            chain=["leaf"],
        )
        assert r["validated"] is True
        assert r["valid"] is False

    def test_validate_chain_empty(self) -> None:
        r = self.monitor.validate_chain(
            domain="test.com", chain=[]
        )
        assert r["validated"] is True
        assert r["valid"] is False

    def test_check_cipher_strength_strong(self) -> None:
        self.monitor.add_certificate(
            domain="strong.com",
            cipher_suite="TLS_AES_256_GCM_SHA384",
            key_size=4096,
        )
        r = self.monitor.check_cipher_strength(
            domain="strong.com"
        )
        assert r["checked"] is True
        assert r["strong"] is True
        assert r["grade"] == "A"

    def test_check_cipher_strength_weak(self) -> None:
        self.monitor.add_certificate(
            domain="weak.com",
            cipher_suite="RC4-SHA",
            key_size=1024,
        )
        r = self.monitor.check_cipher_strength(
            domain="weak.com"
        )
        assert r["checked"] is True
        assert r["weak"] is True
        assert r["grade"] == "F"

    def test_check_cipher_not_found(self) -> None:
        r = self.monitor.check_cipher_strength(
            domain="nope.com"
        )
        assert r["checked"] is False

    def test_enable_auto_renewal(self) -> None:
        self.monitor.add_certificate(
            domain="renew.com",
            expires_at="2027-01-01T00:00:00+00:00",
        )
        r = self.monitor.enable_auto_renewal(
            domain="renew.com"
        )
        assert r["enabled"] is True
        assert r["auto_renew"] is True

    def test_enable_auto_renewal_not_found(self) -> None:
        r = self.monitor.enable_auto_renewal(
            domain="nope.com"
        )
        assert r["enabled"] is False

    def test_renew_certificate(self) -> None:
        self.monitor.add_certificate(
            domain="r.com",
            expires_at="2026-06-01T00:00:00+00:00",
        )
        r = self.monitor.renew_certificate(
            domain="r.com",
            new_expires="2027-06-01T00:00:00+00:00",
        )
        assert r["renewed"] is True

    def test_renew_certificate_auto_date(self) -> None:
        self.monitor.add_certificate(
            domain="auto.com",
            expires_at="2026-03-01T00:00:00+00:00",
        )
        r = self.monitor.renew_certificate(
            domain="auto.com"
        )
        assert r["renewed"] is True

    def test_renew_not_found(self) -> None:
        r = self.monitor.renew_certificate(
            domain="nope.com"
        )
        assert r["renewed"] is False

    def test_get_summary(self) -> None:
        self.monitor.add_certificate(
            domain="a.com",
            expires_at="2027-12-31T00:00:00+00:00",
        )
        r = self.monitor.get_summary()
        assert r["retrieved"] is True
        assert r["total_certs"] == 1


# ─── CodeSecurityAnalyzer ───


class TestCodeSecurityAnalyzer:
    """CodeSecurityAnalyzer testleri."""

    def setup_method(self) -> None:
        self.analyzer = CodeSecurityAnalyzer()

    def test_init(self) -> None:
        assert self.analyzer.analysis_count == 0

    def test_analyze_code_clean(self) -> None:
        r = self.analyzer.analyze_code(
            code="x = 1 + 2",
            source="clean.py",
        )
        assert r["analyzed"] is True
        assert r["total_findings"] == 0

    def test_analyze_code_eval(self) -> None:
        r = self.analyzer.analyze_code(
            code='eval("1+1")',
            source="bad.py",
        )
        assert r["analyzed"] is True
        assert r["total_findings"] >= 1

    def test_analyze_code_md5(self) -> None:
        r = self.analyzer.analyze_code(
            code='hashlib.md5("data")',
            source="hash.py",
        )
        assert r["analyzed"] is True
        assert r["total_findings"] >= 1

    def test_analyze_verify_false(self) -> None:
        r = self.analyzer.analyze_code(
            code="requests.get(url, verify=False)",
            source="http.py",
        )
        assert r["analyzed"] is True
        assert r["total_findings"] >= 1

    def test_analyze_except_pass(self) -> None:
        r = self.analyzer.analyze_code(
            code="except: pass",
            source="err.py",
        )
        assert r["analyzed"] is True
        assert r["total_findings"] >= 1

    def test_check_owasp_clean(self) -> None:
        r = self.analyzer.check_owasp(
            code="x = 1",
            source="ok.py",
        )
        assert r["checked"] is True
        assert r["compliant"] is True

    def test_check_owasp_violation(self) -> None:
        r = self.analyzer.check_owasp(
            code='md5("test")',
            source="bad.py",
        )
        assert r["checked"] is True
        assert r["violation_count"] >= 1

    def test_resolve_finding(self) -> None:
        res = self.analyzer.analyze_code(
            code='eval("x")',
            source="t.py",
        )
        fid = res["findings"][0]["finding_id"]
        r = self.analyzer.resolve_finding(
            finding_id=fid,
            resolution="replaced",
        )
        assert r["resolved"] is True

    def test_resolve_finding_not_found(self) -> None:
        r = self.analyzer.resolve_finding(
            finding_id="nope"
        )
        assert r["resolved"] is False

    def test_get_security_score_perfect(self) -> None:
        r = self.analyzer.get_security_score()
        assert r["calculated"] is True
        assert r["score"] == 100
        assert r["grade"] == "A"

    def test_get_security_score_with_issues(self) -> None:
        self.analyzer.analyze_code(
            code='eval("x")',
            source="t.py",
        )
        r = self.analyzer.get_security_score()
        assert r["calculated"] is True
        assert r["score"] < 100

    def test_get_summary(self) -> None:
        self.analyzer.analyze_code(
            code='eval("x")',
            source="t.py",
        )
        r = self.analyzer.get_summary()
        assert r["retrieved"] is True
        assert r["total_analyses"] == 1

    def test_analysis_count_increments(self) -> None:
        self.analyzer.analyze_code(code="a=1")
        self.analyzer.analyze_code(code="b=2")
        assert self.analyzer.analysis_count == 2


# ─── CVETracker ───


class TestCVETracker:
    """CVETracker testleri."""

    def setup_method(self) -> None:
        self.tracker = CVETracker()

    def test_init(self) -> None:
        assert self.tracker.cve_count == 0

    def test_add_cve(self) -> None:
        r = self.tracker.add_cve(
            cve_id="CVE-2024-1234",
            description="Test vuln",
            severity="critical",
            cvss_score=9.8,
            affected_software="openssl",
        )
        assert r["added"] is True
        assert self.tracker.cve_count == 1

    def test_add_duplicate_cve(self) -> None:
        self.tracker.add_cve(
            cve_id="CVE-2024-1111"
        )
        r = self.tracker.add_cve(
            cve_id="CVE-2024-1111"
        )
        assert r["added"] is False

    def test_register_system(self) -> None:
        r = self.tracker.register_system(
            name="web-server",
            software="nginx",
            version="1.24",
        )
        assert r["registered"] is True

    def test_assess_impact_critical(self) -> None:
        self.tracker.add_cve(
            cve_id="CVE-HIGH",
            cvss_score=9.5,
            affected_software="nginx",
        )
        r = self.tracker.assess_impact(
            cve_id="CVE-HIGH"
        )
        assert r["assessed"] is True
        assert r["impact"] == "critical"

    def test_assess_impact_not_found(self) -> None:
        r = self.tracker.assess_impact(
            cve_id="nope"
        )
        assert r["assessed"] is False

    def test_get_affected_systems(self) -> None:
        self.tracker.add_cve(
            cve_id="CVE-A",
            affected_software="redis",
        )
        self.tracker.register_system(
            name="cache",
            software="redis",
            version="7.0",
        )
        r = self.tracker.get_affected_systems(
            cve_id="CVE-A"
        )
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_get_affected_systems_not_found(self) -> None:
        r = self.tracker.get_affected_systems(
            cve_id="nope"
        )
        assert r["retrieved"] is False

    def test_mark_patched(self) -> None:
        self.tracker.add_cve(
            cve_id="CVE-FIX"
        )
        r = self.tracker.mark_patched(
            cve_id="CVE-FIX",
            patch_version="2.0.1",
        )
        assert r["patched"] is True

    def test_mark_patched_not_found(self) -> None:
        r = self.tracker.mark_patched(
            cve_id="nope"
        )
        assert r["patched"] is False

    def test_send_notification(self) -> None:
        r = self.tracker.send_notification(
            cve_id="CVE-2024-5678",
            channel="telegram",
            recipients=["admin"],
        )
        assert r["sent"] is True

    def test_get_unpatched_cves(self) -> None:
        self.tracker.add_cve(
            cve_id="CVE-OPEN",
            severity="high",
        )
        self.tracker.add_cve(
            cve_id="CVE-FIXED"
        )
        self.tracker.mark_patched(
            cve_id="CVE-FIXED"
        )
        r = self.tracker.get_unpatched_cves()
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_get_summary(self) -> None:
        self.tracker.add_cve(
            cve_id="CVE-S1",
            severity="critical",
        )
        r = self.tracker.get_summary()
        assert r["retrieved"] is True
        assert r["total_cves"] == 1
        assert r["critical"] == 1


# ─── PatchRecommender ───


class TestPatchRecommender:
    """PatchRecommender testleri."""

    def setup_method(self) -> None:
        self.recommender = PatchRecommender()

    def test_init(self) -> None:
        assert self.recommender.patch_count == 0

    def test_add_patch(self) -> None:
        r = self.recommender.add_patch(
            name="security-fix",
            version="1.0.1",
            target_software="myapp",
            severity="critical",
            cve_ids=["CVE-2024-1234"],
        )
        assert r["added"] is True
        assert self.recommender.patch_count == 1

    def test_prioritize_patches(self) -> None:
        self.recommender.add_patch(
            name="low-fix",
            severity="low",
        )
        self.recommender.add_patch(
            name="critical-fix",
            severity="critical",
            cve_ids=["CVE-1", "CVE-2"],
        )
        r = self.recommender.prioritize_patches()
        assert r["prioritized"] is True
        assert r["count"] == 2
        recs = r["recommendations"]
        assert recs[0]["severity"] == "critical"

    def test_check_compatibility_ok(self) -> None:
        self.recommender.add_patch(
            name="p1", severity="high"
        )
        pid = self.recommender._patches[0][
            "patch_id"
        ]
        r = self.recommender.check_compatibility(
            patch_id=pid,
            system_version="3.11",
            dependencies=["requests", "flask"],
        )
        assert r["checked"] is True
        assert r["compatible"] is True

    def test_check_compatibility_conflict(self) -> None:
        self.recommender.add_patch(
            name="p2", severity="high"
        )
        pid = self.recommender._patches[0][
            "patch_id"
        ]
        r = self.recommender.check_compatibility(
            patch_id=pid,
            dependencies=["conflict-lib"],
        )
        assert r["checked"] is True
        assert r["compatible"] is False

    def test_check_compatibility_not_found(self) -> None:
        r = self.recommender.check_compatibility(
            patch_id="nope"
        )
        assert r["checked"] is False

    def test_create_rollback_plan(self) -> None:
        self.recommender.add_patch(name="rp1")
        pid = self.recommender._patches[0][
            "patch_id"
        ]
        r = self.recommender.create_rollback_plan(
            patch_id=pid,
            backup_path="/backups/v1",
        )
        assert r["created"] is True

    def test_create_rollback_plan_custom_steps(self) -> None:
        r = self.recommender.create_rollback_plan(
            patch_id="any",
            steps=["Step 1", "Step 2"],
        )
        assert r["created"] is True

    def test_get_testing_guidance(self) -> None:
        self.recommender.add_patch(
            name="tg1",
            target_software="myapp",
        )
        pid = self.recommender._patches[0][
            "patch_id"
        ]
        r = self.recommender.get_testing_guidance(
            patch_id=pid
        )
        assert r["retrieved"] is True
        assert len(r["test_steps"]) > 0

    def test_get_testing_guidance_not_found(self) -> None:
        r = self.recommender.get_testing_guidance(
            patch_id="nope"
        )
        assert r["retrieved"] is False

    def test_schedule_deployment(self) -> None:
        self.recommender.add_patch(name="sd1")
        pid = self.recommender._patches[0][
            "patch_id"
        ]
        r = self.recommender.schedule_deployment(
            patch_id=pid,
            environment="staging",
        )
        assert r["scheduled"] is True
        assert r["environment"] == "staging"

    def test_mark_deployed(self) -> None:
        self.recommender.add_patch(name="md1")
        pid = self.recommender._patches[0][
            "patch_id"
        ]
        r = self.recommender.mark_deployed(
            patch_id=pid
        )
        assert r["deployed"] is True

    def test_mark_deployed_not_found(self) -> None:
        r = self.recommender.mark_deployed(
            patch_id="nope"
        )
        assert r["deployed"] is False

    def test_get_summary(self) -> None:
        self.recommender.add_patch(
            name="s1", severity="critical"
        )
        r = self.recommender.get_summary()
        assert r["retrieved"] is True
        assert r["total_patches"] == 1
        assert r["critical_pending"] == 1


# ─── SecScanOrchestrator ───


class TestSecScanOrchestrator:
    """SecScanOrchestrator testleri."""

    def setup_method(self) -> None:
        self.orch = SecScanOrchestrator()

    def test_init(self) -> None:
        assert self.orch.vuln_scanner is not None
        assert self.orch.dep_auditor is not None
        assert self.orch.config_detector is not None
        assert self.orch.port_scanner is not None
        assert self.orch.ssl_monitor is not None
        assert self.orch.code_analyzer is not None
        assert self.orch.cve_tracker is not None
        assert self.orch.patch_recommender is not None

    def test_full_code_scan_clean(self) -> None:
        r = self.orch.full_code_scan(
            code="x = 1",
            source="clean.py",
        )
        assert r["scanned"] is True
        assert r["total_findings"] == 0

    def test_full_code_scan_vulns(self) -> None:
        code = 'eval("1+1")\nos.system("cmd")'
        r = self.orch.full_code_scan(
            code=code,
            source="bad.py",
        )
        assert r["scanned"] is True
        assert r["total_findings"] >= 1

    def test_infrastructure_scan(self) -> None:
        r = self.orch.infrastructure_scan(
            host="192.168.1.1",
            config_content="DEBUG = true",
            config_source="app.conf",
        )
        assert r["scanned"] is True
        assert "port_scan" in r
        assert "config_check" in r

    def test_dependency_scan(self) -> None:
        self.orch.dep_auditor.add_package(
            name="old-pkg",
            version="1.0",
            latest_version="2.0",
        )
        r = self.orch.dependency_scan()
        assert r["scanned"] is True
        assert "audit" in r

    def test_security_posture(self) -> None:
        r = self.orch.security_posture()
        assert r["retrieved"] is True
        assert "vulnerabilities" in r
        assert "code_security" in r
        assert "ssl_status" in r

    def test_remediation_plan(self) -> None:
        r = self.orch.remediation_plan()
        assert r["planned"] is True

    def test_remediation_plan_with_issues(self) -> None:
        self.orch.vuln_scanner.scan_code(
            code='os.system("cmd")',
            source="t.py",
        )
        self.orch.config_detector.check_config(
            config_content="DEBUG = true",
            source="s.py",
        )
        r = self.orch.remediation_plan()
        assert r["planned"] is True
        assert r["total_actions"] >= 1

    def test_get_analytics(self) -> None:
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert r["vuln_scans"] == 0
        assert r["code_analyses"] == 0

    def test_get_analytics_after_scans(self) -> None:
        self.orch.vuln_scanner.scan_code(
            code="x=1"
        )
        self.orch.code_analyzer.analyze_code(
            code="y=2"
        )
        r = self.orch.get_analytics()
        assert r["vuln_scans"] == 1
        assert r["code_analyses"] == 1


# ─── Models ───


class TestSecScanModels:
    """SecScan model testleri."""

    def test_scan_type_enum(self) -> None:
        assert ScanType.VULNERABILITY == "vulnerability"
        assert ScanType.FULL == "full"

    def test_severity_level_enum(self) -> None:
        assert SeverityLevel.CRITICAL == "critical"
        assert SeverityLevel.INFO == "info"

    def test_patch_status_enum(self) -> None:
        assert PatchStatus.PENDING == "pending"
        assert PatchStatus.DEPLOYED == "deployed"

    def test_cert_grade_enum(self) -> None:
        assert CertGrade.A == "A"
        assert CertGrade.F == "F"

    def test_port_state_enum(self) -> None:
        assert PortState.OPEN == "open"
        assert PortState.CLOSED == "closed"

    def test_compliance_status_enum(self) -> None:
        assert ComplianceStatus.COMPLIANT == "compliant"

    def test_vulnerability_record(self) -> None:
        v = VulnerabilityRecord(
            finding_id="vf_123",
            name="xss",
            severity=SeverityLevel.HIGH,
        )
        assert v.finding_id == "vf_123"
        assert v.fixed is False

    def test_dependency_record(self) -> None:
        d = DependencyRecord(
            name="requests",
            version="2.28",
            outdated=True,
        )
        assert d.outdated is True

    def test_config_issue_record(self) -> None:
        c = ConfigIssueRecord(
            rule="debug_enabled",
            severity=SeverityLevel.HIGH,
        )
        assert c.resolved is False

    def test_port_record(self) -> None:
        p = PortRecord(
            port=22,
            service="SSH",
            risky=False,
        )
        assert p.port == 22

    def test_certificate_record(self) -> None:
        c = CertificateRecord(
            domain="example.com",
            key_size=4096,
        )
        assert c.key_size == 4096

    def test_cve_record(self) -> None:
        c = CVERecord(
            cve_id="CVE-2024-1234",
            cvss_score=9.8,
        )
        assert c.cvss_score == 9.8
        assert c.patched is False

    def test_patch_record(self) -> None:
        p = PatchRecord(
            name="fix-1",
            status=PatchStatus.TESTING,
        )
        assert p.status == PatchStatus.TESTING

    def test_security_posture(self) -> None:
        s = SecurityPosture(
            score=85,
            grade=CertGrade.B,
            critical_count=2,
        )
        assert s.score == 85
        assert s.compliant is True

    def test_security_posture_defaults(self) -> None:
        s = SecurityPosture()
        assert s.score == 100
        assert s.grade == CertGrade.A
