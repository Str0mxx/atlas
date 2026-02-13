"""TaskAnalyzer testleri.

Gorev analizi, arac tespiti, yetenek eksikligi
ve kurulum onerisi testleri.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.bootstrap.task_analyzer import (
    CRITICAL_TOOLS,
    TASK_TOOL_MAP,
    TaskAnalyzer,
)
from app.models.bootstrap import (
    GapSeverity,
    SkillGap,
    TaskAnalysis,
    ToolRequirement,
)


# === Yardimci Fonksiyonlar ===


def _make_analyzer(**kwargs) -> TaskAnalyzer:
    """Test icin TaskAnalyzer olusturur."""
    return TaskAnalyzer(**kwargs)


# === Enum ve Model Testleri ===


class TestGapSeverity:
    """GapSeverity enum testleri."""

    def test_critical(self) -> None:
        assert GapSeverity.CRITICAL == "critical"

    def test_high(self) -> None:
        assert GapSeverity.HIGH == "high"

    def test_medium(self) -> None:
        assert GapSeverity.MEDIUM == "medium"

    def test_low(self) -> None:
        assert GapSeverity.LOW == "low"


class TestToolRequirement:
    """ToolRequirement model testleri."""

    def test_defaults(self) -> None:
        req = ToolRequirement(name="flask")
        assert req.name == "flask"
        assert req.available is False
        assert req.category == "software"

    def test_available(self) -> None:
        req = ToolRequirement(name="flask", available=True)
        assert req.available is True


class TestSkillGap:
    """SkillGap model testleri."""

    def test_defaults(self) -> None:
        gap = SkillGap(capability="docker")
        assert gap.severity == GapSeverity.MEDIUM
        assert gap.resolution_options == []

    def test_critical_gap(self) -> None:
        gap = SkillGap(capability="sqlalchemy", severity=GapSeverity.CRITICAL)
        assert gap.severity == GapSeverity.CRITICAL


class TestTaskAnalysis:
    """TaskAnalysis model testleri."""

    def test_defaults(self) -> None:
        ta = TaskAnalysis()
        assert ta.feasible is True
        assert ta.confidence == 0.5
        assert ta.required_tools == []

    def test_unique_ids(self) -> None:
        a = TaskAnalysis()
        b = TaskAnalysis()
        assert a.id != b.id

    def test_timestamp(self) -> None:
        ta = TaskAnalysis()
        assert ta.analyzed_at is not None


# === TaskAnalyzer Init Testleri ===


class TestTaskAnalyzerInit:
    """TaskAnalyzer init testleri."""

    def test_default(self) -> None:
        ta = _make_analyzer()
        assert ta.tool_map == TASK_TOOL_MAP

    def test_custom_tool_map(self) -> None:
        custom = {"test": ["test-lib"]}
        ta = _make_analyzer(tool_map=custom)
        assert ta.tool_map == custom


# === ExtractRequirements Testleri ===


class TestExtractRequirements:
    """extract_requirements testleri."""

    def test_web_scraping_keywords(self) -> None:
        ta = _make_analyzer()
        reqs = ta.extract_requirements("Web scraping ile veri topla")
        names = [r.name for r in reqs]
        assert "playwright" in names or "beautifulsoup4" in names

    def test_database_keywords(self) -> None:
        ta = _make_analyzer()
        reqs = ta.extract_requirements("Database baglantisi kur")
        names = [r.name for r in reqs]
        assert "sqlalchemy" in names

    def test_multiple_categories(self) -> None:
        ta = _make_analyzer()
        reqs = ta.extract_requirements("Email gonder ve database kaydet")
        names = [r.name for r in reqs]
        assert len(names) > 0

    def test_no_match(self) -> None:
        ta = _make_analyzer()
        reqs = ta.extract_requirements("Merhaba dunya")
        assert reqs == []


# === CheckAvailability Testleri ===


class TestCheckAvailability:
    """check_availability testleri."""

    async def test_all_available(self) -> None:
        ta = _make_analyzer()
        reqs = [ToolRequirement(name="json")]  # stdlib always available
        with patch.object(ta, "_check_python_package", return_value=True):
            result = await ta.check_availability(reqs)
        assert result[0].available is True

    async def test_some_missing(self) -> None:
        ta = _make_analyzer()
        reqs = [
            ToolRequirement(name="json"),
            ToolRequirement(name="ghost_pkg"),
        ]
        with patch.object(
            ta, "_check_python_package", side_effect=[True, False]
        ):
            with patch.object(
                ta, "_check_system_tool", side_effect=[True, False]
            ):
                result = await ta.check_availability(reqs)
        assert result[0].available is True
        assert result[1].available is False

    async def test_system_tool_fallback(self) -> None:
        ta = _make_analyzer()
        reqs = [ToolRequirement(name="docker")]
        with patch.object(ta, "_check_python_package", return_value=False):
            with patch.object(ta, "_check_system_tool", return_value=True):
                result = await ta.check_availability(reqs)
        assert result[0].available is True


# === IdentifySkillGaps Testleri ===


class TestIdentifySkillGaps:
    """identify_skill_gaps testleri."""

    def test_no_gaps(self) -> None:
        ta = _make_analyzer()
        gaps = ta.identify_skill_gaps([])
        assert gaps == []

    def test_critical_gap(self) -> None:
        ta = _make_analyzer()
        gaps = ta.identify_skill_gaps(["sqlalchemy"])
        assert len(gaps) == 1
        assert gaps[0].severity == GapSeverity.CRITICAL

    def test_medium_gap(self) -> None:
        ta = _make_analyzer()
        gaps = ta.identify_skill_gaps(["pillow"])
        assert len(gaps) == 1
        assert gaps[0].severity == GapSeverity.MEDIUM

    def test_multiple_gaps(self) -> None:
        ta = _make_analyzer()
        gaps = ta.identify_skill_gaps(["sqlalchemy", "pillow"])
        assert len(gaps) == 2


# === SuggestInstallations Testleri ===


class TestSuggestInstallations:
    """suggest_installations testleri."""

    def test_known_package(self) -> None:
        ta = _make_analyzer()
        suggestions = ta.suggest_installations(["httpx"])
        assert "pip install httpx" in suggestions["httpx"]

    def test_unknown_package(self) -> None:
        ta = _make_analyzer()
        suggestions = ta.suggest_installations(["exotic_pkg"])
        assert "pip install exotic_pkg" in suggestions["exotic_pkg"]

    def test_multiple(self) -> None:
        ta = _make_analyzer()
        suggestions = ta.suggest_installations(["httpx", "pillow"])
        assert len(suggestions) == 2


# === Analyze (tam analiz) Testleri ===


class TestAnalyze:
    """analyze testleri."""

    async def test_full_analysis(self) -> None:
        ta = _make_analyzer()
        with patch.object(ta, "_check_python_package", return_value=True):
            with patch.object(ta, "_check_system_tool", return_value=True):
                result = await ta.analyze("Database baglantisi kur")
        assert isinstance(result, TaskAnalysis)
        assert len(result.required_tools) > 0

    async def test_feasible_when_all_available(self) -> None:
        ta = _make_analyzer()
        with patch.object(ta, "_check_python_package", return_value=True):
            with patch.object(ta, "_check_system_tool", return_value=True):
                result = await ta.analyze("Database sorgusu")
        assert result.feasible is True
        assert result.confidence == 1.0

    async def test_not_feasible_critical_missing(self) -> None:
        ta = _make_analyzer()
        with patch.object(ta, "_check_python_package", return_value=False):
            with patch.object(ta, "_check_system_tool", return_value=False):
                result = await ta.analyze("Database sorgusu")
        assert result.feasible is False
        assert len(result.missing_tools) > 0

    async def test_no_requirements(self) -> None:
        ta = _make_analyzer()
        result = await ta.analyze("Merhaba dunya")
        assert result.required_tools == []
        assert result.feasible is True


# === MatchKeywords Testleri ===


class TestMatchKeywords:
    """_match_keywords testleri."""

    def test_single_match(self) -> None:
        ta = _make_analyzer()
        matches = ta._match_keywords("database baglantisi")
        assert "database" in matches

    def test_no_match(self) -> None:
        ta = _make_analyzer()
        matches = ta._match_keywords("merhaba")
        assert matches == []

    def test_case_insensitive(self) -> None:
        ta = _make_analyzer()
        matches = ta._match_keywords("DATABASE sorgusu")
        assert "database" in matches
