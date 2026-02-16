"""ATLAS İş Parçacığı Analizcisi modülü.

İş parçacığı yeniden yapılandırma,
katılımcı takibi, konu evrimi,
çözüm tespiti, anahtar noktalar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ThreadAnalyzer:
    """İş parçacığı analizcisi.

    Email iş parçacıklarını analiz eder.

    Attributes:
        _threads: İş parçacığı kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analizcisi başlatır."""
        self._threads: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "threads_analyzed": 0,
            "resolutions_detected": 0,
        }

        logger.info(
            "ThreadAnalyzer baslatildi",
        )

    def reconstruct_thread(
        self,
        thread_id: str,
        messages: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """İş parçacığı yeniden yapılandırır.

        Args:
            thread_id: İş parçacığı kimliği.
            messages: Mesajlar.

        Returns:
            Yapılandırma bilgisi.
        """
        messages = messages or []

        sorted_msgs = sorted(
            messages,
            key=lambda m: m.get(
                "timestamp", 0,
            ),
        )

        participants = list({
            m.get("sender", "")
            for m in sorted_msgs
            if m.get("sender")
        })

        self._threads[thread_id] = {
            "thread_id": thread_id,
            "messages": sorted_msgs,
            "participants": participants,
            "message_count": len(
                sorted_msgs,
            ),
            "timestamp": time.time(),
        }
        self._stats[
            "threads_analyzed"
        ] += 1

        return {
            "thread_id": thread_id,
            "message_count": len(
                sorted_msgs,
            ),
            "participants": participants,
            "reconstructed": True,
        }

    def track_participants(
        self,
        thread_id: str,
    ) -> dict[str, Any]:
        """Katılımcı takibi yapar.

        Args:
            thread_id: İş parçacığı kimliği.

        Returns:
            Takip bilgisi.
        """
        thread = self._threads.get(
            thread_id,
        )
        if not thread:
            return {
                "thread_id": thread_id,
                "tracked": False,
            }

        messages = thread["messages"]
        participation: dict[
            str, int
        ] = {}

        for m in messages:
            sender = m.get("sender", "")
            if sender:
                participation[sender] = (
                    participation.get(
                        sender, 0,
                    ) + 1
                )

        most_active = (
            max(
                participation,
                key=participation.get,
            )
            if participation
            else ""
        )

        return {
            "thread_id": thread_id,
            "participants": participation,
            "most_active": most_active,
            "total_participants": len(
                participation,
            ),
            "tracked": True,
        }

    def analyze_topic_evolution(
        self,
        thread_id: str,
    ) -> dict[str, Any]:
        """Konu evrimi analiz eder.

        Args:
            thread_id: İş parçacığı kimliği.

        Returns:
            Analiz bilgisi.
        """
        thread = self._threads.get(
            thread_id,
        )
        if not thread:
            return {
                "thread_id": thread_id,
                "analyzed": False,
            }

        messages = thread["messages"]
        topics = []

        for i, m in enumerate(messages):
            subject = m.get("subject", "")
            body = m.get("body", "")
            text = (
                f"{subject} {body}".lower()
            )

            # Basit konu çıkarma
            words = [
                w for w in text.split()
                if len(w) > 3
            ][:3]

            topics.append({
                "message_index": i,
                "keywords": words,
            })

        return {
            "thread_id": thread_id,
            "topic_evolution": topics,
            "message_count": len(messages),
            "analyzed": True,
        }

    def detect_resolution(
        self,
        thread_id: str,
    ) -> dict[str, Any]:
        """Çözüm tespit eder.

        Args:
            thread_id: İş parçacığı kimliği.

        Returns:
            Tespit bilgisi.
        """
        thread = self._threads.get(
            thread_id,
        )
        if not thread:
            return {
                "thread_id": thread_id,
                "detected": False,
            }

        messages = thread["messages"]
        resolution_indicators = [
            "resolved", "done", "completed",
            "fixed", "closed", "thanks",
            "thank you", "approved",
            "confirmed",
        ]

        is_resolved = False
        resolution_msg = ""

        for m in reversed(messages):
            body = m.get(
                "body", "",
            ).lower()
            if any(
                ind in body
                for ind in (
                    resolution_indicators
                )
            ):
                is_resolved = True
                resolution_msg = m.get(
                    "body", "",
                )[:100]
                break

        if is_resolved:
            self._stats[
                "resolutions_detected"
            ] += 1

        return {
            "thread_id": thread_id,
            "is_resolved": is_resolved,
            "resolution_hint": (
                resolution_msg
            ),
            "detected": True,
        }

    def extract_key_points(
        self,
        thread_id: str,
        max_points: int = 5,
    ) -> dict[str, Any]:
        """Anahtar noktaları çıkarır.

        Args:
            thread_id: İş parçacığı kimliği.
            max_points: Maks nokta.

        Returns:
            Çıkarma bilgisi.
        """
        thread = self._threads.get(
            thread_id,
        )
        if not thread:
            return {
                "thread_id": thread_id,
                "extracted": False,
            }

        messages = thread["messages"]
        key_points = []

        for m in messages:
            body = m.get("body", "")
            sentences = [
                s.strip()
                for s in body.split(".")
                if s.strip()
                and len(s.strip()) > 10
            ]

            # En uzun cümleleri al
            sentences.sort(
                key=len, reverse=True,
            )

            for s in sentences[:1]:
                key_points.append({
                    "sender": m.get(
                        "sender", "",
                    ),
                    "point": s[:200],
                })

        return {
            "thread_id": thread_id,
            "key_points": key_points[
                :max_points
            ],
            "count": min(
                len(key_points),
                max_points,
            ),
            "extracted": True,
        }

    @property
    def thread_count(self) -> int:
        """İş parçacığı sayısı."""
        return self._stats[
            "threads_analyzed"
        ]

    @property
    def resolution_count(self) -> int:
        """Çözüm sayısı."""
        return self._stats[
            "resolutions_detected"
        ]
