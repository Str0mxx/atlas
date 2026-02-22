"""A2UI JSONL format ayrıstirma modulu.

A2UI komutlarini ve bilesenlerini ayristirir,
bilesen agaci olusturur ve HTML donusumu yapar.
"""

import json
import logging
import time
from typing import Optional

from app.models.canvas_models import (
    A2UIComponent,
    CanvasCommand,
    ComponentType,
)

logger = logging.getLogger(__name__)


class A2UIParser:
    """A2UI JSONL format ayrıstiricisi.

    JSONL satirlarini ayristirir, bilesenler dogrular
    ve agac yapisi olusturur.
    """

    def __init__(self, max_depth: int = 10) -> None:
        """Parser baslatir.

        Args:
            max_depth: Maksimum bilesen derinligi
        """
        self.max_depth = max_depth
        self._history: list[dict] = []
        self._parse_count: int = 0
        self._error_count: int = 0

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def parse_jsonl(self, content: str) -> list[dict]:
        """A2UI JSONL icerigini ayristirir.

        Args:
            content: JSONL format metin

        Returns:
            Ayrıstirilmis komut listesi
        """
        results = []
        lines = content.strip().split(chr(10))
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parsed = self.parse_command(line)
            if parsed:
                results.append(parsed)
        self._record_history("parse_jsonl", line_count=len(lines), result_count=len(results))
        return results

    def parse_command(self, line: str) -> Optional[dict]:
        """Tek bir A2UI komut satirini ayristirir.

        Args:
            line: JSONL satiri

        Returns:
            Ayrıstirilmis komut veya None
        """
        try:
            data = json.loads(line)
            self._parse_count += 1
            return data
        except json.JSONDecodeError as e:
            self._error_count += 1
            logger.warning(f"JSON ayristirma hatasi: {e}")
            return None

    def validate_component(self, comp: A2UIComponent, depth: int = 0) -> bool:
        """Bilesen yapisini dogrular.

        Args:
            comp: Dogrulanacak bilesen
            depth: Mevcut derinlik

        Returns:
            Gecerli ise True
        """
        if depth > self.max_depth:
            logger.warning(f"Maksimum bilesen derinligi asildi: {depth}")
            return False
        # Tip kontrolu
        valid_types = [t.value for t in ComponentType]
        if comp.type.value not in valid_types:
            return False
        # Alt bilesenler icin tekrarla
        for child in comp.children:
            if not self.validate_component(child, depth + 1):
                return False
        return True

    def build_tree(self, components: list[dict]) -> list[A2UIComponent]:
        """Bilesen sozluklerinden agac yapisi olusturur.

        Args:
            components: Bilesen sozluk listesi

        Returns:
            A2UIComponent agac listesi
        """
        result = []
        for comp_data in components:
            comp = self._dict_to_component(comp_data)
            if comp and self.validate_component(comp):
                result.append(comp)
        self._record_history("build_tree", input_count=len(components), output_count=len(result))
        return result

    def _dict_to_component(self, data: dict) -> Optional[A2UIComponent]:
        """Sozlugu A2UIComponent nesnesine donusturur."""
        try:
            children = []
            for child_data in data.get("children", []):
                child = self._dict_to_component(child_data)
                if child:
                    children.append(child)
            return A2UIComponent(
                type=data.get("type", "text"),
                id=data.get("id", ""),
                props=data.get("props", {}),
                children=children,
                text=data.get("text", ""),
            )
        except Exception as e:
            logger.warning(f"Bilesen donusturme hatasi: {e}")
            return None

    def to_html(self, component: A2UIComponent) -> str:
        """A2UI bilesenini HTML metnine donusturur.

        Args:
            component: Donusturulecek bilesen

        Returns:
            HTML ciktisi
        """
        from app.core.canvas.component_renderer import ComponentRenderer
        renderer = ComponentRenderer()
        return renderer.render(component)

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        return {
            "total_parsed": self._parse_count,
            "total_errors": self._error_count,
            "max_depth": self.max_depth,
            "history_count": len(self._history),
        }
