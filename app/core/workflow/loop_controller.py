"""ATLAS Dongu Kontrolcusu modulu.

For-each, while, paralel donguler,
kirilma kosullari ve iterasyon
limitleri.
"""

import logging
from typing import Any, Callable

from app.models.workflow_engine import LoopType

logger = logging.getLogger(__name__)


class LoopController:
    """Dongu kontrolcusu.

    Is akisi dongularini yonetir
    ve calistirir.

    Attributes:
        _loops: Kayitli donguler.
        _history: Dongu gecmisi.
        _max_iterations: Maks iterasyon.
    """

    def __init__(
        self,
        max_iterations: int = 1000,
    ) -> None:
        """Dongu kontrolcusunu baslatir.

        Args:
            max_iterations: Maks iterasyon.
        """
        self._loops: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[dict[str, Any]] = []
        self._max_iterations = max_iterations
        self._loop_counter = 0

        logger.info("LoopController baslatildi")

    def create_for_each(
        self,
        name: str,
        items: list[Any],
        action: Callable[[Any], Any] | None = None,
    ) -> dict[str, Any]:
        """For-each dongusu olusturur.

        Args:
            name: Dongu adi.
            items: Oge listesi.
            action: Her oge icin aksiyon.

        Returns:
            Dongu bilgisi.
        """
        self._loop_counter += 1
        loop_id = f"loop_{self._loop_counter}"

        loop = {
            "id": loop_id,
            "name": name,
            "type": LoopType.FOR_EACH.value,
            "items": items,
            "action": action,
        }
        self._loops[loop_id] = loop
        return loop

    def create_while(
        self,
        name: str,
        condition: Callable[[], bool] | None = None,
        action: Callable[[], Any] | None = None,
    ) -> dict[str, Any]:
        """While dongusu olusturur.

        Args:
            name: Dongu adi.
            condition: Kosul fonksiyonu.
            action: Aksiyon fonksiyonu.

        Returns:
            Dongu bilgisi.
        """
        self._loop_counter += 1
        loop_id = f"loop_{self._loop_counter}"

        loop = {
            "id": loop_id,
            "name": name,
            "type": LoopType.WHILE.value,
            "condition": condition,
            "action": action,
        }
        self._loops[loop_id] = loop
        return loop

    def create_count(
        self,
        name: str,
        count: int,
        action: Callable[[int], Any] | None = None,
    ) -> dict[str, Any]:
        """Sayac dongusu olusturur.

        Args:
            name: Dongu adi.
            count: Tekrar sayisi.
            action: Her iterasyon icin aksiyon.

        Returns:
            Dongu bilgisi.
        """
        self._loop_counter += 1
        loop_id = f"loop_{self._loop_counter}"

        loop = {
            "id": loop_id,
            "name": name,
            "type": LoopType.COUNT.value,
            "count": min(count, self._max_iterations),
            "action": action,
        }
        self._loops[loop_id] = loop
        return loop

    def execute_for_each(
        self,
        loop_id: str,
        break_on: Callable[[Any], bool] | None = None,
    ) -> dict[str, Any]:
        """For-each calistirir.

        Args:
            loop_id: Dongu ID.
            break_on: Kirilma kosulu.

        Returns:
            Calistirma sonucu.
        """
        loop = self._loops.get(loop_id)
        if not loop:
            return {
                "success": False,
                "reason": "loop_not_found",
            }

        items = loop["items"]
        action = loop["action"]
        results: list[Any] = []
        broken = False

        for i, item in enumerate(items):
            if i >= self._max_iterations:
                break
            if action:
                result = action(item)
                results.append(result)
            if break_on and break_on(item):
                broken = True
                break

        record = {
            "loop_id": loop_id,
            "type": loop["type"],
            "iterations": len(results),
            "total_items": len(items),
            "broken": broken,
            "success": True,
        }
        self._history.append(record)
        return {**record, "results": results}

    def execute_while(
        self,
        loop_id: str,
    ) -> dict[str, Any]:
        """While calistirir.

        Args:
            loop_id: Dongu ID.

        Returns:
            Calistirma sonucu.
        """
        loop = self._loops.get(loop_id)
        if not loop:
            return {
                "success": False,
                "reason": "loop_not_found",
            }

        condition = loop["condition"]
        action = loop["action"]
        results: list[Any] = []
        iterations = 0

        while iterations < self._max_iterations:
            if condition and not condition():
                break
            if action:
                results.append(action())
            iterations += 1
            if not condition:
                break

        record = {
            "loop_id": loop_id,
            "type": loop["type"],
            "iterations": iterations,
            "success": True,
        }
        self._history.append(record)
        return {**record, "results": results}

    def execute_count(
        self,
        loop_id: str,
    ) -> dict[str, Any]:
        """Sayac dongusu calistirir.

        Args:
            loop_id: Dongu ID.

        Returns:
            Calistirma sonucu.
        """
        loop = self._loops.get(loop_id)
        if not loop:
            return {
                "success": False,
                "reason": "loop_not_found",
            }

        count = loop["count"]
        action = loop["action"]
        results: list[Any] = []

        for i in range(count):
            if action:
                results.append(action(i))

        record = {
            "loop_id": loop_id,
            "type": loop["type"],
            "iterations": count,
            "success": True,
        }
        self._history.append(record)
        return {**record, "results": results}

    def remove_loop(
        self,
        loop_id: str,
    ) -> bool:
        """Dongu kaldirir.

        Args:
            loop_id: Dongu ID.

        Returns:
            Basarili ise True.
        """
        if loop_id in self._loops:
            del self._loops[loop_id]
            return True
        return False

    @property
    def loop_count(self) -> int:
        """Dongu sayisi."""
        return len(self._loops)

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._history)

    @property
    def max_iterations(self) -> int:
        """Maks iterasyon."""
        return self._max_iterations
