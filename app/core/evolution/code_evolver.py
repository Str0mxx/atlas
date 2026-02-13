"""ATLAS Kod Evrimi modulu.

Fix/iyilestirme kodu uretimi, versiyon yonetimi,
diff olusturma ve rollback hazirligi.
"""

import logging
from typing import Any

from app.models.evolution import (
    ChangeSeverity,
    CodeChange,
    ImprovementPlan,
    ImprovementType,
)

logger = logging.getLogger(__name__)

# Iyilestirme tipi -> degisiklik tipi
_CHANGE_TYPES: dict[ImprovementType, str] = {
    ImprovementType.BUG_FIX: "fix",
    ImprovementType.PERFORMANCE: "optimize",
    ImprovementType.NEW_CAPABILITY: "add",
    ImprovementType.REFACTOR: "refactor",
    ImprovementType.CONFIGURATION: "config",
    ImprovementType.DOCUMENTATION: "docs",
}


class CodeEvolver:
    """Kod evrimi sistemi.

    Iyilestirme planlarindan kod degisiklikleri uretir,
    versiyonlar, diff olusturur ve rollback hazirlar.

    Attributes:
        _changes: Uretilen degisiklikler.
        _versions: Bilesen bazli versiyon takibi.
        _rollback_stack: Geri alma yigini.
    """

    def __init__(self) -> None:
        """Kod evrimcisini baslatir."""
        self._changes: list[CodeChange] = []
        self._versions: dict[str, int] = {}
        self._rollback_stack: list[CodeChange] = []

        logger.info("CodeEvolver baslatildi")

    def generate_change(self, plan: ImprovementPlan) -> CodeChange:
        """Plandan kod degisikligi uretir.

        Args:
            plan: Iyilestirme plani.

        Returns:
            CodeChange nesnesi.
        """
        change_type = _CHANGE_TYPES.get(plan.improvement_type, "fix")
        file_path = self._resolve_file_path(plan.target_component)
        version = self._next_version(plan.target_component)
        diff = self._generate_diff(plan, change_type)
        rollback = self._prepare_rollback_data(file_path)

        change = CodeChange(
            file_path=file_path,
            change_type=change_type,
            diff=diff,
            description=f"{change_type}: {plan.description}",
            severity=plan.risk_level,
            version=version,
            rollback_data=rollback,
        )

        self._changes.append(change)
        logger.info("Degisiklik uretildi: %s v%d", file_path, version)
        return change

    def generate_changes(self, plans: list[ImprovementPlan]) -> list[CodeChange]:
        """Birden fazla plandan degisiklikler uretir.

        Args:
            plans: Iyilestirme planlari.

        Returns:
            CodeChange listesi.
        """
        return [self.generate_change(p) for p in plans]

    def get_change(self, change_id: str) -> CodeChange | None:
        """Degisiklik getirir.

        Args:
            change_id: Degisiklik ID.

        Returns:
            CodeChange veya None.
        """
        for change in self._changes:
            if change.id == change_id:
                return change
        return None

    def apply_change(self, change: CodeChange) -> bool:
        """Degisikligi uygular (simule).

        Args:
            change: Uygulanacak degisiklik.

        Returns:
            Basarili mi.
        """
        self._rollback_stack.append(change)
        logger.info("Degisiklik uygulandi: %s", change.file_path)
        return True

    def rollback_change(self, change: CodeChange) -> bool:
        """Degisikligi geri alir.

        Args:
            change: Geri alinacak degisiklik.

        Returns:
            Basarili mi.
        """
        if change in self._rollback_stack:
            self._rollback_stack.remove(change)
            # Versiyonu geri al
            comp = change.file_path
            if comp in self._versions and self._versions[comp] > 1:
                self._versions[comp] -= 1
            logger.info("Degisiklik geri alindi: %s", change.file_path)
            return True
        return False

    def rollback_all(self) -> int:
        """Tum degisiklikleri geri alir.

        Returns:
            Geri alinan degisiklik sayisi.
        """
        count = len(self._rollback_stack)
        for change in reversed(self._rollback_stack):
            comp = change.file_path
            if comp in self._versions and self._versions[comp] > 1:
                self._versions[comp] -= 1
        self._rollback_stack.clear()
        logger.info("%d degisiklik geri alindi", count)
        return count

    def get_version(self, component: str) -> int:
        """Bilesen versiyonunu getirir.

        Args:
            component: Bilesen adi.

        Returns:
            Versiyon numarasi.
        """
        return self._versions.get(component, 0)

    def get_diff_summary(self, change: CodeChange) -> dict[str, Any]:
        """Diff ozetini getirir.

        Args:
            change: Kod degisikligi.

        Returns:
            Diff ozeti.
        """
        lines = change.diff.split("\n")
        additions = sum(1 for line in lines if line.startswith("+"))
        deletions = sum(1 for line in lines if line.startswith("-"))

        return {
            "file_path": change.file_path,
            "change_type": change.change_type,
            "version": change.version,
            "additions": additions,
            "deletions": deletions,
            "total_lines": len(lines),
        }

    def _resolve_file_path(self, component: str) -> str:
        """Bilesen adini dosya yoluna cevirir."""
        if ":" in component:
            parts = component.split(":")
            return f"app/core/{parts[0]}/{parts[1]}.py"
        if "/" in component or component.endswith(".py"):
            return component
        return f"app/core/{component}.py"

    def _next_version(self, component: str) -> int:
        """Sonraki versiyon numarasini hesaplar."""
        file_path = self._resolve_file_path(component)
        current = self._versions.get(file_path, 0)
        self._versions[file_path] = current + 1
        return current + 1

    def _generate_diff(self, plan: ImprovementPlan, change_type: str) -> str:
        """Diff uretir."""
        lines = [
            f"--- a/{self._resolve_file_path(plan.target_component)}",
            f"+++ b/{self._resolve_file_path(plan.target_component)}",
            f"@@ {change_type}: {plan.title} @@",
        ]

        if change_type == "fix":
            lines.append(f"-# BUG: {plan.description}")
            lines.append(f"+# FIX: {plan.description}")
        elif change_type == "optimize":
            lines.append(f"+# OPTIMIZE: {plan.description}")
        elif change_type == "add":
            lines.append(f"+# NEW: {plan.description}")
        elif change_type == "refactor":
            lines.append(f"-# OLD: {plan.target_component}")
            lines.append(f"+# REFACTOR: {plan.description}")
        else:
            lines.append(f"+# CHANGE: {plan.description}")

        return "\n".join(lines)

    def _prepare_rollback_data(self, file_path: str) -> str:
        """Rollback verisi hazirlar."""
        return f"ROLLBACK:{file_path}:v{self._versions.get(file_path, 0)}"

    @property
    def change_count(self) -> int:
        """Degisiklik sayisi."""
        return len(self._changes)

    @property
    def pending_rollbacks(self) -> int:
        """Bekleyen rollback sayisi."""
        return len(self._rollback_stack)

    @property
    def changes(self) -> list[CodeChange]:
        """Tum degisiklikler."""
        return list(self._changes)
