"""TeamManager testleri.

Takim olusturma, uye yonetimi, rol atama,
yetenek eslestirme ve is yuku dengeleme.
"""

from app.core.collaboration.team import TeamManager
from app.models.collaboration import TeamRole, TeamStatus


# === Yardimci fonksiyonlar ===


def _make_manager() -> TeamManager:
    tm = TeamManager()
    tm.register_agent("research", ["web_search", "analysis"], workload=0.2)
    tm.register_agent("security", ["scanning", "monitoring"], workload=0.5)
    tm.register_agent("coding", ["code_review", "analysis"], workload=0.1)
    tm.register_agent("marketing", ["ads", "seo"], workload=0.8)
    return tm


# === Init Testleri ===


class TestTeamManagerInit:
    def test_default(self) -> None:
        tm = TeamManager()
        assert tm.teams == {}
        assert tm.agent_profiles == {}


# === register_agent Testleri ===


class TestTeamManagerRegister:
    def test_register(self) -> None:
        tm = TeamManager()
        tm.register_agent("agent_a", ["skill1", "skill2"], workload=0.3)
        assert "agent_a" in tm.agent_profiles
        assert tm.agent_profiles["agent_a"]["capabilities"] == ["skill1", "skill2"]
        assert tm.agent_profiles["agent_a"]["workload"] == 0.3

    def test_workload_clamped(self) -> None:
        tm = TeamManager()
        tm.register_agent("a", [], workload=1.5)
        assert tm.agent_profiles["a"]["workload"] == 1.0
        tm.register_agent("b", [], workload=-0.5)
        assert tm.agent_profiles["b"]["workload"] == 0.0


class TestTeamManagerUpdateWorkload:
    def test_update(self) -> None:
        tm = _make_manager()
        tm.update_workload("research", 0.9)
        assert tm.agent_profiles["research"]["workload"] == 0.9

    def test_update_nonexistent(self) -> None:
        tm = _make_manager()
        tm.update_workload("nope", 0.5)  # Hata vermemeli


# === create_team Testleri ===


class TestTeamManagerCreateTeam:
    async def test_create_basic(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Alpha", "Test mission")
        assert team.name == "Alpha"
        assert team.objective == "Test mission"
        assert team.id in tm.teams
        assert team.status == TeamStatus.ACTIVE

    async def test_create_with_capabilities(self) -> None:
        tm = _make_manager()
        team = await tm.create_team(
            "Analysts", "Data analysis",
            required_capabilities=["analysis"],
        )
        member_names = [m.agent_name for m in team.members]
        assert "research" in member_names
        assert "coding" in member_names
        assert "marketing" not in member_names

    async def test_first_member_is_leader(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "Objective")
        if team.members:
            assert team.members[0].role == TeamRole.LEADER

    async def test_max_members(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Small", "Task", max_members=2)
        assert len(team.members) <= 2

    async def test_no_matching_agents(self) -> None:
        tm = _make_manager()
        team = await tm.create_team(
            "Ghost", "Impossible",
            required_capabilities=["quantum_computing"],
        )
        assert len(team.members) == 0
        assert team.status == TeamStatus.FORMING

    async def test_low_workload_preferred(self) -> None:
        tm = _make_manager()
        # coding has 0.1 workload, marketing has 0.8
        team = await tm.create_team("Workers", "General", max_members=2)
        names = [m.agent_name for m in team.members]
        # coding (0.1) ve research (0.2) en dusuk is yukune sahip
        assert "coding" in names

    async def test_metadata(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("M", "O", metadata={"project": "atlas"})
        assert team.metadata == {"project": "atlas"}


# === add_member Testleri ===


class TestTeamManagerAddMember:
    async def test_add(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O", max_members=1)
        result = await tm.add_member(team.id, "marketing")
        assert result is not None
        assert result.agent_name == "marketing"

    async def test_add_duplicate(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O", max_members=1)
        first_member = team.members[0].agent_name if team.members else None
        if first_member:
            result = await tm.add_member(team.id, first_member)
            assert result is None

    async def test_add_nonexistent_team(self) -> None:
        tm = _make_manager()
        result = await tm.add_member("nope", "research")
        assert result is None

    async def test_add_with_role(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O", max_members=0)
        result = await tm.add_member(team.id, "research", TeamRole.SPECIALIST)
        assert result is not None
        assert result.role == TeamRole.SPECIALIST


# === remove_member Testleri ===


class TestTeamManagerRemoveMember:
    async def test_remove(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O")
        first = team.members[0].agent_name
        result = await tm.remove_member(team.id, first)
        assert result is True
        assert all(m.agent_name != first for m in team.members)

    async def test_remove_nonexistent_member(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O")
        result = await tm.remove_member(team.id, "nonexistent")
        assert result is False

    async def test_remove_nonexistent_team(self) -> None:
        tm = _make_manager()
        result = await tm.remove_member("nope", "research")
        assert result is False

    async def test_remove_leader_promotes(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O")
        leader = team.members[0].agent_name
        await tm.remove_member(team.id, leader)
        if team.members:
            assert team.members[0].role == TeamRole.LEADER


# === assign_role Testleri ===


class TestTeamManagerAssignRole:
    async def test_assign(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O")
        member = team.members[-1].agent_name
        result = await tm.assign_role(team.id, member, TeamRole.SPECIALIST)
        assert result is True
        found = [m for m in team.members if m.agent_name == member]
        assert found[0].role == TeamRole.SPECIALIST

    async def test_assign_nonexistent(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O")
        result = await tm.assign_role(team.id, "nope", TeamRole.LEADER)
        assert result is False

    async def test_assign_nonexistent_team(self) -> None:
        tm = _make_manager()
        result = await tm.assign_role("nope", "research", TeamRole.LEADER)
        assert result is False


# === disband_team Testleri ===


class TestTeamManagerDisband:
    async def test_disband(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("Team", "O")
        result = await tm.disband_team(team.id)
        assert result is True
        assert team.status == TeamStatus.DISBANDED
        assert team.members == []

    async def test_disband_nonexistent(self) -> None:
        tm = _make_manager()
        result = await tm.disband_team("nope")
        assert result is False


# === Yardimci Metot Testleri ===


class TestTeamManagerHelpers:
    async def test_get_agent_teams(self) -> None:
        tm = _make_manager()
        await tm.create_team("T1", "O1", required_capabilities=["analysis"])
        await tm.create_team("T2", "O2", required_capabilities=["analysis"])
        teams = tm.get_agent_teams("research")
        assert len(teams) == 2

    async def test_get_agent_teams_excludes_disbanded(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("T1", "O1")
        await tm.disband_team(team.id)
        teams = tm.get_agent_teams("research")
        assert len(teams) == 0

    async def test_get_team_leader(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("T1", "O1")
        leader = tm.get_team_leader(team.id)
        assert leader is not None

    def test_get_team_leader_nonexistent(self) -> None:
        tm = _make_manager()
        assert tm.get_team_leader("nope") is None

    async def test_get_team_capabilities(self) -> None:
        tm = _make_manager()
        team = await tm.create_team("T1", "O1", required_capabilities=["analysis"])
        caps = tm.get_team_capabilities(team.id)
        assert "analysis" in caps

    def test_get_team_capabilities_nonexistent(self) -> None:
        tm = _make_manager()
        assert tm.get_team_capabilities("nope") == []

    async def test_get_active_teams(self) -> None:
        tm = _make_manager()
        await tm.create_team("T1", "O1")
        await tm.create_team("T2", "O2")
        active = tm.get_active_teams()
        assert len(active) == 2
