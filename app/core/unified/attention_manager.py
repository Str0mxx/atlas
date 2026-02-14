"""ATLAS Dikkat Yoneticisi modulu.

Odak tahsisi, oncelik dikkati, arka plan
isleme, kesinti yonetimi ve baglam gecisi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.unified import AttentionFocus, AttentionState

logger = logging.getLogger(__name__)


class AttentionManager:
    """Dikkat yoneticisi.

    Sistemin dikkatini tahsis eder,
    onceliklendirir ve gecisleri yonetir.

    Attributes:
        _focuses: Aktif odaklar.
        _total_capacity: Toplam kapasite.
        _background_tasks: Arka plan gorevleri.
        _interrupts: Kesinti gecmisi.
        _context_stack: Baglam yigini.
    """

    def __init__(self, total_capacity: float = 1.0) -> None:
        """Dikkat yoneticisini baslatir.

        Args:
            total_capacity: Toplam dikkat kapasitesi.
        """
        self._focuses: dict[str, AttentionFocus] = {}
        self._total_capacity = total_capacity
        self._background_tasks: dict[str, dict[str, Any]] = {}
        self._interrupts: list[dict[str, Any]] = []
        self._context_stack: list[dict[str, Any]] = []

        logger.info(
            "AttentionManager baslatildi (capacity=%.1f)",
            total_capacity,
        )

    def focus_on(
        self,
        target: str,
        priority: int = 5,
        capacity: float = 0.3,
        context: dict[str, Any] | None = None,
    ) -> AttentionFocus | None:
        """Odak olusturur.

        Args:
            target: Hedef.
            priority: Oncelik (1-10).
            capacity: Kapasite (0-1).
            context: Baglam.

        Returns:
            AttentionFocus veya None (kapasite yetersiz).
        """
        used = self.used_capacity
        available = self._total_capacity - used

        if capacity > available:
            return None

        focus = AttentionFocus(
            target=target,
            priority=max(1, min(10, priority)),
            allocated_capacity=max(0.0, min(1.0, capacity)),
            context=context or {},
        )
        self._focuses[focus.focus_id] = focus

        logger.info(
            "Odak olusturuldu: %s (priority=%d, cap=%.2f)",
            target, priority, capacity,
        )
        return focus

    def release_focus(self, focus_id: str) -> bool:
        """Odagi serbest birakir.

        Args:
            focus_id: Odak ID.

        Returns:
            Basarili ise True.
        """
        if focus_id in self._focuses:
            del self._focuses[focus_id]
            return True
        return False

    def reprioritize(
        self,
        focus_id: str,
        new_priority: int,
    ) -> bool:
        """Oncelik degistirir.

        Args:
            focus_id: Odak ID.
            new_priority: Yeni oncelik.

        Returns:
            Basarili ise True.
        """
        focus = self._focuses.get(focus_id)
        if not focus:
            return False

        focus.priority = max(1, min(10, new_priority))
        return True

    def get_highest_priority(self) -> AttentionFocus | None:
        """En yuksek oncelikli odagi getirir.

        Returns:
            AttentionFocus veya None.
        """
        if not self._focuses:
            return None

        return max(
            self._focuses.values(),
            key=lambda f: f.priority,
        )

    def add_background_task(
        self,
        task_id: str,
        description: str,
        capacity: float = 0.05,
    ) -> bool:
        """Arka plan gorevi ekler.

        Args:
            task_id: Gorev ID.
            description: Aciklama.
            capacity: Kullanilacak kapasite.

        Returns:
            Basarili ise True.
        """
        if capacity > (self._total_capacity - self.used_capacity):
            return False

        self._background_tasks[task_id] = {
            "description": description,
            "capacity": capacity,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        return True

    def remove_background_task(self, task_id: str) -> bool:
        """Arka plan gorevini kaldirir.

        Args:
            task_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        if task_id in self._background_tasks:
            del self._background_tasks[task_id]
            return True
        return False

    def handle_interrupt(
        self,
        source: str,
        priority: int,
        description: str = "",
    ) -> dict[str, Any]:
        """Kesintiyi isler.

        Args:
            source: Kesinti kaynagi.
            priority: Oncelik.
            description: Aciklama.

        Returns:
            Kesinti sonucu.
        """
        current_top = self.get_highest_priority()
        should_switch = (
            not current_top
            or priority > current_top.priority
        )

        interrupt = {
            "source": source,
            "priority": priority,
            "description": description,
            "accepted": should_switch,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._interrupts.append(interrupt)

        if should_switch and current_top:
            current_top.state = AttentionState.INTERRUPTED
            self._save_context(current_top)

        return interrupt

    def switch_context(
        self,
        from_focus_id: str,
        to_target: str,
        priority: int = 5,
    ) -> dict[str, Any]:
        """Baglam gecisi yapar.

        Args:
            from_focus_id: Kaynak odak.
            to_target: Hedef.
            priority: Yeni oncelik.

        Returns:
            Gecis sonucu.
        """
        old_focus = self._focuses.get(from_focus_id)
        if old_focus:
            self._save_context(old_focus)
            old_focus.state = AttentionState.SWITCHING
            capacity = old_focus.allocated_capacity
            self.release_focus(from_focus_id)
        else:
            capacity = 0.3

        new_focus = self.focus_on(to_target, priority, capacity)

        return {
            "switched": new_focus is not None,
            "from": from_focus_id,
            "to": new_focus.focus_id if new_focus else None,
            "stack_depth": len(self._context_stack),
        }

    def restore_context(self) -> dict[str, Any] | None:
        """Onceki baglami geri yukler.

        Returns:
            Geri yuklenen baglam veya None.
        """
        if not self._context_stack:
            return None

        ctx = self._context_stack.pop()

        focus = self.focus_on(
            ctx.get("target", ""),
            ctx.get("priority", 5),
            ctx.get("capacity", 0.3),
            ctx.get("context", {}),
        )

        return {
            "restored": focus is not None,
            "target": ctx.get("target"),
            "focus_id": focus.focus_id if focus else None,
        }

    def _save_context(self, focus: AttentionFocus) -> None:
        """Baglami kaydeder.

        Args:
            focus: Kaydedilecek odak.
        """
        self._context_stack.append({
            "target": focus.target,
            "priority": focus.priority,
            "capacity": focus.allocated_capacity,
            "context": dict(focus.context),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })

    def get_focus(self, focus_id: str) -> AttentionFocus | None:
        """Odak getirir.

        Args:
            focus_id: Odak ID.

        Returns:
            AttentionFocus veya None.
        """
        return self._focuses.get(focus_id)

    def get_all_focuses(self) -> list[AttentionFocus]:
        """Tum odaklari getirir.

        Returns:
            Odak listesi (oncelik sirali).
        """
        return sorted(
            self._focuses.values(),
            key=lambda f: f.priority,
            reverse=True,
        )

    @property
    def used_capacity(self) -> float:
        """Kullanilan kapasite."""
        focus_cap = sum(
            f.allocated_capacity for f in self._focuses.values()
        )
        bg_cap = sum(
            t["capacity"] for t in self._background_tasks.values()
        )
        return round(focus_cap + bg_cap, 3)

    @property
    def available_capacity(self) -> float:
        """Kullanilabilir kapasite."""
        return round(self._total_capacity - self.used_capacity, 3)

    @property
    def focus_count(self) -> int:
        """Odak sayisi."""
        return len(self._focuses)

    @property
    def background_count(self) -> int:
        """Arka plan gorev sayisi."""
        return len(self._background_tasks)

    @property
    def interrupt_count(self) -> int:
        """Kesinti sayisi."""
        return len(self._interrupts)

    @property
    def context_depth(self) -> int:
        """Baglam yigin derinligi."""
        return len(self._context_stack)
