"""ATLAS TestGenerator modulu.

Kaynak kodu analiz ederek otomatik test uretimi. AST tabanli
fonksiyon/sinif analizi, birim test, kenar durum testi, mock
ve fixture uretimi islevleri.
"""

import ast
import logging
import re
from typing import Any

from app.models.selfcode import TestCase, TestSuite, TestType

logger = logging.getLogger(__name__)

# Tip anotasyonlarina gore varsayilan test degerleri
DEFAULT_TEST_VALUES: dict[str, list[Any]] = {
    "str": ["", "test", "hello world"],
    "int": [0, 1, -1, 42, 999],
    "float": [0.0, 1.0, -1.5, 3.14],
    "bool": [True, False],
    "list": [[], [1, 2, 3]],
    "dict": [{}, {"key": "value"}],
    "None": [None],
    "NoneType": [None],
}

# Dissal bagimlilik desenleri (mock uretimi icin)
_EXTERNAL_PATTERNS: list[str] = [
    r"requests\.",
    r"httpx\.",
    r"aiohttp\.",
    r"redis\.",
    r"asyncpg\.",
    r"sqlalchemy\.",
    r"boto3\.",
    r"paramiko\.",
    r"smtplib\.",
    r"subprocess\.",
]


class TestGenerator:
    """Otomatik test uretici.

    Kaynak kodu AST ile analiz ederek birim test, kenar durum
    testi, mock ve fixture kodu uretir.

    Attributes:
        coverage_target: Hedef kapsama yuzdesi (0-100).
        include_edge_cases: Kenar durum testleri dahil edilsin mi.
        max_tests_per_function: Fonksiyon basina maks test sayisi.
    """

    def __init__(
        self,
        coverage_target: float = 80.0,
        include_edge_cases: bool = True,
        max_tests_per_function: int = 5,
    ) -> None:
        self.coverage_target = coverage_target
        self.include_edge_cases = include_edge_cases
        self.max_tests_per_function = max_tests_per_function

    # ------------------------------------------------------------------
    # Ana metot
    # ------------------------------------------------------------------

    def generate_tests(self, source_code: str, module_name: str = "module") -> TestSuite:
        """Kaynak kodu analiz ederek test grubu uretir.

        1. AST ile kaynak kodu ayristir.
        2. Fonksiyon ve siniflari cikarir.
        3. Her fonksiyon icin birim test + kenar durum testi uretir.
        4. Dissal bagimliliklar icin mock kodu uretir.
        5. Ortak kaliplar icin fixture kodu uretir.
        6. TestSuite modelini doner.

        Args:
            source_code: Analiz edilecek Python kaynak kodu.
            module_name: Modul adi (import yolunda kullanilir).

        Returns:
            Uretilen testleri iceren TestSuite.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError as exc:
            logger.error("Kaynak kod ayristirma hatasi: %s", exc)
            return TestSuite(
                name=f"Test{module_name.title().replace('_', '')}",
                coverage_target=self.coverage_target,
            )

        functions: list[dict[str, Any]] = []
        classes: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Sinif metodlari ayri islenir
                if not isinstance(
                    getattr(node, "_parent", None), (ast.ClassDef,)
                ):
                    functions.append(self._analyze_function(node))
            elif isinstance(node, ast.ClassDef):
                classes.append(self._analyze_class(node))
                # Sinif metodlarini da isle
                for item in node.body:
                    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                        func_info = self._analyze_function(item)
                        func_info["class_name"] = node.name
                        functions.append(func_info)

        tests: list[TestCase] = []
        all_mocks: list[str] = []

        for func_info in functions:
            # Birim test uret
            unit_test = self.generate_unit_test(func_info, module_name)
            if unit_test:
                tests.append(unit_test)

            # Kenar durum testleri uret
            if self.include_edge_cases:
                edge_tests = self.generate_edge_cases(func_info, module_name)
                tests.extend(edge_tests)

            # Mock kodu uret
            mock_targets = self.generate_mock_code(func_info, source_code)
            all_mocks.extend(mock_targets)

            # Fonksiyon basina limit
            func_tests = [t for t in tests if t.target_function == func_info["name"]]
            if len(func_tests) > self.max_tests_per_function:
                overflow = func_tests[self.max_tests_per_function:]
                for t in overflow:
                    tests.remove(t)

        # Fixture kodu uret
        fixtures_code = self.generate_fixtures(functions, classes)

        # Import listesi olustur
        imports = [
            "import pytest",
            f"from {module_name} import *",
        ]
        if all_mocks:
            imports.append("from unittest.mock import MagicMock, patch, AsyncMock")

        suite_name = f"Test{module_name.title().replace('_', '')}"
        logger.info(
            "Test grubu uretildi: %s (%d test)", suite_name, len(tests)
        )

        return TestSuite(
            name=suite_name,
            tests=tests,
            imports=imports,
            fixtures_code=fixtures_code,
            coverage_target=self.coverage_target,
        )

    # ------------------------------------------------------------------
    # Birim test uretimi
    # ------------------------------------------------------------------

    def generate_unit_test(
        self, func_info: dict[str, Any], module_name: str = "module"
    ) -> TestCase | None:
        """Tek bir fonksiyon icin birim test uretir.

        Args:
            func_info: _analyze_function ciktisi.
            module_name: Modul adi.

        Returns:
            Uretilen TestCase veya None (uretim basarisizsa).
        """
        name = func_info.get("name", "")
        if name.startswith("_") and name != "__init__":
            return None

        params = func_info.get("params", [])
        return_type = func_info.get("return_type", "")
        is_async = func_info.get("is_async", False)
        class_name = func_info.get("class_name", "")

        test_values = self._infer_test_values(params)
        assertions = self.suggest_assertions(return_type)

        test_name = f"test_{name}"
        if class_name:
            test_name = f"test_{class_name.lower()}_{name}"

        code = self._build_test_code(
            test_name=test_name,
            func_name=name,
            class_name=class_name,
            params=params,
            test_values=test_values,
            assertions=assertions,
            is_async=is_async,
        )

        description = f"{name} fonksiyonunun temel calisma testi"
        if class_name:
            description = f"{class_name}.{name} metodunun temel calisma testi"

        return TestCase(
            name=test_name,
            test_type=TestType.UNIT,
            code=code,
            description=description,
            target_function=name,
        )

    # ------------------------------------------------------------------
    # Kenar durum testleri
    # ------------------------------------------------------------------

    def generate_edge_cases(
        self, func_info: dict[str, Any], module_name: str = "module"
    ) -> list[TestCase]:
        """Kenar durum testleri uretir (None, bos, sinir, tip hatasi).

        Args:
            func_info: _analyze_function ciktisi.
            module_name: Modul adi.

        Returns:
            Kenar durum TestCase listesi.
        """
        name = func_info.get("name", "")
        if name.startswith("_") and name != "__init__":
            return []

        params = func_info.get("params", [])
        is_async = func_info.get("is_async", False)
        class_name = func_info.get("class_name", "")
        cases: list[TestCase] = []

        # None testi — Optional parametreler icin
        for param_name, param_type in params:
            if "Optional" in param_type or "None" in param_type:
                test_name = f"test_{name}_none_{param_name}"
                args = ", ".join(
                    f"{p}=None" if p == param_name else f"{p}={self._default_value(t)}"
                    for p, t in params
                )
                call_expr = self._build_call_expr(name, class_name, args, is_async)
                code = self._wrap_test_func(test_name, call_expr, is_async)
                cases.append(TestCase(
                    name=test_name,
                    test_type=TestType.EDGE_CASE,
                    code=code,
                    description=f"{name}: {param_name}=None kenar durumu",
                    target_function=name,
                ))

        # Bos deger testi — str, list, dict
        for param_name, param_type in params:
            base = self._base_type(param_type)
            if base in ("str", "list", "dict"):
                empty = '""' if base == "str" else "[]" if base == "list" else "{}"
                test_name = f"test_{name}_empty_{param_name}"
                args = ", ".join(
                    f"{p}={empty}" if p == param_name else f"{p}={self._default_value(t)}"
                    for p, t in params
                )
                call_expr = self._build_call_expr(name, class_name, args, is_async)
                code = self._wrap_test_func(test_name, call_expr, is_async)
                cases.append(TestCase(
                    name=test_name,
                    test_type=TestType.EDGE_CASE,
                    code=code,
                    description=f"{name}: {param_name} bos deger kenar durumu",
                    target_function=name,
                ))

        # Sinir degeri testi — int, float
        for param_name, param_type in params:
            base = self._base_type(param_type)
            if base in ("int", "float"):
                test_name = f"test_{name}_boundary_{param_name}"
                boundary = "0" if base == "int" else "0.0"
                args = ", ".join(
                    f"{p}={boundary}" if p == param_name else f"{p}={self._default_value(t)}"
                    for p, t in params
                )
                call_expr = self._build_call_expr(name, class_name, args, is_async)
                code = self._wrap_test_func(test_name, call_expr, is_async)
                cases.append(TestCase(
                    name=test_name,
                    test_type=TestType.EDGE_CASE,
                    code=code,
                    description=f"{name}: {param_name} sinir degeri kenar durumu",
                    target_function=name,
                ))

        # Tip hatasi testi
        if params:
            test_name = f"test_{name}_type_error"
            invalid_args = ", ".join(
                f"{p}=object()" for p, _ in params
            )
            call_expr = self._build_call_expr(name, class_name, invalid_args, is_async)
            inner = (
                f"    with pytest.raises((TypeError, ValueError, AttributeError)):\n"
                f"        {call_expr}\n"
            )
            if is_async:
                code = f"@pytest.mark.asyncio\nasync def {test_name}():\n{inner}"
            else:
                code = f"def {test_name}():\n{inner}"
            cases.append(TestCase(
                name=test_name,
                test_type=TestType.EDGE_CASE,
                code=code,
                description=f"{name}: tip hatasi kenar durumu",
                target_function=name,
            ))

        return cases

    # ------------------------------------------------------------------
    # Mock uretimi
    # ------------------------------------------------------------------

    def generate_mock_code(
        self, func_info: dict[str, Any], source_code: str
    ) -> list[str]:
        """Dissal bagimliliklar icin mock/patch kodu uretir.

        Args:
            func_info: _analyze_function ciktisi.
            source_code: Tam kaynak kod (import taramasi icin).

        Returns:
            Mock hedef yollarinin listesi.
        """
        mock_targets: list[str] = []

        for pattern in _EXTERNAL_PATTERNS:
            if re.search(pattern, source_code):
                module_prefix = pattern.rstrip(r"\.").rstrip("\\")
                mock_targets.append(module_prefix)

        decorators = func_info.get("decorators", [])
        for dec in decorators:
            if "celery" in dec.lower() or "task" in dec.lower():
                mock_targets.append("celery.app.task")

        return list(set(mock_targets))

    # ------------------------------------------------------------------
    # Fixture uretimi
    # ------------------------------------------------------------------

    def generate_fixtures(
        self,
        functions: list[dict[str, Any]],
        classes: list[dict[str, Any]],
    ) -> str:
        """Pytest fixture kodu uretir.

        Args:
            functions: Fonksiyon bilgi listesi.
            classes: Sinif bilgi listesi.

        Returns:
            Fixture tanimlarini iceren kod metni.
        """
        lines: list[str] = []

        # Siniflar icin fixture
        for cls_info in classes:
            cls_name = cls_info.get("name", "")
            if not cls_name:
                continue
            fixture_name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls_name).lower()
            lines.append(f"@pytest.fixture")
            lines.append(f"def {fixture_name}():")
            lines.append(f'    """{cls_name} test ornegi."""')
            lines.append(f"    return {cls_name}()")
            lines.append("")

        # Ortak kaliplar icin fixture'lar
        param_types_seen: set[str] = set()
        for func_info in functions:
            for _, ptype in func_info.get("params", []):
                param_types_seen.add(self._base_type(ptype))

        if "str" in param_types_seen:
            lines.append("@pytest.fixture")
            lines.append("def sample_text():")
            lines.append('    """Ornek metin verisi."""')
            lines.append('    return "test input text"')
            lines.append("")

        if "dict" in param_types_seen:
            lines.append("@pytest.fixture")
            lines.append("def sample_dict():")
            lines.append('    """Ornek sozluk verisi."""')
            lines.append('    return {"key": "value", "count": 1}')
            lines.append("")

        if "list" in param_types_seen:
            lines.append("@pytest.fixture")
            lines.append("def sample_list():")
            lines.append('    """Ornek liste verisi."""')
            lines.append("    return [1, 2, 3]")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Assertion onerileri
    # ------------------------------------------------------------------

    def suggest_assertions(self, return_type: str) -> list[str]:
        """Donus tipine gore uygun assertion onerileri uretir.

        Args:
            return_type: Fonksiyonun donus tip anotasyonu.

        Returns:
            Assertion ifade sablonlari listesi.
        """
        base = self._base_type(return_type)

        mapping: dict[str, list[str]] = {
            "str": [
                "assert isinstance(result, str)",
                "assert len(result) >= 0",
            ],
            "int": [
                "assert isinstance(result, int)",
            ],
            "float": [
                "assert isinstance(result, (int, float))",
            ],
            "bool": [
                "assert isinstance(result, bool)",
            ],
            "list": [
                "assert isinstance(result, list)",
            ],
            "dict": [
                "assert isinstance(result, dict)",
            ],
            "None": [
                "assert result is None",
            ],
            "NoneType": [
                "assert result is None",
            ],
        }

        if "Optional" in return_type:
            return ["assert result is None or result is not None"]

        return mapping.get(base, ["assert result is not None"])

    # ------------------------------------------------------------------
    # Dahili analiz yardimcilari
    # ------------------------------------------------------------------

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
        """AST dugumunden fonksiyon bilgisi cikarir.

        Args:
            node: ast.FunctionDef veya ast.AsyncFunctionDef dugumu.

        Returns:
            Fonksiyon bilgisi sozlugu (name, params, return_type, decorators, is_async).
        """
        params: list[tuple[str, str]] = []
        for arg in node.args.args:
            if arg.arg == "self" or arg.arg == "cls":
                continue
            annotation = ""
            if arg.annotation:
                annotation = ast.unparse(arg.annotation)
            params.append((arg.arg, annotation))

        return_type = ""
        if node.returns:
            return_type = ast.unparse(node.returns)

        decorators: list[str] = []
        for dec in node.decorator_list:
            decorators.append(ast.unparse(dec))

        return {
            "name": node.name,
            "params": params,
            "return_type": return_type,
            "decorators": decorators,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "class_name": "",
        }

    def _analyze_class(self, node: ast.ClassDef) -> dict[str, Any]:
        """AST dugumunden sinif bilgisi cikarir.

        Args:
            node: ast.ClassDef dugumu.

        Returns:
            Sinif bilgisi sozlugu (name, methods, bases).
        """
        methods: list[str] = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                methods.append(item.name)

        bases: list[str] = []
        for base in node.bases:
            bases.append(ast.unparse(base))

        return {
            "name": node.name,
            "methods": methods,
            "bases": bases,
        }

    def _infer_test_values(
        self, params: list[tuple[str, str]]
    ) -> dict[str, Any]:
        """Parametre tiplerine ve adlarina gore test giris degerleri uretir.

        Args:
            params: (parametre_adi, tip_anotasyonu) listesi.

        Returns:
            Parametre adi -> test degeri sozlugu.
        """
        values: dict[str, Any] = {}

        for param_name, param_type in params:
            base = self._base_type(param_type)

            # Tip anotasyonundan deger sec
            if base in DEFAULT_TEST_VALUES:
                candidates = DEFAULT_TEST_VALUES[base]
                # Bos olmayan ilk degeri tercih et
                values[param_name] = candidates[1] if len(candidates) > 1 else candidates[0]
            # Isme gore cikarsama
            elif "id" in param_name.lower():
                values[param_name] = '"test_id_123"'
            elif "url" in param_name.lower():
                values[param_name] = '"https://example.com"'
            elif "path" in param_name.lower() or "file" in param_name.lower():
                values[param_name] = '"/tmp/test_file.txt"'
            elif "name" in param_name.lower():
                values[param_name] = '"test_name"'
            elif "count" in param_name.lower() or "num" in param_name.lower():
                values[param_name] = 1
            elif "flag" in param_name.lower() or "enable" in param_name.lower():
                values[param_name] = True
            else:
                values[param_name] = "None"

        return values

    def _build_test_code(
        self,
        test_name: str,
        func_name: str,
        class_name: str,
        params: list[tuple[str, str]],
        test_values: dict[str, Any],
        assertions: list[str],
        is_async: bool,
    ) -> str:
        """Test fonksiyonu kod metnini olusturur.

        Args:
            test_name: Test fonksiyonu adi.
            func_name: Hedef fonksiyon adi.
            class_name: Hedef sinif adi (yoksa bos).
            params: Parametre listesi.
            test_values: Test degerleri sozlugu.
            assertions: Assertion ifade listesi.
            is_async: Async fonksiyon mu.

        Returns:
            Test fonksiyonu kod metni.
        """
        lines: list[str] = []

        # Dekorator ve fonksiyon tanimlama
        if is_async:
            lines.append("@pytest.mark.asyncio")
            lines.append(f"async def {test_name}():")
        else:
            lines.append(f"def {test_name}():")

        # Docstring
        lines.append(f'    """{func_name} fonksiyonunu test eder."""')

        # Sinif ornegi olustur
        if class_name:
            instance_var = class_name[0].lower() + class_name[1:]
            lines.append(f"    {instance_var} = {class_name}()")

        # Fonksiyon cagrisi
        args_str = ", ".join(
            f"{p}={test_values.get(p, 'None')}" for p, _ in params
        )
        if class_name:
            instance_var = class_name[0].lower() + class_name[1:]
            call = f"{instance_var}.{func_name}({args_str})"
        else:
            call = f"{func_name}({args_str})"

        if is_async:
            lines.append(f"    result = await {call}")
        else:
            lines.append(f"    result = {call}")

        # Assertion'lar
        for assertion in assertions:
            lines.append(f"    {assertion}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Yardimci metodlar
    # ------------------------------------------------------------------

    def _base_type(self, type_str: str) -> str:
        """Tip anotasyonundan temel tipi cikarir (orn. 'Optional[str]' -> 'str').

        Args:
            type_str: Tip anotasyonu metni.

        Returns:
            Temel tip adi.
        """
        if not type_str:
            return ""
        # Optional[X] -> X
        cleaned = re.sub(r"Optional\[(.+)\]", r"\1", type_str)
        # list[X] -> list
        cleaned = re.sub(r"(\w+)\[.+\]", r"\1", cleaned)
        # X | None -> X
        cleaned = re.sub(r"\s*\|\s*None", "", cleaned)
        return cleaned.strip()

    def _default_value(self, type_str: str) -> str:
        """Tip icin varsayilan test degeri metni doner.

        Args:
            type_str: Tip anotasyonu.

        Returns:
            Python literal metni.
        """
        base = self._base_type(type_str)
        defaults: dict[str, str] = {
            "str": '"test"',
            "int": "1",
            "float": "1.0",
            "bool": "True",
            "list": "[1, 2, 3]",
            "dict": '{"key": "value"}',
        }
        return defaults.get(base, "None")

    def _build_call_expr(
        self,
        func_name: str,
        class_name: str,
        args_str: str,
        is_async: bool,
    ) -> str:
        """Fonksiyon cagri ifadesi olusturur.

        Args:
            func_name: Fonksiyon adi.
            class_name: Sinif adi (yoksa bos).
            args_str: Arguman metni.
            is_async: Async cagri mi.

        Returns:
            Cagri ifade metni.
        """
        if class_name:
            instance_var = class_name[0].lower() + class_name[1:]
            call = f"{instance_var}.{func_name}({args_str})"
        else:
            call = f"{func_name}({args_str})"

        if is_async:
            return f"await {call}"
        return call

    def _wrap_test_func(
        self, test_name: str, call_expr: str, is_async: bool
    ) -> str:
        """Cagri ifadesini test fonksiyonuna sarar.

        Args:
            test_name: Test fonksiyonu adi.
            call_expr: Fonksiyon cagri ifadesi.
            is_async: Async fonksiyon mu.

        Returns:
            Test fonksiyonu kod metni.
        """
        if is_async:
            return (
                f"@pytest.mark.asyncio\n"
                f"async def {test_name}():\n"
                f'    """{test_name} kenar durum testi."""\n'
                f"    result = {call_expr}\n"
            )
        return (
            f"def {test_name}():\n"
            f'    """{test_name} kenar durum testi."""\n'
            f"    result = {call_expr}\n"
        )
