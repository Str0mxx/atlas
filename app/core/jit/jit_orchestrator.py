"""ATLAS JIT Orkestratoru modulu.

Request -> Check -> Build -> Test -> Deploy -> Respond
pipeline'i, timeout yonetimi, kismi basari,
build ogrenme ve basarili build cache.
"""

import logging
import time
from typing import Any

from app.core.jit.api_discoverer import APIDiscoverer
from app.core.jit.capability_checker import CapabilityChecker
from app.core.jit.credential_manager import CredentialManager
from app.core.jit.live_integrator import LiveIntegrator
from app.core.jit.rapid_builder import RapidBuilder
from app.core.jit.requirement_analyzer import RequirementAnalyzer
from app.core.jit.sandbox_tester import SandboxTester
from app.core.jit.user_communicator import UserCommunicator
from app.models.jit import (
    BuildPhase,
    CapabilityStatus,
    JITResult,
    SandboxTestResult,
)

logger = logging.getLogger(__name__)


class JITOrchestrator:
    """JIT orkestratoru.

    Tum JIT bilesenlerini koordine eder:
    Request -> Check -> Build -> Test -> Deploy -> Respond.

    Attributes:
        _checker: Yetenek kontrol.
        _analyzer: Ihtiyac analizi.
        _discoverer: API kesfi.
        _builder: Hizli insa.
        _integrator: Canli entegrasyon.
        _credentials: Kimlik yonetimi.
        _tester: Sandbox test.
        _communicator: Kullanici iletisimi.
        _cache: Basarili build cache.
        _history: Build gecmisi.
    """

    def __init__(self, timeout_seconds: int = 120) -> None:
        """JIT orkestratoru baslatir.

        Args:
            timeout_seconds: Maksimum islem suresi.
        """
        self._checker = CapabilityChecker()
        self._analyzer = RequirementAnalyzer()
        self._discoverer = APIDiscoverer()
        self._builder = RapidBuilder()
        self._integrator = LiveIntegrator()
        self._credentials = CredentialManager()
        self._tester = SandboxTester()
        self._communicator = UserCommunicator()
        self._timeout = timeout_seconds
        self._cache: dict[str, JITResult] = {}
        self._history: list[JITResult] = []
        self._learning: dict[str, dict[str, Any]] = {}

        logger.info("JITOrchestrator baslatildi (timeout=%ds)", timeout_seconds)

    def process_request(self, request: str) -> JITResult:
        """Tam JIT pipeline'i calistirir.

        Args:
            request: Kullanici istegi.

        Returns:
            JITResult nesnesi.
        """
        start_time = time.monotonic()
        phases_completed: list[str] = []

        # Cache kontrolu
        cache_key = request.lower().strip()
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached_copy = cached.model_copy()
            cached_copy.cached = True
            logger.info("Cache'den donuluyor: %s", cached.capability_name)
            return cached_copy

        # 1. Analiz
        self._communicator.send_progress(request[:30], BuildPhase.ANALYZING, 10, "Ihtiyac analiz ediliyor...")
        spec = self._analyzer.analyze(request)
        capability_name = spec.parsed_intent.replace(":", "_").replace(" ", "_")
        phases_completed.append(BuildPhase.ANALYZING.value)

        # Timeout kontrolu
        if self._is_timed_out(start_time):
            return self._make_timeout_result(request, capability_name, phases_completed, start_time)

        # 2. Yetenek kontrolu
        if self._checker.check_exists(capability_name):
            similar = self._checker.find_similar(capability_name, top_k=1)
            if similar and similar[0].similarity_score > 0.8:
                result = JITResult(
                    request=request,
                    capability_name=capability_name,
                    status=CapabilityStatus.ACTIVE,
                    phases_completed=["existing"],
                    build_time_ms=(time.monotonic() - start_time) * 1000,
                )
                self._history.append(result)
                return result

        # 3. API kesfi
        self._communicator.send_progress(capability_name, BuildPhase.DISCOVERING, 25, "API'ler kesfediliyor...")
        all_endpoints = []
        for api_name in spec.required_apis:
            endpoints = self._discoverer.search(api_name)
            all_endpoints.extend(endpoints)

            # Kimlik kontrolu
            auth = self._discoverer.get_auth_method(api_name)
            if auth.value != "none" and not self._credentials.has_credential(api_name):
                self._credentials.request_api_key(api_name)
        phases_completed.append(BuildPhase.DISCOVERING.value)

        if self._is_timed_out(start_time):
            return self._make_timeout_result(request, capability_name, phases_completed, start_time)

        # 4. Insa
        self._communicator.send_progress(capability_name, BuildPhase.BUILDING, 45, "Kod uretiliyor...")
        generated_modules = []

        # Istemci kodu
        if all_endpoints:
            for api_name in spec.required_apis:
                ep_list = [ep for ep in all_endpoints if api_name in ep.name]
                if ep_list:
                    client_code = self._builder.generate_client(api_name, ep_list)
                    generated_modules.append(client_code)

        # Agent kodu
        agent_code = self._builder.generate_agent(capability_name, spec)
        generated_modules.append(agent_code)

        # Model kodu
        model_code = self._builder.generate_models(capability_name)
        generated_modules.append(model_code)

        # Test kodu
        test_code = self._builder.generate_tests(capability_name, generated_modules)
        generated_modules.append(test_code)

        # Baglanti
        self._builder.wire_together(generated_modules)
        phases_completed.append(BuildPhase.BUILDING.value)

        if self._is_timed_out(start_time):
            return self._make_timeout_result(request, capability_name, phases_completed, start_time)

        # 5. Test
        self._communicator.send_progress(capability_name, BuildPhase.TESTING, 65, "Testler calistiriliyor...")
        tests_passed = 0
        tests_total = 0

        for module in generated_modules:
            if module.code_type == "test":
                continue
            results = self._tester.run_all_checks(module)
            for r in results:
                tests_total += 1
                if r.result == SandboxTestResult.PASSED:
                    tests_passed += 1
        phases_completed.append(BuildPhase.TESTING.value)

        # Test basarisizliginda kismi sonuc
        if tests_total > 0 and tests_passed < tests_total * 0.5:
            self._communicator.send_error(
                capability_name,
                f"Testlerin %{int(tests_passed / tests_total * 100)}'i gecti",
                "Kod gozden gecirilmeli",
            )
            result = JITResult(
                request=request,
                capability_name=capability_name,
                status=CapabilityStatus.FAILED,
                phases_completed=phases_completed,
                build_time_ms=(time.monotonic() - start_time) * 1000,
                tests_passed=tests_passed,
                tests_total=tests_total,
                rollback_available=True,
            )
            self._history.append(result)
            return result

        if self._is_timed_out(start_time):
            return self._make_timeout_result(request, capability_name, phases_completed, start_time)

        # 6. Entegrasyon
        self._communicator.send_progress(capability_name, BuildPhase.INTEGRATING, 80, "Entegre ediliyor...")
        for module in generated_modules:
            self._integrator.hot_load(module)
        self._integrator.register_with_master(capability_name, {"intent": spec.parsed_intent})
        self._integrator.update_routing(capability_name, f"jit_{capability_name}")
        phases_completed.append(BuildPhase.INTEGRATING.value)

        # 7. Deploy
        self._communicator.send_progress(capability_name, BuildPhase.DEPLOYING, 95, "Deploy ediliyor...")
        phases_completed.append(BuildPhase.DEPLOYING.value)

        # 8. Basari
        self._communicator.send_progress(capability_name, BuildPhase.COMPLETE, 100, "Tamamlandi!")
        self._communicator.send_success(capability_name, f"{len(generated_modules)} modul uretildi ve deploy edildi")
        phases_completed.append(BuildPhase.COMPLETE.value)

        build_time = (time.monotonic() - start_time) * 1000
        result = JITResult(
            request=request,
            capability_name=capability_name,
            status=CapabilityStatus.ACTIVE,
            phases_completed=phases_completed,
            build_time_ms=build_time,
            tests_passed=tests_passed,
            tests_total=tests_total,
            rollback_available=True,
        )

        # Cache'e ekle
        self._cache[cache_key] = result
        self._history.append(result)

        # Ogrenim kaydi
        self._learn_from_build(capability_name, result)

        logger.info(
            "JIT tamamlandi: %s (%.0fms, %d/%d test gecti)",
            capability_name, build_time, tests_passed, tests_total,
        )
        return result

    def rollback(self, capability_name: str) -> bool:
        """Yetenegi geri alir.

        Args:
            capability_name: Yetenek adi.

        Returns:
            Basarili mi.
        """
        result = self._integrator.rollback_capability(capability_name)
        if result:
            # Cache'den cikar
            keys_to_remove = [k for k, v in self._cache.items() if v.capability_name == capability_name]
            for key in keys_to_remove:
                del self._cache[key]

            self._communicator.send_error(capability_name, "Yetenek geri alindi", "Tekrar denenebilir")
        return result

    def _is_timed_out(self, start_time: float) -> bool:
        """Timeout kontrolu yapar."""
        return (time.monotonic() - start_time) > self._timeout

    def _make_timeout_result(
        self,
        request: str,
        capability_name: str,
        phases: list[str],
        start_time: float,
    ) -> JITResult:
        """Timeout sonucu olusturur."""
        self._communicator.send_error(capability_name, "Zaman asimi", "Islem cok uzun surdu")
        result = JITResult(
            request=request,
            capability_name=capability_name,
            status=CapabilityStatus.FAILED,
            phases_completed=phases,
            build_time_ms=(time.monotonic() - start_time) * 1000,
            rollback_available=bool(phases),
        )
        self._history.append(result)
        return result

    def _learn_from_build(self, capability_name: str, result: JITResult) -> None:
        """Build'den ogrenir.

        Args:
            capability_name: Yetenek adi.
            result: Build sonucu.
        """
        learning = self._learning.get(capability_name, {"attempts": 0, "successes": 0})
        learning["attempts"] += 1
        if result.status == CapabilityStatus.ACTIVE:
            learning["successes"] += 1
        learning["last_build_time_ms"] = result.build_time_ms
        learning["last_test_ratio"] = result.tests_passed / max(result.tests_total, 1)
        self._learning[capability_name] = learning

    @property
    def checker(self) -> CapabilityChecker:
        """Yetenek kontrol."""
        return self._checker

    @property
    def analyzer(self) -> RequirementAnalyzer:
        """Ihtiyac analizi."""
        return self._analyzer

    @property
    def discoverer(self) -> APIDiscoverer:
        """API kesfi."""
        return self._discoverer

    @property
    def builder(self) -> RapidBuilder:
        """Hizli insa."""
        return self._builder

    @property
    def integrator(self) -> LiveIntegrator:
        """Canli entegrasyon."""
        return self._integrator

    @property
    def credentials(self) -> CredentialManager:
        """Kimlik yonetimi."""
        return self._credentials

    @property
    def tester(self) -> SandboxTester:
        """Sandbox test."""
        return self._tester

    @property
    def communicator(self) -> UserCommunicator:
        """Kullanici iletisimi."""
        return self._communicator

    @property
    def cache_count(self) -> int:
        """Cache'deki build sayisi."""
        return len(self._cache)

    @property
    def history(self) -> list[JITResult]:
        """Build gecmisi."""
        return list(self._history)

    @property
    def build_count(self) -> int:
        """Toplam build sayisi."""
        return len(self._history)
