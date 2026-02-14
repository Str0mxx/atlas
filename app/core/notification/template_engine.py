"""ATLAS Bildirim Sablon Motoru modulu.

Mesaj sablonlari, degisken yerlestirme,
coklu dil, zengin bicimlendirme
ve onizleme uretimi.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class NotificationTemplateEngine:
    """Bildirim sablon motoru.

    Bildirimleri sablonlardan uretir
    ve bicimlendirir.

    Attributes:
        _templates: Sablonlar.
        _partials: Kismi sablonlar.
    """

    def __init__(self) -> None:
        """Sablon motorunu baslatir."""
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._partials: dict[str, str] = {}

        logger.info(
            "NotificationTemplateEngine baslatildi",
        )

    def register_template(
        self,
        name: str,
        subject: str,
        body: str,
        lang: str = "en",
        format_type: str = "text",
    ) -> dict[str, Any]:
        """Sablon kaydeder.

        Args:
            name: Sablon adi.
            subject: Konu sablonu.
            body: Govde sablonu.
            lang: Dil.
            format_type: Bicim (text, html, markdown).

        Returns:
            Sablon bilgisi.
        """
        key = f"{name}:{lang}"
        template = {
            "name": name,
            "subject": subject,
            "body": body,
            "lang": lang,
            "format": format_type,
        }
        self._templates[key] = template
        return template

    def render(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
        lang: str = "en",
    ) -> dict[str, str]:
        """Sablon render eder.

        Args:
            name: Sablon adi.
            variables: Degiskenler.
            lang: Dil.

        Returns:
            Render edilmis sablon.
        """
        key = f"{name}:{lang}"
        template = self._templates.get(key)

        # Dil yedekleme
        if not template:
            key = f"{name}:en"
            template = self._templates.get(key)
        if not template:
            return {
                "subject": name,
                "body": name,
            }

        vars_ = variables or {}

        subject = self._substitute(
            template["subject"], vars_,
        )
        body = self._substitute(
            template["body"], vars_,
        )

        return {
            "subject": subject,
            "body": body,
            "format": template["format"],
        }

    def preview(
        self,
        name: str,
        lang: str = "en",
    ) -> dict[str, str]:
        """Sablon onizleme uretir.

        Args:
            name: Sablon adi.
            lang: Dil.

        Returns:
            Onizleme.
        """
        key = f"{name}:{lang}"
        template = self._templates.get(key)
        if not template:
            return {"subject": "", "body": ""}

        # Placeholder'lari ornek degerlerle doldur
        sample_vars: dict[str, str] = {}
        placeholders = re.findall(
            r"\{(\w+)\}", template["body"],
        )
        placeholders += re.findall(
            r"\{(\w+)\}", template["subject"],
        )
        for ph in set(placeholders):
            sample_vars[ph] = f"[{ph}]"

        return self.render(name, sample_vars, lang)

    def register_partial(
        self,
        name: str,
        content: str,
    ) -> None:
        """Kismi sablon kaydeder.

        Args:
            name: Kismi adi.
            content: Icerik.
        """
        self._partials[name] = content

    def render_with_partials(
        self,
        body: str,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """Kismi sablonlarla render eder.

        Args:
            body: Govde.
            variables: Degiskenler.

        Returns:
            Render edilmis metin.
        """
        result = body
        for name, content in self._partials.items():
            result = result.replace(
                f"{{{{> {name}}}}}", content,
            )
        if variables:
            result = self._substitute(result, variables)
        return result

    def list_templates(
        self,
        lang: str | None = None,
    ) -> list[dict[str, Any]]:
        """Sablonlari listeler.

        Args:
            lang: Dil filtresi.

        Returns:
            Sablon listesi.
        """
        if lang:
            return [
                t for t in self._templates.values()
                if t["lang"] == lang
            ]
        return list(self._templates.values())

    def delete_template(
        self,
        name: str,
        lang: str = "en",
    ) -> bool:
        """Sablon siler.

        Args:
            name: Sablon adi.
            lang: Dil.

        Returns:
            Basarili ise True.
        """
        key = f"{name}:{lang}"
        if key in self._templates:
            del self._templates[key]
            return True
        return False

    def _substitute(
        self,
        text: str,
        variables: dict[str, Any],
    ) -> str:
        """Degisken yerlestirme.

        Args:
            text: Metin.
            variables: Degiskenler.

        Returns:
            Degiskenler yerlestirilmis metin.
        """
        result = text
        for key, val in variables.items():
            result = result.replace(
                f"{{{key}}}", str(val),
            )
        return result

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)

    @property
    def partial_count(self) -> int:
        """Kismi sablon sayisi."""
        return len(self._partials)
