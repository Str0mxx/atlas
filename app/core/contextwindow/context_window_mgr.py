"""Context window yoneticisi.

Token takibi, limit yonetimi,
tasma isleme ve optimizasyon.
"""

import logging
import time
from typing import Any

from app.core.contextwindow.message_summarizer import (
    MessageSummarizer,
)
from app.core.contextwindow.priority_retainer import (
    PriorityRetainer,
)
from app.core.contextwindow.system_prompt_guarantee import (
    SystemPromptGuarantee,
)
from app.core.contextwindow.token_counter import (
    TokenCounter,
)
from app.models.contextwindow_models import (
    MessagePriority,
    OverflowStrategy,
    SummaryLevel,
    WindowSnapshot,
    WindowStatus,
)

logger = logging.getLogger(__name__)

# Varsayilan ayarlar
_DEFAULT_MAX_TOKENS = 128000
_WARNING_THRESHOLD = 0.75
_CRITICAL_THRESHOLD = 0.90
_MAX_SNAPSHOTS = 500


class ContextWindowMgr:
    """Context window yoneticisi.

    Token takibi, limit yonetimi,
    tasma isleme ve optimizasyon.

    Attributes:
        _max_tokens: Maks token limiti.
        _counter: Token sayici.
        _summarizer: Ozetleyici.
        _retainer: Oncelik koruyucu.
        _guarantee: Prompt garantisi.
    """

    def __init__(
        self,
        max_tokens: int = (
            _DEFAULT_MAX_TOKENS
        ),
        model: str = "default",
        summary_threshold: float = (
            _CRITICAL_THRESHOLD
        ),
        system_prompt_reserve: int = 2000,
        overflow_strategy: (
            OverflowStrategy
        ) = OverflowStrategy.SUMMARIZE,
    ) -> None:
        """ContextWindowMgr baslatir.

        Args:
            max_tokens: Maks token.
            model: Model adi.
            summary_threshold: Ozet esigi.
            system_prompt_reserve: Prompt
                rezervi.
            overflow_strategy: Tasma
                stratejisi.
        """
        self._max_tokens: int = max_tokens
        self._summary_threshold: float = (
            summary_threshold
        )
        self._overflow_strategy: (
            OverflowStrategy
        ) = overflow_strategy

        # Alt bilesenler
        self._counter = TokenCounter(
            model=model,
        )
        self._summarizer = MessageSummarizer()
        self._retainer = PriorityRetainer()
        self._guarantee = (
            SystemPromptGuarantee(
                reserve_tokens=(
                    system_prompt_reserve
                ),
            )
        )

        # Durum
        self._current_tokens: int = 0
        self._messages: list[
            dict[str, Any]
        ] = []
        self._snapshots: list[
            WindowSnapshot
        ] = []
        self._total_optimizations: int = 0
        self._total_overflows: int = 0

        logger.info(
            "ContextWindowMgr baslatildi: "
            "max=%d",
            max_tokens,
        )

    # ---- Token Takibi ----

    def add_message(
        self,
        role: str,
        content: str,
        priority: MessagePriority = (
            MessagePriority.MEDIUM
        ),
        metadata: (
            dict[str, Any] | None
        ) = None,
    ) -> bool:
        """Mesaj ekler.

        Args:
            role: Mesaj rolu.
            content: Icerik.
            priority: Oncelik.
            metadata: Ust veri.

        Returns:
            Eklendi ise True.
        """
        if not content:
            return False

        tokens = self._counter.count(content)
        tokens += self._counter.count(role) + 4

        msg: dict[str, Any] = {
            "role": role,
            "content": content,
            "tokens": tokens,
            "priority": priority.value,
            "timestamp": time.time(),
            "id": f"msg_{len(self._messages)}",
            "metadata": metadata or {},
        }

        # Tasma kontrolu
        new_total = (
            self._current_tokens + tokens
        )
        if new_total > self._max_tokens:
            self._total_overflows += 1
            ok = self._handle_overflow(tokens)
            if not ok:
                return False

        self._messages.append(msg)
        self._current_tokens += tokens

        return True

    def remove_message(
        self, index: int,
    ) -> bool:
        """Mesaj siler.

        Args:
            index: Mesaj indeksi.

        Returns:
            Silindi ise True.
        """
        if (
            index < 0
            or index >= len(self._messages)
        ):
            return False

        msg = self._messages[index]

        # Korunuyor mu?
        if msg.get("role") == "system":
            active = (
                self._guarantee
                .get_active_prompt()
            )
            if (
                active
                and active.is_protected
                and msg.get("content")
                == active.prompt_text
            ):
                return False

        tokens = msg.get("tokens", 0)
        self._messages.pop(index)
        self._current_tokens = max(
            0,
            self._current_tokens - tokens,
        )

        return True

    def get_messages(
        self,
    ) -> list[dict[str, Any]]:
        """Mesajlari dondurur.

        Returns:
            Mesaj listesi.
        """
        return list(self._messages)

    def get_message_count(self) -> int:
        """Mesaj sayisini dondurur.

        Returns:
            Mesaj sayisi.
        """
        return len(self._messages)

    def clear_messages(self) -> int:
        """Mesajlari temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._messages)
        self._messages = []
        self._current_tokens = 0
        return count

    # ---- Durum ----

    def get_status(self) -> WindowStatus:
        """Pencere durumunu dondurur.

        Returns:
            Durum.
        """
        ratio = self.get_usage_ratio()

        if ratio >= 1.0:
            return WindowStatus.OVERFLOW
        if ratio >= _CRITICAL_THRESHOLD:
            return WindowStatus.CRITICAL
        if ratio >= _WARNING_THRESHOLD:
            return WindowStatus.WARNING
        return WindowStatus.HEALTHY

    def get_usage_ratio(self) -> float:
        """Kullanim oranini dondurur.

        Returns:
            Oran (0.0-1.0+).
        """
        if self._max_tokens <= 0:
            return 1.0
        return (
            self._current_tokens
            / self._max_tokens
        )

    def get_available_tokens(self) -> int:
        """Kullanilabilir token.

        Returns:
            Kalan token.
        """
        return max(
            0,
            self._max_tokens
            - self._current_tokens,
        )

    def get_current_tokens(self) -> int:
        """Mevcut token kullanimi.

        Returns:
            Kullanilan token.
        """
        return self._current_tokens

    def take_snapshot(self) -> WindowSnapshot:
        """Anlik goruntu alir.

        Returns:
            Snapshot.
        """
        system_tokens = sum(
            m.get("tokens", 0)
            for m in self._messages
            if m.get("role") == "system"
        )

        reserve = (
            self._guarantee.get_reserve()
        )

        snap = WindowSnapshot(
            total_tokens=(
                self._current_tokens
            ),
            max_tokens=self._max_tokens,
            used_ratio=self.get_usage_ratio(),
            status=self.get_status(),
            message_count=len(self._messages),
            system_tokens=system_tokens,
            reserved_tokens=reserve,
            available_tokens=(
                self.get_available_tokens()
            ),
            timestamp=time.time(),
        )

        self._snapshots.append(snap)
        if (
            len(self._snapshots)
            > _MAX_SNAPSHOTS
        ):
            self._snapshots = (
                self._snapshots[
                    -_MAX_SNAPSHOTS:
                ]
            )

        return snap

    def get_snapshots(
        self, limit: int = 20,
    ) -> list[WindowSnapshot]:
        """Snapshot gecmisi.

        Args:
            limit: Maks sonuc.

        Returns:
            Snapshot listesi.
        """
        return list(
            reversed(
                self._snapshots[-limit:],
            ),
        )

    # ---- Limit Yonetimi ----

    def set_max_tokens(
        self, max_tokens: int,
    ) -> None:
        """Maks token ayarlar.

        Args:
            max_tokens: Yeni limit.
        """
        self._max_tokens = max(0, max_tokens)

    def get_max_tokens(self) -> int:
        """Maks token dondurur.

        Returns:
            Token limiti.
        """
        return self._max_tokens

    def set_overflow_strategy(
        self,
        strategy: OverflowStrategy,
    ) -> None:
        """Tasma stratejisi ayarlar.

        Args:
            strategy: Yeni strateji.
        """
        self._overflow_strategy = strategy

    def set_summary_threshold(
        self, threshold: float,
    ) -> None:
        """Ozet esigini ayarlar.

        Args:
            threshold: Yeni esik (0-1).
        """
        self._summary_threshold = max(
            0.0, min(1.0, threshold),
        )

    # ---- Tasma Isleme ----

    def _handle_overflow(
        self, needed: int,
    ) -> bool:
        """Tasmayi isler.

        Args:
            needed: Gereken token.

        Returns:
            Basarili ise True.
        """
        strategy = self._overflow_strategy

        if (
            strategy
            == OverflowStrategy.TRUNCATE
        ):
            return self._truncate(needed)
        if (
            strategy
            == OverflowStrategy.SUMMARIZE
        ):
            return self._summarize_old(needed)
        if (
            strategy
            == OverflowStrategy.DROP_OLDEST
        ):
            return self._drop_oldest(needed)
        if (
            strategy
            == OverflowStrategy.DROP_LOWEST
        ):
            return self._drop_lowest(needed)

        return False

    def _truncate(
        self, needed: int,
    ) -> bool:
        """En eski mesajlari keser.

        Args:
            needed: Gereken token.

        Returns:
            Basarili ise True.
        """
        freed = 0
        to_remove: list[int] = []

        for i, m in enumerate(self._messages):
            if m.get("role") == "system":
                continue
            to_remove.append(i)
            freed += m.get("tokens", 0)
            if freed >= needed:
                break

        for idx in reversed(to_remove):
            self._messages.pop(idx)

        self._current_tokens -= freed
        self._current_tokens = max(
            0, self._current_tokens,
        )
        self._total_optimizations += 1
        return freed >= needed

    def _drop_oldest(
        self, needed: int,
    ) -> bool:
        """En eski mesajlari kaldirir.

        Args:
            needed: Gereken token.

        Returns:
            Basarili ise True.
        """
        return self._truncate(needed)

    def _drop_lowest(
        self, needed: int,
    ) -> bool:
        """En dusuk onceligu kaldirir.

        Args:
            needed: Gereken token.

        Returns:
            Basarili ise True.
        """
        # Oncelik sirasina gore sirala
        indexed = list(
            enumerate(self._messages),
        )
        priority_order = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
            "disposable": 0,
        }

        # Sistem mesajlarini koru
        indexed.sort(
            key=lambda x: (
                1
                if x[1].get("role")
                == "system"
                else 0,
                priority_order.get(
                    x[1].get(
                        "priority", "medium",
                    ),
                    2,
                ),
            ),
        )

        freed = 0
        to_remove: list[int] = []

        for idx, msg in indexed:
            if msg.get("role") == "system":
                continue
            to_remove.append(idx)
            freed += msg.get("tokens", 0)
            if freed >= needed:
                break

        for idx in sorted(
            to_remove, reverse=True,
        ):
            self._messages.pop(idx)

        self._current_tokens -= freed
        self._current_tokens = max(
            0, self._current_tokens,
        )
        self._total_optimizations += 1
        return freed >= needed

    def _summarize_old(
        self, needed: int,
    ) -> bool:
        """Eski mesajlari ozetler.

        Args:
            needed: Gereken token.

        Returns:
            Basarili ise True.
        """
        # Sistem olmayan mesajlari bul
        non_system: list[
            tuple[int, dict[str, Any]]
        ] = []
        for i, m in enumerate(self._messages):
            if m.get("role") != "system":
                non_system.append((i, m))

        if not non_system:
            return False

        # Ilk yarisi ozetlenecek
        half = max(
            1, len(non_system) // 2,
        )
        to_summarize = non_system[:half]

        # Ozetle
        msgs_for_summary = [
            {
                "role": m.get("role", ""),
                "content": m.get(
                    "content", "",
                ),
            }
            for _, m in to_summarize
        ]

        result = self._summarizer.summarize(
            msgs_for_summary,
            SummaryLevel.BRIEF,
        )

        # Eski mesajlari sil
        freed = 0
        indices = [
            i for i, _ in to_summarize
        ]
        for idx in sorted(
            indices, reverse=True,
        ):
            freed += self._messages[idx].get(
                "tokens", 0,
            )
            self._messages.pop(idx)

        # Ozet mesaji ekle
        summary_tokens = (
            self._counter.count(
                result.summary_text,
            )
        )
        summary_msg: dict[str, Any] = {
            "role": "system",
            "content": (
                f"[Summary] "
                f"{result.summary_text}"
            ),
            "tokens": summary_tokens + 4,
            "priority": "high",
            "timestamp": time.time(),
            "id": f"summary_{result.summary_id}",
            "metadata": {
                "is_summary": True,
            },
        }

        # Sistem mesajlarindan sonra ekle
        insert_idx = 0
        for i, m in enumerate(self._messages):
            if m.get("role") != "system":
                insert_idx = i
                break
        else:
            insert_idx = len(self._messages)

        self._messages.insert(
            insert_idx, summary_msg,
        )

        net_freed = freed - (
            summary_tokens + 4
        )
        self._current_tokens -= net_freed
        self._current_tokens = max(
            0, self._current_tokens,
        )
        self._total_optimizations += 1

        return net_freed >= needed

    # ---- Optimizasyon ----

    def optimize(self) -> int:
        """Pencereyi optimize eder.

        Returns:
            Kazanilan token.
        """
        before = self._current_tokens

        status = self.get_status()
        if status == WindowStatus.HEALTHY:
            return 0

        # Dusuk oncelikli mesajlari kaldir
        to_remove: list[int] = []
        for i, m in enumerate(self._messages):
            if (
                m.get("priority")
                == "disposable"
                and m.get("role") != "system"
            ):
                to_remove.append(i)

        for idx in reversed(to_remove):
            self._current_tokens -= (
                self._messages[idx].get(
                    "tokens", 0,
                )
            )
            self._messages.pop(idx)

        self._current_tokens = max(
            0, self._current_tokens,
        )

        # Hala kritik ise ozetle
        if (
            self.get_usage_ratio()
            >= self._summary_threshold
        ):
            self._summarize_old(
                int(
                    self._current_tokens * 0.2,
                ),
            )

        saved = before - self._current_tokens
        if saved > 0:
            self._total_optimizations += 1

        return max(0, saved)

    def needs_optimization(self) -> bool:
        """Optimizasyon gerekli mi.

        Returns:
            Gerekli ise True.
        """
        return (
            self.get_usage_ratio()
            >= self._summary_threshold
        )

    # ---- Alt Bilesen Erisimi ----

    @property
    def counter(self) -> TokenCounter:
        """Token sayici."""
        return self._counter

    @property
    def summarizer(self) -> MessageSummarizer:
        """Ozetleyici."""
        return self._summarizer

    @property
    def retainer(self) -> PriorityRetainer:
        """Oncelik koruyucu."""
        return self._retainer

    @property
    def guarantee(
        self,
    ) -> SystemPromptGuarantee:
        """Prompt garantisi."""
        return self._guarantee

    # ---- Istatistikler ----

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "max_tokens": self._max_tokens,
            "current_tokens": (
                self._current_tokens
            ),
            "usage_ratio": (
                self.get_usage_ratio()
            ),
            "status": (
                self.get_status().value
            ),
            "message_count": len(
                self._messages,
            ),
            "overflow_strategy": (
                self._overflow_strategy.value
            ),
            "summary_threshold": (
                self._summary_threshold
            ),
            "total_optimizations": (
                self._total_optimizations
            ),
            "total_overflows": (
                self._total_overflows
            ),
            "snapshot_count": len(
                self._snapshots,
            ),
        }
