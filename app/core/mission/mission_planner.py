"""ATLAS Gorev Planlayici modulu.

Faz ayirma, kilometre tasi, kritik yol analizi,
bagimlilik haritalama ve risk tespiti.
"""

import logging
from typing import Any

from app.models.mission import (
    MilestoneDefinition,
    MilestoneState,
    PhaseDefinition,
    PhaseState,
)

logger = logging.getLogger(__name__)


class MissionPlanner:
    """Gorev planlayici.

    Gorevleri fazlara ayirir, kilometre taslarini tanimlar,
    kritik yol ve bagimliliklari analiz eder.

    Attributes:
        _phases: Faz tanimlari.
        _milestones: Kilometre taslari.
        _risks: Tespit edilen riskler.
    """

    def __init__(self) -> None:
        """Planlayiciyi baslatir."""
        self._phases: dict[str, PhaseDefinition] = {}
        self._milestones: dict[str, MilestoneDefinition] = {}
        self._risks: list[dict[str, Any]] = []

        logger.info("MissionPlanner baslatildi")

    def create_phase(
        self,
        mission_id: str,
        name: str,
        order: int = 0,
        description: str = "",
        dependencies: list[str] | None = None,
        gate_criteria: list[str] | None = None,
        parallel: bool = False,
    ) -> PhaseDefinition:
        """Faz olusturur.

        Args:
            mission_id: Gorev ID.
            name: Faz adi.
            order: Sira numarasi.
            description: Aciklama.
            dependencies: Bagimli faz ID'leri.
            gate_criteria: Gecis kriterleri.
            parallel: Paralel calisabilir mi.

        Returns:
            PhaseDefinition nesnesi.
        """
        phase = PhaseDefinition(
            mission_id=mission_id,
            name=name,
            order=order,
            description=description,
            dependencies=dependencies or [],
            gate_criteria=gate_criteria or [],
            parallel=parallel,
        )
        self._phases[phase.phase_id] = phase

        logger.info("Faz olusturuldu: %s (%s)", name, phase.phase_id)
        return phase

    def create_milestone(
        self,
        mission_id: str,
        phase_id: str,
        name: str,
        target_date: Any = None,
    ) -> MilestoneDefinition:
        """Kilometre tasi olusturur.

        Args:
            mission_id: Gorev ID.
            phase_id: Faz ID.
            name: Kilometre tasi adi.
            target_date: Hedef tarih.

        Returns:
            MilestoneDefinition nesnesi.
        """
        milestone = MilestoneDefinition(
            mission_id=mission_id,
            phase_id=phase_id,
            name=name,
            target_date=target_date,
        )
        self._milestones[milestone.milestone_id] = milestone

        logger.info("Kilometre tasi: %s", name)
        return milestone

    def get_phases(self, mission_id: str) -> list[PhaseDefinition]:
        """Gorev fazlarini getirir (siralı).

        Args:
            mission_id: Gorev ID.

        Returns:
            Sirali faz listesi.
        """
        phases = [
            p for p in self._phases.values()
            if p.mission_id == mission_id
        ]
        return sorted(phases, key=lambda p: p.order)

    def get_milestones(
        self,
        mission_id: str,
        phase_id: str = "",
    ) -> list[MilestoneDefinition]:
        """Kilometre taslarini getirir.

        Args:
            mission_id: Gorev ID.
            phase_id: Faz filtresi.

        Returns:
            Kilometre tasi listesi.
        """
        milestones = [
            m for m in self._milestones.values()
            if m.mission_id == mission_id
        ]
        if phase_id:
            milestones = [m for m in milestones if m.phase_id == phase_id]
        return milestones

    def get_phase(self, phase_id: str) -> PhaseDefinition | None:
        """Fazi getirir.

        Args:
            phase_id: Faz ID.

        Returns:
            PhaseDefinition veya None.
        """
        return self._phases.get(phase_id)

    def get_critical_path(self, mission_id: str) -> list[str]:
        """Kritik yolu hesaplar.

        Bagimlilik zincirlerindeki en uzun yolu bulur.

        Args:
            mission_id: Gorev ID.

        Returns:
            Kritik yol faz ID'leri.
        """
        phases = self.get_phases(mission_id)
        if not phases:
            return []

        # Bagimlilik grafini olustur
        graph: dict[str, list[str]] = {}
        for phase in phases:
            graph[phase.phase_id] = phase.dependencies

        # En uzun yol (DFS)
        def longest_path(node: str, visited: set[str]) -> list[str]:
            if node in visited:
                return []
            visited.add(node)

            best: list[str] = []
            for dep in graph.get(node, []):
                path = longest_path(dep, visited)
                if len(path) > len(best):
                    best = path

            visited.discard(node)
            return best + [node]

        longest: list[str] = []
        for phase in phases:
            path = longest_path(phase.phase_id, set())
            if len(path) > len(longest):
                longest = path

        return longest

    def get_dependency_map(
        self,
        mission_id: str,
    ) -> dict[str, list[str]]:
        """Bagimlilik haritasini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Faz ID -> bagimlilik listesi.
        """
        phases = self.get_phases(mission_id)
        return {
            p.phase_id: list(p.dependencies) for p in phases
        }

    def identify_risks(
        self,
        mission_id: str,
    ) -> list[dict[str, Any]]:
        """Riskleri tespit eder.

        Args:
            mission_id: Gorev ID.

        Returns:
            Risk listesi.
        """
        risks: list[dict[str, Any]] = []
        phases = self.get_phases(mission_id)

        # Risk: fazlar arasi bagimlilik dongusu
        dep_map = self.get_dependency_map(mission_id)
        for phase_id, deps in dep_map.items():
            for dep in deps:
                if dep not in self._phases:
                    risks.append({
                        "type": "missing_dependency",
                        "phase_id": phase_id,
                        "dependency": dep,
                        "severity": "high",
                    })

        # Risk: kriterleri olmayan fazlar
        for phase in phases:
            if not phase.gate_criteria:
                risks.append({
                    "type": "no_gate_criteria",
                    "phase_id": phase.phase_id,
                    "severity": "medium",
                })

        # Risk: atanmamis agent'lar
        for phase in phases:
            if not phase.assigned_agents:
                risks.append({
                    "type": "no_agents_assigned",
                    "phase_id": phase.phase_id,
                    "severity": "medium",
                })

        # Risk: kilometre tasi olmayan fazlar
        for phase in phases:
            ms = self.get_milestones(mission_id, phase.phase_id)
            if not ms:
                risks.append({
                    "type": "no_milestones",
                    "phase_id": phase.phase_id,
                    "severity": "low",
                })

        self._risks = risks
        return risks

    def complete_milestone(self, milestone_id: str) -> bool:
        """Kilometre tasini tamamlar.

        Args:
            milestone_id: Kilometre tasi ID.

        Returns:
            Basarili ise True.
        """
        milestone = self._milestones.get(milestone_id)
        if not milestone or milestone.state == MilestoneState.COMPLETED:
            return False

        milestone.state = MilestoneState.COMPLETED
        return True

    def is_phase_ready(self, phase_id: str) -> bool:
        """Faz baslayabilir mi kontrol eder.

        Args:
            phase_id: Faz ID.

        Returns:
            Hazir ise True.
        """
        phase = self._phases.get(phase_id)
        if not phase or phase.state != PhaseState.PENDING:
            return False

        # Tum bagimliliklari kontrol et
        for dep_id in phase.dependencies:
            dep = self._phases.get(dep_id)
            if not dep or dep.state != PhaseState.PASSED:
                return False

        return True

    @property
    def total_phases(self) -> int:
        """Toplam faz sayisi."""
        return len(self._phases)

    @property
    def total_milestones(self) -> int:
        """Toplam kilometre tasi sayisi."""
        return len(self._milestones)
