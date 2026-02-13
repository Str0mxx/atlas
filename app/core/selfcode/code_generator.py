"""ATLAS kod uretici modulu.

Sablon tabanli ve LLM tabanli kod uretimi saglar. Fonksiyon, sinif
ve modul seviyesinde kod uretimi, docstring ekleme, import yonetimi
ve stil uygulamasi destekler.
"""

import logging
import re
import textwrap
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.selfcode import (
    CodeGenerationRequest,
    CodeGenStrategy,
    CodeStyle,
    GeneratedCode,
)

logger = logging.getLogger(__name__)

# Yaygin parametre adi kaliplari icin tip ipucu eslesmesi
TYPE_HINT_MAP: dict[str, str] = {
    "name": "str",
    "path": "str",
    "url": "str",
    "key": "str",
    "title": "str",
    "description": "str",
    "message": "str",
    "text": "str",
    "count": "int",
    "size": "int",
    "limit": "int",
    "max_": "int",
    "min_": "int",
    "index": "int",
    "port": "int",
    "timeout": "float",
    "enabled": "bool",
    "active": "bool",
    "is_": "bool",
    "has_": "bool",
    "allow_": "bool",
    "items": "list",
    "values": "list",
    "list_": "list",
    "tags": "list",
    "config": "dict",
    "options": "dict",
    "data": "dict",
    "metadata": "dict",
    "params": "dict",
    "headers": "dict",
}

# Yaygin kaliplar icin sablon sozlugu
TEMPLATES: dict[str, str] = {
    "function": textwrap.dedent("""\
        def {name}({params}) -> {return_type}:
            \"""{docstring}\"""
            {body}
        """),
    "async_function": textwrap.dedent("""\
        async def {name}({params}) -> {return_type}:
            \"""{docstring}\"""
            {body}
        """),
    "class": textwrap.dedent("""\
        class {name}({bases}):
            \"""{docstring}\"""

            def __init__(self{init_params}) -> None:
                \"""Yeni {name} olusturur.\"""
                {init_body}
        {methods}
        """),
    "pydantic_model": textwrap.dedent("""\
        class {name}(BaseModel):
            \"""{docstring}

            Attributes:
        {attributes}
            \"""

        {fields}
        """),
    "test_class": textwrap.dedent("""\
        class Test{name}:
            \"""{name} icin testler.\"""

            def setup_method(self) -> None:
                \"""Test oncesi hazirlik.\"""
                {setup_body}

        {test_methods}
        """),
    "fastapi_endpoint": textwrap.dedent("""\
        @router.{method}("{path}")
        async def {name}({params}) -> {return_type}:
            \"""{docstring}\"""
            {body}
        """),
}


class CodeGenerator:
    """Sablon ve LLM tabanli kod uretici.

    Fonksiyon, sinif ve modul seviyesinde kod uretimi yapar.
    Stil uygulamasi, import yonetimi ve docstring olusturma destekler.

    Attributes:
        default_style: Varsayilan kod stili.
        indent_size: Girinti boyutu (bosluk sayisi).
        max_line_length: Maksimum satir uzunlugu.
    """

    def __init__(
        self,
        default_style: CodeStyle = CodeStyle.PEP8,
        indent_size: int = 4,
        max_line_length: int = 88,
    ) -> None:
        """Yeni CodeGenerator olusturur.

        Args:
            default_style: Varsayilan kod stili.
            indent_size: Girinti boyutu (bosluk sayisi).
            max_line_length: Maksimum satir uzunlugu (black varsayilani 88).
        """
        self.default_style = default_style
        self.indent_size = indent_size
        self.max_line_length = max_line_length
        self._indent = " " * indent_size
        logger.info(
            "CodeGenerator baslatildi (stil=%s, girinti=%d, maks_satir=%d)",
            default_style.value,
            indent_size,
            max_line_length,
        )

    def generate(self, request: CodeGenerationRequest) -> GeneratedCode:
        """Ana kod uretim metodu.

        Istek stratejisine gore sablon, LLM veya hibrit uretim yapar.

        Args:
            request: Kod uretim istegi.

        Returns:
            Uretilen kod sonucu.
        """
        logger.info(
            "Kod uretimi basliyor: strateji=%s, aciklama='%s'",
            request.strategy.value,
            request.description[:60],
        )

        strategy = request.strategy

        # Stratejiye gore uygun ureticiye yonlendir
        if strategy == CodeGenStrategy.TEMPLATE:
            result = self.generate_from_template(request)
        elif strategy == CodeGenStrategy.LLM:
            # LLM mevcut degil - yer tutucu sonuc dondur
            logger.warning("LLM stratejisi secildi ancak LLM mevcut degil")
            result = GeneratedCode(
                request_id=request.id,
                code="# LLM tabanli uretim henuz mevcut degil",
                language=request.language,
                confidence=0.0,
                metadata={"note": "LLM backend not available"},
            )
        elif strategy == CodeGenStrategy.HYBRID:
            # Hibrit: once sablon dene
            result = self.generate_from_template(request)
            if result.confidence < 0.5:
                logger.info("Sablon guveni dusuk, hibrit modda LLM atlanildi")
                result.metadata["hybrid_fallback"] = "template_only"
        else:
            result = self.generate_from_template(request)

        # Stil uygula ve importlari duzenle
        result.code = self.enforce_style(result.code)
        result.imports = self.manage_imports(result.imports)

        logger.info(
            "Kod uretimi tamamlandi: guven=%.2f, satir=%d",
            result.confidence,
            result.code.count("\n") + 1,
        )
        return result

    def generate_from_template(
        self, request: CodeGenerationRequest
    ) -> GeneratedCode:
        """Sablon tabanli kod uretimi.

        Istek baglamindaki sablona gore kod uretir.

        Args:
            request: Kod uretim istegi.

        Returns:
            Uretilen kod sonucu.
        """
        context = request.context
        template_name = context.get("template", "function")
        template = TEMPLATES.get(template_name, TEMPLATES["function"])

        # Baglam degerlerini sablona uygula
        placeholders: dict[str, str] = {
            "name": context.get("name", "my_function"),
            "params": context.get("params", ""),
            "return_type": context.get("return_type", "None"),
            "docstring": context.get("docstring", request.description),
            "body": context.get("body", "pass"),
            "bases": context.get("bases", ""),
            "init_params": context.get("init_params", ""),
            "init_body": context.get("init_body", "pass"),
            "methods": context.get("methods", ""),
            "fields": context.get("fields", ""),
            "attributes": context.get("attributes", ""),
            "setup_body": context.get("setup_body", "pass"),
            "test_methods": context.get("test_methods", ""),
            "method": context.get("method", "get"),
            "path": context.get("path", "/"),
        }

        code = template
        for key, value in placeholders.items():
            code = code.replace("{" + key + "}", value)

        imports = list(request.dependencies)
        confidence = 0.8 if template_name in TEMPLATES else 0.5

        logger.debug(
            "Sablon uretimi: sablon=%s, guven=%.2f", template_name, confidence
        )
        return GeneratedCode(
            request_id=request.id,
            code=code,
            language=request.language,
            imports=imports,
            docstring=placeholders["docstring"],
            confidence=confidence,
            metadata={"template": template_name},
        )

    def generate_function(
        self,
        name: str,
        params: list[dict[str, str]],
        return_type: str = "None",
        body: str = "pass",
        docstring: str = "",
        is_async: bool = False,
    ) -> str:
        """Fonksiyon kodu uretir.

        Imza, docstring ve govde ile tam fonksiyon uretir.

        Args:
            name: Fonksiyon adi.
            params: Parametre listesi (her biri {name, type, default}).
            return_type: Donus tipi.
            body: Fonksiyon govdesi.
            docstring: Fonksiyon dokumantasyonu.
            is_async: Asenkron fonksiyon mu.

        Returns:
            Uretilen fonksiyon kodu.
        """
        param_str = self._build_param_string(params)
        doc = docstring or f"{name} fonksiyonu."
        code = self._build_function_code(
            name=name,
            params=param_str,
            return_type=return_type,
            body=body,
            docstring=doc,
            is_async=is_async,
        )
        logger.debug("Fonksiyon uretildi: %s", name)
        return code

    def generate_class(
        self,
        name: str,
        bases: Optional[list[str]] = None,
        methods: Optional[list[dict[str, Any]]] = None,
        docstring: str = "",
        init_params: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Sinif kodu uretir.

        Metotlar, docstring ve __init__ ile tam sinif uretir.

        Args:
            name: Sinif adi.
            bases: Temel sinif listesi.
            methods: Metot tanimlari listesi.
            docstring: Sinif dokumantasyonu.
            init_params: __init__ parametreleri.

        Returns:
            Uretilen sinif kodu.
        """
        code = self._build_class_code(
            name=name,
            bases=bases or [],
            methods=methods or [],
            docstring=docstring or f"{name} sinifi.",
            init_params=init_params or [],
        )
        logger.debug("Sinif uretildi: %s", name)
        return code

    def generate_module(
        self,
        module_docstring: str,
        imports: Optional[list[str]] = None,
        classes: Optional[list[str]] = None,
        functions: Optional[list[str]] = None,
    ) -> str:
        """Tam modul kodu uretir.

        Importlar, siniflar ve fonksiyonlar ile eksiksiz modul uretir.

        Args:
            module_docstring: Modul dokumantasyonu.
            imports: Import ifadeleri listesi.
            classes: Sinif kodlari listesi.
            functions: Fonksiyon kodlari listesi.

        Returns:
            Uretilen modul kodu.
        """
        parts: list[str] = []

        # Modul docstring
        parts.append(f'"""{module_docstring}"""')
        parts.append("")

        # Importlar
        if imports:
            sorted_imports = self._format_imports(imports)
            parts.append(sorted_imports)
            parts.append("")

        # Logger
        parts.append("logger = logging.getLogger(__name__)")
        parts.append("")

        # Siniflar
        if classes:
            for cls_code in classes:
                parts.append("")
                parts.append(cls_code)

        # Fonksiyonlar
        if functions:
            for func_code in functions:
                parts.append("")
                parts.append(func_code)

        module_code = "\n".join(parts) + "\n"
        logger.debug(
            "Modul uretildi: %d sinif, %d fonksiyon",
            len(classes or []),
            len(functions or []),
        )
        return module_code

    def add_docstring(
        self,
        code: str,
        description: str = "",
        args: Optional[dict[str, str]] = None,
        returns: str = "",
        raises: Optional[dict[str, str]] = None,
    ) -> str:
        """Koda Google-style docstring ekler veya uretir.

        Args:
            code: Docstring eklenecek kod.
            description: Fonksiyon/sinif aciklamasi.
            args: Parametre aciklamalari {isim: aciklama}.
            returns: Donus degeri aciklamasi.
            raises: Firlatilan istisnalar {tip: aciklama}.

        Returns:
            Docstring eklenmis kod.
        """
        indent = self._indent
        lines: list[str] = []
        lines.append(f'{indent}"""')
        lines.append(f"{indent}{description or 'Fonksiyon aciklamasi.'}")
        lines.append("")

        if args:
            lines.append(f"{indent}Args:")
            for arg_name, arg_desc in args.items():
                lines.append(f"{indent}{indent}{arg_name}: {arg_desc}")
            lines.append("")

        if returns:
            lines.append(f"{indent}Returns:")
            lines.append(f"{indent}{indent}{returns}")
            lines.append("")

        if raises:
            lines.append(f"{indent}Raises:")
            for exc_type, exc_desc in raises.items():
                lines.append(f"{indent}{indent}{exc_type}: {exc_desc}")
            lines.append("")

        lines.append(f'{indent}"""')
        docstring_block = "\n".join(lines)

        # Ilk satirdan sonra docstring ekle (def/class satiri)
        code_lines = code.split("\n")
        if code_lines:
            result = code_lines[0] + "\n" + docstring_block
            if len(code_lines) > 1:
                # Mevcut docstring varsa atla
                rest_start = 1
                if len(code_lines) > 1 and '"""' in code_lines[1]:
                    for i in range(2, len(code_lines)):
                        if '"""' in code_lines[i]:
                            rest_start = i + 1
                            break
                result += "\n" + "\n".join(code_lines[rest_start:])
            return result

        return code

    def manage_imports(self, imports: list[str]) -> list[str]:
        """Importlari duzenler, siralar ve tekillestirir.

        Stdlib, ucuncu parti ve yerel importlari gruplar.

        Args:
            imports: Import ifadeleri listesi.

        Returns:
            Duzenlenmis ve tekillestirilmis import listesi.
        """
        if not imports:
            return []

        # Tekillestir
        unique: list[str] = list(dict.fromkeys(imports))

        stdlib: list[str] = []
        third_party: list[str] = []
        local: list[str] = []

        stdlib_modules = {
            "os", "sys", "re", "json", "logging", "typing", "datetime",
            "collections", "pathlib", "textwrap", "uuid", "enum", "abc",
            "asyncio", "functools", "itertools", "math", "hashlib",
            "dataclasses", "contextlib", "io", "time", "copy",
        }

        for imp in unique:
            # Import edilen modul adini cikart
            match = re.match(r"(?:from\s+(\S+)|import\s+(\S+))", imp)
            if match:
                module_name = (match.group(1) or match.group(2)).split(".")[0]
                if module_name in stdlib_modules:
                    stdlib.append(imp)
                elif module_name == "app":
                    local.append(imp)
                else:
                    third_party.append(imp)
            else:
                third_party.append(imp)

        result: list[str] = []
        result.extend(sorted(stdlib))
        result.extend(sorted(third_party))
        result.extend(sorted(local))

        logger.debug(
            "Importlar duzenlendi: %d stdlib, %d 3.parti, %d yerel",
            len(stdlib),
            len(third_party),
            len(local),
        )
        return result

    def enforce_style(self, code: str) -> str:
        """Koda stil kurallari uygular.

        PEP8 konvansiyonlarina uygunluk saglar: bosluklar, bos satirlar,
        sondaki bosluklar temizlenir.

        Args:
            code: Stil uygulanacak kod.

        Returns:
            Stil uygulanmis kod.
        """
        lines = code.split("\n")
        result: list[str] = []
        prev_blank = False
        consecutive_blanks = 0

        for line in lines:
            # Sondaki bosluklari temizle
            stripped = line.rstrip()

            # Ust uste 2'den fazla bos satiri onle
            if not stripped:
                consecutive_blanks += 1
                if consecutive_blanks > 2:
                    continue
                prev_blank = True
            else:
                consecutive_blanks = 0
                prev_blank = False

            # Tab karakterlerini bosluklara cevir
            stripped = stripped.replace("\t", self._indent)

            result.append(stripped)

        # Son bos satirlari temizle, tek satir sonu birak
        while result and not result[-1]:
            result.pop()

        code_out = "\n".join(result)
        if code_out and not code_out.endswith("\n"):
            code_out += "\n"

        return code_out

    # --- Dahili yardimci metotlar ---

    def _build_param_string(self, params: list[dict[str, str]]) -> str:
        """Parametre listesinden parametre dizgesi olusturur.

        Args:
            params: Parametre sozlukleri listesi.

        Returns:
            Virgul ile ayrilmis parametre dizgesi.
        """
        parts: list[str] = []
        for p in params:
            name = p.get("name", "arg")
            type_hint = p.get("type", self._generate_type_hints(name))
            default = p.get("default", "")
            if default:
                parts.append(f"{name}: {type_hint} = {default}")
            else:
                parts.append(f"{name}: {type_hint}")
        return ", ".join(parts)

    def _build_function_code(
        self,
        name: str,
        params: str,
        return_type: str,
        body: str,
        docstring: str,
        is_async: bool = False,
    ) -> str:
        """Dahili fonksiyon kodu olusturucu.

        Args:
            name: Fonksiyon adi.
            params: Parametre dizgesi.
            return_type: Donus tipi.
            body: Fonksiyon govdesi.
            docstring: Dokumantasyon.
            is_async: Asenkron mu.

        Returns:
            Olusturulan fonksiyon kodu.
        """
        indent = self._indent
        keyword = "async def" if is_async else "def"
        lines: list[str] = []
        lines.append(f"{keyword} {name}({params}) -> {return_type}:")
        lines.append(f'{indent}"""{docstring}"""')

        # Govde satirlarini girintile
        for body_line in body.split("\n"):
            lines.append(f"{indent}{body_line}" if body_line.strip() else "")

        return "\n".join(lines)

    def _build_class_code(
        self,
        name: str,
        bases: list[str],
        methods: list[dict[str, Any]],
        docstring: str,
        init_params: list[dict[str, str]],
    ) -> str:
        """Dahili sinif kodu olusturucu.

        Args:
            name: Sinif adi.
            bases: Temel siniflar.
            methods: Metot tanimlari.
            docstring: Sinif dokumantasyonu.
            init_params: __init__ parametreleri.

        Returns:
            Olusturulan sinif kodu.
        """
        indent = self._indent
        bases_str = ", ".join(bases) if bases else ""
        class_def = f"class {name}({bases_str}):" if bases_str else f"class {name}:"

        lines: list[str] = []
        lines.append(class_def)
        lines.append(f'{indent}"""{docstring}"""')
        lines.append("")

        # __init__ metodu
        if init_params:
            param_str = self._build_param_string(init_params)
            lines.append(f"{indent}def __init__(self, {param_str}) -> None:")
            lines.append(f'{indent}{indent}"""Yeni {name} olusturur."""')
            for p in init_params:
                pname = p.get("name", "arg")
                lines.append(f"{indent}{indent}self.{pname} = {pname}")
        else:
            lines.append(f"{indent}def __init__(self) -> None:")
            lines.append(f'{indent}{indent}"""Yeni {name} olusturur."""')
            lines.append(f"{indent}{indent}pass")

        # Ek metotlar
        for method in methods:
            lines.append("")
            method_name = method.get("name", "method")
            method_params = method.get("params", [])
            method_return = method.get("return_type", "None")
            method_body = method.get("body", "pass")
            method_doc = method.get("docstring", f"{method_name} metodu.")
            method_async = method.get("is_async", False)

            param_str = self._build_param_string(method_params)
            self_param = f"self, {param_str}" if param_str else "self"
            keyword = "async def" if method_async else "def"

            lines.append(
                f"{indent}{keyword} {method_name}({self_param}) -> {method_return}:"
            )
            lines.append(f'{indent}{indent}"""{method_doc}"""')
            for bl in method_body.split("\n"):
                lines.append(f"{indent}{indent}{bl}" if bl.strip() else "")

        return "\n".join(lines)

    def _format_imports(self, imports: list[str]) -> str:
        """Import ifadelerini siralar ve formatlar.

        Stdlib, ucuncu parti ve yerel importlari gruplar
        ve aralarinda bos satir birakir.

        Args:
            imports: Import ifadeleri listesi.

        Returns:
            Formatlanmis import blogu.
        """
        managed = self.manage_imports(imports)
        if not managed:
            return ""

        # Gruplari ayir
        groups: list[list[str]] = []
        current_group: list[str] = []
        prev_prefix: Optional[str] = None

        for imp in managed:
            match = re.match(r"(?:from\s+(\S+)|import\s+(\S+))", imp)
            module = ""
            if match:
                module = (match.group(1) or match.group(2)).split(".")[0]

            if prev_prefix is not None and module != prev_prefix:
                # Farkli grup - oncekini kaydet
                if current_group:
                    groups.append(current_group)
                    current_group = []

            current_group.append(imp)
            prev_prefix = module

        if current_group:
            groups.append(current_group)

        return "\n\n".join("\n".join(g) for g in groups)

    def _generate_type_hints(self, param_name: str) -> str:
        """Parametre adina gore tip ipucu onerir.

        TYPE_HINT_MAP'teki kaliplari kullanarak uygun tipi tahmin eder.

        Args:
            param_name: Parametre adi.

        Returns:
            Onerilen tip ipucu dizgesi.
        """
        lower_name = param_name.lower()

        # Tam eslesme kontrol et
        if lower_name in TYPE_HINT_MAP:
            return TYPE_HINT_MAP[lower_name]

        # Onek eslesmesi kontrol et
        for pattern, type_hint in TYPE_HINT_MAP.items():
            if pattern.endswith("_") and lower_name.startswith(pattern):
                return type_hint

        # Sonek eslesmesi kontrol et
        for pattern, type_hint in TYPE_HINT_MAP.items():
            if not pattern.endswith("_") and lower_name.endswith(pattern):
                return type_hint

        # Varsayilan tip
        return "Any"
