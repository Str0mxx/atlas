"""Kod analizi ve gelistirme agent modulu.

Anthropic Claude API ve statik analiz ile kod inceler:
- Kod analizi ve aciklama
- Bug tespit ve duzeltme onerisi
- Kod optimizasyonu ve refactoring
- Guvenlik acigi taramasi (SQL injection, XSS vb.)
- Basit kod uretimi (fonksiyon, script)
- Code review ve kalite degerlendirme

Desteklenen diller: Python, PHP, JavaScript, SQL, Bash
Sonuclari risk/aciliyet olarak siniflandirir ve karar matrisine iletir.
"""

import json
import logging
import re
from typing import Any

import anthropic

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import (
    DECISION_RULES,
    ActionType,
    RiskLevel,
    UrgencyLevel,
)
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

logger = logging.getLogger("atlas.agent.coding")

# Dil uzantisi eslestirmesi
_EXTENSION_MAP: dict[str, CodeLanguage] = {
    ".py": CodeLanguage.PYTHON,
    ".php": CodeLanguage.PHP,
    ".js": CodeLanguage.JAVASCRIPT,
    ".mjs": CodeLanguage.JAVASCRIPT,
    ".ts": CodeLanguage.JAVASCRIPT,
    ".sql": CodeLanguage.SQL,
    ".sh": CodeLanguage.BASH,
    ".bash": CodeLanguage.BASH,
}

# === Statik analiz kaliplari ===
# Her kalip: (regex, VulnerabilityType, SeverityLevel, aciklama, duzeltme)
_SECURITY_PATTERNS: dict[CodeLanguage, list[tuple[str, VulnerabilityType, SeverityLevel, str, str]]] = {
    CodeLanguage.PYTHON: [
        (
            r"""(?:execute|executemany)\s*\(\s*(?:f['"]|['"].*%s|['"].*\.format\()""",
            VulnerabilityType.SQL_INJECTION,
            SeverityLevel.CRITICAL,
            "SQL sorgusu string formatlama ile olusturuluyor",
            "Parameterized query kullanin: cursor.execute('SELECT * FROM t WHERE id = %s', (id,))",
        ),
        (
            r"""(?:f['"](?:SELECT|INSERT|UPDATE|DELETE)\b|['"](?:SELECT|INSERT|UPDATE|DELETE)\b.*\.format\()""",
            VulnerabilityType.SQL_INJECTION,
            SeverityLevel.CRITICAL,
            "SQL sorgusu string formatlama ile olusturuluyor (f-string/format)",
            "Parameterized query kullanin",
        ),
        (
            r"""subprocess\.(?:call|run|Popen)\s*\(\s*(?:f['"]|.*\+\s*|.*\.format\()""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.CRITICAL,
            "Shell komutu kullanici girdisiyle olusturulabilir",
            "shlex.quote() kullanin veya shell=False ile liste argumanlari gecirin",
        ),
        (
            r"""os\.system\s*\(""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.ERROR,
            "os.system() guvenli degil",
            "subprocess.run(..., shell=False) kullanin",
        ),
        (
            r"""eval\s*\(""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.CRITICAL,
            "eval() rastgele kod calistirabilir",
            "eval() yerine guvenli alternatif kullanin (ast.literal_eval, json.loads vb.)",
        ),
        (
            r"""pickle\.loads?\s*\(""",
            VulnerabilityType.INSECURE_DESERIALIZATION,
            SeverityLevel.ERROR,
            "pickle deserializasyonu guvenli degil",
            "Guvenilir olmayan verilerle pickle kullanmayin; JSON tercih edin",
        ),
        (
            r"""(?:hashlib\.)?(?:md5|sha1)\s*\(""",
            VulnerabilityType.INSECURE_HASH,
            SeverityLevel.WARNING,
            "MD5/SHA1 kriptografik olarak zayif",
            "SHA-256 veya daha guclu hash fonksiyonu kullanin",
        ),
        (
            r"""(?:password|secret|api_key|token)\s*=\s*['"][^'"]{4,}['"]""",
            VulnerabilityType.HARDCODED_SECRET,
            SeverityLevel.ERROR,
            "Hardcoded secret/password tespit edildi",
            "Hassas degerleri environment variable veya secret manager'da saklayin",
        ),
        (
            r"""open\s*\(.*\+""",
            VulnerabilityType.PATH_TRAVERSAL,
            SeverityLevel.WARNING,
            "Dosya yolu kullanici girdisiyle olusturulabilir",
            "os.path.abspath() ve yol dogrulamasi kullanin",
        ),
    ],
    CodeLanguage.PHP: [
        (
            r"""(?:mysql_query|mysqli_query|->query)\s*\(\s*(?:\$|['"].*\.\s*\$)""",
            VulnerabilityType.SQL_INJECTION,
            SeverityLevel.CRITICAL,
            "SQL sorgusu degisken birlestirme ile olusturuluyor",
            "Prepared statements kullanin: $stmt = $pdo->prepare('SELECT * FROM t WHERE id = ?')",
        ),
        (
            r"""echo\s+\$_(?:GET|POST|REQUEST|COOKIE)\b""",
            VulnerabilityType.XSS,
            SeverityLevel.CRITICAL,
            "Kullanici girdisi dogrudan HTML'e yaziliyor",
            "htmlspecialchars() ile ciktiyi escape edin",
        ),
        (
            r"""(?:exec|system|passthru|shell_exec|popen)\s*\(.*\$""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.CRITICAL,
            "Shell komutu kullanici girdisi iceriyor",
            "escapeshellarg() veya escapeshellcmd() kullanin",
        ),
        (
            r"""(?:include|require)(?:_once)?\s*\(\s*\$""",
            VulnerabilityType.PATH_TRAVERSAL,
            SeverityLevel.CRITICAL,
            "Dinamik dosya dahil etme (LFI/RFI riski)",
            "Whitelist kontrol ile sadece izinli dosyalari dahil edin",
        ),
        (
            r"""eval\s*\(""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.CRITICAL,
            "eval() rastgele kod calistirabilir",
            "eval() kullanmaktan kacinin",
        ),
        (
            r"""unserialize\s*\(""",
            VulnerabilityType.INSECURE_DESERIALIZATION,
            SeverityLevel.ERROR,
            "unserialize() guvenli degil",
            "json_decode() tercih edin; guvenilir olmayan veriyle unserialize kullanmayin",
        ),
    ],
    CodeLanguage.JAVASCRIPT: [
        (
            r"""\.innerHTML\s*=\s*(?!['"`]<)""",
            VulnerabilityType.XSS,
            SeverityLevel.ERROR,
            "innerHTML ile XSS riski",
            "textContent kullanin veya DOMPurify ile sanitize edin",
        ),
        (
            r"""document\.write\s*\(""",
            VulnerabilityType.XSS,
            SeverityLevel.ERROR,
            "document.write() XSS'e acik",
            "DOM API kullanin (createElement, appendChild)",
        ),
        (
            r"""eval\s*\(""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.CRITICAL,
            "eval() rastgele kod calistirabilir",
            "eval() yerine JSON.parse() veya Function constructor kullanin",
        ),
        (
            r"""(?:password|secret|api[_-]?key|token)\s*[:=]\s*['"`][^'"`]{4,}['"`]""",
            VulnerabilityType.HARDCODED_SECRET,
            SeverityLevel.ERROR,
            "Hardcoded secret tespit edildi",
            "Environment variable kullanin (process.env.API_KEY)",
        ),
        (
            r"""window\.location\s*=\s*(?!['"])""",
            VulnerabilityType.OPEN_REDIRECT,
            SeverityLevel.WARNING,
            "Open redirect riski",
            "Yonlendirme URL'sini whitelist ile dogrulayin",
        ),
    ],
    CodeLanguage.SQL: [
        (
            r"""GRANT\s+ALL\s+PRIVILEGES""",
            VulnerabilityType.OTHER,
            SeverityLevel.WARNING,
            "Tum yetkiler veriliyor",
            "Sadece gerekli yetkileri verin (en az yetki prensibi)",
        ),
        (
            r"""--\s*password.*=\s*\S+""",
            VulnerabilityType.HARDCODED_SECRET,
            SeverityLevel.ERROR,
            "SQL icinde hardcoded sifre",
            "Sifreleri SQL dosyalarinda saklamayin",
        ),
    ],
    CodeLanguage.BASH: [
        (
            r"""eval\s+["']?\$""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.CRITICAL,
            "eval ile degisken genisletme tehlikeli",
            "eval kullanmaktan kacinin; dogrudan komut calistirin",
        ),
        (
            r"""\$\{?\w+\}?\s*(?:&&|\|\||;)\s*""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.WARNING,
            "Dogrulanmamis degisken komut zincirinde",
            "Degiskenleri cift tirnak icine alin ve dogrulayin",
        ),
        (
            r"""chmod\s+777""",
            VulnerabilityType.OTHER,
            SeverityLevel.WARNING,
            "777 izin tum kullanicilara yazma hakki verir",
            "En az yetki prensibi: chmod 755 veya daha kisitli izin kullanin",
        ),
        (
            r"""curl\s+.*\|\s*(?:bash|sh)""",
            VulnerabilityType.COMMAND_INJECTION,
            SeverityLevel.ERROR,
            "curl | bash uzaktan kod calistirma riski",
            "Scripti once indirin, inceleyin, sonra calistirin",
        ),
    ],
}

# === LLM prompt sablonlari ===
_SYSTEM_PROMPT = (
    "Sen bir uzman yazilim muhendisisin. Turkce yanit ver. "
    "Analizlerini JSON formatinda dondur."
)

_TASK_PROMPTS: dict[CodeTaskType, str] = {
    CodeTaskType.ANALYZE: (
        "Asagidaki {language} kodunu analiz et ve acikla.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"explanation": "kodun ne yaptiginin detayli aciklamasi", '
        '"issues": [{{"line": 0, "severity": "info|warning|error|critical", '
        '"category": "kategori", "message": "aciklama", "suggestion": "oneri"}}], '
        '"quality": {{"complexity": 1-10, "readability": 1-10, '
        '"maintainability": 1-10, "overall_score": 1-10}}, '
        '"suggestions": ["genel oneri listesi"]}}\n\n'
        "Kod:\n```{language}\n{code}\n```"
    ),
    CodeTaskType.BUG_DETECT: (
        "Asagidaki {language} kodundaki bug'lari tespit et.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"issues": [{{"line": 0, "severity": "info|warning|error|critical", '
        '"category": "bug tipi", "message": "bug aciklamasi", '
        '"suggestion": "duzeltme onerisi"}}], '
        '"summary": "genel degerlendirme"}}\n\n'
        "Kod:\n```{language}\n{code}\n```"
    ),
    CodeTaskType.OPTIMIZE: (
        "Asagidaki {language} kodunu optimize et ve refactoring oner.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"suggestions": ["optimizasyon onerisi listesi"], '
        '"issues": [{{"line": 0, "severity": "info|warning", '
        '"category": "performance|readability|structure", '
        '"message": "sorun", "suggestion": "iyilestirme"}}], '
        '"generated_code": "optimize edilmis kod (varsa)", '
        '"summary": "genel degerlendirme"}}\n\n'
        "Kod:\n```{language}\n{code}\n```"
    ),
    CodeTaskType.SECURITY_SCAN: (
        "Asagidaki {language} kodundaki guvenlik aciklarini tara.\n"
        "OWASP Top 10, SQL injection, XSS, command injection, "
        "path traversal, hardcoded secret gibi aciklari ara.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"vulnerabilities": [{{"vuln_type": "sql_injection|xss|command_injection|'
        'path_traversal|hardcoded_secret|insecure_deserialization|insecure_hash|'
        'open_redirect|other", "line": 0, '
        '"severity": "info|warning|error|critical", '
        '"description": "aciklama", "fix": "duzeltme", "snippet": "sorunlu kod"}}], '
        '"summary": "genel degerlendirme"}}\n\n'
        "Kod:\n```{language}\n{code}\n```"
    ),
    CodeTaskType.GENERATE: (
        "Asagidaki istege gore {language} kodu yaz.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"generated_code": "uretilen kod", '
        '"explanation": "kodun aciklamasi", '
        '"summary": "ne yaptigi"}}\n\n'
        "Istek: {prompt}"
    ),
    CodeTaskType.REVIEW: (
        "Asagidaki {language} kodu icin kapsamli code review yap.\n"
        "Kalite, guvenlik, performans, okunabilirlik ve "
        "best practice acisindan degerlendir.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"issues": [{{"line": 0, "severity": "info|warning|error|critical", '
        '"category": "quality|security|performance|style|best_practice", '
        '"message": "bulgu", "suggestion": "oneri"}}], '
        '"quality": {{"complexity": 1-10, "readability": 1-10, '
        '"maintainability": 1-10, "overall_score": 1-10}}, '
        '"suggestions": ["genel oneri listesi"], '
        '"summary": "genel degerlendirme"}}\n\n'
        "Kod:\n```{language}\n{code}\n```"
    ),
}


class CodingAgent(BaseAgent):
    """Kod analizi ve gelistirme agent'i.

    Anthropic Claude API ve regex tabanli statik analiz ile
    kod inceler, bug tespit eder, guvenlik aciklari tarar,
    optimizasyon oner ve kod uretir.

    Attributes:
        config: Coding yapilandirmasi.
    """

    def __init__(
        self,
        config: CodingConfig | None = None,
    ) -> None:
        """CodingAgent'i baslatir.

        Args:
            config: Coding yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="coding")
        self.config = config or CodingConfig()
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        """Anthropic API istemcisini dondurur (lazy init).

        Returns:
            Yapilandirilmis AsyncAnthropic.

        Raises:
            ValueError: API key eksikse.
        """
        if self._client is not None:
            return self._client

        api_key = settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError("Anthropic API key yapilandirilmamis.")

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._client

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Kod gorevini calistirir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - task_type: Gorev tipi (analyze/bug_detect/optimize/
                  security_scan/generate/review).
                - code: Analiz edilecek kaynak kodu.
                - language: Programlama dili (opsiyonel, otomatik tespit).
                - filename: Dosya adi (dil tespiti icin, opsiyonel).
                - prompt: Kod uretimi icin istek metni (generate icin).
                - config: Ozel yapilandirma (dict, opsiyonel).

        Returns:
            Kod analiz sonuclarini iceren TaskResult.
        """
        if task.get("config"):
            self.config = CodingConfig(**task["config"])

        # Gorev tipini belirle
        task_type_str = task.get("task_type", "analyze")
        try:
            task_type = CodeTaskType(task_type_str)
        except ValueError:
            return TaskResult(
                success=False,
                message=f"Gecersiz gorev tipi: {task_type_str}",
                errors=[f"Gecerli tipler: {[t.value for t in CodeTaskType]}"],
            )

        code = task.get("code", "")
        prompt = task.get("prompt", "")

        # generate haricinde kod gerekli
        if task_type != CodeTaskType.GENERATE and not code:
            return TaskResult(
                success=False,
                message="Analiz edilecek kod belirtilmemis.",
                errors=["code alani bos."],
            )

        # generate icin prompt gerekli
        if task_type == CodeTaskType.GENERATE and not prompt:
            return TaskResult(
                success=False,
                message="Kod uretimi icin istek metni belirtilmemis.",
                errors=["prompt alani bos."],
            )

        # Dil tespiti
        language = self._detect_language(
            task.get("language", ""),
            task.get("filename", ""),
            code,
        )

        self.logger.info(
            "Kod analizi baslatiliyor: tip=%s, dil=%s, uzunluk=%d",
            task_type.value,
            language.value,
            len(code),
        )

        analysis_result = CodeAnalysisResult(
            task_type=task_type,
            language=language,
        )
        errors: list[str] = []

        # 1. Statik analiz (guvenlik taramasi icin her zaman, diger tipler icin de calistir)
        if self.config.static_analysis_enabled and code:
            static_vulns = self._run_static_analysis(code, language)
            analysis_result.vulnerabilities.extend(static_vulns)

        # 2. LLM analizi
        try:
            llm_result = await self._run_llm_analysis(
                task_type, code, language, prompt,
            )
            self._merge_llm_result(analysis_result, llm_result)
        except Exception as exc:
            self.logger.error("LLM analiz hatasi: %s", exc)
            errors.append(f"LLM analizi: {exc}")

        # Ozet olustur
        if not analysis_result.summary:
            analysis_result.summary = self._build_summary(analysis_result)

        # Karar matrisi icin analiz
        analysis = await self.analyze({"result": analysis_result.model_dump()})

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "analysis_result": analysis_result.model_dump(),
                "analysis": analysis,
            },
            message=analysis_result.summary or "Kod analizi tamamlandi.",
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Kod Raporu:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analiz sonuclarini degerlendirir ve risk/aciliyet belirler.

        Args:
            data: {"result": CodeAnalysisResult dict}.

        Returns:
            Analiz sonuclari: risk, urgency, action, summary, issues.
        """
        result_dict = data.get("result", {})
        result = (
            CodeAnalysisResult(**result_dict)
            if isinstance(result_dict, dict)
            else result_dict
        )

        issues: list[str] = []

        # Guvenlik aciklari
        for v in result.vulnerabilities:
            issues.append(
                f"GUVENLIK [{v.severity.value.upper()}]: {v.description} "
                f"(tip={v.vuln_type.value}, satir={v.line})"
            )

        # Kod sorunlari
        critical_count = 0
        error_count = 0
        for i in result.issues:
            if i.severity == SeverityLevel.CRITICAL:
                critical_count += 1
            elif i.severity == SeverityLevel.ERROR:
                error_count += 1
            if i.severity in (SeverityLevel.CRITICAL, SeverityLevel.ERROR):
                issues.append(
                    f"KOD [{i.severity.value.upper()}]: {i.message} "
                    f"(kategori={i.category}, satir={i.line})"
                )

        # Kalite
        if result.quality.overall_score < 4.0:
            issues.append(
                f"Dusuk kod kalitesi: genel={result.quality.overall_score:.1f}/10"
            )

        # Risk ve aciliyet eslestirmesi
        risk, urgency = self._map_to_risk_urgency(result)
        action = self._determine_action(risk, urgency)

        return {
            "task_type": result.task_type.value,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": result.summary,
            "issues": issues,
            "stats": {
                "vulnerability_count": len(result.vulnerabilities),
                "critical_vulns": sum(
                    1 for v in result.vulnerabilities
                    if v.severity == SeverityLevel.CRITICAL
                ),
                "issue_count": len(result.issues),
                "critical_issues": critical_count,
                "error_issues": error_count,
                "quality_score": result.quality.overall_score,
                "suggestion_count": len(result.suggestions),
            },
        }

    async def report(self, result: TaskResult) -> str:
        """Kod analiz sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Telegram ve log icin formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        stats = analysis.get("stats", {})
        issues = analysis.get("issues", [])

        lines = [
            "=== KOD ANALIZ RAPORU ===",
            f"Gorev: {analysis.get('task_type', 'bilinmiyor').upper()}",
            f"Risk: {analysis.get('risk', '-')} | Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            "",
            analysis.get("summary", ""),
            "",
            "--- Istatistikler ---",
            f"  Guvenlik acigi: {stats.get('vulnerability_count', 0)}"
            f" (kritik: {stats.get('critical_vulns', 0)})",
            f"  Kod sorunu: {stats.get('issue_count', 0)}"
            f" (kritik: {stats.get('critical_issues', 0)},"
            f" hata: {stats.get('error_issues', 0)})",
            f"  Kalite puani: {stats.get('quality_score', 0):.1f}/10",
            f"  Oneri sayisi: {stats.get('suggestion_count', 0)}",
            "",
        ]

        if issues:
            lines.append("--- Bulgular ---")
            for issue in issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Dahili metodlar ===

    def _detect_language(
        self,
        language_str: str,
        filename: str,
        code: str,
    ) -> CodeLanguage:
        """Programlama dilini tespit eder.

        Oncelik sirasi:
        1. Acikca belirtilen dil
        2. Dosya uzantisi
        3. Kod iceriginden tahmin

        Args:
            language_str: Kullanicinin belirttigi dil.
            filename: Dosya adi.
            code: Kaynak kodu.

        Returns:
            Tespit edilen dil.
        """
        # 1. Acikca belirtilmis
        if language_str:
            try:
                return CodeLanguage(language_str.lower())
            except ValueError:
                pass

        # 2. Dosya uzantisi
        if filename:
            for ext, lang in _EXTENSION_MAP.items():
                if filename.endswith(ext):
                    return lang

        # 3. Icerik tahmini
        if code:
            if re.search(r"^(?:def |class |import |from .+ import )", code, re.MULTILINE):
                return CodeLanguage.PYTHON
            if re.search(r"<\?php", code):
                return CodeLanguage.PHP
            if re.search(
                r"(?:function\s+\w+|const\s+\w+|=>\s*\{|require\(|import\s+.+from)",
                code,
            ):
                return CodeLanguage.JAVASCRIPT
            if re.search(r"(?:SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\s", code, re.IGNORECASE):
                return CodeLanguage.SQL
            if re.search(r"^#!.*(?:bash|sh)", code) or re.search(r"^\s*(?:if\s+\[|fi$|done$)", code, re.MULTILINE):
                return CodeLanguage.BASH

        return CodeLanguage.PYTHON

    def _run_static_analysis(
        self,
        code: str,
        language: CodeLanguage,
    ) -> list[SecurityVulnerability]:
        """Regex tabanli statik guvenlik analizi yapar.

        Args:
            code: Kaynak kodu.
            language: Programlama dili.

        Returns:
            Tespit edilen guvenlik aciklari.
        """
        vulns: list[SecurityVulnerability] = []
        patterns = _SECURITY_PATTERNS.get(language, [])

        for pattern_str, vuln_type, severity, desc, fix in patterns:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
            except re.error:
                continue

            for match in pattern.finditer(code):
                # Satir numarasi hesapla
                line_num = code[:match.start()].count("\n") + 1
                snippet = match.group(0)[:100]

                vulns.append(
                    SecurityVulnerability(
                        vuln_type=vuln_type,
                        line=line_num,
                        severity=severity,
                        description=desc,
                        fix=fix,
                        snippet=snippet,
                    )
                )

        return vulns

    async def _run_llm_analysis(
        self,
        task_type: CodeTaskType,
        code: str,
        language: CodeLanguage,
        prompt: str,
    ) -> dict[str, Any]:
        """Anthropic Claude API ile kod analizi yapar.

        Args:
            task_type: Gorev tipi.
            code: Kaynak kodu.
            language: Programlama dili.
            prompt: Kod uretimi icin istek metni.

        Returns:
            LLM analiz sonucu (dict).
        """
        client = self._get_client()

        template = _TASK_PROMPTS[task_type]
        user_message = template.format(
            language=language.value,
            code=code,
            prompt=prompt,
        )

        response = await client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Yaniti parse et
        raw_text = response.content[0].text
        return self._parse_llm_response(raw_text)

    @staticmethod
    def _parse_llm_response(text: str) -> dict[str, Any]:
        """LLM yanitini JSON olarak parse eder.

        Args:
            text: LLM ham yaniti.

        Returns:
            Parse edilmis dict. Parse basarisizsa bos dict icinde
            raw_text anahtar ile ham metin doner.
        """
        # JSON blogu bul (``` arasinda veya dogrudan)
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        json_str = json_match.group(1) if json_match else text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Yanit dumduz JSON degilse, icinden { } blogu cikar
            brace_match = re.search(r"\{.*\}", json_str, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"raw_text": text}

    @staticmethod
    def _merge_llm_result(
        result: CodeAnalysisResult,
        llm_data: dict[str, Any],
    ) -> None:
        """LLM sonucunu CodeAnalysisResult'a birlestirir.

        Args:
            result: Mevcut analiz sonucu.
            llm_data: LLM'den gelen dict.
        """
        # Issues
        for issue_dict in llm_data.get("issues", []):
            try:
                severity = SeverityLevel(issue_dict.get("severity", "info"))
            except ValueError:
                severity = SeverityLevel.INFO
            result.issues.append(
                CodeIssue(
                    line=issue_dict.get("line", 0),
                    severity=severity,
                    category=issue_dict.get("category", ""),
                    message=issue_dict.get("message", ""),
                    suggestion=issue_dict.get("suggestion", ""),
                )
            )

        # Vulnerabilities (LLM'den gelen ek guvenlik bulgusu)
        for vuln_dict in llm_data.get("vulnerabilities", []):
            try:
                vuln_type = VulnerabilityType(vuln_dict.get("vuln_type", "other"))
            except ValueError:
                vuln_type = VulnerabilityType.OTHER
            try:
                severity = SeverityLevel(vuln_dict.get("severity", "warning"))
            except ValueError:
                severity = SeverityLevel.WARNING
            result.vulnerabilities.append(
                SecurityVulnerability(
                    vuln_type=vuln_type,
                    line=vuln_dict.get("line", 0),
                    severity=severity,
                    description=vuln_dict.get("description", ""),
                    fix=vuln_dict.get("fix", ""),
                    snippet=vuln_dict.get("snippet", ""),
                )
            )

        # Quality
        quality_dict = llm_data.get("quality")
        if quality_dict and isinstance(quality_dict, dict):
            result.quality = CodeQualityMetrics(
                complexity=quality_dict.get("complexity", 5.0),
                readability=quality_dict.get("readability", 5.0),
                maintainability=quality_dict.get("maintainability", 5.0),
                overall_score=quality_dict.get("overall_score", 5.0),
            )

        # Suggestions
        result.suggestions.extend(llm_data.get("suggestions", []))

        # Generated code
        if llm_data.get("generated_code"):
            result.generated_code = llm_data["generated_code"]

        # Explanation
        if llm_data.get("explanation"):
            result.explanation = llm_data["explanation"]

        # Summary
        if llm_data.get("summary"):
            result.summary = llm_data["summary"]

    def _build_summary(self, result: CodeAnalysisResult) -> str:
        """Analiz ozeti olusturur.

        Args:
            result: Kod analiz sonucu.

        Returns:
            Ozet metni.
        """
        parts = [f"Gorev: {result.task_type.value}", f"Dil: {result.language.value}"]

        if result.vulnerabilities:
            critical = sum(
                1 for v in result.vulnerabilities
                if v.severity == SeverityLevel.CRITICAL
            )
            parts.append(f"{len(result.vulnerabilities)} guvenlik acigi (kritik: {critical})")

        if result.issues:
            parts.append(f"{len(result.issues)} kod sorunu")

        parts.append(f"Kalite: {result.quality.overall_score:.1f}/10")

        if result.generated_code:
            parts.append("Kod uretildi")

        return " | ".join(parts)

    @staticmethod
    def _map_to_risk_urgency(
        result: CodeAnalysisResult,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """Kod analiz bulgularini RiskLevel ve UrgencyLevel'a esler.

        Karar matrisi entegrasyonu:
        - Kritik guvenlik acigi -> HIGH risk, HIGH urgency (acil)
        - Error guvenlik acigi veya kritik bug -> HIGH risk, MEDIUM urgency
        - Warning guvenlik acigi veya error bug -> MEDIUM risk, MEDIUM urgency
        - Sadece bilgi/uyari -> LOW risk, LOW urgency
        - Dusuk kalite (< 4.0) -> MEDIUM risk, LOW urgency

        Args:
            result: Kod analiz sonucu.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        has_critical_vuln = any(
            v.severity == SeverityLevel.CRITICAL for v in result.vulnerabilities
        )
        has_error_vuln = any(
            v.severity == SeverityLevel.ERROR for v in result.vulnerabilities
        )
        has_critical_issue = any(
            i.severity == SeverityLevel.CRITICAL for i in result.issues
        )
        has_error_issue = any(
            i.severity == SeverityLevel.ERROR for i in result.issues
        )

        # Kritik guvenlik acigi -> en yuksek oncelik
        if has_critical_vuln:
            return RiskLevel.HIGH, UrgencyLevel.HIGH

        # Error seviye guvenlik acigi veya kritik bug
        if has_error_vuln or has_critical_issue:
            return RiskLevel.HIGH, UrgencyLevel.MEDIUM

        # Warning guvenlik acigi veya error bug
        if result.vulnerabilities or has_error_issue:
            return RiskLevel.MEDIUM, UrgencyLevel.MEDIUM

        # Dusuk kalite
        if result.quality.overall_score < 4.0:
            return RiskLevel.MEDIUM, UrgencyLevel.LOW

        # Kod uretimi veya temiz sonuc
        return RiskLevel.LOW, UrgencyLevel.LOW

    @staticmethod
    def _determine_action(risk: RiskLevel, urgency: UrgencyLevel) -> ActionType:
        """Risk ve aciliyetten aksiyon tipini belirler.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.

        Returns:
            Uygun aksiyon tipi.
        """
        action, _ = DECISION_RULES.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),
        )
        return action
