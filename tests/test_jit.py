"""ATLAS Just-in-Time Capability sistemi testleri.

CapabilityChecker, RequirementAnalyzer, APIDiscoverer,
RapidBuilder, LiveIntegrator, CredentialManager,
SandboxTester, UserCommunicator, JITOrchestrator
icin kapsamli testler.
"""

import pytest

from app.core.jit.api_discoverer import APIDiscoverer
from app.core.jit.capability_checker import CapabilityChecker
from app.core.jit.credential_manager import CredentialManager
from app.core.jit.jit_orchestrator import JITOrchestrator
from app.core.jit.live_integrator import LiveIntegrator
from app.core.jit.rapid_builder import RapidBuilder
from app.core.jit.requirement_analyzer import RequirementAnalyzer
from app.core.jit.sandbox_tester import SandboxTester
from app.core.jit.user_communicator import UserCommunicator
from app.models.jit import (
    APIEndpoint,
    AuthMethod,
    BuildPhase,
    CapabilityInfo,
    CapabilityStatus,
    CredentialEntry,
    EffortLevel,
    FeasibilityLevel,
    GeneratedCode,
    JITResult,
    OutputFormat,
    RequirementSpec,
    SandboxResult,
    SecurityLevel,
    SandboxTestResult,
)


# === Yardimci Fonksiyonlar ===


def _make_endpoint(name: str = "test_api", path: str = "/test") -> APIEndpoint:
    """Test endpoint olusturur."""
    return APIEndpoint(name=name, base_url="https://api.test.com", path=path)


def _make_code(
    module: str = "test_module",
    code_type: str = "client",
    source: str = "x = 1\n",
    lines: int = 1,
) -> GeneratedCode:
    """Test kodu olusturur."""
    return GeneratedCode(
        module_name=module, code_type=code_type,
        source_code=source, line_count=lines,
    )


def _make_spec(intent: str = "fetch:data", apis: list[str] | None = None) -> RequirementSpec:
    """Test spesifikasyonu olusturur."""
    return RequirementSpec(parsed_intent=intent, required_apis=apis or [])


# === Model Testleri ===


class TestJITModels:
    """JIT veri modeli testleri."""

    def test_capability_info_defaults(self):
        c = CapabilityInfo()
        assert c.status == CapabilityStatus.AVAILABLE
        assert c.effort == EffortLevel.MODERATE
        assert c.feasibility == FeasibilityLevel.MEDIUM

    def test_requirement_spec_defaults(self):
        r = RequirementSpec()
        assert r.output_format == OutputFormat.JSON
        assert r.security_level == SecurityLevel.API_KEY
        assert r.priority == 5

    def test_api_endpoint_defaults(self):
        e = APIEndpoint()
        assert e.method == "GET"
        assert e.auth_method == AuthMethod.NONE
        assert e.response_format == OutputFormat.JSON

    def test_generated_code_defaults(self):
        g = GeneratedCode()
        assert g.code_type == ""
        assert g.line_count == 0

    def test_credential_entry_defaults(self):
        c = CredentialEntry()
        assert c.auth_method == AuthMethod.API_KEY
        assert c.is_set is False

    def test_sandbox_result_defaults(self):
        s = SandboxResult()
        assert s.result == SandboxTestResult.PASSED
        assert s.security_issues == []

    def test_jit_result_defaults(self):
        j = JITResult()
        assert j.status == CapabilityStatus.ACTIVE
        assert j.cached is False
        assert j.rollback_available is False

    def test_enum_values(self):
        assert CapabilityStatus.BUILDING.value == "building"
        assert EffortLevel.TRIVIAL.value == "trivial"
        assert BuildPhase.TESTING.value == "testing"
        assert SandboxTestResult.PASSED.value == "passed"
        assert AuthMethod.OAUTH2.value == "oauth2"


# === CapabilityChecker Testleri ===


class TestCapabilityChecker:
    """Yetenek kontrol testleri."""

    def test_check_exists_builtin(self):
        cc = CapabilityChecker()
        assert cc.check_exists("server") is True
        assert cc.check_exists("monitor") is True
        assert cc.check_exists("security") is True

    def test_check_exists_not_found(self):
        cc = CapabilityChecker()
        assert cc.check_exists("quantum_teleportation") is False

    def test_check_exists_custom(self):
        cc = CapabilityChecker()
        cc.register_capability(CapabilityInfo(name="custom_cap"))
        assert cc.check_exists("custom_cap") is True

    def test_find_similar(self):
        cc = CapabilityChecker()
        cc.register_capability(CapabilityInfo(name="email_sender", description="Email gonderme"))
        results = cc.find_similar("email")
        assert len(results) >= 1

    def test_find_similar_empty(self):
        cc = CapabilityChecker()
        results = cc.find_similar("zzzznonexistent")
        assert len(results) == 0

    def test_find_similar_top_k(self):
        cc = CapabilityChecker()
        results = cc.find_similar("server", top_k=3)
        assert len(results) <= 3

    def test_estimate_effort_trivial(self):
        cc = CapabilityChecker()
        effort = cc.estimate_effort("parse data")
        assert effort in (EffortLevel.TRIVIAL, EffortLevel.EASY)

    def test_estimate_effort_complex(self):
        cc = CapabilityChecker()
        effort = cc.estimate_effort("oauth real-time streaming machine learning pipeline with database migration and webhook")
        assert effort in (EffortLevel.COMPLEX, EffortLevel.HARD)

    def test_estimate_effort_moderate(self):
        cc = CapabilityChecker()
        effort = cc.estimate_effort("rest api query")
        assert effort in (EffortLevel.MODERATE, EffortLevel.EASY, EffortLevel.HARD)

    def test_analyze_dependencies_api(self):
        cc = CapabilityChecker()
        deps = cc.analyze_dependencies("weather_api")
        assert "httpx" in deps
        assert "authentication" in deps

    def test_analyze_dependencies_email(self):
        cc = CapabilityChecker()
        deps = cc.analyze_dependencies("email_service")
        assert len(deps) >= 1

    def test_analyze_dependencies_empty(self):
        cc = CapabilityChecker()
        deps = cc.analyze_dependencies("generic_thing")
        assert isinstance(deps, list)

    def test_assess_feasibility_high(self):
        cc = CapabilityChecker()
        level = cc.assess_feasibility("parse json data")
        assert level in (FeasibilityLevel.HIGH, FeasibilityLevel.MEDIUM)

    def test_assess_feasibility_low(self):
        cc = CapabilityChecker()
        level = cc.assess_feasibility(
            "oauth streaming ml pipeline",
            {"api_keys_available": False, "network_access": False},
        )
        assert level in (FeasibilityLevel.LOW, FeasibilityLevel.INFEASIBLE)

    def test_register_capability(self):
        cc = CapabilityChecker()
        cc.register_capability(CapabilityInfo(name="new_cap"))
        assert cc.capability_count == 1
        assert cc.get_capability("new_cap") is not None

    def test_get_capability_not_found(self):
        cc = CapabilityChecker()
        assert cc.get_capability("nonexistent") is None

    def test_all_capabilities(self):
        cc = CapabilityChecker()
        cc.register_capability(CapabilityInfo(name="a"))
        cc.register_capability(CapabilityInfo(name="b"))
        assert len(cc.all_capabilities) == 2


# === RequirementAnalyzer Testleri ===


class TestRequirementAnalyzer:
    """Ihtiyac analizi testleri."""

    def test_analyze_basic(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Hava durumu bilgisini getir")
        assert spec.raw_request == "Hava durumu bilgisini getir"
        assert "weather" in spec.required_apis

    def test_parse_intent_fetch(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Verileri getir")
        assert spec.parsed_intent.startswith("fetch:")

    def test_parse_intent_send(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Email gonder kullaniciya")
        assert spec.parsed_intent.startswith("send:")

    def test_parse_intent_analyze(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Performansi incele ve degerlendir")
        assert spec.parsed_intent.startswith("analyze:")

    def test_parse_intent_create(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Yeni rapor olustur")
        assert spec.parsed_intent.startswith("create:")

    def test_parse_intent_monitor(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Sunucuyu izle ve takip et")
        assert spec.parsed_intent.startswith("monitor:")

    def test_extract_apis_gmail(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Gmail uzerinden email gonder")
        assert "gmail" in spec.required_apis

    def test_extract_apis_telegram(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Telegram bot ile mesaj gonder")
        assert "telegram" in spec.required_apis

    def test_extract_apis_multiple(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Google Ads kampanya olustur ve telegram ile bildir")
        assert "google_ads" in spec.required_apis
        assert "telegram" in spec.required_apis

    def test_identify_data_sources_database(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Veritabani sorgula ve sonuclari getir")
        assert "database" in spec.data_sources

    def test_identify_data_sources_web(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Web sitesinden veri cek")
        assert "web" in spec.data_sources

    def test_determine_output_csv(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Sonuclari CSV formatinda disa aktar")
        assert spec.output_format == OutputFormat.CSV

    def test_determine_output_html(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("HTML rapor olustur")
        assert spec.output_format == OutputFormat.HTML

    def test_determine_output_default_json(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Veri getir")
        assert spec.output_format == OutputFormat.JSON

    def test_analyze_security_oauth(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Instagram uzerinden sosyal medya postu paylas")
        assert spec.security_level == SecurityLevel.OAUTH

    def test_analyze_security_api_key(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Hava durumu API'sinden veri cek")
        assert spec.security_level == SecurityLevel.API_KEY

    def test_extract_constraints_time(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("30 saniye icinde sonuc getir")
        assert spec.constraints.get("saniye") == 30

    def test_extract_constraints_schedule(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Her gun kontrol et")
        assert spec.constraints.get("schedule") == "daily"

    def test_extract_constraints_realtime(self):
        ra = RequirementAnalyzer()
        spec = ra.analyze("Gercek zamanli veri akisi")
        assert spec.constraints.get("realtime") is True

    def test_spec_count(self):
        ra = RequirementAnalyzer()
        ra.analyze("Test 1")
        ra.analyze("Test 2")
        assert ra.spec_count == 2

    def test_specs_property(self):
        ra = RequirementAnalyzer()
        ra.analyze("Test")
        assert len(ra.specs) == 1


# === APIDiscoverer Testleri ===


class TestAPIDiscoverer:
    """API kesfi testleri."""

    def test_search_known_api(self):
        ad = APIDiscoverer()
        endpoints = ad.search("telegram")
        assert len(endpoints) >= 1
        assert any("sendMessage" in ep.name for ep in endpoints)

    def test_search_unknown_api(self):
        ad = APIDiscoverer()
        endpoints = ad.search("nonexistent_api_xyz")
        assert len(endpoints) == 0

    def test_search_cached(self):
        ad = APIDiscoverer()
        ad.search("telegram")
        endpoints2 = ad.search("telegram")
        assert len(endpoints2) >= 1

    def test_find_documentation(self):
        ad = APIDiscoverer()
        doc = ad.find_documentation("github")
        assert "github" in doc.lower()

    def test_find_documentation_not_found(self):
        ad = APIDiscoverer()
        doc = ad.find_documentation("nonexistent")
        assert doc == ""

    def test_get_auth_method(self):
        ad = APIDiscoverer()
        auth = ad.get_auth_method("telegram")
        assert auth == AuthMethod.BEARER_TOKEN

    def test_get_auth_method_oauth(self):
        ad = APIDiscoverer()
        auth = ad.get_auth_method("gmail")
        assert auth == AuthMethod.OAUTH2

    def test_get_auth_method_unknown(self):
        ad = APIDiscoverer()
        auth = ad.get_auth_method("nonexistent")
        assert auth == AuthMethod.NONE

    def test_get_rate_limit(self):
        ad = APIDiscoverer()
        limit = ad.get_rate_limit("telegram")
        assert limit == 30

    def test_get_rate_limit_unknown(self):
        ad = APIDiscoverer()
        limit = ad.get_rate_limit("nonexistent")
        assert limit == 0

    def test_register_custom_api(self):
        ad = APIDiscoverer()
        ad.register_api("custom", {"base_url": "https://custom.api", "auth": "api_key", "endpoints": ["data"]})
        endpoints = ad.search("custom")
        assert len(endpoints) == 1

    def test_discovered_count(self):
        ad = APIDiscoverer()
        ad.search("telegram")
        ad.search("github")
        assert ad.discovered_count == 2

    def test_known_apis(self):
        ad = APIDiscoverer()
        apis = ad.known_apis
        assert "telegram" in apis
        assert "github" in apis

    def test_fuzzy_search(self):
        ad = APIDiscoverer()
        endpoints = ad.search("weather")
        assert len(endpoints) >= 1


# === RapidBuilder Testleri ===


class TestRapidBuilder:
    """Hizli insa testleri."""

    def test_generate_client(self):
        rb = RapidBuilder()
        endpoints = [_make_endpoint("test_data", "/data"), _make_endpoint("test_users", "/users")]
        code = rb.generate_client("test", endpoints)
        assert code.code_type == "client"
        assert code.line_count > 0
        assert "class TestClient" in code.source_code

    def test_generate_agent(self):
        rb = RapidBuilder()
        spec = _make_spec("fetch:weather")
        code = rb.generate_agent("weather_checker", spec)
        assert code.code_type == "agent"
        assert "WeatherCheckerAgent" in code.source_code

    def test_generate_models(self):
        rb = RapidBuilder()
        code = rb.generate_models("weather", {"temp": "float", "city": "str"})
        assert code.code_type == "model"
        assert "WeatherModel" in code.source_code
        assert "temp: float" in code.source_code

    def test_generate_models_defaults(self):
        rb = RapidBuilder()
        code = rb.generate_models("basic")
        assert "name: str" in code.source_code

    def test_generate_tests(self):
        rb = RapidBuilder()
        modules = [_make_code("mod1", "client", "x=1\n", 1), _make_code("mod2", "agent", "y=2\n", 1)]
        code = rb.generate_tests("feature", modules)
        assert code.code_type == "test"
        assert "TestMod1" in code.source_code

    def test_wire_together(self):
        rb = RapidBuilder()
        modules = [
            _make_code("client", "client", "x=1\n", 10, ),
            _make_code("agent", "agent", "y=2\n", 20),
        ]
        modules[0].dependencies = ["httpx"]
        wiring = rb.wire_together(modules)
        assert "client" in wiring["modules"]
        assert "httpx" in wiring["dependencies"]
        assert wiring["total_lines"] == 30

    def test_generated_count(self):
        rb = RapidBuilder()
        rb.generate_models("a")
        rb.generate_models("b")
        assert rb.generated_count == 2

    def test_total_lines(self):
        rb = RapidBuilder()
        rb.generate_models("a")
        assert rb.total_lines > 0

    def test_generated_modules_property(self):
        rb = RapidBuilder()
        rb.generate_models("x")
        assert len(rb.generated_modules) == 1

    def test_class_name_conversion(self):
        rb = RapidBuilder()
        assert rb._to_class_name("hello_world") == "HelloWorld"
        assert rb._to_class_name("api-client") == "ApiClient"


# === LiveIntegrator Testleri ===


class TestLiveIntegrator:
    """Canli entegrasyon testleri."""

    def test_hot_load(self):
        li = LiveIntegrator()
        code = _make_code("test_mod")
        assert li.hot_load(code) is True
        assert li.is_loaded("test_mod")
        assert li.loaded_count == 1

    def test_hot_load_update(self):
        li = LiveIntegrator()
        li.hot_load(_make_code("mod1", lines=10))
        li.hot_load(_make_code("mod1", lines=20))
        assert li.loaded_count == 1
        assert li.rollback_depth == 2

    def test_register_with_master(self):
        li = LiveIntegrator()
        assert li.register_with_master("weather", {"type": "agent"}) is True
        assert "weather" in li.registered_capabilities

    def test_update_routing(self):
        li = LiveIntegrator()
        li.update_routing("weather", "weather_agent")
        assert li.routing_table["weather"] == "weather_agent"

    def test_rollback_add(self):
        li = LiveIntegrator()
        li.hot_load(_make_code("mod1"))
        assert li.loaded_count == 1
        rolled = li.rollback(1)
        assert rolled == 1
        assert li.loaded_count == 0

    def test_rollback_update(self):
        li = LiveIntegrator()
        li.hot_load(_make_code("mod1", lines=10))
        li.hot_load(_make_code("mod1", lines=20))
        li.rollback(1)
        status = li.get_status("mod1")
        assert status["line_count"] == 10

    def test_rollback_empty(self):
        li = LiveIntegrator()
        assert li.rollback(1) == 0

    def test_rollback_capability(self):
        li = LiveIntegrator()
        li.hot_load(_make_code("weather_client"))
        li.hot_load(_make_code("weather_agent"))
        li.update_routing("weather", "handler")
        li.register_with_master("weather", {})
        assert li.rollback_capability("weather") is True
        assert li.loaded_count == 0

    def test_rollback_capability_not_found(self):
        li = LiveIntegrator()
        assert li.rollback_capability("nonexistent") is False

    def test_get_status_not_loaded(self):
        li = LiveIntegrator()
        status = li.get_status("nonexistent")
        assert status["status"] == "not_loaded"

    def test_routing_table(self):
        li = LiveIntegrator()
        li.update_routing("a", "handler_a")
        li.update_routing("b", "handler_b")
        assert len(li.routing_table) == 2


# === CredentialManager Testleri ===


class TestCredentialManager:
    """Kimlik yonetimi testleri."""

    def test_request_api_key(self):
        cm = CredentialManager()
        req = cm.request_api_key("weather_api")
        assert req["service"] == "weather_api"
        assert req["status"] == "pending"
        assert cm.pending_count == 1

    def test_store_credential(self):
        cm = CredentialManager()
        assert cm.store_credential("weather", "sk-12345") is True
        assert cm.has_credential("weather") is True

    def test_has_credential_false(self):
        cm = CredentialManager()
        assert cm.has_credential("nonexistent") is False

    def test_store_clears_pending(self):
        cm = CredentialManager()
        cm.request_api_key("svc")
        assert cm.pending_count == 1
        cm.store_credential("svc", "key123")
        assert cm.pending_count == 0

    def test_rotate_key(self):
        cm = CredentialManager()
        cm.store_credential("svc", "old_key")
        assert cm.rotate_key("svc", "new_key") is True
        cred = cm.get_credential_info("svc")
        assert cred.last_rotated is not None

    def test_rotate_key_not_found(self):
        cm = CredentialManager()
        assert cm.rotate_key("nonexistent", "key") is False

    def test_init_oauth_flow(self):
        cm = CredentialManager()
        result = cm.init_oauth_flow("gmail", "client_id_123", ["read", "send"])
        assert "state" in result
        cred = cm.get_credential_info("gmail")
        assert cred.auth_method == AuthMethod.OAUTH2

    def test_complete_oauth(self):
        cm = CredentialManager()
        cm.init_oauth_flow("gmail", "cid")
        assert cm.complete_oauth("gmail", "access_tok", "refresh_tok") is True
        assert cm.has_credential("gmail") is True

    def test_complete_oauth_no_flow(self):
        cm = CredentialManager()
        assert cm.complete_oauth("nonexistent", "tok") is False

    def test_refresh_token(self):
        cm = CredentialManager()
        cm.init_oauth_flow("gmail", "cid")
        cm.complete_oauth("gmail", "at", "rt")
        assert cm.refresh_token("gmail") is True

    def test_refresh_token_no_refresh(self):
        cm = CredentialManager()
        cm.init_oauth_flow("svc", "cid")
        cm.complete_oauth("svc", "at", "")  # no refresh token
        assert cm.refresh_token("svc") is False

    def test_remove_credential(self):
        cm = CredentialManager()
        cm.store_credential("svc", "key")
        assert cm.remove_credential("svc") is True
        assert cm.has_credential("svc") is False

    def test_remove_credential_not_found(self):
        cm = CredentialManager()
        assert cm.remove_credential("nonexistent") is False

    def test_credential_count(self):
        cm = CredentialManager()
        cm.store_credential("a", "k1")
        cm.store_credential("b", "k2")
        assert cm.credential_count == 2

    def test_services_with_credentials(self):
        cm = CredentialManager()
        cm.store_credential("active", "key")
        cm.request_api_key("pending")
        services = cm.services_with_credentials
        assert "active" in services
        assert "pending" not in services


# === SandboxTester Testleri ===


class TestSandboxTester:
    """Sandbox test testleri."""

    def test_run_isolated_pass(self):
        st = SandboxTester()
        code = _make_code("mod", "client", "x = 1\ny = 2\n", 2)
        result = st.run_isolated(code)
        assert result.result == SandboxTestResult.PASSED

    def test_run_isolated_syntax_error(self):
        st = SandboxTester()
        code = _make_code("bad", "client", "def foo(:\n  pass\n", 2)
        result = st.run_isolated(code)
        assert result.result == SandboxTestResult.FAILED
        assert "Syntax" in result.error

    def test_mock_service(self):
        st = SandboxTester()
        st.mock_service("weather", {"temp": 25})
        mock = st.get_mock("weather")
        assert mock["temp"] == 25

    def test_get_mock_not_found(self):
        st = SandboxTester()
        assert st.get_mock("nonexistent") is None

    def test_validate_response_pass(self):
        st = SandboxTester()
        result = st.validate_response({"name": "ok", "value": 1}, ["name", "value"])
        assert result.result == SandboxTestResult.PASSED

    def test_validate_response_fail(self):
        st = SandboxTester()
        result = st.validate_response({"name": "ok"}, ["name", "value", "status"])
        assert result.result == SandboxTestResult.FAILED
        assert "value" in result.error

    def test_check_performance_pass(self):
        st = SandboxTester()
        code = _make_code("perf", "client", "x = 1\n", 5)
        result = st.check_performance(code)
        assert result.result == SandboxTestResult.PASSED

    def test_check_performance_too_many_lines(self):
        st = SandboxTester()
        code = _make_code("big", "client", "x = 1\n" * 100, 1500)
        result = st.check_performance(code)
        assert result.result == SandboxTestResult.FAILED

    def test_scan_security_clean(self):
        st = SandboxTester()
        code = _make_code("safe", "client", "x = 1\nprint(x)\n", 2)
        result = st.scan_security(code)
        assert result.result == SandboxTestResult.PASSED
        assert len(result.security_issues) == 0

    def test_scan_security_eval(self):
        st = SandboxTester()
        code = _make_code("unsafe", "client", "result = eval(user_input)\n", 1)
        result = st.scan_security(code)
        assert result.result == SandboxTestResult.FAILED
        assert len(result.security_issues) >= 1

    def test_scan_security_exec(self):
        st = SandboxTester()
        code = _make_code("unsafe2", "client", "exec(code_str)\n", 1)
        result = st.scan_security(code)
        assert result.result == SandboxTestResult.FAILED

    def test_scan_security_subprocess(self):
        st = SandboxTester()
        code = _make_code("cmd", "client", "import subprocess\n", 1)
        result = st.scan_security(code)
        assert result.result == SandboxTestResult.FAILED

    def test_run_all_checks(self):
        st = SandboxTester()
        code = _make_code("mod", "client", "x = 1\ny = 2\n", 2)
        results = st.run_all_checks(code)
        assert len(results) == 3  # isolated + performance + security

    def test_result_count(self):
        st = SandboxTester()
        st.run_isolated(_make_code(source="a=1\n"))
        st.run_isolated(_make_code(source="b=2\n"))
        assert st.result_count == 2

    def test_pass_fail_counts(self):
        st = SandboxTester()
        st.run_isolated(_make_code(source="a=1\n"))
        st.run_isolated(_make_code(source="def f(:\n"))
        assert st.pass_count == 1
        assert st.fail_count == 1


# === UserCommunicator Testleri ===


class TestUserCommunicator:
    """Kullanici iletisimi testleri."""

    def test_send_progress(self):
        uc = UserCommunicator()
        progress = uc.send_progress("weather", BuildPhase.BUILDING, 50, "Insa ediliyor")
        assert progress.phase == BuildPhase.BUILDING
        assert progress.progress_pct == 50

    def test_send_progress_clamped(self):
        uc = UserCommunicator()
        p = uc.send_progress("x", BuildPhase.COMPLETE, 150)
        assert p.progress_pct == 100.0

    def test_request_info(self):
        uc = UserCommunicator()
        req = uc.request_info("weather", "Hangi sehir?", ["Istanbul", "Ankara"])
        assert req["type"] == "info_request"
        assert req["options"] == ["Istanbul", "Ankara"]

    def test_request_approval(self):
        uc = UserCommunicator()
        req = uc.request_approval("weather", "Deploy edilsin mi?")
        assert req["type"] == "approval"
        assert uc.pending_approval_count == 1

    def test_set_approval(self):
        uc = UserCommunicator()
        uc.request_approval("weather", "Deploy?")
        assert uc.set_approval("deploy_weather", True) is True
        assert uc.is_approved("deploy_weather") is True
        assert uc.pending_approval_count == 0

    def test_set_approval_rejected(self):
        uc = UserCommunicator()
        uc.request_approval("x", "Deploy?")
        uc.set_approval("deploy_x", False)
        assert uc.is_approved("deploy_x") is False

    def test_set_approval_not_found(self):
        uc = UserCommunicator()
        assert uc.set_approval("nonexistent", True) is False

    def test_is_approved_not_found(self):
        uc = UserCommunicator()
        assert uc.is_approved("nonexistent") is False

    def test_send_error(self):
        uc = UserCommunicator()
        msg = uc.send_error("weather", "API hatasi", "Anahtari kontrol edin")
        assert msg["type"] == "error"
        assert msg["suggestion"] == "Anahtari kontrol edin"

    def test_send_success(self):
        uc = UserCommunicator()
        msg = uc.send_success("weather", "Basariyla deploy edildi")
        assert msg["type"] == "success"

    def test_get_messages_filtered(self):
        uc = UserCommunicator()
        uc.send_error("a", "hata")
        uc.send_success("b", "ok")
        errors = uc.get_messages("error")
        assert len(errors) == 1
        all_msgs = uc.get_messages()
        assert len(all_msgs) == 2

    def test_message_count(self):
        uc = UserCommunicator()
        uc.send_progress("x", BuildPhase.ANALYZING, 10)
        uc.send_success("x", "ok")
        assert uc.message_count == 2

    def test_progress_history(self):
        uc = UserCommunicator()
        uc.send_progress("x", BuildPhase.ANALYZING, 10)
        uc.send_progress("x", BuildPhase.BUILDING, 50)
        assert len(uc.progress_history) == 2


# === JITOrchestrator Testleri ===


class TestJITOrchestrator:
    """JIT orkestratoru testleri."""

    def test_process_request_basic(self):
        jit = JITOrchestrator()
        result = jit.process_request("Hava durumu bilgisini getir")
        assert result.status in (CapabilityStatus.ACTIVE, CapabilityStatus.FAILED)
        assert len(result.phases_completed) >= 1
        assert result.build_time_ms > 0

    def test_process_request_cached(self):
        jit = JITOrchestrator()
        r1 = jit.process_request("Test istegi")
        r2 = jit.process_request("Test istegi")
        assert r2.cached is True

    def test_process_request_with_api(self):
        jit = JITOrchestrator()
        result = jit.process_request("Telegram ile mesaj gonder")
        assert result.status in (CapabilityStatus.ACTIVE, CapabilityStatus.FAILED)
        assert BuildPhase.DISCOVERING.value in result.phases_completed

    def test_rollback(self):
        jit = JITOrchestrator()
        jit.process_request("Test capability olustur")
        # Cache'den capability name bul
        if jit.history:
            cap_name = jit.history[0].capability_name
            result = jit.rollback(cap_name)
            # Rollback sonrasi cache temizlenmeli
            assert jit.cache_count == 0

    def test_build_count(self):
        jit = JITOrchestrator()
        jit.process_request("Test 1")
        jit.process_request("Test 2")
        assert jit.build_count == 2

    def test_history_property(self):
        jit = JITOrchestrator()
        jit.process_request("Test")
        assert len(jit.history) == 1

    def test_component_accessors(self):
        jit = JITOrchestrator()
        assert jit.checker is not None
        assert jit.analyzer is not None
        assert jit.discoverer is not None
        assert jit.builder is not None
        assert jit.integrator is not None
        assert jit.credentials is not None
        assert jit.tester is not None
        assert jit.communicator is not None

    def test_cache_count(self):
        jit = JITOrchestrator()
        jit.process_request("Unique request 12345")
        assert jit.cache_count >= 1

    def test_phases_order(self):
        jit = JITOrchestrator()
        result = jit.process_request("API veri cek ve raporla")
        if result.status == CapabilityStatus.ACTIVE:
            assert BuildPhase.ANALYZING.value in result.phases_completed
            assert BuildPhase.BUILDING.value in result.phases_completed
            assert BuildPhase.COMPLETE.value in result.phases_completed

    def test_tests_tracked(self):
        jit = JITOrchestrator()
        result = jit.process_request("Basit veri isleme")
        assert result.tests_total >= 0
        assert result.tests_passed >= 0


# === Entegrasyon Testleri ===


class TestJITIntegration:
    """End-to-end entegrasyon testleri."""

    def test_full_pipeline_no_api(self):
        """API gerektirmeyen basit yetenek."""
        jit = JITOrchestrator()
        result = jit.process_request("Basit veri formatla ve cikart")
        assert result.build_time_ms > 0
        assert len(result.phases_completed) >= 3

    def test_full_pipeline_with_api(self):
        """API gerektiren yetenek."""
        jit = JITOrchestrator()
        result = jit.process_request("Weather API'sinden hava durumu bilgisi getir")
        assert BuildPhase.DISCOVERING.value in result.phases_completed

    def test_credential_flow(self):
        """Kimlik bilgisi akisi."""
        cm = CredentialManager()
        cm.request_api_key("test_api")
        assert cm.pending_count == 1
        cm.store_credential("test_api", "sk-test-key")
        assert cm.pending_count == 0
        assert cm.has_credential("test_api") is True

    def test_build_test_deploy(self):
        """Insa -> Test -> Deploy akisi."""
        builder = RapidBuilder()
        tester = SandboxTester()
        integrator = LiveIntegrator()

        # Insa
        code = builder.generate_models("test_cap")
        # Test
        results = tester.run_all_checks(code)
        all_passed = all(r.result == SandboxTestResult.PASSED for r in results)
        # Deploy
        if all_passed:
            integrator.hot_load(code)
            assert integrator.is_loaded("test_cap_model")

    def test_rollback_flow(self):
        """Rollback akisi."""
        integrator = LiveIntegrator()
        integrator.hot_load(_make_code("cap_client"))
        integrator.hot_load(_make_code("cap_agent"))
        integrator.update_routing("cap", "handler")
        assert integrator.loaded_count == 2

        integrator.rollback_capability("cap")
        assert integrator.loaded_count == 0
