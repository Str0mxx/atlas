"""ATLAS Gorev Cikarici modulu.

Ort ulu gorev tespiti, belirsizlik cozumu,
takip tahmini, gorev tamamlama tespiti
ve sonraki adim onerisi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import IntentCategory

logger = logging.getLogger(__name__)


class TaskInferrer:
    """Gorev cikarici.

    Kullanici mesajlarindan ortulu gorevleri
    tespit eder ve sonraki adimlari tahmin eder.

    Attributes:
        _inferred_tasks: Cikarilmis gorevler.
        _ambiguities: Belirsizlik kayitlari.
        _follow_ups: Takip tahminleri.
        _completions: Tamamlama kayitlari.
        _task_keywords: Gorev anahtar kelimeleri.
    """

    def __init__(self) -> None:
        """Gorev cikariciyi baslatir."""
        self._inferred_tasks: list[dict[str, Any]] = []
        self._ambiguities: list[dict[str, Any]] = []
        self._follow_ups: list[dict[str, Any]] = []
        self._completions: list[dict[str, Any]] = []
        self._task_keywords: dict[str, list[str]] = {
            "deploy": ["deploy", "yayinla", "production", "release"],
            "monitor": ["izle", "kontrol", "monitor", "check"],
            "analyze": ["analiz", "incele", "arastir", "analyze"],
            "fix": ["duzelt", "fix", "hata", "bug", "sorun"],
            "create": ["olustur", "yap", "create", "ekle", "add"],
            "report": ["rapor", "ozet", "summary", "report"],
            "optimize": ["optimize", "iyilestir", "hizlandir"],
            "backup": ["yedekle", "backup", "kaydet"],
        }

        logger.info("TaskInferrer baslatildi")

    def detect_implicit_task(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ortulu gorev tespit eder.

        Args:
            message: Kullanici mesaji.
            context: Baglam.

        Returns:
            Tespit sonucu.
        """
        ctx = context or {}
        message_lower = message.lower()
        detected_tasks: list[dict[str, str]] = []

        for task_type, keywords in self._task_keywords.items():
            for kw in keywords:
                if kw in message_lower:
                    detected_tasks.append({
                        "type": task_type,
                        "keyword": kw,
                        "confidence": "high"
                        if kw == message_lower.split()[0]
                        else "medium",
                    })
                    break

        # Soru -> bilgi gorevi
        if message.strip().endswith("?"):
            detected_tasks.append({
                "type": "query",
                "keyword": "?",
                "confidence": "high",
            })

        result = {
            "message": message,
            "tasks_found": len(detected_tasks),
            "tasks": detected_tasks,
            "has_implicit_task": len(detected_tasks) > 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._inferred_tasks.append(result)

        if detected_tasks:
            logger.info(
                "%d ortulu gorev tespit edildi: %s",
                len(detected_tasks),
                [t["type"] for t in detected_tasks],
            )

        return result

    def resolve_ambiguity(
        self,
        message: str,
        possible_intents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Belirsizlik cozer.

        Args:
            message: Belirsiz mesaj.
            possible_intents: Olasi niyetler.

        Returns:
            Cozum sonucu.
        """
        if not possible_intents:
            result = {
                "resolved": False,
                "message": message,
                "reason": "Olasi niyet yok",
            }
            self._ambiguities.append(result)
            return result

        # En yuksek guvenli niyeti sec
        scored = []
        for intent in possible_intents:
            conf = intent.get("confidence", 0.5)
            if isinstance(conf, str):
                conf = {"high": 0.9, "medium": 0.6, "low": 0.3}.get(conf, 0.5)
            scored.append((conf, intent))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_conf, best_intent = scored[0]

        # Belirsizlik esigi
        needs_clarification = False
        if len(scored) >= 2:
            diff = best_conf - scored[1][0]
            if diff < 0.2:
                needs_clarification = True

        result = {
            "resolved": not needs_clarification,
            "message": message,
            "selected_intent": best_intent,
            "confidence": best_conf,
            "needs_clarification": needs_clarification,
            "alternatives": [i for _, i in scored[1:3]],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._ambiguities.append(result)

        return result

    def predict_follow_up(
        self,
        completed_task: str,
        task_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Takip gorevleri tahmin eder.

        Args:
            completed_task: Tamamlanan gorev.
            task_result: Gorev sonucu.

        Returns:
            Takip onerileri.
        """
        result = task_result or {}
        suggestions: list[dict[str, Any]] = []

        task_lower = completed_task.lower()

        # Gorev turune gore takipler
        follow_up_map: dict[str, list[dict[str, str]]] = {
            "deploy": [
                {"task": "Monitor deployment", "reason": "Deployment durumunu izle"},
                {"task": "Run smoke tests", "reason": "Temel kontroller yap"},
            ],
            "analyze": [
                {"task": "Generate report", "reason": "Analiz raporla"},
                {"task": "Share findings", "reason": "Bulgulari paylas"},
            ],
            "fix": [
                {"task": "Run tests", "reason": "Duzeltmeyi dogrula"},
                {"task": "Deploy fix", "reason": "Duzeltmeyi yayinla"},
            ],
            "create": [
                {"task": "Test creation", "reason": "Olusturulani test et"},
                {"task": "Document", "reason": "Belgele"},
            ],
            "report": [
                {"task": "Send report", "reason": "Raporu gonder"},
                {"task": "Schedule next", "reason": "Sonraki raporu zamanla"},
            ],
        }

        for key, follow_ups in follow_up_map.items():
            if key in task_lower:
                suggestions.extend(follow_ups)

        # Hata varsa duzeltme oner
        if result.get("has_errors") or result.get("error"):
            suggestions.insert(0, {
                "task": "Fix errors",
                "reason": "Hatalari duzelt",
            })

        record = {
            "completed_task": completed_task,
            "suggestions": suggestions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._follow_ups.append(record)

        return suggestions

    def detect_completion(
        self,
        task_description: str,
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Gorev tamamlanmasini tespit eder.

        Args:
            task_description: Gorev tanimi.
            current_state: Mevcut durum.

        Returns:
            Tamamlama durumu.
        """
        completion_indicators = [
            "completed",
            "done",
            "finished",
            "success",
            "tamamlandi",
            "bitti",
            "basarili",
        ]

        state_str = str(current_state).lower()
        status = current_state.get("status", "")

        is_complete = (
            status in ("completed", "done", "success")
            or any(ind in state_str for ind in completion_indicators)
        )

        progress = current_state.get("progress", 0)
        if isinstance(progress, (int, float)) and progress >= 100:
            is_complete = True

        result = {
            "task": task_description,
            "is_complete": is_complete,
            "progress": progress,
            "status": status or ("completed" if is_complete else "in_progress"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._completions.append(result)

        return result

    def suggest_next_step(
        self,
        current_task: str,
        progress: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sonraki adimi onerir.

        Args:
            current_task: Mevcut gorev.
            progress: Ilerleme (0-100).
            context: Baglam.

        Returns:
            Oneri bilgisi.
        """
        ctx = context or {}

        if progress >= 100:
            follow_ups = self.predict_follow_up(current_task)
            return {
                "current_task": current_task,
                "status": "completed",
                "suggestion": follow_ups[0]["task"] if follow_ups else "Tamamlandi",
                "reason": follow_ups[0]["reason"] if follow_ups else "Gorev bitti",
                "follow_ups": follow_ups,
            }

        if progress >= 75:
            return {
                "current_task": current_task,
                "status": "nearly_done",
                "suggestion": "Tamamlamaya devam et",
                "reason": f"Ilerleme: {progress:.0f}%",
            }

        if progress >= 25:
            return {
                "current_task": current_task,
                "status": "in_progress",
                "suggestion": "Devam et",
                "reason": f"Ilerleme: {progress:.0f}%",
            }

        return {
            "current_task": current_task,
            "status": "starting",
            "suggestion": "Baslangic adimlariyla basla",
            "reason": f"Henuz baslangiçta ({progress:.0f}%)",
        }

    def add_task_keywords(
        self,
        task_type: str,
        keywords: list[str],
    ) -> None:
        """Gorev anahtar kelimeleri ekler.

        Args:
            task_type: Gorev turu.
            keywords: Anahtar kelimeler.
        """
        existing = self._task_keywords.get(task_type, [])
        self._task_keywords[task_type] = list(
            set(existing + keywords),
        )

    @property
    def inferred_count(self) -> int:
        """Cikarilmis gorev sayisi."""
        return len(self._inferred_tasks)

    @property
    def ambiguity_count(self) -> int:
        """Belirsizlik sayisi."""
        return len(self._ambiguities)

    @property
    def follow_up_count(self) -> int:
        """Takip sayisi."""
        return len(self._follow_ups)

    @property
    def completion_count(self) -> int:
        """Tamamlama sayisi."""
        return len(self._completions)
