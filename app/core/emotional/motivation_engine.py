"""ATLAS Motivasyon Motoru modulu.

Basarisizliklarda tesvik, basarilarda kutlama,
ilerleme onaylama, hedef hatirlatma ve pozitif pekistirme.
"""

import logging
from typing import Any

from app.models.emotional import (
    MoodLevel,
    MotivationMessage,
    MotivationType,
    UserEmotionalState,
)

logger = logging.getLogger(__name__)

# Motivasyon sablonlari
_TEMPLATES: dict[MotivationType, list[str]] = {
    MotivationType.ENCOURAGEMENT: [
        "Endiselenme, herkes hata yapar. Onemli olan devam etmek!",
        "Bu sefer olmadi ama bir sonraki denemede basaracaksin.",
        "Zorluklar seni guclendirir. Devam et!",
    ],
    MotivationType.CELEBRATION: [
        "Harika is cikardi! Tebrikler!",
        "Basarini kutluyorum, supersin!",
        "Mukemmel sonuc! Boyle devam!",
    ],
    MotivationType.PROGRESS: [
        "Guzel ilerliyorsun, {progress} tamamlandi.",
        "Her adim hedefe yaklastiriyor. Yolun {progress}'i bitti.",
        "Istikrarli ilerleme! {progress} tamamlandi.",
    ],
    MotivationType.GOAL_REMINDER: [
        "Hatirlatma: '{goal}' hedefin icin calisiyoruz.",
        "Hedefiniz '{goal}' - odaklanmaya devam!",
    ],
    MotivationType.POSITIVE_REINFORCEMENT: [
        "Bu yaklasim cok iyi calisiyor, devam et!",
        "Dogru yoldasin, boyle devam!",
        "Harika bir karar, sonuclari goruyoruz.",
    ],
}


class MotivationEngine:
    """Motivasyon motoru.

    Kullaniciya duygusal durumuna gore motivasyon
    mesajlari uretir ve gonderir.

    Attributes:
        _messages: Gonderilen mesajlar.
        _goals: Kullanici hedefleri.
        _progress: Ilerleme takibi.
    """

    def __init__(self) -> None:
        """Motivasyon motorunu baslatir."""
        self._messages: list[MotivationMessage] = []
        self._goals: dict[str, list[str]] = {}
        self._progress: dict[str, dict[str, float]] = {}

        logger.info("MotivationEngine baslatildi")

    def encourage(self, user_id: str, context: str = "") -> MotivationMessage:
        """Tesvik mesaji uretir.

        Args:
            user_id: Kullanici ID.
            context: Baglam.

        Returns:
            MotivationMessage nesnesi.
        """
        templates = _TEMPLATES[MotivationType.ENCOURAGEMENT]
        idx = len(self._messages) % len(templates)
        message = templates[idx]

        return self._create_message(user_id, MotivationType.ENCOURAGEMENT, message, context)

    def celebrate(self, user_id: str, achievement: str = "") -> MotivationMessage:
        """Kutlama mesaji uretir.

        Args:
            user_id: Kullanici ID.
            achievement: Basari aciklamasi.

        Returns:
            MotivationMessage nesnesi.
        """
        templates = _TEMPLATES[MotivationType.CELEBRATION]
        idx = len(self._messages) % len(templates)
        message = templates[idx]

        if achievement:
            message = f"{message} ({achievement})"

        return self._create_message(user_id, MotivationType.CELEBRATION, message, achievement)

    def acknowledge_progress(self, user_id: str, task: str, progress_pct: float) -> MotivationMessage:
        """Ilerleme onaylar.

        Args:
            user_id: Kullanici ID.
            task: Gorev adi.
            progress_pct: Ilerleme yuzdesi.

        Returns:
            MotivationMessage nesnesi.
        """
        # Ilerleme kaydet
        user_progress = self._progress.setdefault(user_id, {})
        user_progress[task] = progress_pct

        templates = _TEMPLATES[MotivationType.PROGRESS]
        idx = len(self._messages) % len(templates)
        message = templates[idx].format(progress=f"%{progress_pct:.0f}")

        return self._create_message(user_id, MotivationType.PROGRESS, message, task)

    def remind_goal(self, user_id: str, goal: str) -> MotivationMessage:
        """Hedef hatirlatir.

        Args:
            user_id: Kullanici ID.
            goal: Hedef aciklamasi.

        Returns:
            MotivationMessage nesnesi.
        """
        # Hedef kaydet
        goals = self._goals.setdefault(user_id, [])
        if goal not in goals:
            goals.append(goal)

        templates = _TEMPLATES[MotivationType.GOAL_REMINDER]
        idx = len(self._messages) % len(templates)
        message = templates[idx].format(goal=goal)

        return self._create_message(user_id, MotivationType.GOAL_REMINDER, message, goal)

    def reinforce(self, user_id: str, context: str = "") -> MotivationMessage:
        """Pozitif pekistirme yapar.

        Args:
            user_id: Kullanici ID.
            context: Baglam.

        Returns:
            MotivationMessage nesnesi.
        """
        templates = _TEMPLATES[MotivationType.POSITIVE_REINFORCEMENT]
        idx = len(self._messages) % len(templates)
        message = templates[idx]

        return self._create_message(user_id, MotivationType.POSITIVE_REINFORCEMENT, message, context)

    def get_appropriate_motivation(self, user_id: str, state: UserEmotionalState) -> MotivationMessage | None:
        """Duruma uygun motivasyon getirir.

        Args:
            user_id: Kullanici ID.
            state: Kullanici duygusal durumu.

        Returns:
            MotivationMessage veya None.
        """
        if state.current_mood in (MoodLevel.VERY_LOW, MoodLevel.LOW):
            return self.encourage(user_id, "ruh hali dusuk")
        if state.current_mood == MoodLevel.VERY_HIGH:
            return self.reinforce(user_id, "ruh hali yuksek")
        return None

    def set_goal(self, user_id: str, goal: str) -> None:
        """Hedef belirler.

        Args:
            user_id: Kullanici ID.
            goal: Hedef.
        """
        goals = self._goals.setdefault(user_id, [])
        if goal not in goals:
            goals.append(goal)

    def get_goals(self, user_id: str) -> list[str]:
        """Kullanici hedeflerini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Hedef listesi.
        """
        return list(self._goals.get(user_id, []))

    def get_progress(self, user_id: str) -> dict[str, float]:
        """Ilerleme bilgisini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Gorev -> ilerleme sozlugu.
        """
        return dict(self._progress.get(user_id, {}))

    def get_user_messages(self, user_id: str, limit: int = 10) -> list[MotivationMessage]:
        """Kullanici mesajlarini getirir.

        Args:
            user_id: Kullanici ID.
            limit: Maks mesaj.

        Returns:
            MotivationMessage listesi.
        """
        user_msgs = [m for m in self._messages if m.user_id == user_id]
        return user_msgs[-limit:]

    def _create_message(
        self, user_id: str, mtype: MotivationType, message: str, context: str
    ) -> MotivationMessage:
        """Mesaj olusturur ve kaydeder."""
        msg = MotivationMessage(
            user_id=user_id,
            motivation_type=mtype,
            message=message,
            context=context,
            delivered=True,
        )
        self._messages.append(msg)
        return msg

    @property
    def message_count(self) -> int:
        """Mesaj sayisi."""
        return len(self._messages)
