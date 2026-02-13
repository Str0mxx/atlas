"""CodingMetaAgent testleri.

Pipeline calistirma, analiz, uretim, test, debug,
refactor ve gecmis yonetimi testleri.
"""

import pytest

from app.agents.coding_meta_agent import CodingMetaAgent
from app.models.selfcode import (
    CodeGenerationRequest,
    CodeGenStrategy,
    ExecutionResult,
    ExecutionStatus,
    PipelineResult,
    PipelineStage,
)


# === Yardimci Fonksiyonlar ===


def _make_meta(**kwargs) -> CodingMetaAgent:
    """Test icin CodingMetaAgent olusturur."""
    return CodingMetaAgent(**kwargs)


def _make_request(**kwargs) -> CodeGenerationRequest:
    """Test icin CodeGenerationRequest olusturur."""
    defaults = {
        "description": "Basit fonksiyon uret",
        "strategy": CodeGenStrategy.TEMPLATE,
        "context": {"name": "add", "body": "return a + b", "params": "a, b"},
    }
    defaults.update(kwargs)
    return CodeGenerationRequest(**defaults)


# === Init Testleri ===


class TestInit:
    """CodingMetaAgent init testleri."""

    def test_defaults(self) -> None:
        ma = _make_meta()
        assert ma.max_iterations == 3
        assert ma.require_tests is True

    def test_custom(self) -> None:
        ma = _make_meta(max_iterations=5, require_tests=False)
        assert ma.max_iterations == 5
        assert ma.require_tests is False

    def test_sub_components_initialized(self) -> None:
        ma = _make_meta()
        assert ma.analyzer is not None
        assert ma.generator is not None
        assert ma.test_generator is not None
        assert ma.executor is not None
        assert ma.debugger is not None
        assert ma.refactorer is not None


# === ExecutePipeline Testleri ===


class TestExecutePipeline:
    """execute_pipeline() testleri."""

    def test_basic_pipeline(self) -> None:
        ma = _make_meta()
        req = _make_request()
        result = ma.execute_pipeline(req)
        assert isinstance(result, PipelineResult)
        assert len(result.stages_completed) > 0

    def test_pipeline_includes_generate(self) -> None:
        ma = _make_meta()
        req = _make_request()
        result = ma.execute_pipeline(req)
        assert PipelineStage.GENERATE in result.stages_completed

    def test_pipeline_includes_analyze(self) -> None:
        ma = _make_meta()
        req = _make_request()
        result = ma.execute_pipeline(req)
        assert PipelineStage.ANALYZE in result.stages_completed

    def test_pipeline_with_tests(self) -> None:
        ma = _make_meta(require_tests=True)
        req = _make_request()
        result = ma.execute_pipeline(req)
        assert PipelineStage.TEST in result.stages_completed

    def test_pipeline_without_tests(self) -> None:
        ma = _make_meta(require_tests=False)
        req = _make_request()
        result = ma.execute_pipeline(req)
        assert PipelineStage.TEST not in result.stages_completed

    def test_pipeline_has_artifacts(self) -> None:
        ma = _make_meta()
        req = _make_request()
        result = ma.execute_pipeline(req)
        assert "generated_code" in result.artifacts

    def test_pipeline_duration_tracked(self) -> None:
        ma = _make_meta()
        req = _make_request()
        result = ma.execute_pipeline(req)
        assert result.duration >= 0

    def test_pipeline_history_updated(self) -> None:
        ma = _make_meta()
        req = _make_request()
        ma.execute_pipeline(req)
        assert len(ma.get_pipeline_history()) == 1

    def test_multiple_pipelines(self) -> None:
        ma = _make_meta()
        ma.execute_pipeline(_make_request())
        ma.execute_pipeline(_make_request(description="Ikinci gorev"))
        assert len(ma.get_pipeline_history()) == 2

    def test_pipeline_result_has_id(self) -> None:
        ma = _make_meta()
        result = ma.execute_pipeline(_make_request())
        assert result.id != ""


# === AnalyzeTask Testleri ===


class TestAnalyzeTask:
    """analyze_task() testleri."""

    def test_empty_source(self) -> None:
        ma = _make_meta()
        req = _make_request(context={})
        report = ma.analyze_task(req)
        assert report.score == 100.0

    def test_with_source(self) -> None:
        ma = _make_meta()
        req = _make_request(context={"source": "def f():\n    return 1\n"})
        report = ma.analyze_task(req)
        assert report.score > 0


# === GenerateCode Testleri ===


class TestGenerateCode:
    """generate_code() testleri."""

    def test_generates_code(self) -> None:
        ma = _make_meta()
        req = _make_request()
        result = ma.generate_code(req)
        assert result.code != ""

    def test_confidence_set(self) -> None:
        ma = _make_meta()
        req = _make_request()
        result = ma.generate_code(req)
        assert result.confidence >= 0.0


# === GenerateTests Testleri ===


class TestGenerateTests:
    """generate_tests() testleri."""

    def test_generates_tests(self) -> None:
        ma = _make_meta()
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        suite = ma.generate_tests(code)
        assert len(suite.tests) > 0

    def test_empty_code(self) -> None:
        ma = _make_meta()
        suite = ma.generate_tests("")
        assert isinstance(suite.tests, list)


# === RunTests Testleri ===


class TestRunTests:
    """run_tests() testleri."""

    def test_sandbox_execution(self) -> None:
        ma = _make_meta()
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        suite = ma.generate_tests(code)
        result = ma.run_tests(suite)
        assert result.status == ExecutionStatus.COMPLETED


# === DebugFailures Testleri ===


class TestDebugFailures:
    """debug_failures() testleri."""

    def test_debug_report_generated(self) -> None:
        ma = _make_meta()
        exec_result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            stderr='NameError: name "x" is not defined',
        )
        report = ma.debug_failures("y = 1\nprint(x)\n", exec_result)
        assert report.root_cause != ""


# === RefactorResult Testleri ===


class TestRefactorResult:
    """refactor_result() testleri."""

    def test_clean_code_unchanged(self) -> None:
        ma = _make_meta()
        code = "def f():\n    return 1\n"
        result = ma.refactor_result(code)
        assert result.success is True

    def test_dead_code_removed(self) -> None:
        ma = _make_meta()
        code = "def f():\n    return 1\n    print('dead')\n"
        result = ma.refactor_result(code)
        assert result.success is True


# === GetPipelineHistory Testleri ===


class TestGetPipelineHistory:
    """get_pipeline_history() testleri."""

    def test_empty_history(self) -> None:
        ma = _make_meta()
        assert ma.get_pipeline_history() == []

    def test_history_is_copy(self) -> None:
        ma = _make_meta()
        ma.execute_pipeline(_make_request())
        history = ma.get_pipeline_history()
        history.clear()
        assert len(ma.get_pipeline_history()) == 1
