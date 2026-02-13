"""ATLAS Kod Analiz Motoru.

AST tabanli kod analizi: bagimlilik cikarimi, karmasiklik hesaplama,
kod kokusu tespiti ve guvenlik acigi taramasi.
"""

import ast
import logging
import re
from typing import Optional

from app.models.selfcode import (
    AnalysisIssue,
    AnalysisSeverity,
    CodeAnalysisReport,
    CodeSmellType,
    ComplexityMetrics,
    DependencyInfo,
)

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """AST tabanli Python kod analizci.

    Kaynak kodu ayristirip bagimlilik, karmasiklik, kod kokusu
    ve guvenlik acigi analizlerini calistirir.

    Attributes:
        max_method_lines: Uzun metot esigi (satir sayisi).
        max_class_lines: Buyuk sinif esigi (satir sayisi).
        max_complexity: Karmasiklik esigi.
    """

    # Guvenlik acigi desenleri: desen adi -> tehlikeli fonksiyonlar
    SECURITY_PATTERNS: dict[str, str] = {
        "eval_usage": r"\beval\s*\(",
        "exec_usage": r"\bexec\s*\(",
        "subprocess_shell": r"subprocess\.\w+\(.*shell\s*=\s*True",
        "os_system": r"\bos\.system\s*\(",
        "dynamic_import": r"\b__import__\s*\(",
        "pickle_loads": r"\bpickle\.loads\s*\(",
        "unsafe_yaml": r"\byaml\.load\s*\([^)]*(?!Loader\s*=\s*SafeLoader)[^)]*\)",
    }

    # Standart kutuphane modulleri (yaygin olanlar)
    STDLIB_MODULES: set[str] = {
        "abc", "argparse", "ast", "asyncio", "base64", "bisect",
        "calendar", "cmath", "codecs", "collections", "colorsys",
        "configparser", "contextlib", "copy", "csv", "ctypes",
        "dataclasses", "datetime", "decimal", "difflib", "dis",
        "email", "enum", "errno", "fcntl", "filecmp", "fnmatch",
        "fractions", "ftplib", "functools", "gc", "getpass", "glob",
        "gzip", "hashlib", "heapq", "hmac", "html", "http",
        "importlib", "inspect", "io", "ipaddress", "itertools",
        "json", "keyword", "linecache", "locale", "logging",
        "math", "mimetypes", "multiprocessing", "numbers",
        "operator", "os", "pathlib", "pickle", "platform",
        "pprint", "queue", "random", "re", "secrets", "select",
        "shelve", "shlex", "shutil", "signal", "smtplib", "socket",
        "sqlite3", "ssl", "stat", "statistics", "string",
        "struct", "subprocess", "sys", "syslog", "tempfile",
        "textwrap", "threading", "time", "timeit", "token",
        "tokenize", "traceback", "types", "typing", "unicodedata",
        "unittest", "urllib", "uuid", "venv", "warnings",
        "weakref", "xml", "zipfile", "zlib",
    }

    def __init__(
        self,
        max_method_lines: int = 50,
        max_class_lines: int = 300,
        max_complexity: int = 10,
    ) -> None:
        """Kod analizcisini yapilandirir.

        Args:
            max_method_lines: Uzun metot esigi (satir sayisi).
            max_class_lines: Buyuk sinif esigi (satir sayisi).
            max_complexity: Karmasiklik esigi.
        """
        self.max_method_lines = max_method_lines
        self.max_class_lines = max_class_lines
        self.max_complexity = max_complexity

    def parse(self, source: str) -> Optional[ast.Module]:
        """Kaynak kodu AST'ye ayristirir.

        Args:
            source: Python kaynak kodu.

        Returns:
            AST modul dugumu veya None (ayristirma hatasinda).
        """
        try:
            tree = ast.parse(source)
            logger.debug("Kaynak kod basariyla ayristirildi")
            return tree
        except SyntaxError as e:
            logger.warning(f"Sozdizimi hatasi: {e}")
            return None

    def analyze(self, source: str, file_path: str = "") -> CodeAnalysisReport:
        """Kaynak kodu tam analiz eder.

        Ayristirma, bagimlilik cikarimi, karmasiklik hesaplama,
        kod kokusu tespiti ve guvenlik taramasi yapar.

        Args:
            source: Python kaynak kodu.
            file_path: Dosya yolu (raporlama icin).

        Returns:
            Tum bulgulari iceren analiz raporu.
        """
        report = CodeAnalysisReport(file_path=file_path)
        tree = self.parse(source)

        if tree is None:
            report.issues.append(
                AnalysisIssue(
                    message="Kaynak kod ayristirilamadi (sozdizimi hatasi)",
                    severity=AnalysisSeverity.ERROR,
                    rule="syntax_error",
                )
            )
            report.score = 0.0
            logger.error(f"Analiz basarisiz - ayristirma hatasi: {file_path}")
            return report

        # 1. Bagimliliklari cikar
        report.dependencies = self.extract_dependencies(tree)

        # 2. Karmasiklik hesapla
        report.complexity = self.calculate_complexity(tree, source)

        # 3. Kod kokularini tespit et
        smells, smell_issues = self.detect_code_smells(tree, source)
        report.code_smells = smells
        report.issues.extend(smell_issues)

        # 4. Guvenlik sorunlarini tespit et
        report.security_issues = self.detect_security_issues(source)

        # 5. Genel puani hesapla
        score = 100.0
        # Her WARNING icin 2 puan dus
        score -= sum(
            2 for i in report.issues if i.severity == AnalysisSeverity.WARNING
        )
        # Her ERROR icin 5 puan dus
        score -= sum(
            5 for i in report.issues if i.severity == AnalysisSeverity.ERROR
        )
        # Her CRITICAL icin 10 puan dus
        score -= sum(
            10 for i in report.issues if i.severity == AnalysisSeverity.CRITICAL
        )
        # Kod kokulari icin 3 puan dus
        score -= len(report.code_smells) * 3
        # Guvenlik sorunlari icin 8 puan dus
        score -= len(report.security_issues) * 8
        # Karmasiklik esik asimi icin 5 puan dus
        if report.complexity.cyclomatic > self.max_complexity:
            score -= 5

        report.score = max(0.0, min(100.0, score))

        logger.info(
            f"Analiz tamamlandi: {file_path} "
            f"(puan={report.score:.1f}, "
            f"sorun={len(report.issues)}, "
            f"guvenlik={len(report.security_issues)})"
        )
        return report

    def extract_dependencies(self, tree: ast.Module) -> list[DependencyInfo]:
        """AST'den import ifadelerini cikarir.

        Args:
            tree: Ayristirilmis AST modulu.

        Returns:
            Bagimlilik bilgileri listesi.
        """
        dependencies: list[DependencyInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    dependencies.append(
                        DependencyInfo(
                            module=alias.name,
                            names=[alias.asname or alias.name],
                            is_stdlib=module_name in self.STDLIB_MODULES,
                            is_local=alias.name.startswith("app."),
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    imported_names = [
                        a.asname or a.name for a in (node.names or [])
                    ]
                    dependencies.append(
                        DependencyInfo(
                            module=node.module,
                            names=imported_names,
                            is_stdlib=module_name in self.STDLIB_MODULES,
                            is_local=node.module.startswith("app."),
                        )
                    )

        logger.debug(f"{len(dependencies)} bagimlilik cikarildi")
        return dependencies

    def calculate_complexity(
        self, tree: ast.Module, source: str
    ) -> ComplexityMetrics:
        """Kod karmasiklik metriklerini hesaplar.

        Siklomatik ve bilissel karmasiklik, satir sayisi
        ve bakim endeksi hesaplanir.

        Args:
            tree: Ayristirilmis AST modulu.
            source: Ham kaynak kod metni.

        Returns:
            Karmasiklik metrikleri.
        """
        lines = source.strip().splitlines()
        loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

        # Siklomatik karmasiklik: 1 + dal noktalari sayisi
        cyclomatic = 1 + self._count_branches(tree)

        # Bilissel karmasiklik: ic ice yuvalama penaltisi ile dallar
        cognitive = self._calculate_cognitive(tree)

        # Halstead hacmi (basitlestirilmis: operator + operand sayilari)
        operators = 0
        operands = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare)):
                operators += 1
            elif isinstance(node, (ast.Constant, ast.Name)):
                operands += 1
        total = operators + operands
        volume = total * (total.bit_length() if total > 0 else 1)

        # Bakim endeksi (basitlestirilmis formul)
        if loc > 0 and cyclomatic > 0:
            mi = max(0.0, 171 - 5.2 * (loc ** 0.5) - 0.23 * cyclomatic - 16.2 * (volume ** 0.1))
            mi = min(100.0, mi * (100.0 / 171.0))
        else:
            mi = 100.0

        return ComplexityMetrics(
            cyclomatic=cyclomatic,
            cognitive=cognitive,
            halstead_volume=float(volume),
            lines_of_code=loc,
            maintainability_index=round(mi, 2),
        )

    def detect_code_smells(
        self, tree: ast.Module, source: str
    ) -> tuple[list[CodeSmellType], list[AnalysisIssue]]:
        """Kod kokularini tespit eder.

        Uzun metot, buyuk sinif, olasi oluk kod gibi kokulari tarar.

        Args:
            tree: Ayristirilmis AST modulu.
            source: Ham kaynak kod metni.

        Returns:
            Kod koku tipleri ve ilgili analiz sorunlari demeti.
        """
        smells: list[CodeSmellType] = []
        issues: list[AnalysisIssue] = []

        # Uzun metot kontrolu
        method_results = self._check_method_length(tree)
        for name, line, length in method_results:
            smells.append(CodeSmellType.LONG_METHOD)
            issues.append(
                AnalysisIssue(
                    message=f"Uzun metot: '{name}' ({length} satir, esik: {self.max_method_lines})",
                    severity=AnalysisSeverity.WARNING,
                    line=line,
                    rule="long_method",
                    suggestion=f"'{name}' metodunu daha kucuk parcalara bolerek refactor edin",
                )
            )

        # Buyuk sinif kontrolu
        class_results = self._check_class_size(tree)
        for name, line, length in class_results:
            smells.append(CodeSmellType.LARGE_CLASS)
            issues.append(
                AnalysisIssue(
                    message=f"Buyuk sinif: '{name}' ({length} satir, esik: {self.max_class_lines})",
                    severity=AnalysisSeverity.WARNING,
                    line=line,
                    rule="large_class",
                    suggestion=f"'{name}' sinifini sorumluluk alanina gore bolin",
                )
            )

        # God class: cok fazla metot
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = sum(
                    1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                if method_count > 20:
                    smells.append(CodeSmellType.GOD_CLASS)
                    issues.append(
                        AnalysisIssue(
                            message=f"God class: '{node.name}' ({method_count} metot)",
                            severity=AnalysisSeverity.WARNING,
                            line=node.lineno,
                            rule="god_class",
                            suggestion=f"'{node.name}' sinifini daha kucuk siniflara bolin",
                        )
                    )

        # Dead code: erisilemez kod (return sonrasi ifadeler)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return) and i < len(node.body) - 1:
                        smells.append(CodeSmellType.DEAD_CODE)
                        issues.append(
                            AnalysisIssue(
                                message=f"Olu kod: '{node.name}' icinde return sonrasi ifadeler",
                                severity=AnalysisSeverity.INFO,
                                line=stmt.lineno,
                                rule="dead_code",
                                suggestion="Return sonrasindaki erisilemeyen kodu kaldirin",
                            )
                        )
                        break

        logger.debug(f"{len(smells)} kod kokusu tespit edildi")
        return smells, issues

    def detect_security_issues(self, source: str) -> list[AnalysisIssue]:
        """Kaynak kodda guvenlik aciklari arar.

        eval, exec, subprocess shell=True gibi tehlikeli desenleri tarar.

        Args:
            source: Ham kaynak kod metni.

        Returns:
            Guvenlik sorunlari listesi.
        """
        security_issues: list[AnalysisIssue] = []

        for name, pattern in self.SECURITY_PATTERNS.items():
            for i, line in enumerate(source.splitlines(), start=1):
                if re.search(pattern, line):
                    security_issues.append(
                        AnalysisIssue(
                            message=f"Guvenlik acigi: {name}",
                            severity=AnalysisSeverity.CRITICAL,
                            line=i,
                            rule=f"security_{name}",
                            suggestion=f"'{name}' kullanimi guvenlik riski tasir, guvenli alternatif kullanin",
                        )
                    )

        logger.debug(f"{len(security_issues)} guvenlik sorunu tespit edildi")
        return security_issues

    def get_functions(self, tree: ast.Module) -> list[dict[str, object]]:
        """Tum fonksiyon/metot tanimlarini listeler.

        Args:
            tree: Ayristirilmis AST modulu.

        Returns:
            Her fonksiyon icin ad, satir, arguman sayisi ve async bilgisi.
        """
        functions: list[dict[str, object]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": len(node.args.args),
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "decorators": [
                        ast.dump(d) if not isinstance(d, ast.Name) else d.id
                        for d in node.decorator_list
                    ],
                })

        return functions

    def get_classes(self, tree: ast.Module) -> list[dict[str, object]]:
        """Tum sinif tanimlarini listeler.

        Args:
            tree: Ayristirilmis AST modulu.

        Returns:
            Her sinif icin ad, satir, temel siniflar ve metot sayisi.
        """
        classes: list[dict[str, object]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(ast.dump(base))

                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "bases": bases,
                    "methods": methods,
                    "method_count": len(methods),
                })

        return classes

    def _count_branches(self, tree: ast.Module) -> int:
        """Siklomatik karmasiklik icin dal noktalarini sayar.

        if, elif, for, while, except, and, or, assert, with ifadelerini sayar.

        Args:
            tree: Ayristirilmis AST modulu.

        Returns:
            Dal noktasi sayisi.
        """
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor)):
                count += 1
            elif isinstance(node, ast.ExceptHandler):
                count += 1
            elif isinstance(node, ast.BoolOp):
                # and/or her biri bir dal
                count += len(node.values) - 1
            elif isinstance(node, ast.Assert):
                count += 1
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                count += 1
        return count

    def _calculate_cognitive(self, tree: ast.Module, depth: int = 0) -> int:
        """Bilissel karmasiklik hesaplar (ic ice yuvalama penaltisi ile).

        Args:
            tree: AST dugumu.
            depth: Mevcut yuvalama derinligi.

        Returns:
            Bilissel karmasiklik puani.
        """
        total = 0
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor)):
                # Temel maliyet + yuvalama penaltisi
                total += 1 + depth
                total += self._calculate_cognitive(node, depth + 1)
            elif isinstance(node, ast.ExceptHandler):
                total += 1 + depth
                total += self._calculate_cognitive(node, depth + 1)
            elif isinstance(node, ast.BoolOp):
                total += len(node.values) - 1
                total += self._calculate_cognitive(node, depth)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Fonksiyon tanimlari derinligi sifirlar
                total += self._calculate_cognitive(node, 0)
            elif isinstance(node, ast.ClassDef):
                total += self._calculate_cognitive(node, 0)
            else:
                total += self._calculate_cognitive(node, depth)
        return total

    def _check_method_length(
        self, tree: ast.Module
    ) -> list[tuple[str, int, int]]:
        """Esigi asan metotlari tespit eder.

        Args:
            tree: Ayristirilmis AST modulu.

        Returns:
            (metot_adi, satir_no, satir_sayisi) demetleri listesi.
        """
        results: list[tuple[str, int, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Metot son satirini bul
                end_line = node.end_lineno or node.lineno
                length = end_line - node.lineno + 1
                if length > self.max_method_lines:
                    results.append((node.name, node.lineno, length))

        return results

    def _check_class_size(
        self, tree: ast.Module
    ) -> list[tuple[str, int, int]]:
        """Esigi asan siniflari tespit eder.

        Args:
            tree: Ayristirilmis AST modulu.

        Returns:
            (sinif_adi, satir_no, satir_sayisi) demetleri listesi.
        """
        results: list[tuple[str, int, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                end_line = node.end_lineno or node.lineno
                length = end_line - node.lineno + 1
                if length > self.max_class_lines:
                    results.append((node.name, node.lineno, length))

        return results
