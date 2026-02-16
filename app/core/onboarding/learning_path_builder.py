"""ATLAS Öğrenme Yolu Oluşturucu modülü.

Kişiselleştirilmiş öğrenme yolları,
ön koşul yönetimi, süre tahmini,
kilometre taşı, adaptif sıralama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LearningPathBuilder:
    """Öğrenme yolu oluşturucu.

    Kişisel öğrenme yolları oluşturur.

    Attributes:
        _paths: Öğrenme yolları.
        _modules: Modül kayıtları.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._paths: dict[
            str, dict[str, Any]
        ] = {}
        self._modules: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "paths_created": 0,
            "modules_added": 0,
        }

        logger.info(
            "LearningPathBuilder "
            "baslatildi",
        )

    def build_personalized_path(
        self,
        user_id: str,
        skill_level: str = "beginner",
        target_skills: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Kişisel öğrenme yolu oluşturur.

        Args:
            user_id: Kullanıcı kimliği.
            skill_level: Beceri seviyesi.
            target_skills: Hedef beceriler.

        Returns:
            Yol bilgisi.
        """
        target_skills = (
            target_skills or []
        )
        self._counter += 1
        pid = f"path_{self._counter}"

        modules = []
        for skill in target_skills:
            modules.append({
                "skill": skill,
                "level": skill_level,
                "status": "pending",
                "order": len(modules) + 1,
            })

        self._paths[pid] = {
            "path_id": pid,
            "user_id": user_id,
            "skill_level": skill_level,
            "target_skills": target_skills,
            "modules": modules,
            "status": "active",
            "timestamp": time.time(),
        }
        self._modules[pid] = modules
        self._stats["paths_created"] += 1

        return {
            "path_id": pid,
            "user_id": user_id,
            "module_count": len(modules),
            "built": True,
        }

    def handle_prerequisites(
        self,
        path_id: str,
        module_name: str,
        prerequisites: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Ön koşulları yönetir.

        Args:
            path_id: Yol kimliği.
            module_name: Modül adı.
            prerequisites: Ön koşullar.

        Returns:
            Ön koşul bilgisi.
        """
        prerequisites = (
            prerequisites or []
        )
        path = self._paths.get(path_id)
        if not path:
            return {
                "path_id": path_id,
                "found": False,
            }

        modules = self._modules.get(
            path_id, [],
        )
        completed = [
            m["skill"] for m in modules
            if m["status"] == "completed"
        ]

        unmet = [
            p for p in prerequisites
            if p not in completed
        ]

        return {
            "path_id": path_id,
            "module": module_name,
            "prerequisites": prerequisites,
            "unmet": unmet,
            "ready": len(unmet) == 0,
            "handled": True,
        }

    def estimate_duration(
        self,
        path_id: str,
        hours_per_module: float = 2.0,
    ) -> dict[str, Any]:
        """Süre tahmini yapar.

        Args:
            path_id: Yol kimliği.
            hours_per_module: Modül başına saat.

        Returns:
            Tahmin bilgisi.
        """
        path = self._paths.get(path_id)
        if not path:
            return {
                "path_id": path_id,
                "found": False,
            }

        modules = self._modules.get(
            path_id, [],
        )
        pending = sum(
            1 for m in modules
            if m["status"] != "completed"
        )

        total_hours = (
            pending * hours_per_module
        )

        return {
            "path_id": path_id,
            "total_modules": len(modules),
            "pending_modules": pending,
            "estimated_hours": total_hours,
            "estimated": True,
        }

    def set_milestones(
        self,
        path_id: str,
        milestones: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Kilometre taşları belirler.

        Args:
            path_id: Yol kimliği.
            milestones: Kilometre taşları.

        Returns:
            Taş bilgisi.
        """
        milestones = milestones or []
        path = self._paths.get(path_id)
        if not path:
            return {
                "path_id": path_id,
                "found": False,
            }

        path["milestones"] = milestones

        return {
            "path_id": path_id,
            "milestone_count": len(
                milestones,
            ),
            "set": True,
        }

    def adapt_sequence(
        self,
        path_id: str,
        performance_scores: dict[
            str, float
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Adaptif sıralama yapar.

        Args:
            path_id: Yol kimliği.
            performance_scores: Performans
                puanları.

        Returns:
            Sıralama bilgisi.
        """
        performance_scores = (
            performance_scores or {}
        )
        path = self._paths.get(path_id)
        if not path:
            return {
                "path_id": path_id,
                "found": False,
            }

        modules = self._modules.get(
            path_id, [],
        )

        weak = [
            skill
            for skill, score in (
                performance_scores.items()
            )
            if score < 50
        ]

        reordered = False
        if weak:
            for m in modules:
                if m["skill"] in weak:
                    m["priority"] = "high"
                    reordered = True

        return {
            "path_id": path_id,
            "weak_areas": weak,
            "reordered": reordered,
            "adapted": True,
        }

    @property
    def path_count(self) -> int:
        """Yol sayısı."""
        return self._stats[
            "paths_created"
        ]
