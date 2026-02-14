"""ATLAS Baglam Olusturucu modulu.

Kullanici profili, konusma gecmisi,
gorev baglami, cevre ve zaman farkindaligiyla
zengin baglam olusturur.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import ContextSnapshot, ContextType

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Baglam olusturucu.

    Farkli kaynaklardan bilgi toplayarak
    zengin bir baglam goruntusu olusturur.

    Attributes:
        _user_profile: Kullanici profili.
        _conversation_history: Konusma gecmisi.
        _task_context: Gorev baglami.
        _environment: Cevre bilgisi.
        _contexts: Olusturulan baglamlar.
        _context_window: Baglam penceresi boyutu.
    """

    def __init__(self, context_window: int = 50) -> None:
        """Baglam olusturucuyu baslatir.

        Args:
            context_window: Baglam penceresi boyutu.
        """
        self._user_profile: dict[str, Any] = {}
        self._conversation_history: list[dict[str, Any]] = []
        self._task_context: dict[str, Any] = {}
        self._environment: dict[str, Any] = {}
        self._contexts: list[ContextSnapshot] = []
        self._context_window = max(1, context_window)

        logger.info(
            "ContextBuilder baslatildi (window=%d)",
            self._context_window,
        )

    def load_user_profile(
        self,
        profile: dict[str, Any],
    ) -> ContextSnapshot:
        """Kullanici profilini yukler.

        Args:
            profile: Profil verisi.

        Returns:
            ContextSnapshot nesnesi.
        """
        self._user_profile.update(profile)

        snapshot = ContextSnapshot(
            context_type=ContextType.USER,
            data=dict(self._user_profile),
            relevance=0.9,
        )
        self._contexts.append(snapshot)

        logger.info("Kullanici profili yuklendi: %d alan", len(profile))
        return snapshot

    def add_conversation_turn(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ContextSnapshot:
        """Konusma turu ekler.

        Args:
            role: Rol (user/assistant).
            content: Icerik.
            metadata: Ek bilgi.

        Returns:
            ContextSnapshot nesnesi.
        """
        turn = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._conversation_history.append(turn)

        # Pencere sinirla
        if len(self._conversation_history) > self._context_window:
            self._conversation_history = (
                self._conversation_history[-self._context_window:]
            )

        snapshot = ContextSnapshot(
            context_type=ContextType.CONVERSATION,
            data=turn,
            relevance=0.8,
        )
        self._contexts.append(snapshot)

        return snapshot

    def set_task_context(
        self,
        task_id: str,
        task_data: dict[str, Any],
    ) -> ContextSnapshot:
        """Gorev baglamini ayarlar.

        Args:
            task_id: Gorev ID.
            task_data: Gorev verisi.

        Returns:
            ContextSnapshot nesnesi.
        """
        self._task_context = {
            "task_id": task_id,
            **task_data,
        }

        snapshot = ContextSnapshot(
            context_type=ContextType.TASK,
            data=dict(self._task_context),
            relevance=0.85,
        )
        self._contexts.append(snapshot)

        logger.info("Gorev baglami ayarlandi: %s", task_id)
        return snapshot

    def clear_task_context(self) -> None:
        """Gorev baglamini temizler."""
        self._task_context = {}

    def update_environment(
        self,
        env_data: dict[str, Any],
    ) -> ContextSnapshot:
        """Cevre bilgisini gunceller.

        Args:
            env_data: Cevre verisi.

        Returns:
            ContextSnapshot nesnesi.
        """
        self._environment.update(env_data)

        snapshot = ContextSnapshot(
            context_type=ContextType.ENVIRONMENT,
            data=dict(self._environment),
            relevance=0.6,
        )
        self._contexts.append(snapshot)

        return snapshot

    def get_temporal_context(self) -> ContextSnapshot:
        """Zamansal baglami getirir.

        Returns:
            ContextSnapshot nesnesi.
        """
        now = datetime.now(timezone.utc)
        temporal = {
            "datetime": now.isoformat(),
            "hour": now.hour,
            "day_of_week": now.strftime("%A"),
            "is_weekend": now.weekday() >= 5,
            "is_business_hours": 9 <= now.hour <= 18,
            "timezone": "UTC",
        }

        snapshot = ContextSnapshot(
            context_type=ContextType.TEMPORAL,
            data=temporal,
            relevance=0.5,
        )
        self._contexts.append(snapshot)

        return snapshot

    def build_full_context(self) -> dict[str, Any]:
        """Tam baglami olusturur.

        Returns:
            Birlesik baglam sozlugu.
        """
        temporal = self.get_temporal_context()

        return {
            "user_profile": dict(self._user_profile),
            "conversation_history": list(
                self._conversation_history[-self._context_window:],
            ),
            "task_context": dict(self._task_context),
            "environment": dict(self._environment),
            "temporal": temporal.data,
            "total_turns": len(self._conversation_history),
        }

    def get_relevant_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[ContextSnapshot]:
        """Sorguyla ilgili baglamlari getirir.

        Args:
            query: Sorgu metni.
            top_k: Maks sonuc.

        Returns:
            Ilgili baglam listesi.
        """
        query_lower = query.lower()
        scored: list[tuple[float, ContextSnapshot]] = []

        for ctx in self._contexts:
            score = ctx.relevance
            data_str = str(ctx.data).lower()

            # Kelime eslesmesi bonusu
            words = query_lower.split()
            match_count = sum(1 for w in words if w in data_str)
            if words:
                score += 0.3 * (match_count / len(words))

            score = min(1.0, score)
            scored.append((score, ctx))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ctx for _, ctx in scored[:top_k]]

    def get_contexts_by_type(
        self,
        context_type: ContextType,
    ) -> list[ContextSnapshot]:
        """Ture gore baglamlari getirir.

        Args:
            context_type: Baglam turu.

        Returns:
            Baglam listesi.
        """
        return [
            c for c in self._contexts
            if c.context_type == context_type
        ]

    @property
    def user_profile(self) -> dict[str, Any]:
        """Kullanici profili."""
        return dict(self._user_profile)

    @property
    def conversation_length(self) -> int:
        """Konusma uzunlugu."""
        return len(self._conversation_history)

    @property
    def has_task_context(self) -> bool:
        """Gorev baglami var mi."""
        return bool(self._task_context)

    @property
    def context_count(self) -> int:
        """Toplam baglam sayisi."""
        return len(self._contexts)
