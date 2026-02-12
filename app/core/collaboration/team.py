"""ATLAS Agent takim yonetimi modulu.

Takim olusturma, rol atama, yetenek eslestirme
ve is yuku dengeleme.
"""

import logging
from typing import Any

from app.models.collaboration import (
    Team,
    TeamMember,
    TeamRole,
    TeamStatus,
)

logger = logging.getLogger(__name__)


class TeamManager:
    """Takim yoneticisi.

    Dinamik takim olusturma, yetenek tabanlı uye secimi,
    rol atama ve is yuku dengeleme.

    Attributes:
        teams: Kayitli takimlar (id -> Team).
        agent_profiles: Agent profilleri (agent_adi -> {capabilities, workload}).
    """

    def __init__(self) -> None:
        self.teams: dict[str, Team] = {}
        self.agent_profiles: dict[str, dict[str, Any]] = {}

    def register_agent(
        self,
        agent_name: str,
        capabilities: list[str],
        workload: float = 0.0,
    ) -> None:
        """Agent profilini kayit eder.

        Args:
            agent_name: Agent adi.
            capabilities: Yetenek listesi.
            workload: Mevcut is yuku (0.0-1.0).
        """
        self.agent_profiles[agent_name] = {
            "capabilities": list(capabilities),
            "workload": max(0.0, min(1.0, workload)),
        }

    def update_workload(self, agent_name: str, workload: float) -> None:
        """Agent is yukunu gunceller.

        Args:
            agent_name: Agent adi.
            workload: Yeni is yuku (0.0-1.0).
        """
        profile = self.agent_profiles.get(agent_name)
        if profile is not None:
            profile["workload"] = max(0.0, min(1.0, workload))

    async def create_team(
        self,
        name: str,
        objective: str,
        required_capabilities: list[str] | None = None,
        max_members: int = 5,
        metadata: dict[str, Any] | None = None,
    ) -> Team:
        """Yeni takim olusturur ve uygun uyeleri atar.

        Args:
            name: Takim adi.
            objective: Takim hedefi.
            required_capabilities: Gerekli yetenekler.
            max_members: Maksimum uye sayisi.
            metadata: Ek veriler.

        Returns:
            Olusturulan takim.
        """
        team = Team(
            name=name,
            objective=objective,
            required_capabilities=required_capabilities or [],
            metadata=metadata or {},
        )

        # Uygun uyeleri sec
        candidates = self._find_candidates(
            required_capabilities or [],
            max_members,
        )

        for i, agent_name in enumerate(candidates):
            role = TeamRole.LEADER if i == 0 else TeamRole.MEMBER
            profile = self.agent_profiles.get(agent_name, {})
            member = TeamMember(
                agent_name=agent_name,
                role=role,
                capabilities=profile.get("capabilities", []),
                workload=profile.get("workload", 0.0),
            )
            team.members.append(member)

        if team.members:
            team.status = TeamStatus.ACTIVE

        self.teams[team.id] = team

        logger.info(
            "Takim olusturuldu: %s (%d uye)",
            name,
            len(team.members),
        )
        return team

    def _find_candidates(
        self,
        required_capabilities: list[str],
        max_count: int,
    ) -> list[str]:
        """Yeteneklere gore aday agentlari bulur ve siralar.

        Siralama: yetenek eslesmesi (cok = once), is yuku (az = once).

        Args:
            required_capabilities: Gerekli yetenekler.
            max_count: Maksimum aday sayisi.

        Returns:
            Sirali agent listesi.
        """
        scored: list[tuple[float, str]] = []
        required_set = set(required_capabilities)

        for agent_name, profile in self.agent_profiles.items():
            caps = set(profile.get("capabilities", []))
            workload = profile.get("workload", 0.0)

            if required_set and not required_set.intersection(caps):
                continue

            # Puan: yetenek eslesmesi - is yuku
            if required_set:
                match_ratio = len(required_set.intersection(caps)) / len(required_set)
            else:
                match_ratio = 1.0

            score = match_ratio * 0.7 + (1.0 - workload) * 0.3
            scored.append((score, agent_name))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [name for _, name in scored[:max_count]]

    async def add_member(
        self,
        team_id: str,
        agent_name: str,
        role: TeamRole = TeamRole.MEMBER,
    ) -> TeamMember | None:
        """Takima uye ekler.

        Args:
            team_id: Takim ID.
            agent_name: Eklenecek agent.
            role: Rol.

        Returns:
            Eklenen uye veya None.
        """
        team = self.teams.get(team_id)
        if team is None:
            return None

        # Zaten uye mi kontrol et
        for member in team.members:
            if member.agent_name == agent_name:
                return None

        profile = self.agent_profiles.get(agent_name, {})
        member = TeamMember(
            agent_name=agent_name,
            role=role,
            capabilities=profile.get("capabilities", []),
            workload=profile.get("workload", 0.0),
        )
        team.members.append(member)

        logger.info("Uye eklendi: %s -> takim %s", agent_name, team.name)
        return member

    async def remove_member(self, team_id: str, agent_name: str) -> bool:
        """Takimdan uye cikarir.

        Args:
            team_id: Takim ID.
            agent_name: Cikarilacak agent.

        Returns:
            Basarili mi.
        """
        team = self.teams.get(team_id)
        if team is None:
            return False

        original_len = len(team.members)
        team.members = [m for m in team.members if m.agent_name != agent_name]

        if len(team.members) < original_len:
            # Lider cikarilmissa yeni lider ata
            if not any(m.role == TeamRole.LEADER for m in team.members):
                if team.members:
                    team.members[0].role = TeamRole.LEADER
            return True

        return False

    async def assign_role(
        self, team_id: str, agent_name: str, role: TeamRole
    ) -> bool:
        """Uye rolunu degistirir.

        Args:
            team_id: Takim ID.
            agent_name: Agent adi.
            role: Yeni rol.

        Returns:
            Basarili mi.
        """
        team = self.teams.get(team_id)
        if team is None:
            return False

        for member in team.members:
            if member.agent_name == agent_name:
                member.role = role
                return True

        return False

    async def disband_team(self, team_id: str) -> bool:
        """Takimi dagitr.

        Args:
            team_id: Takim ID.

        Returns:
            Basarili mi.
        """
        team = self.teams.get(team_id)
        if team is None:
            return False

        team.status = TeamStatus.DISBANDED
        team.members.clear()

        logger.info("Takim dagildi: %s", team.name)
        return True

    def get_agent_teams(self, agent_name: str) -> list[Team]:
        """Agent'in uye oldugu takimlari dondurur.

        Args:
            agent_name: Agent adi.

        Returns:
            Takim listesi.
        """
        result: list[Team] = []
        for team in self.teams.values():
            if team.status == TeamStatus.DISBANDED:
                continue
            for member in team.members:
                if member.agent_name == agent_name:
                    result.append(team)
                    break
        return result

    def get_team_leader(self, team_id: str) -> str | None:
        """Takim liderini dondurur.

        Args:
            team_id: Takim ID.

        Returns:
            Lider agent adi veya None.
        """
        team = self.teams.get(team_id)
        if team is None:
            return None

        for member in team.members:
            if member.role == TeamRole.LEADER:
                return member.agent_name

        return None

    def get_team_capabilities(self, team_id: str) -> list[str]:
        """Takimin toplam yeteneklerini dondurur.

        Args:
            team_id: Takim ID.

        Returns:
            Birlesik yetenek listesi.
        """
        team = self.teams.get(team_id)
        if team is None:
            return []

        caps: set[str] = set()
        for member in team.members:
            caps.update(member.capabilities)
        return sorted(caps)

    def get_active_teams(self) -> list[Team]:
        """Aktif takimlari dondurur.

        Returns:
            Aktif takim listesi.
        """
        return [
            t for t in self.teams.values()
            if t.status in (TeamStatus.ACTIVE, TeamStatus.EXECUTING)
        ]
