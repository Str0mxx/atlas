"""ATLAS Otomatik Hata Ayiklama Motoru.

Hata mesajlarini ayristirma, kok neden analizi, duzeltme onerisi
uretimi ve basit durumlarda otomatik duzeltme islevleri saglar.
"""

import ast
import difflib
import logging
import re
from typing import Optional

from app.models.selfcode import DebugReport, FixConfidence, FixSuggestion

logger = logging.getLogger(__name__)

# Hata tiplerine gore yaygin duzeltme kaliplari
COMMON_FIXES: dict[str, str] = {
    "NameError": "Yazim hatasi kontrol et (difflib), eksik import kontrol et",
    "TypeError": "Arguman sayisi uyumsuzlugu veya tip donusumu kontrol et",
    "ImportError": "pip install ile yukle veya modul adini kontrol et",
    "ModuleNotFoundError": "pip install ile yukle veya modul adini kontrol et",
    "AttributeError": "Dogru attribute adini kontrol et",
    "IndexError": "Liste sinirlarini kontrol et",
    "KeyError": "Sozluk anahtarlarini kontrol et, .get() kullan",
    "ValueError": "Tip ve deger dogrulamasini kontrol et",
    "ZeroDivisionError": "Sifira bolme kontrolu ekle",
}

_ERROR_CATEGORIES: dict[str, str] = {
    "SyntaxError": "syntax", "IndentationError": "syntax", "TabError": "syntax",
    "NameError": "name", "UnboundLocalError": "name",
    "TypeError": "type", "ValueError": "value",
    "ImportError": "import", "ModuleNotFoundError": "import",
    "AttributeError": "attribute", "IndexError": "index", "KeyError": "key",
    "ZeroDivisionError": "runtime", "FileNotFoundError": "runtime",
    "PermissionError": "runtime", "RuntimeError": "runtime",
    "RecursionError": "runtime", "OSError": "runtime",
}

_COMMON_IMPORTS: dict[str, str] = {
    "Path": "from pathlib import Path", "Optional": "from typing import Optional",
    "Any": "from typing import Any", "Dict": "from typing import Dict",
    "List": "from typing import List", "datetime": "from datetime import datetime",
    "timezone": "from datetime import timezone", "Enum": "from enum import Enum",
    "BaseModel": "from pydantic import BaseModel", "Field": "from pydantic import Field",
    "json": "import json", "re": "import re", "os": "import os", "sys": "import sys",
}

_PIP_NAME_MAP: dict[str, str] = {
    "cv2": "opencv-python", "PIL": "Pillow", "sklearn": "scikit-learn",
    "yaml": "PyYAML", "bs4": "beautifulsoup4", "dotenv": "python-dotenv",
}


class AutoDebugger:
    """Otomatik hata ayiklama ve duzeltme motoru.

    Attributes:
        max_suggestions: Maksimum oneri sayisi.
        auto_fix_confidence_threshold: Otomatik duzeltme icin minimum guven esigi.
    """

    def __init__(self, max_suggestions: int = 5,
                 auto_fix_confidence_threshold: FixConfidence = FixConfidence.HIGH) -> None:
        """Yeni AutoDebugger olusturur.

        Args:
            max_suggestions: Maksimum duzeltme onerisi sayisi.
            auto_fix_confidence_threshold: Otomatik duzeltme icin minimum guven.
        """
        self.max_suggestions = max_suggestions
        self.auto_fix_confidence_threshold = auto_fix_confidence_threshold

    def parse_error(self, error_text: str) -> dict[str, str]:
        """Hata mesajini ayristirarak tip, mesaj, dosya ve satir numarasi cikarir.

        Args:
            error_text: Hata mesaji veya traceback metni.

        Returns:
            error_type, message, file, line anahtarli sozluk.
        """
        result = {"error_type": "", "message": "", "file": "", "line": ""}
        m = re.search(r"(\w*(?:Error|Exception|Warning))\s*:\s*(.+)", error_text)
        if m:
            result["error_type"], result["message"] = m.group(1), m.group(2).strip()
        m = re.search(r'File\s+"([^"]+)",\s+line\s+(\d+)', error_text)
        if m:
            result["file"], result["line"] = m.group(1), m.group(2)
        return result

    def analyze_traceback(self, traceback_text: str) -> list[dict[str, str]]:
        """Tam stack trace'i yapisal frame listesine donusturur.

        Args:
            traceback_text: Tam traceback metni.

        Returns:
            Her frame icin file, line, function, code iceren sozluk listesi.
        """
        frames: list[dict[str, str]] = []
        pattern = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+(\S+)')
        lines = traceback_text.splitlines()
        for i, line in enumerate(lines):
            m = pattern.search(line)
            if m:
                code = lines[i + 1].strip() if i + 1 < len(lines) and not lines[i + 1].strip().startswith("File ") else ""
                frames.append({"file": m.group(1), "line": m.group(2), "function": m.group(3), "code": code})
        return frames

    def find_root_cause(self, error_text: str, source: str = "") -> str:
        """Hatayi analiz ederek kok neden aciklamasi uretir.

        Args:
            error_text: Hata mesaji veya traceback.
            source: Kaynak kod (varsa daha detayli analiz icin).

        Returns:
            Kok neden aciklama metni.
        """
        p = self.parse_error(error_text)
        cat = self._classify_error(p["error_type"])
        msg = p["message"]

        if cat == "name":
            nm = re.search(r"name '(\w+)' is not defined", msg)
            if nm:
                cause = f"'{nm.group(1)}' tanimsiz."
                if source:
                    close = difflib.get_close_matches(nm.group(1), self._get_names(source), n=3, cutoff=0.6)
                    if close:
                        cause += f" Benzerler: {close}"
                return cause
        elif cat == "import":
            mm = re.search(r"No module named '([^']+)'", msg)
            if mm:
                return f"'{mm.group(1)}' modulu bulunamadi. pip install veya ad kontrolu gerekli."
        elif cat == "type":
            if "argument" in msg:
                return f"Arguman uyumsuzlugu: {msg}"
            if "unsupported operand" in msg:
                return f"Desteklenmeyen islem: {msg}. Tip donusumu gerekebilir."
        elif cat == "attribute":
            am = re.search(r"'(\w+)' object has no attribute '(\w+)'", msg)
            if am:
                return f"'{am.group(1)}' nesnesinde '{am.group(2)}' yok."
        elif cat == "key":
            return f"Sozlukte anahtar bulunamadi: {msg}. dict.get() kullanin."
        elif cat == "index":
            return f"Indeks siniri asildi: {msg}. Boyut kontrol edin."
        elif cat == "syntax":
            return f"Sozdizimi hatasi: {msg}"
        return f"{p['error_type']}: {msg}" if p["error_type"] else msg

    def suggest_fixes(self, error_text: str, source: str = "") -> list[FixSuggestion]:
        """Hata tipine gore duzeltme onerisi listesi uretir.

        Args:
            error_text: Hata mesaji veya traceback.
            source: Kaynak kod metni.

        Returns:
            Oncelikli FixSuggestion listesi.
        """
        p = self.parse_error(error_text)
        et, msg, ln = p["error_type"], p["message"], int(p["line"] or 0)
        suggestions: list[FixSuggestion] = []

        if et in ("NameError", "UnboundLocalError"):
            suggestions.extend(self._suggest_name_fix(msg, source, ln))
        elif et == "TypeError":
            suggestions.extend(self._suggest_type_fix(msg, ln))
        elif et in ("ImportError", "ModuleNotFoundError"):
            suggestions.extend(self._suggest_import_fix(msg, ln))
        elif et == "KeyError":
            suggestions.append(FixSuggestion(
                description="dict.get() kullanarak varsayilan deger belirtin",
                confidence=FixConfidence.HIGH, line=ln, auto_fixable=False))
        elif et == "IndexError":
            suggestions.append(FixSuggestion(
                description="Indeks erisiminden once len() ile boyut kontrol edin",
                confidence=FixConfidence.MEDIUM, line=ln, auto_fixable=False))
        elif et == "ZeroDivisionError":
            el = self._extract_error_line(source, ln)
            dm = re.search(r"/\s*(\w+)", el) if el else None
            if dm:
                suggestions.append(FixSuggestion(
                    description=f"Sifira bolme kontrolu: {dm.group(1)} != 0",
                    confidence=FixConfidence.HIGH, code_before=el.strip(),
                    code_after=f"if {dm.group(1)} != 0:\n    {el.strip()}",
                    line=ln, auto_fixable=True))
        elif et == "AttributeError":
            suggestions.append(FixSuggestion(
                description="Dogru attribute adini kontrol edin",
                confidence=FixConfidence.MEDIUM, line=ln, auto_fixable=False))
        elif et == "ValueError":
            suggestions.append(FixSuggestion(
                description="Girdi degerini islemden once dogrulayin",
                confidence=FixConfidence.LOW, line=ln, auto_fixable=False))

        if not suggestions and et in COMMON_FIXES:
            suggestions.append(FixSuggestion(
                description=COMMON_FIXES[et], confidence=FixConfidence.LOW, line=ln))

        logger.info("%d oneri uretildi (tip=%s)", len(suggestions), et)
        return suggestions[:self.max_suggestions]

    def auto_fix(self, error_text: str, source: str) -> Optional[str]:
        """Basit hatalari kaynak kodda otomatik duzeltmeyi dener.

        Args:
            error_text: Hata mesaji veya traceback.
            source: Duzeltilecek kaynak kod.

        Returns:
            Duzeltilmis kaynak kod veya None.
        """
        order = [FixConfidence.CERTAIN, FixConfidence.HIGH, FixConfidence.MEDIUM, FixConfidence.LOW]
        allowed = set(order[:order.index(self.auto_fix_confidence_threshold) + 1])

        for fix in self.suggest_fixes(error_text, source):
            if not fix.auto_fixable or fix.confidence not in allowed:
                continue
            if not fix.code_before or not fix.code_after:
                continue
            if fix.code_before in source:
                fixed = source.replace(fix.code_before, fix.code_after, 1)
                try:
                    ast.parse(fixed)
                except SyntaxError:
                    continue
                logger.info("Otomatik duzeltme uygulandi: %s", fix.description)
                return fixed
        return None

    def check_regression(self, original_source: str, fixed_source: str) -> dict[str, object]:
        """Duzeltmenin mevcut islevi bozmadigini dogrular.

        Args:
            original_source: Orijinal kaynak kod.
            fixed_source: Duzeltilmis kaynak kod.

        Returns:
            passed, diff, original_valid, fixed_valid, functions_changed iceren sozluk.
        """
        result: dict[str, object] = {
            "passed": True, "diff": "", "original_valid": True,
            "fixed_valid": True, "functions_changed": [],
        }
        try:
            ot = ast.parse(original_source)
        except SyntaxError:
            result["original_valid"] = False
            ot = None
        try:
            ft = ast.parse(fixed_source)
        except SyntaxError:
            result["fixed_valid"] = False
            result["passed"] = False
            ft = None

        diff = list(difflib.unified_diff(
            original_source.splitlines(keepends=True),
            fixed_source.splitlines(keepends=True), fromfile="original", tofile="fixed"))
        result["diff"] = "".join(diff)

        if ot and ft:
            ofn = {n.name for n in ast.walk(ot) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            ffn = {n.name for n in ast.walk(ft) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            changed = list((ofn - ffn) | (ffn - ofn))
            ofc = self._func_sources(original_source, ot)
            ffc = self._func_sources(fixed_source, ft)
            for fn in ofn & ffn:
                if ofc.get(fn) != ffc.get(fn):
                    changed.append(fn)
            result["functions_changed"] = changed
            if ofn - ffn:
                result["passed"] = False
        return result

    # --- Dahili yardimcilar ---

    def _classify_error(self, error_type: str) -> str:
        """Hata tipini kategoriye siniflandirir."""
        return _ERROR_CATEGORIES.get(error_type, "runtime")

    def _extract_error_line(self, source: str, line_number: int) -> str:
        """Kaynak koddan belirtilen satiri cikarir."""
        if not source or line_number <= 0:
            return ""
        lines = source.splitlines()
        return lines[line_number - 1] if line_number <= len(lines) else ""

    def _get_names(self, source: str) -> list[str]:
        """Kaynak kodda tanimli tum isimleri cikarir."""
        names: list[str] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return names
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.append(node.name)
            elif isinstance(node, ast.ClassDef):
                names.append(node.name)
            elif isinstance(node, ast.Name) and isinstance(getattr(node, "ctx", None), ast.Store):
                names.append(node.id)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    names.append(a.asname or a.name.split(".")[-1])
            elif isinstance(node, ast.ImportFrom):
                for a in (node.names or []):
                    names.append(a.asname or a.name)
        return list(set(names))

    def _suggest_name_fix(self, message: str, source: str, ln: int) -> list[FixSuggestion]:
        """NameError icin duzeltme: yazim hatasi tespiti ve eksik import."""
        suggestions: list[FixSuggestion] = []
        nm = re.search(r"name '(\w+)' is not defined", message)
        if not nm:
            return suggestions
        undefined = nm.group(1)
        if source:
            el = self._extract_error_line(source, ln)
            for match in difflib.get_close_matches(undefined, self._get_names(source), n=3, cutoff=0.6):
                only = len(difflib.get_close_matches(undefined, self._get_names(source), n=3, cutoff=0.6)) == 1
                suggestions.append(FixSuggestion(
                    description=f"'{undefined}' yerine '{match}' olabilir",
                    confidence=FixConfidence.HIGH if only else FixConfidence.MEDIUM,
                    code_before=el.strip() if el else undefined,
                    code_after=(el.replace(undefined, match).strip() if el else match),
                    line=ln, auto_fixable=only))
        if undefined in _COMMON_IMPORTS:
            suggestions.append(FixSuggestion(
                description=f"Eksik import: {_COMMON_IMPORTS[undefined]}",
                confidence=FixConfidence.HIGH, code_after=_COMMON_IMPORTS[undefined],
                line=1, auto_fixable=False))
        return suggestions

    def _suggest_type_fix(self, message: str, ln: int) -> list[FixSuggestion]:
        """TypeError icin duzeltme: arguman sayisi ve tip donusumu."""
        suggestions: list[FixSuggestion] = []
        am = re.search(r"(\w+)\(\) takes (\d+) positional arguments? but (\d+)", message)
        if am:
            suggestions.append(FixSuggestion(
                description=f"'{am.group(1)}()' {am.group(2)} arguman bekliyor, {am.group(3)} verildi",
                confidence=FixConfidence.MEDIUM, line=ln, auto_fixable=False))
        om = re.search(r"unsupported operand type\(s\) for (.+): '(\w+)' and '(\w+)'", message)
        if om:
            suggestions.append(FixSuggestion(
                description=f"'{om.group(2)}' ve '{om.group(3)}' arasi tip donusumu gerekli",
                confidence=FixConfidence.MEDIUM, line=ln, auto_fixable=False))
        if "not callable" in message:
            suggestions.append(FixSuggestion(
                description="Nesne cagrilabilir degil, parantezleri kontrol edin",
                confidence=FixConfidence.MEDIUM, line=ln, auto_fixable=False))
        return suggestions

    def _suggest_import_fix(self, message: str, ln: int) -> list[FixSuggestion]:
        """ImportError icin duzeltme: pip install onerisi ve ad duzeltmesi."""
        suggestions: list[FixSuggestion] = []
        mm = re.search(r"No module named '([^']+)'", message)
        if mm:
            mod = mm.group(1).split(".")[0]
            pip = _PIP_NAME_MAP.get(mod, mod)
            suggestions.append(FixSuggestion(
                description=f"Modulu yukleyin: pip install {pip}",
                confidence=FixConfidence.MEDIUM, code_after=f"# pip install {pip}",
                line=ln, auto_fixable=False))
            common = ["os", "sys", "re", "json", "logging", "typing", "datetime",
                       "pathlib", "asyncio", "pydantic", "fastapi", "redis", "celery"]
            for c in difflib.get_close_matches(mod, common, n=2, cutoff=0.6):
                suggestions.append(FixSuggestion(
                    description=f"'{mod}' yerine '{c}' mi demek istediniz?",
                    confidence=FixConfidence.HIGH, code_before=mod, code_after=c,
                    line=ln, auto_fixable=False))
        nm = re.search(r"cannot import name '(\w+)' from '([^']+)'", message)
        if nm:
            suggestions.append(FixSuggestion(
                description=f"'{nm.group(2)}' modulunde '{nm.group(1)}' bulunamadi",
                confidence=FixConfidence.LOW, line=ln, auto_fixable=False))
        return suggestions

    def _func_sources(self, source: str, tree: ast.Module) -> dict[str, str]:
        """Her fonksiyonun kaynak kodunu cikarir."""
        lines = source.splitlines()
        return {
            n.name: "\n".join(lines[n.lineno - 1:(n.end_lineno or n.lineno)])
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
