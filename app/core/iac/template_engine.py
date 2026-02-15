"""ATLAS IaC Sablon Motoru modulu.

Sablon render, degisken ikamesi,
fonksiyon destegi, donguler/kosullar
ve ekleme/aktarma.
"""

import logging
import re
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class IaCTemplateEngine:
    """IaC sablon motoru.

    Sablonlari isle ve render eder.

    Attributes:
        _templates: Kayitli sablonlar.
        _functions: Sablon fonksiyonlari.
    """

    def __init__(self) -> None:
        """Motoru baslatir."""
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._functions: dict[
            str, Callable[..., Any]
        ] = {}
        self._partials: dict[str, str] = {}
        self._stats = {
            "renders": 0,
            "errors": 0,
        }

        # Yerlesik fonksiyonlar
        self._functions["upper"] = (
            lambda s: str(s).upper()
        )
        self._functions["lower"] = (
            lambda s: str(s).lower()
        )
        self._functions["join"] = (
            lambda lst, sep=",": sep.join(
                str(x) for x in lst
            )
        )
        self._functions["default"] = (
            lambda val, d: val if val else d
        )

        logger.info(
            "IaCTemplateEngine baslatildi",
        )

    def register_template(
        self,
        name: str,
        content: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Sablon kaydeder.

        Args:
            name: Sablon adi.
            content: Sablon icerigi.
            description: Aciklama.

        Returns:
            Kayit bilgisi.
        """
        self._templates[name] = {
            "content": content,
            "description": description,
            "registered_at": time.time(),
        }
        return {"name": name}

    def get_template(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Sablon getirir.

        Args:
            name: Sablon adi.

        Returns:
            Sablon bilgisi veya None.
        """
        return self._templates.get(name)

    def remove_template(
        self,
        name: str,
    ) -> bool:
        """Sablon kaldirir.

        Args:
            name: Sablon adi.

        Returns:
            Basarili mi.
        """
        if name in self._templates:
            del self._templates[name]
            return True
        return False

    def render(
        self,
        template: str,
        variables: dict[str, Any]
            | None = None,
    ) -> str:
        """Sablon render eder.

        Args:
            template: Sablon metni.
            variables: Degiskenler.

        Returns:
            Render edilmis metin.
        """
        self._stats["renders"] += 1
        vars_ = variables or {}
        result = template

        # Partial ekleme: {% include "name" %}
        include_pattern = re.compile(
            r'\{%\s*include\s+"(\w+)"\s*%\}',
        )
        for match in include_pattern.finditer(
            result,
        ):
            partial_name = match.group(1)
            partial = self._partials.get(
                partial_name, "",
            )
            result = result.replace(
                match.group(0), partial,
            )

        # Kosullar: {% if var %}...{% endif %}
        if_pattern = re.compile(
            r'\{%\s*if\s+(\w+)\s*%\}'
            r'(.*?)'
            r'\{%\s*endif\s*%\}',
            re.DOTALL,
        )
        for match in if_pattern.finditer(result):
            var_name = match.group(1)
            body = match.group(2)
            if vars_.get(var_name):
                result = result.replace(
                    match.group(0), body.strip(),
                )
            else:
                result = result.replace(
                    match.group(0), "",
                )

        # Dongu: {% for item in list %}...{% endfor %}
        for_pattern = re.compile(
            r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}'
            r'(.*?)'
            r'\{%\s*endfor\s*%\}',
            re.DOTALL,
        )
        for match in for_pattern.finditer(result):
            item_name = match.group(1)
            list_name = match.group(2)
            body_tmpl = match.group(3)
            items = vars_.get(list_name, [])
            rendered_items: list[str] = []
            for item in items:
                item_body = body_tmpl.strip()
                item_body = item_body.replace(
                    "{{ " + item_name + " }}",
                    str(item),
                )
                rendered_items.append(item_body)
            result = result.replace(
                match.group(0),
                "\n".join(rendered_items),
            )

        # Fonksiyon cagrilari: {{ func(arg) }}
        func_pattern = re.compile(
            r'\{\{\s*(\w+)\(([^)]*)\)\s*\}\}',
        )
        for match in func_pattern.finditer(result):
            fname = match.group(1)
            arg_str = match.group(2).strip()
            fn = self._functions.get(fname)
            if fn:
                # Argumani cozumle
                arg = vars_.get(
                    arg_str, arg_str,
                )
                try:
                    val = fn(arg)
                    result = result.replace(
                        match.group(0), str(val),
                    )
                except Exception:
                    self._stats["errors"] += 1

        # Degisken ikamesi: {{ var }}
        var_pattern = re.compile(
            r'\{\{\s*(\w+)\s*\}\}',
        )
        for match in var_pattern.finditer(result):
            var_name = match.group(1)
            if var_name in vars_:
                result = result.replace(
                    match.group(0),
                    str(vars_[var_name]),
                )

        return result

    def render_template(
        self,
        name: str,
        variables: dict[str, Any]
            | None = None,
    ) -> str | None:
        """Kayitli sablonu render eder.

        Args:
            name: Sablon adi.
            variables: Degiskenler.

        Returns:
            Render sonucu veya None.
        """
        tmpl = self._templates.get(name)
        if not tmpl:
            return None

        return self.render(
            tmpl["content"], variables,
        )

    def register_function(
        self,
        name: str,
        func: Callable[..., Any],
    ) -> None:
        """Sablon fonksiyonu kaydeder.

        Args:
            name: Fonksiyon adi.
            func: Fonksiyon.
        """
        self._functions[name] = func

    def register_partial(
        self,
        name: str,
        content: str,
    ) -> None:
        """Partial (parca) kaydeder.

        Args:
            name: Parca adi.
            content: Icerik.
        """
        self._partials[name] = content

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)

    @property
    def function_count(self) -> int:
        """Fonksiyon sayisi."""
        return len(self._functions)

    @property
    def partial_count(self) -> int:
        """Partial sayisi."""
        return len(self._partials)

    @property
    def render_count(self) -> int:
        """Render sayisi."""
        return self._stats["renders"]
