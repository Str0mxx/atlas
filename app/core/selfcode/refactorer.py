"""ATLAS Kod Yeniden Duzenleme Motoru.

AST tabanli kod yeniden duzenleme: metot cikarimi, sinif cikarimi,
sembol yeniden adlandirma, olu kod temizligi ve basitlestirme.
"""

import ast
import logging
import re
import textwrap
from collections import Counter
from typing import Optional
from uuid import uuid4

from app.models.selfcode import (
    CodeSmellType,
    RefactorPlan,
    RefactorResult,
    RefactorType,
)

logger = logging.getLogger(__name__)


class CodeRefactorer:
    """AST tabanli Python kod yeniden duzenleyici.

    Attributes:
        max_method_lines: Uzun metot esigi (satir sayisi).
        min_duplicate_lines: Tekrar blok esigi (satir sayisi).
    """

    def __init__(self, max_method_lines: int = 50, min_duplicate_lines: int = 4) -> None:
        """Yeni CodeRefactorer olusturur.

        Args:
            max_method_lines: Uzun metot esigi (satir sayisi).
            min_duplicate_lines: Tekrar blok esigi (satir sayisi).
        """
        self.max_method_lines = max_method_lines
        self.min_duplicate_lines = min_duplicate_lines

    def analyze(self, source: str, file_path: str = "") -> list[RefactorPlan]:
        """Kaynak kodu analiz ederek yeniden duzenleme firsatlarini tespit eder.

        Args:
            source: Python kaynak kodu.
            file_path: Dosya yolu (raporlama icin).

        Returns:
            Tespit edilen yeniden duzenleme planlari listesi.
        """
        plans: list[RefactorPlan] = []
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            logger.warning("Ayristirma hatasi, analiz atlanildi: %s", exc)
            return plans

        # Uzun metotlar
        for name, line, length in self._find_long_methods(tree):
            plans.append(RefactorPlan(
                id=uuid4().hex[:12], refactor_type=RefactorType.EXTRACT_METHOD,
                target=name, file_path=file_path,
                description=f"'{name}' metodu cok uzun ({length} satir, esik: {self.max_method_lines})",
                estimated_impact=min(1.0, length / (self.max_method_lines * 3)),
            ))
        # Tekrar bloklar
        for block_text, count in self._find_duplicate_blocks(source):
            plans.append(RefactorPlan(
                id=uuid4().hex[:12], refactor_type=RefactorType.EXTRACT_METHOD,
                target=block_text[:60], file_path=file_path,
                description=f"Tekrarlanan kod blogu ({count} kez)",
                estimated_impact=min(1.0, count * 0.2),
            ))
        # Kullanilmayan importlar
        for imp_line in self._find_unused_imports(source, tree):
            plans.append(RefactorPlan(
                id=uuid4().hex[:12], refactor_type=RefactorType.DEAD_CODE_REMOVAL,
                target=imp_line.strip(), file_path=file_path,
                description=f"Kullanilmayan import: '{imp_line.strip()}'",
                estimated_impact=0.1,
            ))
        # Olu kod (return sonrasi ifadeler)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return) and i < len(node.body) - 1:
                        plans.append(RefactorPlan(
                            id=uuid4().hex[:12], refactor_type=RefactorType.DEAD_CODE_REMOVAL,
                            target=node.name, file_path=file_path,
                            description=f"'{node.name}' icinde return sonrasi erisilemeyen kod",
                            estimated_impact=0.3,
                        ))
                        break

        logger.info("Analiz tamamlandi: %s (%d plan)", file_path, len(plans))
        return plans

    def extract_method(self, source: str, start_line: int, end_line: int, method_name: str) -> RefactorResult:
        """Belirtilen satir araligini yeni bir metoda cikarir.

        Args:
            source: Kaynak kod metni.
            start_line: Baslangic satiri (1-tabanli).
            end_line: Bitis satiri (1-tabanli, dahil).
            method_name: Yeni metot adi.

        Returns:
            Cikarim sonucu.
        """
        lines = source.splitlines()
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            logger.warning("Gecersiz satir araligi: %d-%d", start_line, end_line)
            return RefactorResult(success=False, original_code=source, refactored_code=source)

        block = lines[start_line - 1: end_line]
        # Mevcut girintiyi tespit et
        base_indent = re.match(r"^(\s*)", block[0]).group(1)
        body_lines = [l[len(base_indent):] if l.startswith(base_indent) else l for l in block]

        new_method_lines = [
            f"{base_indent}def {method_name}(self):",
            f'{base_indent}    """{method_name} islemini gerceklestirir."""',
        ]
        for bl in body_lines:
            new_method_lines.append(f"{base_indent}    {bl}" if bl.strip() else "")

        call_line = f"{base_indent}self.{method_name}()"
        new_lines = lines[:start_line - 1] + [call_line] + lines[end_line:] + [""] + new_method_lines
        refactored = "\n".join(new_lines)
        added, removed = self._count_changes(source, refactored)

        logger.info("Metot cikarimi: '%s' (%d satir)", method_name, end_line - start_line + 1)
        return RefactorResult(
            success=True, original_code=source, refactored_code=refactored,
            changes_count=added + removed, lines_added=added, lines_removed=removed,
        )

    def extract_class(self, source: str, method_names: list[str], new_class_name: str) -> RefactorResult:
        """Belirtilen metotlari yeni bir sinifa cikarir.

        Args:
            source: Kaynak kod metni.
            method_names: Cikarilacak metot adlari.
            new_class_name: Yeni sinif adi.

        Returns:
            Cikarim sonucu.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return RefactorResult(success=False, original_code=source, refactored_code=source)

        lines = source.splitlines()
        extracted_ranges: list[tuple[int, int]] = []
        extracted_blocks: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in method_names:
                end_line = node.end_lineno or node.lineno
                extracted_ranges.append((node.lineno, end_line))
                extracted_blocks.append("\n".join(lines[node.lineno - 1: end_line]))

        if not extracted_blocks:
            logger.warning("Cikarilacak metot bulunamadi: %s", method_names)
            return RefactorResult(success=False, original_code=source, refactored_code=source)

        class_lines = [f"class {new_class_name}:", f'    """{new_class_name} sinifi."""', ""]
        for block in extracted_blocks:
            for bl in block.splitlines():
                class_lines.append(f"    {bl}" if bl.strip() else "")
            class_lines.append("")

        new_lines = lines[:]
        for start, end in sorted(extracted_ranges, reverse=True):
            del new_lines[start - 1: end]
        new_lines.extend(["", ""] + class_lines)

        refactored = "\n".join(new_lines)
        added, removed = self._count_changes(source, refactored)
        logger.info("Sinif cikarimi: '%s' (%d metot)", new_class_name, len(extracted_blocks))
        return RefactorResult(
            success=True, original_code=source, refactored_code=refactored,
            changes_count=added + removed, lines_added=added, lines_removed=removed,
        )

    def rename_symbol(self, source: str, old_name: str, new_name: str) -> RefactorResult:
        """Degisken/fonksiyon/sinif adini tum kodda yeniden adlandirir.

        Args:
            source: Kaynak kod metni.
            old_name: Mevcut sembol adi.
            new_name: Yeni sembol adi.

        Returns:
            Yeniden adlandirma sonucu.
        """
        pattern = re.compile(r"\b" + re.escape(old_name) + r"\b")
        refactored = pattern.sub(new_name, source)
        if refactored == source:
            logger.info("Sembol bulunamadi: '%s'", old_name)
            return RefactorResult(success=False, original_code=source, refactored_code=source)

        count = len(pattern.findall(source))
        added, removed = self._count_changes(source, refactored)
        logger.info("Sembol yeniden adlandirildi: '%s' -> '%s' (%d yer)", old_name, new_name, count)
        return RefactorResult(
            success=True, original_code=source, refactored_code=refactored,
            changes_count=count, lines_added=added, lines_removed=removed,
        )

    def remove_dead_code(self, source: str) -> RefactorResult:
        """Erisilemeyen ve kullanilmayan kodu tespit edip kaldirir.

        Args:
            source: Kaynak kod metni.

        Returns:
            Temizleme sonucu.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return RefactorResult(success=False, original_code=source, refactored_code=source)

        lines = source.splitlines()
        lines_to_remove: set[int] = set()

        # Return/raise sonrasi erisilemeyen satirlar
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found_terminal = False
                for stmt in node.body:
                    if found_terminal:
                        end = stmt.end_lineno or stmt.lineno
                        for ln in range(stmt.lineno, end + 1):
                            lines_to_remove.add(ln)
                    if isinstance(stmt, (ast.Return, ast.Raise)):
                        found_terminal = True

        # Kullanilmayan importlar
        for imp_line in self._find_unused_imports(source, tree):
            for i, line in enumerate(lines, start=1):
                if line.strip() == imp_line.strip():
                    lines_to_remove.add(i)

        if not lines_to_remove:
            return RefactorResult(success=True, original_code=source, refactored_code=source, changes_count=0)

        new_lines = [line for i, line in enumerate(lines, start=1) if i not in lines_to_remove]
        refactored = "\n".join(new_lines)
        added, removed = self._count_changes(source, refactored)
        logger.info("Olu kod temizlendi: %d satir kaldirildi", removed)
        return RefactorResult(
            success=True, original_code=source, refactored_code=refactored,
            changes_count=removed, lines_added=added, lines_removed=removed,
        )

    def simplify(self, source: str) -> RefactorResult:
        """Basitlestirme donusumleri uygular (gereksiz else, ic ice if birlestirme).

        Args:
            source: Kaynak kod metni.

        Returns:
            Basitlestirme sonucu.
        """
        refactored = source
        # return sonrasi gereksiz else kaldir
        refactored = re.sub(
            r"([ \t]*)(if\s+.+:\s*\n(?:\1[ \t]+.+\n)*\1[ \t]+return\s+.+\n)\1else:\s*\n",
            r"\1\2", refactored,
        )
        # Ic ice if birlestirme
        refactored = re.sub(
            r"([ \t]*)if\s+(.+):\s*\n\1([ \t]+)if\s+(.+):\s*\n",
            r"\1if \2 and \4:\n", refactored,
        )
        if refactored == source:
            return RefactorResult(success=True, original_code=source, refactored_code=source, changes_count=0)

        added, removed = self._count_changes(source, refactored)
        logger.info("Basitlestirme uygulandi: +%d/-%d satir", added, removed)
        return RefactorResult(
            success=True, original_code=source, refactored_code=refactored,
            changes_count=added + removed, lines_added=added, lines_removed=removed,
        )

    def apply_plan(self, plan: RefactorPlan, source: str) -> RefactorResult:
        """Verilen yeniden duzenleme planini kaynak koda uygular.

        Args:
            plan: Uygulanacak yeniden duzenleme plani.
            source: Kaynak kod metni.

        Returns:
            Uygulama sonucu.
        """
        logger.info("Plan uygulaniyor: tip=%s, hedef='%s'", plan.refactor_type.value, plan.target)

        if plan.refactor_type == RefactorType.DEAD_CODE_REMOVAL:
            result = self.remove_dead_code(source)
        elif plan.refactor_type == RefactorType.SIMPLIFY:
            result = self.simplify(source)
        elif plan.refactor_type == RefactorType.RENAME:
            parts = plan.target.split("->")
            if len(parts) == 2:
                result = self.rename_symbol(source, parts[0].strip(), parts[1].strip())
            else:
                result = RefactorResult(success=False, original_code=source, refactored_code=source)
        elif plan.refactor_type == RefactorType.EXTRACT_METHOD:
            result = self.simplify(source)
        else:
            result = RefactorResult(success=False, original_code=source, refactored_code=source)

        result.plan_id = plan.id
        logger.info("Plan sonucu: basari=%s, degisiklik=%d", result.success, result.changes_count)
        return result

    # --- Dahili yardimcilar ---

    def _find_long_methods(self, tree: ast.Module) -> list[tuple[str, int, int]]:
        """Esigi asan metotlari tespit eder."""
        results: list[tuple[str, int, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = node.end_lineno or node.lineno
                length = end - node.lineno + 1
                if length > self.max_method_lines:
                    results.append((node.name, node.lineno, length))
        return results

    def _find_duplicate_blocks(self, source: str) -> list[tuple[str, int]]:
        """Tekrar eden kod bloklarini tespit eder (satir tabanli eslestirme)."""
        lines = [l.strip() for l in source.splitlines() if l.strip()]
        if len(lines) < self.min_duplicate_lines:
            return []

        counter: Counter[str] = Counter()
        w = self.min_duplicate_lines
        skip = {"pass", '"""', "..."}
        for i in range(len(lines) - w + 1):
            block = lines[i: i + w]
            if any(bl in skip for bl in block):
                continue
            counter["\n".join(block)] += 1

        return [(text, cnt) for text, cnt in counter.items() if cnt >= 2]

    def _find_unused_imports(self, source: str, tree: ast.Module) -> list[str]:
        """Kullanilmayan import ifadelerini tespit eder."""
        lines = source.splitlines()
        rest = "\n".join(l for l in lines if not l.strip().startswith(("import ", "from ")))
        unused: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[-1]
                    if not re.search(r"\b" + re.escape(name) + r"\b", rest):
                        unused.append(ast.unparse(node))
                        break
            elif isinstance(node, ast.ImportFrom) and node.names:
                if all(
                    (a.asname or a.name) != "*"
                    and not re.search(r"\b" + re.escape(a.asname or a.name) + r"\b", rest)
                    for a in node.names
                ):
                    unused.append(ast.unparse(node))
        return unused

    def _count_changes(self, original: str, refactored: str) -> tuple[int, int]:
        """Orijinal ve duzenlenmis kod arasindaki eklenen/silinen satir sayisini hesaplar."""
        orig = original.splitlines()
        new = refactored.splitlines()
        added = max(0, len(new) - len(orig))
        removed = max(0, len(orig) - len(new))
        changed = sum(1 for i in range(min(len(orig), len(new))) if orig[i] != new[i])
        return added + changed, removed + changed
