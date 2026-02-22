"""Canvas bilesen render modulu.

A2UI bilesenlerini HTML ciktisina donusturur.
XSS onleme ve stil uygulama islevleri icerir.
"""

import html
import logging
import re
import time
from typing import Optional

from app.models.canvas_models import A2UIComponent, ComponentType

logger = logging.getLogger(__name__)


class ComponentRenderer:
    """A2UI bilesen render motoru.

    Bilesenlerden HTML uretir, stiller uygular ve
    guvenlik temizligi yapar.
    """

    def __init__(self) -> None:
        """Renderer baslatir."""
        self._history: list[dict] = []
        self._render_count: int = 0

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def render(self, component: A2UIComponent) -> str:
        """Bileseni HTML olarak render eder.

        Args:
            component: Render edilecek bilesen

        Returns:
            HTML ciktisi
        """
        self._render_count += 1
        renderer_map = {
            ComponentType.TEXT: self.render_text,
            ComponentType.BUTTON: self.render_button,
            ComponentType.INPUT: self.render_input,
            ComponentType.IMAGE: self.render_image,
            ComponentType.CARD: self.render_card,
            ComponentType.ROW: self.render_row,
            ComponentType.COLUMN: self.render_column,
            ComponentType.CONTAINER: self.render_container,
        }
        renderer = renderer_map.get(component.type, self.render_text)
        result = renderer(component)
        self._record_history("render", component_type=component.type.value)
        return result

    def render_text(self, component: A2UIComponent) -> str:
        """Text bilesen render eder."""
        safe_text = self.sanitize_html(component.text)
        css_class = component.props.get("class", "")
        tag = component.props.get("tag", "span")
        if tag not in ("span", "p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "label"):
            tag = "span"
        return f'<{tag} class="{css_class}" data-id="{component.id}">{safe_text}</{tag}>'

    def render_button(self, component: A2UIComponent) -> str:
        """Button bilesen render eder."""
        safe_text = self.sanitize_html(component.text)
        css_class = component.props.get("class", "btn")
        disabled = "disabled" if component.props.get("disabled") else ""
        return f'<button class="{css_class}" data-id="{component.id}" {disabled}>{safe_text}</button>'

    def render_input(self, component: A2UIComponent) -> str:
        """Input bilesen render eder."""
        input_type = component.props.get("type", "text")
        if input_type not in ("text", "number", "email", "password", "search", "tel", "url"):
            input_type = "text"
        placeholder = self.sanitize_html(component.props.get("placeholder", ""))
        value = self.sanitize_html(component.props.get("value", ""))
        return f'<input type="{input_type}" placeholder="{placeholder}" value="{value}" data-id="{component.id}" />'

    def render_image(self, component: A2UIComponent) -> str:
        """Image bilesen render eder."""
        src = self.sanitize_html(component.props.get("src", ""))
        alt = self.sanitize_html(component.props.get("alt", ""))
        width = component.props.get("width", "auto")
        height = component.props.get("height", "auto")
        return f'<img src="{src}" alt="{alt}" width="{width}" height="{height}" data-id="{component.id}" />'

    def render_card(self, component: A2UIComponent) -> str:
        """Card bilesen render eder."""
        children_html = self._render_children(component)
        css_class = component.props.get("class", "card")
        return f'<div class="{css_class}" data-id="{component.id}">{children_html}</div>'

    def render_row(self, component: A2UIComponent) -> str:
        """Row bilesen render eder."""
        children_html = self._render_children(component)
        return f'<div class="row" style="display:flex;flex-direction:row;" data-id="{component.id}">{children_html}</div>'

    def render_column(self, component: A2UIComponent) -> str:
        """Column bilesen render eder."""
        children_html = self._render_children(component)
        return f'<div class="column" style="display:flex;flex-direction:column;" data-id="{component.id}">{children_html}</div>'

    def render_container(self, component: A2UIComponent) -> str:
        """Container bilesen render eder."""
        children_html = self._render_children(component)
        css_class = component.props.get("class", "container")
        return f'<div class="{css_class}" data-id="{component.id}">{children_html}</div>'

    def _render_children(self, component: A2UIComponent) -> str:
        """Alt bilesenlerini render eder."""
        parts = []
        for child in component.children:
            parts.append(self.render(child))
        return "".join(parts)

    def apply_styles(self, html_content: str, styles: dict[str, str]) -> str:
        """HTML icerigine CSS stilleri uygular.

        Args:
            html_content: HTML icerigi
            styles: CSS stil sozlugu

        Returns:
            Stillendirilmis HTML
        """
        style_str = ";".join(f"{k}:{v}" for k, v in styles.items())
        wrapped = f'<div style="{style_str}">{html_content}</div>'
        self._record_history("apply_styles", style_count=len(styles))
        return wrapped

    def sanitize_html(self, text: str) -> str:
        """HTML icerigini XSS saldirilarina karsi temizler.

        Args:
            text: Temizlenecek metin

        Returns:
            Temizlenmis metin
        """
        if not text:
            return ""
        # HTML varliklarina cevir
        safe = html.escape(str(text))
        # Script etiketlerini kaldir
        safe = re.sub(r'<script[^>]*>.*?</script>', '', safe, flags=re.IGNORECASE | re.DOTALL)
        # Event handler ozelliklerini kaldir
        safe = re.sub(r'\bon\w+\s*=', '', safe, flags=re.IGNORECASE)
        return safe

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        return {
            "total_renders": self._render_count,
            "history_count": len(self._history),
        }
