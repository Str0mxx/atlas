"""ATLAS CodingMetaAgent - Self-coding pipeline orkestratoru.

Kod uretim pipeline'ini bastan sona yonetir:
analiz -> uretim -> test -> hata ayiklama -> yeniden duzenleme.
"""

import logging
import time

from app.core.selfcode.code_analyzer import CodeAnalyzer
from app.core.selfcode.code_executor import SafeExecutor
from app.core.selfcode.code_generator import CodeGenerator
from app.core.selfcode.debugger import AutoDebugger
from app.core.selfcode.refactorer import CodeRefactorer
from app.core.selfcode.test_generator import TestGenerator
from app.models.selfcode import (
    CodeAnalysisReport,
    CodeGenerationRequest,
    DebugReport,
    ExecutionResult,
    ExecutionStatus,
    GeneratedCode,
    PipelineResult,
    PipelineStage,
    RefactorResult,
    TestSuite,
)

logger = logging.getLogger(__name__)


class CodingMetaAgent:
    """Tam kod uretim pipeline'ini orkestre eden meta agent.

    Attributes:
        max_iterations: Hata ayiklama dongusu icin maks deneme.
        require_tests: Test asamasi zorunlu mu.
    """

    def __init__(self, max_iterations: int = 3, require_tests: bool = True) -> None:
        """CodingMetaAgent'i baslatir.

        Args:
            max_iterations: Hata ayiklama dongusunde maks deneme sayisi.
            require_tests: Test uretimi ve calistirmasi zorunlu mu.
        """
        self.max_iterations = max_iterations
        self.require_tests = require_tests
        self.analyzer = CodeAnalyzer()
        self.generator = CodeGenerator()
        self.test_generator = TestGenerator()
        self.executor = SafeExecutor()
        self.debugger = AutoDebugger()
        self.refactorer = CodeRefactorer()
        self._history: list[PipelineResult] = []
        logger.info("CodingMetaAgent baslatildi (max_iter=%d, tests=%s)", max_iterations, require_tests)

    def execute_pipeline(self, request: CodeGenerationRequest) -> PipelineResult:
        """Tam pipeline'i calistirir: analiz -> uretim -> test -> debug -> refactor.

        Args:
            request: Kod uretim istegi.

        Returns:
            Tum asama sonuclarini iceren PipelineResult.
        """
        start = time.monotonic()
        stages: list[PipelineStage] = []
        artifacts: dict[str, str] = {}
        errors: list[str] = []
        total = 5 if self.require_tests else 3
        logger.info("Pipeline basliyor: '%s'", request.description[:80])

        # 1. Analiz
        try:
            analysis = self.analyze_task(request)
            stages.append(PipelineStage.ANALYZE)
            artifacts["analysis_score"] = str(analysis.score)
        except Exception as exc:
            errors.append(f"Analiz hatasi: {exc}")
            return self._create_pipeline_result(stages, total, False, artifacts, errors, start)

        # 2. Uretim
        try:
            generated = self.generate_code(request)
            stages.append(PipelineStage.GENERATE)
            artifacts["generated_code"] = generated.code
            artifacts["generation_confidence"] = str(generated.confidence)
        except Exception as exc:
            errors.append(f"Uretim hatasi: {exc}")
            return self._create_pipeline_result(stages, total, False, artifacts, errors, start)

        # Testler zorunlu degilse dogrudan refactor'a gec
        if not self.require_tests:
            try:
                ref = self.refactor_result(generated.code)
                stages.append(PipelineStage.REFACTOR)
                artifacts["refactored_code"] = ref.refactored_code
            except Exception as exc:
                errors.append(f"Refactor hatasi: {exc}")
            return self._create_pipeline_result(stages, total, not errors, artifacts, errors, start)

        # 3. Test
        try:
            test_suite = self.generate_tests(generated.code)
            exec_result = self.run_tests(test_suite)
            stages.append(PipelineStage.TEST)
            artifacts["test_count"] = str(len(test_suite.tests))
            tests_passed = exec_result.status == ExecutionStatus.COMPLETED
        except Exception as exc:
            errors.append(f"Test hatasi: {exc}")
            return self._create_pipeline_result(stages, total, False, artifacts, errors, start)

        # 4. Debug (testler basarisizsa)
        current_code = generated.code
        if not tests_passed:
            try:
                report = self.debug_failures(current_code, exec_result)
                stages.append(PipelineStage.DEBUG)
                if report.auto_fixed:
                    fixed = self.debugger.auto_fix(exec_result.stderr, current_code)
                    if fixed:
                        current_code = fixed
                        artifacts["generated_code"] = current_code
                artifacts["debug_root_cause"] = report.root_cause
            except Exception as exc:
                errors.append(f"Debug hatasi: {exc}")
        else:
            stages.append(PipelineStage.DEBUG)

        # 5. Refactor
        try:
            ref = self.refactor_result(current_code)
            stages.append(PipelineStage.REFACTOR)
            artifacts["refactored_code"] = ref.refactored_code
        except Exception as exc:
            errors.append(f"Refactor hatasi: {exc}")

        result = self._create_pipeline_result(stages, total, not errors, artifacts, errors, start)
        logger.info("Pipeline bitti: basari=%s, %d/%d, %.2fs", result.success, len(stages), total, result.duration)
        return result

    def analyze_task(self, request: CodeGenerationRequest) -> CodeAnalysisReport:
        """Kod uretim gorevini analiz eder ve gereksinimleri belirler."""
        source = request.context.get("source", "")
        file_path = request.context.get("file_path", "")
        if source:
            return self.analyzer.analyze(source, file_path=file_path)
        return CodeAnalysisReport(file_path=file_path, score=100.0)

    def generate_code(self, request: CodeGenerationRequest) -> GeneratedCode:
        """CodeGenerator ile istek icin kod uretir."""
        result = self.generator.generate(request)
        logger.info("Kod uretildi: guven=%.2f, satir=%d", result.confidence, result.code.count("\n") + 1)
        return result

    def generate_tests(self, code: str) -> TestSuite:
        """Uretilen kod icin TestGenerator ile test grubu olusturur."""
        suite = self.test_generator.generate_tests(code)
        logger.info("Test grubu: %d test", len(suite.tests))
        return suite

    def run_tests(self, test_suite: TestSuite) -> ExecutionResult:
        """TestSuite'i birlestirip SafeExecutor ile calistirir."""
        parts: list[str] = list(test_suite.imports) + [""]
        if test_suite.fixtures_code:
            parts.extend([test_suite.fixtures_code, ""])
        for tc in test_suite.tests:
            parts.extend([tc.code, ""])
        result = self.executor.execute_tests("\n".join(parts))
        logger.info("Testler: durum=%s, sure=%.2fs", result.status.value, result.duration)
        return result

    def debug_failures(self, code: str, exec_result: ExecutionResult) -> DebugReport:
        """Test hatalarini analiz edip max_iterations kadar otomatik duzeltme dener."""
        error_text = exec_result.stderr or exec_result.stdout
        parsed = self.debugger.parse_error(error_text)
        root_cause = self.debugger.find_root_cause(error_text, code)
        suggestions = self.debugger.suggest_fixes(error_text, code)
        auto_fixed = False
        current_code = code

        for i in range(self.max_iterations):
            fixed = self.debugger.auto_fix(error_text, current_code)
            if fixed is None:
                break
            current_code = fixed
            auto_fixed = True
            logger.info("Otomatik duzeltme uygulandi (deneme %d/%d)", i + 1, self.max_iterations)
            # Duzeltilmis kodu tekrar test et
            re_exec = self.run_tests(self.generate_tests(current_code))
            if re_exec.status == ExecutionStatus.COMPLETED:
                break
            error_text = re_exec.stderr or re_exec.stdout

        return DebugReport(
            error_type=parsed.get("error_type", ""),
            error_message=parsed.get("message", ""),
            file_path=parsed.get("file", ""),
            line_number=int(parsed.get("line", "0") or "0"),
            stack_trace=error_text, root_cause=root_cause,
            suggestions=suggestions, auto_fixed=auto_fixed,
        )

    def refactor_result(self, code: str) -> RefactorResult:
        """Uretilen kodu yeniden duzenler (olu kod temizligi + basitlestirme)."""
        dead = self.refactorer.remove_dead_code(code)
        simp = self.refactorer.simplify(dead.refactored_code)
        return RefactorResult(
            success=True, original_code=code,
            refactored_code=simp.refactored_code,
            changes_count=dead.changes_count + simp.changes_count,
            lines_added=dead.lines_added + simp.lines_added,
            lines_removed=dead.lines_removed + simp.lines_removed,
        )

    def get_pipeline_history(self) -> list[PipelineResult]:
        """Gecmis pipeline sonuclarini dondurur."""
        return list(self._history)

    def _create_pipeline_result(
        self, stages_completed: list[PipelineStage], total_stages: int,
        success: bool, artifacts: dict[str, str],
        errors: list[str], start_time: float,
    ) -> PipelineResult:
        """Asama sonuclarindan PipelineResult olusturur ve gecmise ekler."""
        result = PipelineResult(
            stages_completed=stages_completed, total_stages=total_stages,
            success=success, artifacts=artifacts,
            errors=errors, duration=round(time.monotonic() - start_time, 3),
        )
        self._history.append(result)
        return result
