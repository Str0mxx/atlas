"""CodingAgent unit testleri.

Anthropic API mock'lanarak coding agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.agents.coding_agent import CodingAgent, _SECURITY_PATTERNS
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.coding import (
    CodeAnalysisResult,
    CodeIssue,
    CodeLanguage,
    CodeQualityMetrics,
    CodeTaskType,
    CodingConfig,
    SecurityVulnerability,
    SeverityLevel,
    VulnerabilityType,
)


# === Fixtures ===


@pytest.fixture
def config() -> CodingConfig:
    """Ornek coding yapilandirmasi."""
    return CodingConfig(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        static_analysis_enabled=True,
    )


@pytest.fixture
def agent(config: CodingConfig) -> CodingAgent:
    """Yapilandirilmis CodingAgent."""
    return CodingAgent(config=config)


# === Ornek kodlar ===

CLEAN_PYTHON = """
import hashlib

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    return hashlib.sha256(salt + password.encode()).hexdigest()
"""

VULNERABLE_PYTHON = """
import os
import pickle
import subprocess

password = "SuperSecret123"

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

def run_command(cmd):
    os.system(cmd)
    subprocess.call(f"echo {cmd}", shell=True)

def load_data(data):
    return pickle.loads(data)

def check_hash(value):
    return hashlib.md5(value).hexdigest()

def read_file(name):
    return open("/tmp/" + name).read()
"""

VULNERABLE_PHP = """
<?php
$user = $_GET['user'];
echo $_GET['name'];
$result = mysql_query("SELECT * FROM users WHERE name = '" . $user . "'");
exec("ls " . $_GET['dir']);
include($_GET['page']);
$data = unserialize($_POST['data']);
eval($_POST['code']);
?>
"""

VULNERABLE_JS = """
const apiKey = "sk-1234567890abcdef";
document.getElementById('output').innerHTML = userInput;
document.write(data);
eval(userCode);
window.location = redirectUrl;
"""

VULNERABLE_BASH = """#!/bin/bash
eval "$USER_INPUT"
chmod 777 /var/www/html
curl https://example.com/script.sh | bash
$CMD && rm -rf /tmp
"""

VULNERABLE_SQL = """
GRANT ALL PRIVILEGES ON *.* TO 'app_user'@'%';
-- password=MyS3cret123
"""

SAMPLE_PHP_CODE = """<?php echo "hello"; ?>"""
SAMPLE_JS_CODE = """const x = () => { return 1; };"""
SAMPLE_SQL_CODE = """SELECT * FROM users WHERE id = 1;"""
SAMPLE_BASH_CODE = """#!/bin/bash\necho hello"""
SAMPLE_PYTHON_CODE = """def foo():\n    pass"""


# === Dil tespiti testleri ===


class TestLanguageDetection:
    """_detect_language testleri."""

    def test_explicit_language(self, agent: CodingAgent) -> None:
        """Acikca belirtilen dil kullanilmali."""
        assert agent._detect_language("python", "", "") == CodeLanguage.PYTHON
        assert agent._detect_language("php", "", "") == CodeLanguage.PHP
        assert agent._detect_language("javascript", "", "") == CodeLanguage.JAVASCRIPT

    def test_filename_extension(self, agent: CodingAgent) -> None:
        """Dosya uzantisinden dil tespiti."""
        assert agent._detect_language("", "main.py", "") == CodeLanguage.PYTHON
        assert agent._detect_language("", "index.php", "") == CodeLanguage.PHP
        assert agent._detect_language("", "app.js", "") == CodeLanguage.JAVASCRIPT
        assert agent._detect_language("", "app.ts", "") == CodeLanguage.JAVASCRIPT
        assert agent._detect_language("", "query.sql", "") == CodeLanguage.SQL
        assert agent._detect_language("", "deploy.sh", "") == CodeLanguage.BASH
        assert agent._detect_language("", "run.bash", "") == CodeLanguage.BASH

    def test_content_detection_python(self, agent: CodingAgent) -> None:
        """Icerikten Python tespiti."""
        assert agent._detect_language("", "", SAMPLE_PYTHON_CODE) == CodeLanguage.PYTHON

    def test_content_detection_php(self, agent: CodingAgent) -> None:
        """Icerikten PHP tespiti."""
        assert agent._detect_language("", "", SAMPLE_PHP_CODE) == CodeLanguage.PHP

    def test_content_detection_javascript(self, agent: CodingAgent) -> None:
        """Icerikten JavaScript tespiti."""
        assert agent._detect_language("", "", SAMPLE_JS_CODE) == CodeLanguage.JAVASCRIPT

    def test_content_detection_sql(self, agent: CodingAgent) -> None:
        """Icerikten SQL tespiti."""
        assert agent._detect_language("", "", SAMPLE_SQL_CODE) == CodeLanguage.SQL

    def test_content_detection_bash(self, agent: CodingAgent) -> None:
        """Icerikten Bash tespiti."""
        assert agent._detect_language("", "", SAMPLE_BASH_CODE) == CodeLanguage.BASH

    def test_fallback_to_python(self, agent: CodingAgent) -> None:
        """Bilinmeyen icerik Python'a dusmeli."""
        assert agent._detect_language("", "", "x = 1") == CodeLanguage.PYTHON

    def test_explicit_overrides_filename(self, agent: CodingAgent) -> None:
        """Acik dil belirtmesi dosya uzantisini ezmeli."""
        assert agent._detect_language("javascript", "main.py", "") == CodeLanguage.JAVASCRIPT

    def test_invalid_language_falls_to_filename(self, agent: CodingAgent) -> None:
        """Gecersiz dil belirtilirse dosya uzantisina dusmeli."""
        assert agent._detect_language("cobol", "app.js", "") == CodeLanguage.JAVASCRIPT


# === Statik analiz testleri ===


class TestStaticAnalysis:
    """_run_static_analysis testleri."""

    def test_python_sql_injection(self, agent: CodingAgent) -> None:
        """Python SQL injection tespiti."""
        code = 'cursor.execute(f"SELECT * FROM users WHERE id = {uid}")'
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert any(v.vuln_type == VulnerabilityType.SQL_INJECTION for v in vulns)

    def test_python_command_injection_os_system(self, agent: CodingAgent) -> None:
        """Python os.system() tespiti."""
        code = 'os.system(cmd)'
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert any(v.vuln_type == VulnerabilityType.COMMAND_INJECTION for v in vulns)

    def test_python_eval(self, agent: CodingAgent) -> None:
        """Python eval() tespiti."""
        code = 'result = eval(user_input)'
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert any(v.vuln_type == VulnerabilityType.COMMAND_INJECTION for v in vulns)

    def test_python_pickle(self, agent: CodingAgent) -> None:
        """Python pickle.loads tespiti."""
        code = 'data = pickle.loads(raw)'
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert any(v.vuln_type == VulnerabilityType.INSECURE_DESERIALIZATION for v in vulns)

    def test_python_hardcoded_secret(self, agent: CodingAgent) -> None:
        """Python hardcoded secret tespiti."""
        code = 'api_key = "sk-1234567890abcdef"'
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert any(v.vuln_type == VulnerabilityType.HARDCODED_SECRET for v in vulns)

    def test_python_weak_hash(self, agent: CodingAgent) -> None:
        """Python MD5/SHA1 tespiti."""
        code = 'h = hashlib.md5(data)'
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert any(v.vuln_type == VulnerabilityType.INSECURE_HASH for v in vulns)

    def test_python_path_traversal(self, agent: CodingAgent) -> None:
        """Python path traversal tespiti."""
        code = 'f = open("/tmp/" + filename)'
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert any(v.vuln_type == VulnerabilityType.PATH_TRAVERSAL for v in vulns)

    def test_python_multiple_vulns(self, agent: CodingAgent) -> None:
        """Birden fazla Python guvenlik acigi tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_PYTHON, CodeLanguage.PYTHON)
        vuln_types = {v.vuln_type for v in vulns}
        assert VulnerabilityType.SQL_INJECTION in vuln_types
        assert VulnerabilityType.COMMAND_INJECTION in vuln_types
        assert VulnerabilityType.HARDCODED_SECRET in vuln_types
        assert VulnerabilityType.INSECURE_DESERIALIZATION in vuln_types
        assert VulnerabilityType.INSECURE_HASH in vuln_types
        assert len(vulns) >= 6

    def test_php_sql_injection(self, agent: CodingAgent) -> None:
        """PHP SQL injection tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_PHP, CodeLanguage.PHP)
        assert any(v.vuln_type == VulnerabilityType.SQL_INJECTION for v in vulns)

    def test_php_xss(self, agent: CodingAgent) -> None:
        """PHP XSS tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_PHP, CodeLanguage.PHP)
        assert any(v.vuln_type == VulnerabilityType.XSS for v in vulns)

    def test_php_command_injection(self, agent: CodingAgent) -> None:
        """PHP command injection tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_PHP, CodeLanguage.PHP)
        assert any(v.vuln_type == VulnerabilityType.COMMAND_INJECTION for v in vulns)

    def test_php_path_traversal(self, agent: CodingAgent) -> None:
        """PHP LFI/RFI tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_PHP, CodeLanguage.PHP)
        assert any(v.vuln_type == VulnerabilityType.PATH_TRAVERSAL for v in vulns)

    def test_php_deserialization(self, agent: CodingAgent) -> None:
        """PHP unserialize tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_PHP, CodeLanguage.PHP)
        assert any(v.vuln_type == VulnerabilityType.INSECURE_DESERIALIZATION for v in vulns)

    def test_js_xss_innerhtml(self, agent: CodingAgent) -> None:
        """JavaScript innerHTML XSS tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_JS, CodeLanguage.JAVASCRIPT)
        assert any(v.vuln_type == VulnerabilityType.XSS for v in vulns)

    def test_js_eval(self, agent: CodingAgent) -> None:
        """JavaScript eval tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_JS, CodeLanguage.JAVASCRIPT)
        assert any(v.vuln_type == VulnerabilityType.COMMAND_INJECTION for v in vulns)

    def test_js_hardcoded_secret(self, agent: CodingAgent) -> None:
        """JavaScript hardcoded secret tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_JS, CodeLanguage.JAVASCRIPT)
        assert any(v.vuln_type == VulnerabilityType.HARDCODED_SECRET for v in vulns)

    def test_js_open_redirect(self, agent: CodingAgent) -> None:
        """JavaScript open redirect tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_JS, CodeLanguage.JAVASCRIPT)
        assert any(v.vuln_type == VulnerabilityType.OPEN_REDIRECT for v in vulns)

    def test_bash_eval(self, agent: CodingAgent) -> None:
        """Bash eval tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_BASH, CodeLanguage.BASH)
        assert any(v.vuln_type == VulnerabilityType.COMMAND_INJECTION for v in vulns)

    def test_bash_chmod_777(self, agent: CodingAgent) -> None:
        """Bash chmod 777 tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_BASH, CodeLanguage.BASH)
        assert any("777" in v.description for v in vulns)

    def test_bash_curl_pipe(self, agent: CodingAgent) -> None:
        """Bash curl | bash tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_BASH, CodeLanguage.BASH)
        assert any("curl" in v.description.lower() for v in vulns)

    def test_sql_grant_all(self, agent: CodingAgent) -> None:
        """SQL GRANT ALL tespiti."""
        vulns = agent._run_static_analysis(VULNERABLE_SQL, CodeLanguage.SQL)
        assert any("yetki" in v.description.lower() for v in vulns)

    def test_clean_code_no_vulns(self, agent: CodingAgent) -> None:
        """Temiz kod acik dondurmemeli."""
        clean = "def add(a: int, b: int) -> int:\n    return a + b\n"
        vulns = agent._run_static_analysis(clean, CodeLanguage.PYTHON)
        assert len(vulns) == 0

    def test_line_numbers_correct(self, agent: CodingAgent) -> None:
        """Satir numaralari dogru hesaplanmali."""
        code = "line1\nline2\nos.system(cmd)\nline4"
        vulns = agent._run_static_analysis(code, CodeLanguage.PYTHON)
        assert len(vulns) >= 1
        assert vulns[0].line == 3

    def test_all_supported_languages_have_patterns(self) -> None:
        """Tum desteklenen diller icin en az bir kalip olmali."""
        for lang in CodeLanguage:
            assert lang in _SECURITY_PATTERNS, f"{lang.value} icin kalip yok"


# === LLM yanit parse testleri ===


class TestParseLlmResponse:
    """_parse_llm_response testleri."""

    def test_parse_json_block(self) -> None:
        """JSON code block parse edilmeli."""
        text = '```json\n{"summary": "test", "issues": []}\n```'
        result = CodingAgent._parse_llm_response(text)
        assert result["summary"] == "test"

    def test_parse_raw_json(self) -> None:
        """Dogrudan JSON parse edilmeli."""
        text = '{"summary": "hello", "issues": []}'
        result = CodingAgent._parse_llm_response(text)
        assert result["summary"] == "hello"

    def test_parse_json_with_surrounding_text(self) -> None:
        """Metin icindeki JSON blogu bulunmali."""
        text = 'Here is the analysis:\n{"summary": "found", "issues": []}\nEnd.'
        result = CodingAgent._parse_llm_response(text)
        assert result["summary"] == "found"

    def test_parse_invalid_json_returns_raw(self) -> None:
        """Gecersiz JSON raw_text donmeli."""
        text = "This is not JSON at all, no braces here"
        result = CodingAgent._parse_llm_response(text)
        assert "raw_text" in result

    def test_parse_empty_code_block(self) -> None:
        """Bos code block icindeki gecersiz JSON."""
        text = "```json\nnot json\n```"
        result = CodingAgent._parse_llm_response(text)
        assert "raw_text" in result


# === LLM sonuc birlestirme testleri ===


class TestMergeLlmResult:
    """_merge_llm_result testleri."""

    def test_merge_issues(self) -> None:
        """Issues birlestirilmeli."""
        result = CodeAnalysisResult()
        llm_data = {
            "issues": [
                {"line": 5, "severity": "error", "category": "bug",
                 "message": "Null check eksik", "suggestion": "if x is not None ekle"},
            ],
        }
        CodingAgent._merge_llm_result(result, llm_data)
        assert len(result.issues) == 1
        assert result.issues[0].line == 5
        assert result.issues[0].severity == SeverityLevel.ERROR

    def test_merge_vulnerabilities(self) -> None:
        """Vulnerabilities birlestirilmeli."""
        result = CodeAnalysisResult()
        llm_data = {
            "vulnerabilities": [
                {"vuln_type": "sql_injection", "line": 10, "severity": "critical",
                 "description": "SQL injection", "fix": "Parameterize"},
            ],
        }
        CodingAgent._merge_llm_result(result, llm_data)
        assert len(result.vulnerabilities) == 1
        assert result.vulnerabilities[0].vuln_type == VulnerabilityType.SQL_INJECTION

    def test_merge_quality(self) -> None:
        """Quality birlestirilmeli."""
        result = CodeAnalysisResult()
        llm_data = {
            "quality": {"complexity": 3.0, "readability": 8.0,
                        "maintainability": 7.0, "overall_score": 7.5},
        }
        CodingAgent._merge_llm_result(result, llm_data)
        assert result.quality.overall_score == 7.5
        assert result.quality.readability == 8.0

    def test_merge_generated_code(self) -> None:
        """Generated code birlestirilmeli."""
        result = CodeAnalysisResult()
        llm_data = {"generated_code": "def foo(): pass", "explanation": "Bos fonksiyon"}
        CodingAgent._merge_llm_result(result, llm_data)
        assert result.generated_code == "def foo(): pass"
        assert result.explanation == "Bos fonksiyon"

    def test_merge_suggestions(self) -> None:
        """Suggestions birlestirilmeli."""
        result = CodeAnalysisResult()
        result.suggestions = ["eski oneri"]
        llm_data = {"suggestions": ["yeni oneri 1", "yeni oneri 2"]}
        CodingAgent._merge_llm_result(result, llm_data)
        assert len(result.suggestions) == 3

    def test_merge_invalid_severity_defaults(self) -> None:
        """Gecersiz severity INFO'ya dusmeli."""
        result = CodeAnalysisResult()
        llm_data = {"issues": [{"severity": "invalid_level", "message": "test"}]}
        CodingAgent._merge_llm_result(result, llm_data)
        assert result.issues[0].severity == SeverityLevel.INFO

    def test_merge_invalid_vuln_type_defaults(self) -> None:
        """Gecersiz vuln_type OTHER'a dusmeli."""
        result = CodeAnalysisResult()
        llm_data = {"vulnerabilities": [{"vuln_type": "unknown_type", "description": "test"}]}
        CodingAgent._merge_llm_result(result, llm_data)
        assert result.vulnerabilities[0].vuln_type == VulnerabilityType.OTHER

    def test_merge_empty_data(self) -> None:
        """Bos LLM verisi mevcut sonucu degistirmemeli."""
        result = CodeAnalysisResult(summary="original")
        CodingAgent._merge_llm_result(result, {})
        assert result.summary == "original"
        assert len(result.issues) == 0


# === Risk/Aciliyet eslestirme testleri ===


class TestRiskUrgencyMapping:
    """_map_to_risk_urgency testleri."""

    def test_critical_vuln_high_high(self) -> None:
        """Kritik guvenlik acigi -> HIGH/HIGH."""
        result = CodeAnalysisResult(
            vulnerabilities=[
                SecurityVulnerability(
                    vuln_type=VulnerabilityType.SQL_INJECTION,
                    severity=SeverityLevel.CRITICAL,
                ),
            ],
        )
        risk, urgency = CodingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH

    def test_error_vuln_high_medium(self) -> None:
        """Error seviye guvenlik acigi -> HIGH/MEDIUM."""
        result = CodeAnalysisResult(
            vulnerabilities=[
                SecurityVulnerability(
                    vuln_type=VulnerabilityType.HARDCODED_SECRET,
                    severity=SeverityLevel.ERROR,
                ),
            ],
        )
        risk, urgency = CodingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.MEDIUM

    def test_critical_issue_high_medium(self) -> None:
        """Kritik kod sorunu -> HIGH/MEDIUM."""
        result = CodeAnalysisResult(
            issues=[
                CodeIssue(severity=SeverityLevel.CRITICAL, message="Kritik bug"),
            ],
        )
        risk, urgency = CodingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.MEDIUM

    def test_warning_vuln_medium_medium(self) -> None:
        """Warning guvenlik acigi -> MEDIUM/MEDIUM."""
        result = CodeAnalysisResult(
            vulnerabilities=[
                SecurityVulnerability(
                    severity=SeverityLevel.WARNING,
                ),
            ],
        )
        risk, urgency = CodingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.MEDIUM

    def test_error_issue_medium_medium(self) -> None:
        """Error seviye kod sorunu -> MEDIUM/MEDIUM."""
        result = CodeAnalysisResult(
            issues=[
                CodeIssue(severity=SeverityLevel.ERROR, message="Hata"),
            ],
        )
        risk, urgency = CodingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.MEDIUM

    def test_low_quality_medium_low(self) -> None:
        """Dusuk kalite -> MEDIUM/LOW."""
        result = CodeAnalysisResult(
            quality=CodeQualityMetrics(overall_score=3.0),
        )
        risk, urgency = CodingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.LOW

    def test_clean_result_low_low(self) -> None:
        """Temiz sonuc -> LOW/LOW."""
        result = CodeAnalysisResult(
            quality=CodeQualityMetrics(overall_score=8.0),
        )
        risk, urgency = CodingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW


# === Aksiyon belirleme testleri ===


class TestActionDetermination:
    """Aksiyon tipi belirleme testleri."""

    def test_low_low_logs(self) -> None:
        assert CodingAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW) == ActionType.LOG

    def test_medium_medium_notifies(self) -> None:
        assert CodingAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.MEDIUM) == ActionType.NOTIFY

    def test_high_high_immediate(self) -> None:
        assert CodingAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH) == ActionType.IMMEDIATE

    def test_high_medium_auto_fix(self) -> None:
        assert CodingAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.MEDIUM) == ActionType.AUTO_FIX


# === Ozet olusturma testleri ===


class TestBuildSummary:
    """_build_summary testleri."""

    def test_basic_summary(self, agent: CodingAgent) -> None:
        result = CodeAnalysisResult(
            task_type=CodeTaskType.REVIEW,
            language=CodeLanguage.PYTHON,
            quality=CodeQualityMetrics(overall_score=7.5),
        )
        summary = agent._build_summary(result)
        assert "review" in summary
        assert "python" in summary
        assert "7.5" in summary

    def test_summary_with_vulns(self, agent: CodingAgent) -> None:
        result = CodeAnalysisResult(
            vulnerabilities=[
                SecurityVulnerability(severity=SeverityLevel.CRITICAL),
                SecurityVulnerability(severity=SeverityLevel.WARNING),
            ],
        )
        summary = agent._build_summary(result)
        assert "2 guvenlik acigi" in summary
        assert "kritik: 1" in summary

    def test_summary_with_issues(self, agent: CodingAgent) -> None:
        result = CodeAnalysisResult(
            issues=[CodeIssue(message="test")],
        )
        summary = agent._build_summary(result)
        assert "1 kod sorunu" in summary

    def test_summary_with_generated_code(self, agent: CodingAgent) -> None:
        result = CodeAnalysisResult(
            task_type=CodeTaskType.GENERATE,
            generated_code="def foo(): pass",
        )
        summary = agent._build_summary(result)
        assert "Kod uretildi" in summary


# === Analiz testleri ===


class TestAnalyze:
    """analyze() metodu testleri."""

    @pytest.mark.asyncio
    async def test_clean_analysis(self, agent: CodingAgent) -> None:
        """Temiz sonuc: LOW risk, LOG action."""
        result = CodeAnalysisResult(
            quality=CodeQualityMetrics(overall_score=8.0),
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["risk"] == RiskLevel.LOW.value
        assert analysis["action"] == ActionType.LOG.value

    @pytest.mark.asyncio
    async def test_critical_vuln_analysis(self, agent: CodingAgent) -> None:
        """Kritik guvenlik acigi: HIGH risk, IMMEDIATE action."""
        result = CodeAnalysisResult(
            vulnerabilities=[
                SecurityVulnerability(
                    vuln_type=VulnerabilityType.SQL_INJECTION,
                    severity=SeverityLevel.CRITICAL,
                    description="SQL injection tespit edildi",
                ),
            ],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["risk"] == RiskLevel.HIGH.value
        assert analysis["action"] == ActionType.IMMEDIATE.value
        assert analysis["stats"]["critical_vulns"] == 1

    @pytest.mark.asyncio
    async def test_analysis_issues_list(self, agent: CodingAgent) -> None:
        """Issues listesi tum bulgu turlerini icermeli."""
        result = CodeAnalysisResult(
            vulnerabilities=[
                SecurityVulnerability(
                    severity=SeverityLevel.ERROR,
                    description="Hardcoded secret",
                ),
            ],
            issues=[
                CodeIssue(
                    severity=SeverityLevel.ERROR,
                    category="bug",
                    message="NullPointer",
                ),
            ],
            quality=CodeQualityMetrics(overall_score=3.0),
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        issues = analysis["issues"]
        assert any("GUVENLIK" in i for i in issues)
        assert any("KOD" in i for i in issues)
        assert any("Dusuk kod kalitesi" in i for i in issues)

    @pytest.mark.asyncio
    async def test_analysis_stats(self, agent: CodingAgent) -> None:
        """Analiz istatistikleri dogru olmali."""
        result = CodeAnalysisResult(
            vulnerabilities=[
                SecurityVulnerability(severity=SeverityLevel.CRITICAL),
                SecurityVulnerability(severity=SeverityLevel.WARNING),
            ],
            issues=[
                CodeIssue(severity=SeverityLevel.ERROR),
                CodeIssue(severity=SeverityLevel.INFO),
            ],
            quality=CodeQualityMetrics(overall_score=6.0),
            suggestions=["oneri1", "oneri2"],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        stats = analysis["stats"]
        assert stats["vulnerability_count"] == 2
        assert stats["critical_vulns"] == 1
        assert stats["issue_count"] == 2
        assert stats["error_issues"] == 1
        assert stats["quality_score"] == 6.0
        assert stats["suggestion_count"] == 2


# === Rapor format testleri ===


class TestReport:
    """report() metodu testleri."""

    @pytest.mark.asyncio
    async def test_report_contains_header(self, agent: CodingAgent) -> None:
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "task_type": "review",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "Temiz kod.",
                    "issues": [],
                    "stats": {
                        "vulnerability_count": 0, "critical_vulns": 0,
                        "issue_count": 0, "critical_issues": 0,
                        "error_issues": 0, "quality_score": 8.0,
                        "suggestion_count": 0,
                    },
                },
            },
            message="ok",
        )
        report = await agent.report(task_result)
        assert "KOD ANALIZ RAPORU" in report

    @pytest.mark.asyncio
    async def test_report_contains_stats(self, agent: CodingAgent) -> None:
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "task_type": "security_scan",
                    "risk": "high",
                    "urgency": "high",
                    "action": "immediate",
                    "summary": "Kritik aciklar!",
                    "issues": ["GUVENLIK [CRITICAL]: SQL injection"],
                    "stats": {
                        "vulnerability_count": 3, "critical_vulns": 2,
                        "issue_count": 1, "critical_issues": 0,
                        "error_issues": 1, "quality_score": 4.0,
                        "suggestion_count": 5,
                    },
                },
            },
            message="acik",
        )
        report = await agent.report(task_result)
        assert "kritik: 2" in report
        assert "4.0/10" in report
        assert "SQL injection" in report

    @pytest.mark.asyncio
    async def test_report_contains_errors(self, agent: CodingAgent) -> None:
        task_result = TaskResult(
            success=False,
            data={
                "analysis": {
                    "task_type": "analyze",
                    "risk": "low", "urgency": "low", "action": "log",
                    "summary": "", "issues": [],
                    "stats": {
                        "vulnerability_count": 0, "critical_vulns": 0,
                        "issue_count": 0, "critical_issues": 0,
                        "error_issues": 0, "quality_score": 5.0,
                        "suggestion_count": 0,
                    },
                },
            },
            message="hata",
            errors=["Anthropic API: rate limit exceeded"],
        )
        report = await agent.report(task_result)
        assert "HATALAR" in report
        assert "rate limit" in report


# === Execute testleri ===


class TestExecute:
    """execute() metodu testleri."""

    @pytest.mark.asyncio
    async def test_execute_invalid_task_type(self, agent: CodingAgent) -> None:
        result = await agent.execute({"task_type": "nonexistent"})
        assert result.success is False
        assert "Gecersiz" in result.message

    @pytest.mark.asyncio
    async def test_execute_no_code(self, agent: CodingAgent) -> None:
        result = await agent.execute({"task_type": "analyze"})
        assert result.success is False
        assert "code" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_generate_no_prompt(self, agent: CodingAgent) -> None:
        result = await agent.execute({"task_type": "generate"})
        assert result.success is False
        assert "prompt" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_security_scan_with_static(self, agent: CodingAgent) -> None:
        """Statik analiz ile guvenlik taramasi (LLM mock)."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"vulnerabilities": [], "summary": "LLM clean"}')]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent.execute({
                "task_type": "security_scan",
                "code": VULNERABLE_PYTHON,
                "language": "python",
            })

        assert result.success is True
        analysis_result = result.data["analysis_result"]
        # Statik analiz aciklari bulunmali
        assert len(analysis_result["vulnerabilities"]) >= 5

    @pytest.mark.asyncio
    async def test_execute_analyze_with_mock_llm(self, agent: CodingAgent) -> None:
        """Mock LLM ile kod analizi."""
        llm_response = (
            '{"explanation": "Toplama fonksiyonu", '
            '"issues": [{"line": 1, "severity": "info", "category": "style", '
            '"message": "Type hint eksik", "suggestion": "Ekleyin"}], '
            '"quality": {"complexity": 2, "readability": 9, '
            '"maintainability": 8, "overall_score": 8}, '
            '"suggestions": ["Docstring ekleyin"]}'
        )
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=llm_response)]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent.execute({
                "task_type": "analyze",
                "code": "def add(a, b): return a + b",
                "language": "python",
            })

        assert result.success is True
        ar = result.data["analysis_result"]
        assert ar["explanation"] == "Toplama fonksiyonu"
        assert ar["quality"]["overall_score"] == 8
        assert len(ar["issues"]) == 1
        assert len(ar["suggestions"]) == 1

    @pytest.mark.asyncio
    async def test_execute_generate_with_mock_llm(self, agent: CodingAgent) -> None:
        """Mock LLM ile kod uretimi."""
        llm_response = (
            '{"generated_code": "def fibonacci(n):\\n    if n <= 1: return n\\n    '
            'return fibonacci(n-1) + fibonacci(n-2)", '
            '"explanation": "Recursive fibonacci", "summary": "Fibonacci fonksiyonu"}'
        )
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=llm_response)]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent.execute({
                "task_type": "generate",
                "prompt": "Fibonacci fonksiyonu yaz",
                "language": "python",
            })

        assert result.success is True
        assert "fibonacci" in result.data["analysis_result"]["generated_code"]

    @pytest.mark.asyncio
    async def test_execute_llm_error_handled(self, agent: CodingAgent) -> None:
        """LLM hatasi graceful handling."""
        with patch.object(agent, "_get_client") as mock_get:
            mock_get.side_effect = ValueError("API key yok")
            result = await agent.execute({
                "task_type": "analyze",
                "code": "x = 1",
                "language": "python",
            })

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_static_analysis_disabled(self) -> None:
        """Statik analiz kapatildiginda calistirilmamali."""
        agent = CodingAgent(config=CodingConfig(static_analysis_enabled=False))

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"summary": "ok"}')]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent.execute({
                "task_type": "security_scan",
                "code": VULNERABLE_PYTHON,
                "language": "python",
            })

        assert result.success is True
        # Statik analiz kapali -> acik bulunmamali (LLM bos dondu)
        assert len(result.data["analysis_result"]["vulnerabilities"]) == 0

    @pytest.mark.asyncio
    async def test_execute_config_override(self) -> None:
        """Task'tan config override edilebilmeli."""
        agent = CodingAgent()

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"summary": "ok"}')]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(agent, "_get_client", return_value=mock_client):
            result = await agent.execute({
                "task_type": "analyze",
                "code": "x = 1",
                "config": {"max_tokens": 1024, "static_analysis_enabled": False},
            })

        assert result.success is True
        assert agent.config.max_tokens == 1024


# === Model testleri ===


class TestModels:
    """Coding veri modeli testleri."""

    def test_coding_config_defaults(self) -> None:
        config = CodingConfig()
        assert len(config.supported_languages) == 5
        assert config.max_tokens == 4096
        assert config.static_analysis_enabled is True

    def test_code_analysis_result_defaults(self) -> None:
        result = CodeAnalysisResult()
        assert result.task_type == CodeTaskType.ANALYZE
        assert result.language == CodeLanguage.PYTHON
        assert result.issues == []
        assert result.vulnerabilities == []
        assert result.generated_code == ""

    def test_code_issue(self) -> None:
        issue = CodeIssue(
            line=10, severity=SeverityLevel.ERROR,
            category="bug", message="NullPointer",
        )
        assert issue.line == 10
        assert issue.severity == SeverityLevel.ERROR

    def test_security_vulnerability(self) -> None:
        vuln = SecurityVulnerability(
            vuln_type=VulnerabilityType.SQL_INJECTION,
            severity=SeverityLevel.CRITICAL,
            description="SQL injection",
        )
        assert vuln.vuln_type == VulnerabilityType.SQL_INJECTION

    def test_code_quality_metrics_defaults(self) -> None:
        q = CodeQualityMetrics()
        assert q.complexity == 5.0
        assert q.overall_score == 5.0

    def test_code_task_type_values(self) -> None:
        assert CodeTaskType.ANALYZE.value == "analyze"
        assert CodeTaskType.SECURITY_SCAN.value == "security_scan"
        assert CodeTaskType.GENERATE.value == "generate"

    def test_code_language_values(self) -> None:
        assert CodeLanguage.PYTHON.value == "python"
        assert CodeLanguage.PHP.value == "php"
        assert CodeLanguage.JAVASCRIPT.value == "javascript"
        assert CodeLanguage.SQL.value == "sql"
        assert CodeLanguage.BASH.value == "bash"

    def test_vulnerability_type_values(self) -> None:
        assert VulnerabilityType.SQL_INJECTION.value == "sql_injection"
        assert VulnerabilityType.XSS.value == "xss"
        assert VulnerabilityType.COMMAND_INJECTION.value == "command_injection"

    def test_severity_level_values(self) -> None:
        assert SeverityLevel.INFO.value == "info"
        assert SeverityLevel.CRITICAL.value == "critical"


# === BaseAgent entegrasyon testleri ===


class TestBaseAgentIntegration:
    """BaseAgent miras ve entegrasyon testleri."""

    def test_agent_name(self, agent: CodingAgent) -> None:
        assert agent.name == "coding"

    def test_agent_info(self, agent: CodingAgent) -> None:
        info = agent.get_info()
        assert info["name"] == "coding"
        assert info["status"] == "idle"
        assert info["task_count"] == 0

    @pytest.mark.asyncio
    async def test_run_wraps_execute(self) -> None:
        """run() execute()'u sarmalayip hata yakalamali."""
        agent = CodingAgent()
        result = await agent.run({"task_type": "analyze"})
        assert isinstance(result, TaskResult)
        assert result.success is False
