"""ATLAS Swarm Intelligence sistemi testleri.

SwarmCoordinator, PheromoneSystem, CollectiveMemory,
VotingSystem, TaskAuction, EmergentBehavior,
SwarmLoadBalancer, SwarmFaultTolerance, SwarmOrchestrator testleri.
"""

import pytest

from app.models.swarm import (
    AuctionRecord,
    AuctionState,
    BalanceStrategy,
    FaultAction,
    FaultEvent,
    PheromoneMarker,
    PheromoneType,
    SwarmInfo,
    SwarmSnapshot,
    SwarmState,
    VoteSession,
    VoteType,
)

from app.core.swarm.swarm_coordinator import SwarmCoordinator
from app.core.swarm.pheromone_system import PheromoneSystem
from app.core.swarm.collective_memory import CollectiveMemory
from app.core.swarm.voting_system import VotingSystem
from app.core.swarm.task_auction import TaskAuction
from app.core.swarm.emergent_behavior import EmergentBehavior
from app.core.swarm.load_balancer import SwarmLoadBalancer
from app.core.swarm.fault_tolerance import SwarmFaultTolerance
from app.core.swarm.swarm_orchestrator import SwarmOrchestrator


# ── Model Testleri ──────────────────────────────────────────────

class TestSwarmModels:
    """Swarm model testleri."""

    def test_swarm_state_values(self):
        assert SwarmState.FORMING == "forming"
        assert SwarmState.ACTIVE == "active"
        assert SwarmState.WORKING == "working"
        assert SwarmState.CONVERGING == "converging"
        assert SwarmState.DISSOLVED == "dissolved"

    def test_pheromone_type_values(self):
        assert PheromoneType.ATTRACTION == "attraction"
        assert PheromoneType.REPULSION == "repulsion"
        assert PheromoneType.TRAIL == "trail"
        assert PheromoneType.ALARM == "alarm"
        assert PheromoneType.SUCCESS == "success"

    def test_vote_type_values(self):
        assert VoteType.MAJORITY == "majority"
        assert VoteType.UNANIMOUS == "unanimous"
        assert VoteType.WEIGHTED == "weighted"
        assert VoteType.QUORUM == "quorum"

    def test_auction_state_values(self):
        assert AuctionState.OPEN == "open"
        assert AuctionState.BIDDING == "bidding"
        assert AuctionState.CLOSED == "closed"
        assert AuctionState.AWARDED == "awarded"
        assert AuctionState.CANCELLED == "cancelled"

    def test_fault_action_values(self):
        assert FaultAction.REASSIGN == "reassign"
        assert FaultAction.RETRY == "retry"
        assert FaultAction.ESCALATE == "escalate"
        assert FaultAction.HEAL == "heal"

    def test_balance_strategy_values(self):
        assert BalanceStrategy.WORK_STEALING == "work_stealing"
        assert BalanceStrategy.ROUND_ROBIN == "round_robin"
        assert BalanceStrategy.LEAST_LOADED == "least_loaded"

    def test_swarm_info_defaults(self):
        s = SwarmInfo(name="test")
        assert s.swarm_id
        assert s.state == SwarmState.FORMING
        assert s.members == []
        assert s.min_size == 2

    def test_pheromone_marker_defaults(self):
        m = PheromoneMarker(source_agent="a1", location="loc1")
        assert m.marker_id
        assert m.pheromone_type == PheromoneType.TRAIL
        assert m.intensity == 1.0

    def test_vote_session_defaults(self):
        v = VoteSession(topic="test")
        assert v.session_id
        assert v.vote_type == VoteType.MAJORITY
        assert not v.resolved

    def test_auction_record_defaults(self):
        a = AuctionRecord(task_id="t1")
        assert a.auction_id
        assert a.state == AuctionState.OPEN
        assert a.bids == {}

    def test_fault_event_defaults(self):
        f = FaultEvent(agent_id="a1")
        assert f.event_id
        assert f.action_taken == FaultAction.REASSIGN
        assert not f.resolved

    def test_swarm_snapshot_defaults(self):
        s = SwarmSnapshot()
        assert s.total_swarms == 0
        assert s.health_score == 1.0

    def test_pheromone_intensity_bounds(self):
        m = PheromoneMarker(intensity=0.5)
        assert m.intensity == 0.5

    def test_swarm_snapshot_health_bounds(self):
        s = SwarmSnapshot(health_score=0.75)
        assert s.health_score == 0.75


# ── SwarmCoordinator Testleri ───────────────────────────────────

class TestSwarmCoordinator:
    """Suru koordinatoru testleri."""

    def test_create_swarm(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test", goal="Arastir")
        assert swarm.name == "Test"
        assert swarm.state == SwarmState.FORMING

    def test_join_swarm(self):
        sc = SwarmCoordinator(min_size=2)
        swarm = sc.create_swarm("Test")
        assert sc.join_swarm(swarm.swarm_id, "a1") is True
        assert sc.join_swarm(swarm.swarm_id, "a2") is True
        assert swarm.state == SwarmState.ACTIVE

    def test_join_sets_leader(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        assert swarm.leader_id == "a1"

    def test_join_duplicate(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        assert sc.join_swarm(swarm.swarm_id, "a1") is False

    def test_join_max_size(self):
        sc = SwarmCoordinator(max_size=2)
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        sc.join_swarm(swarm.swarm_id, "a2")
        assert sc.join_swarm(swarm.swarm_id, "a3") is False

    def test_leave_swarm(self):
        sc = SwarmCoordinator(min_size=2)
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        sc.join_swarm(swarm.swarm_id, "a2")
        assert sc.leave_swarm(swarm.swarm_id, "a2") is True
        assert len(swarm.members) == 1

    def test_leave_leader_reassigns(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        sc.join_swarm(swarm.swarm_id, "a2")
        sc.leave_swarm(swarm.swarm_id, "a1")
        assert swarm.leader_id == "a2"

    def test_set_goal(self):
        sc = SwarmCoordinator(min_size=1)
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        sc.set_goal(swarm.swarm_id, "New Goal")
        assert swarm.goal == "New Goal"
        assert swarm.state == SwarmState.WORKING

    def test_dissolve_swarm(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        assert sc.dissolve_swarm(swarm.swarm_id) is True
        assert swarm.state == SwarmState.DISSOLVED
        assert len(swarm.members) == 0

    def test_get_agent_swarm(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        found = sc.get_agent_swarm("a1")
        assert found is not None
        assert found.swarm_id == swarm.swarm_id

    def test_elect_leader(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        sc.join_swarm(swarm.swarm_id, "a2")
        assert sc.elect_leader(swarm.swarm_id, "a2") is True
        assert swarm.leader_id == "a2"

    def test_list_swarms(self):
        sc = SwarmCoordinator()
        sc.create_swarm("S1")
        sc.create_swarm("S2")
        assert len(sc.list_swarms()) == 2

    def test_distribute_goal(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.join_swarm(swarm.swarm_id, "a1")
        sc.join_swarm(swarm.swarm_id, "a2")
        dist = sc.distribute_goal(swarm.swarm_id, ["g1", "g2", "g3"])
        assert len(dist) == 2  # 2 agents

    def test_swarm_count(self):
        sc = SwarmCoordinator()
        sc.create_swarm("S1")
        assert sc.swarm_count == 1

    def test_join_dissolved(self):
        sc = SwarmCoordinator()
        swarm = sc.create_swarm("Test")
        sc.dissolve_swarm(swarm.swarm_id)
        assert sc.join_swarm(swarm.swarm_id, "a1") is False

    def test_agent_switches_swarm(self):
        sc = SwarmCoordinator()
        s1 = sc.create_swarm("S1")
        s2 = sc.create_swarm("S2")
        sc.join_swarm(s1.swarm_id, "a1")
        sc.join_swarm(s2.swarm_id, "a1")
        assert "a1" not in s1.members
        assert "a1" in s2.members


# ── PheromoneSystem Testleri ────────────────────────────────────

class TestPheromoneSystem:
    """Feromon sistemi testleri."""

    def test_leave_marker(self):
        ps = PheromoneSystem()
        m = ps.leave_marker("a1", "loc1", PheromoneType.TRAIL, 0.8)
        assert m.source_agent == "a1"
        assert m.intensity == 0.8
        assert ps.total_markers == 1

    def test_get_markers_at(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1", PheromoneType.TRAIL)
        ps.leave_marker("a2", "loc1", PheromoneType.ALARM)
        markers = ps.get_markers_at("loc1")
        assert len(markers) == 2

    def test_get_markers_by_type(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1", PheromoneType.TRAIL)
        ps.leave_marker("a2", "loc1", PheromoneType.ALARM)
        trails = ps.get_markers_at("loc1", PheromoneType.TRAIL)
        assert len(trails) == 1

    def test_strongest_trail(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1", PheromoneType.TRAIL, 0.3)
        ps.leave_marker("a2", "loc1", PheromoneType.TRAIL, 0.9)
        strongest = ps.get_strongest_trail("loc1")
        assert strongest is not None
        assert strongest.intensity == 0.9

    def test_reinforce_marker(self):
        ps = PheromoneSystem()
        m = ps.leave_marker("a1", "loc1", intensity=0.5)
        ps.reinforce_marker(m.marker_id, boost=0.3)
        updated = ps.get_markers_at("loc1")[0]
        assert updated.intensity == pytest.approx(0.8)

    def test_decay_all(self):
        ps = PheromoneSystem(decay_rate=0.5, min_intensity=0.1)
        ps.leave_marker("a1", "loc1", intensity=0.15)
        removed = ps.decay_all()
        assert removed >= 1

    def test_decay_preserves_strong(self):
        ps = PheromoneSystem(decay_rate=0.1)
        ps.leave_marker("a1", "loc1", intensity=1.0)
        ps.decay_all()
        markers = ps.get_markers_at("loc1")
        assert len(markers) == 1
        assert markers[0].intensity == pytest.approx(0.9)

    def test_broadcast_signal(self):
        ps = PheromoneSystem()
        count = ps.broadcast_signal("a1", ["l1", "l2", "l3"], PheromoneType.ALARM)
        assert count == 3
        assert ps.total_markers == 3

    def test_attraction_score_positive(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1", PheromoneType.ATTRACTION, 0.8)
        score = ps.get_attraction_score("loc1")
        assert score > 0

    def test_attraction_score_negative(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1", PheromoneType.REPULSION, 0.8)
        score = ps.get_attraction_score("loc1")
        assert score < 0

    def test_get_locations_by_type(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1", PheromoneType.ALARM)
        ps.leave_marker("a2", "loc2", PheromoneType.ALARM)
        locs = ps.get_locations_by_type(PheromoneType.ALARM)
        assert len(locs) == 2

    def test_clear_location(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1")
        ps.leave_marker("a2", "loc1")
        removed = ps.clear_location("loc1")
        assert removed == 2
        assert ps.total_markers == 0

    def test_active_locations(self):
        ps = PheromoneSystem()
        ps.leave_marker("a1", "loc1")
        ps.leave_marker("a2", "loc2")
        assert ps.active_locations == 2


# ── CollectiveMemory Testleri ───────────────────────────────────

class TestCollectiveMemory:
    """Kolektif hafiza testleri."""

    def test_store_and_retrieve(self):
        cm = CollectiveMemory()
        cm.store("key1", "value1", "a1")
        assert cm.retrieve("key1") == "value1"

    def test_retrieve_nonexistent(self):
        cm = CollectiveMemory()
        assert cm.retrieve("nonexistent") is None

    def test_retrieve_with_confidence(self):
        cm = CollectiveMemory()
        cm.store("key1", "val1", confidence=0.9)
        value, conf = cm.retrieve_with_confidence("key1")
        assert value == "val1"
        assert conf == 0.9

    def test_delete(self):
        cm = CollectiveMemory()
        cm.store("key1", "val1")
        assert cm.delete("key1") is True
        assert cm.retrieve("key1") is None

    def test_delete_nonexistent(self):
        cm = CollectiveMemory()
        assert cm.delete("nonexistent") is False

    def test_search(self):
        cm = CollectiveMemory()
        cm.store("market_trend", "up")
        cm.store("market_price", 100)
        cm.store("weather", "sunny")
        results = cm.search("market")
        assert len(results) == 2

    def test_merge_new(self):
        cm = CollectiveMemory()
        count = cm.merge({"k1": "v1", "k2": "v2"}, "a1")
        assert count == 2
        assert cm.size == 2

    def test_merge_conflict_overwrite(self):
        cm = CollectiveMemory()
        cm.store("k1", "old")
        count = cm.merge({"k1": "new"}, conflict_strategy="overwrite")
        assert count == 1
        assert cm.retrieve("k1") == "new"

    def test_vote_on_fact(self):
        cm = CollectiveMemory()
        winner = cm.vote_on_fact("color", {"a1": "blue", "a2": "blue", "a3": "red"})
        assert winner == "blue"

    def test_get_contributors(self):
        cm = CollectiveMemory()
        cm.store("k1", "v1", "a1")
        cm.store("k1", "v2", "a2")
        contribs = cm.get_contributors("k1")
        assert "a1" in contribs
        assert "a2" in contribs

    def test_get_high_confidence(self):
        cm = CollectiveMemory()
        cm.store("high", "val", confidence=0.95)
        cm.store("low", "val", confidence=0.3)
        high = cm.get_high_confidence(0.8)
        assert "high" in high
        assert "low" not in high

    def test_size_and_avg_confidence(self):
        cm = CollectiveMemory()
        cm.store("k1", "v1", confidence=0.8)
        cm.store("k2", "v2", confidence=0.6)
        assert cm.size == 2
        assert cm.avg_confidence == pytest.approx(0.7)


# ── VotingSystem Testleri ───────────────────────────────────────

class TestVotingSystem:
    """Oylama sistemi testleri."""

    def test_create_session(self):
        vs = VotingSystem()
        s = vs.create_session("Topic", ["A", "B"], VoteType.MAJORITY)
        assert s.topic == "Topic"
        assert len(s.options) == 2

    def test_cast_vote(self):
        vs = VotingSystem()
        s = vs.create_session("T", ["A", "B"])
        assert vs.cast_vote(s.session_id, "a1", "A") is True

    def test_cast_invalid_choice(self):
        vs = VotingSystem()
        s = vs.create_session("T", ["A", "B"])
        assert vs.cast_vote(s.session_id, "a1", "C") is False

    def test_resolve_majority(self):
        vs = VotingSystem(default_threshold=0.5)
        s = vs.create_session("T", ["A", "B"])
        vs.cast_vote(s.session_id, "a1", "A")
        vs.cast_vote(s.session_id, "a2", "A")
        vs.cast_vote(s.session_id, "a3", "B")
        winner = vs.resolve(s.session_id)
        assert winner == "A"

    def test_resolve_unanimous_success(self):
        vs = VotingSystem()
        s = vs.create_session("T", ["A", "B"], VoteType.UNANIMOUS)
        vs.cast_vote(s.session_id, "a1", "A")
        vs.cast_vote(s.session_id, "a2", "A")
        winner = vs.resolve(s.session_id)
        assert winner == "A"

    def test_resolve_unanimous_fail(self):
        vs = VotingSystem()
        s = vs.create_session("T", ["A", "B"], VoteType.UNANIMOUS)
        vs.cast_vote(s.session_id, "a1", "A")
        vs.cast_vote(s.session_id, "a2", "B")
        winner = vs.resolve(s.session_id)
        assert winner == ""

    def test_resolve_weighted(self):
        vs = VotingSystem()
        s = vs.create_session(
            "T", ["A", "B"], VoteType.WEIGHTED,
            weights={"a1": 10.0, "a2": 1.0},
        )
        vs.cast_vote(s.session_id, "a1", "A")
        vs.cast_vote(s.session_id, "a2", "B")
        winner = vs.resolve(s.session_id)
        assert winner == "A"

    def test_quorum_not_met(self):
        vs = VotingSystem()
        s = vs.create_session("T", ["A", "B"], quorum=3)
        vs.cast_vote(s.session_id, "a1", "A")
        winner = vs.resolve(s.session_id)
        assert winner == ""

    def test_veto(self):
        vs = VotingSystem()
        vs.grant_veto("a1")
        s = vs.create_session("T", ["A", "B"])
        vs.cast_vote(s.session_id, "a1", "VETO:B")
        vs.cast_vote(s.session_id, "a2", "A")
        winner = vs.resolve(s.session_id)
        assert winner == ""

    def test_get_results(self):
        vs = VotingSystem()
        s = vs.create_session("T", ["A", "B"])
        vs.cast_vote(s.session_id, "a1", "A")
        vs.cast_vote(s.session_id, "a2", "B")
        results = vs.get_results(s.session_id)
        assert results["total_votes"] == 2

    def test_active_sessions(self):
        vs = VotingSystem()
        vs.create_session("T1", ["A", "B"])
        vs.create_session("T2", ["C", "D"])
        assert vs.active_sessions == 2

    def test_revoke_veto(self):
        vs = VotingSystem()
        vs.grant_veto("a1")
        vs.revoke_veto("a1")
        assert vs.veto_holder_count == 0


# ── TaskAuction Testleri ────────────────────────────────────────

class TestTaskAuction:
    """Gorev acik artirma testleri."""

    def test_create_auction(self):
        ta = TaskAuction()
        a = ta.create_auction("t1", "Test task")
        assert a.task_id == "t1"
        assert a.state == AuctionState.OPEN

    def test_place_bid(self):
        ta = TaskAuction()
        a = ta.create_auction("t1")
        assert ta.place_bid(a.auction_id, "a1", 0.8) is True
        assert a.state == AuctionState.BIDDING

    def test_place_bid_capability_check(self):
        ta = TaskAuction()
        ta.register_agent("a1", ["search"])
        ta.register_agent("a2", ["execute"])
        a = ta.create_auction("t1", required_capabilities=["search"])
        assert ta.place_bid(a.auction_id, "a1", 0.8) is True
        assert ta.place_bid(a.auction_id, "a2", 0.9) is False

    def test_close_auction(self):
        ta = TaskAuction()
        a = ta.create_auction("t1")
        ta.place_bid(a.auction_id, "a1", 0.5)
        ta.place_bid(a.auction_id, "a2", 0.9)
        winner = ta.close_auction(a.auction_id)
        assert winner == "a2"
        assert a.state == AuctionState.AWARDED

    def test_close_empty_auction(self):
        ta = TaskAuction()
        a = ta.create_auction("t1")
        winner = ta.close_auction(a.auction_id)
        assert winner == ""
        assert a.state == AuctionState.CANCELLED

    def test_fairness_bonus(self):
        ta = TaskAuction()
        # a1 has won before
        a1 = ta.create_auction("t1")
        ta.place_bid(a1.auction_id, "a1", 0.9)
        ta.close_auction(a1.auction_id)

        # New auction, similar bids
        a2 = ta.create_auction("t2")
        ta.place_bid(a2.auction_id, "a1", 0.6)
        ta.place_bid(a2.auction_id, "a2", 0.6)
        winner = ta.close_auction(a2.auction_id, fairness_weight=0.5)
        assert winner == "a2"  # a2 gets fairness bonus

    def test_cancel_auction(self):
        ta = TaskAuction()
        a = ta.create_auction("t1")
        assert ta.cancel_auction(a.auction_id) is True
        assert a.state == AuctionState.CANCELLED

    def test_get_open_auctions(self):
        ta = TaskAuction()
        ta.create_auction("t1")
        ta.create_auction("t2")
        assert len(ta.get_open_auctions()) == 2

    def test_get_agent_wins(self):
        ta = TaskAuction()
        a = ta.create_auction("t1")
        ta.place_bid(a.auction_id, "a1", 1.0)
        ta.close_auction(a.auction_id)
        assert ta.get_agent_wins("a1") == 1

    def test_get_statistics(self):
        ta = TaskAuction()
        ta.register_agent("a1", ["cap1"])
        ta.create_auction("t1")
        stats = ta.get_statistics()
        assert stats["total_auctions"] == 1
        assert stats["registered_agents"] == 1


# ── EmergentBehavior Testleri ───────────────────────────────────

class TestEmergentBehavior:
    """Ortaya cikan davranis testleri."""

    def test_record_action(self):
        eb = EmergentBehavior()
        eb.record_action("a1", "search")
        assert eb.tracked_agents == 1

    def test_detect_convergent_pattern(self):
        eb = EmergentBehavior()
        for agent in ["a1", "a2", "a3"]:
            for _ in range(5):
                eb.record_action(agent, "search")
        patterns = eb.detect_patterns()
        convergent = [p for p in patterns if p["type"] == "convergent_behavior"]
        assert len(convergent) >= 1

    def test_detect_sequence_pattern(self):
        eb = EmergentBehavior()
        for agent in ["a1", "a2"]:
            eb.record_action(agent, "analyze")
            eb.record_action(agent, "report")
        patterns = eb.detect_patterns()
        sequences = [p for p in patterns if p["type"] == "sequence_pattern"]
        assert len(sequences) >= 1

    def test_detect_synergy(self):
        eb = EmergentBehavior()
        synergies = eb.detect_synergy(
            [("a1", "a2")],
            {"a1": 5.0, "a2": 5.0, "a1+a2": 15.0},
        )
        assert len(synergies) == 1
        assert synergies[0]["synergy_ratio"] > 1.0

    def test_no_synergy(self):
        eb = EmergentBehavior()
        synergies = eb.detect_synergy(
            [("a1", "a2")],
            {"a1": 5.0, "a2": 5.0, "a1+a2": 8.0},
        )
        assert len(synergies) == 0

    def test_register_behavior(self):
        eb = EmergentBehavior()
        eb.register_behavior("rush", trigger_conditions={"load": 0.9})
        assert eb.behavior_count == 1

    def test_check_behavior_trigger(self):
        eb = EmergentBehavior()
        eb.register_behavior("rush", trigger_conditions={"load": 0.9})
        assert eb.check_behavior_trigger("rush", {"load": 0.95}) is True
        assert eb.check_behavior_trigger("rush", {"load": 0.5}) is False

    def test_self_organization_score(self):
        eb = EmergentBehavior()
        for agent in ["a1", "a2", "a3"]:
            eb.record_action(agent, "search")
            eb.record_action(agent, "analyze")
        eb.detect_patterns()
        score = eb.get_self_organization_score()
        assert score >= 0

    def test_collective_intelligence_score(self):
        eb = EmergentBehavior()
        ci = eb.get_collective_intelligence_score(
            {"a1": 5.0, "a2": 5.0}, 15.0,
        )
        assert ci == 3.0

    def test_collective_intelligence_zero(self):
        eb = EmergentBehavior()
        ci = eb.get_collective_intelligence_score({}, 10.0)
        assert ci == 0.0


# ── SwarmLoadBalancer Testleri ──────────────────────────────────

class TestSwarmLoadBalancer:
    """Yuk dengeleyici testleri."""

    def test_register_and_assign(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.register_agent("a2")
        assigned = lb.assign_task("t1")
        assert assigned in ("a1", "a2")

    def test_least_loaded(self):
        lb = SwarmLoadBalancer(BalanceStrategy.LEAST_LOADED)
        lb.register_agent("a1")
        lb.register_agent("a2")
        lb.assign_task("t1")
        lb.assign_task("t2", preferred_agent="a1")
        assigned = lb.assign_task("t3")
        assert assigned == "a2"

    def test_complete_task(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.assign_task("t1")
        assert lb.complete_task("a1", "t1") is True
        assert lb.total_tasks == 0

    def test_work_stealing(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.register_agent("a2")
        lb.assign_task("t1", preferred_agent="a1")
        lb.assign_task("t2", preferred_agent="a1")
        result = lb.steal_work("a2")
        assert result["success"] is True
        assert result["from_agent"] == "a1"

    def test_work_stealing_nothing_to_steal(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.register_agent("a2")
        result = lb.steal_work("a2")
        assert result["success"] is False

    def test_detect_bottlenecks(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1", capacity=1.0)
        for i in range(10):
            lb.assign_task(f"t{i}", preferred_agent="a1")
        bottlenecks = lb.detect_bottlenecks(threshold=0.5)
        assert len(bottlenecks) >= 1

    def test_rebalance(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.register_agent("a2")
        for i in range(5):
            lb.assign_task(f"t{i}", preferred_agent="a1")
        transfers = lb.rebalance()
        assert len(transfers) >= 1

    def test_get_load_distribution(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.register_agent("a2")
        dist = lb.get_load_distribution()
        assert "a1" in dist
        assert "a2" in dist

    def test_fairness_index(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.register_agent("a2")
        idx = lb.get_fairness_index()
        assert idx == 1.0  # Both at 0

    def test_unregister_returns_tasks(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        lb.assign_task("t1", preferred_agent="a1")
        tasks = lb.unregister_agent("a1")
        assert "t1" in tasks

    def test_avg_load(self):
        lb = SwarmLoadBalancer()
        lb.register_agent("a1")
        assert lb.avg_load == 0.0


# ── SwarmFaultTolerance Testleri ────────────────────────────────

class TestSwarmFaultTolerance:
    """Hata toleransi testleri."""

    def test_report_failure(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1", ["t1"])
        event = ft.report_failure("a1", "t1", "timeout")
        assert event.agent_id == "a1"
        assert ft.total_events == 1

    def test_reassign_task(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1", ["t1"])
        ft.register_agent("a2")
        ft.report_failure("a1", "t1")
        assigned = ft.reassign_task("t1", "a1", ["a1", "a2"])
        assert assigned == "a2"

    def test_reassign_to_backup(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1", ["t1"])
        ft.register_agent("a2")
        ft.set_backup("a1", "a2")
        ft.report_failure("a1", "t1")
        assigned = ft.reassign_task("t1", "a1", ["a2"])
        assert assigned == "a2"

    def test_retry_task(self):
        ft = SwarmFaultTolerance(max_retries=2)
        ft.register_agent("a1")
        assert ft.retry_task("a1", "t1") is True
        assert ft.retry_task("a1", "t1") is True
        assert ft.retry_task("a1", "t1") is False

    def test_heal_agent(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1")
        ft.report_failure("a1")
        assert "a1" in ft.get_failed_agents()
        assert ft.heal_agent("a1") is True
        assert "a1" in ft.get_healthy_agents()

    def test_get_events_filtered(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1")
        ft.register_agent("a2")
        ft.report_failure("a1", "t1")
        ft.report_failure("a2", "t2")
        events = ft.get_events(agent_id="a1")
        assert len(events) == 1

    def test_redundancy_coverage(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1")
        ft.register_agent("a2")
        ft.set_backup("a1", "a2")
        coverage = ft.get_redundancy_coverage()
        assert coverage == 0.5

    def test_healthy_ratio(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1")
        ft.register_agent("a2")
        ft.report_failure("a1")
        assert ft.healthy_ratio == 0.5

    def test_critical_escalation(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1")
        event = ft.report_failure("a1", "t1", "critical")
        assert event.action_taken == FaultAction.ESCALATE

    def test_get_backup(self):
        ft = SwarmFaultTolerance()
        ft.register_agent("a1")
        ft.register_agent("a2")
        ft.set_backup("a1", "a2")
        assert ft.get_backup("a1") == "a2"


# ── SwarmOrchestrator Testleri ──────────────────────────────────

class TestSwarmOrchestrator:
    """Suru orkestratoru testleri."""

    def test_create_mission(self):
        orch = SwarmOrchestrator()
        result = orch.create_mission("M1", "Research", ["a1", "a2", "a3"])
        assert result["success"] is True
        assert result["members"] == 3

    def test_assign_task_load_balance(self):
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Work", ["a1", "a2"])
        result = orch.assign_task(
            orch.coordinator.list_swarms()[0].swarm_id,
            "t1", "Test task",
        )
        assert result["success"] is True
        assert result["method"] == "load_balance"

    def test_assign_task_auction(self):
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Work", ["a1", "a2"])
        swarm_id = orch.coordinator.list_swarms()[0].swarm_id
        result = orch.assign_task(swarm_id, "t1", use_auction=True)
        assert result["success"] is True
        assert result["method"] == "auction"

    def test_vote_on_decision(self):
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Decide", ["a1", "a2", "a3"])
        swarm_id = orch.coordinator.list_swarms()[0].swarm_id
        result = orch.vote_on_decision(
            swarm_id, "Color", ["blue", "red"],
            {"a1": "blue", "a2": "blue", "a3": "red"},
        )
        assert result["winner"] == "blue"

    def test_handle_failure(self):
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Work", ["a1", "a2"])
        result = orch.handle_failure("a1", "t1", "timeout")
        assert result["success"] is True

    def test_share_knowledge(self):
        orch = SwarmOrchestrator()
        assert orch.share_knowledge("a1", "fact1", "data1") is True
        assert orch.memory.retrieve("fact1") == "data1"

    def test_get_collective_knowledge(self):
        orch = SwarmOrchestrator()
        orch.share_knowledge("a1", "k1", "v1", 0.9)
        knowledge = orch.get_collective_knowledge()
        assert "k1" in knowledge

    def test_optimize(self):
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Work", ["a1", "a2"])
        result = orch.optimize()
        assert "rebalanced" in result
        assert "decayed_markers" in result

    def test_dissolve_mission(self):
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Work", ["a1", "a2"])
        swarm_id = orch.coordinator.list_swarms()[0].swarm_id
        assert orch.dissolve_mission(swarm_id) is True

    def test_get_snapshot(self):
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Work", ["a1", "a2"])
        snap = orch.get_snapshot()
        assert snap.total_swarms >= 1
        assert snap.total_members >= 2
        assert snap.health_score > 0

    def test_subsystem_access(self):
        orch = SwarmOrchestrator()
        assert orch.coordinator is not None
        assert orch.pheromones is not None
        assert orch.memory is not None
        assert orch.voting is not None
        assert orch.auction is not None
        assert orch.emergent is not None
        assert orch.balancer is not None
        assert orch.fault is not None

    def test_assign_task_nonexistent_swarm(self):
        orch = SwarmOrchestrator()
        result = orch.assign_task("nonexistent", "t1")
        assert result["success"] is False


# ── Entegrasyon Testleri ────────────────────────────────────────

class TestSwarmIntegration:
    """Entegrasyon testleri."""

    def test_full_mission_lifecycle(self):
        """Tam gorev yasam dongusu."""
        orch = SwarmOrchestrator(min_swarm_size=2)

        # Gorev olustur
        result = orch.create_mission("Research", "Find trends", ["a1", "a2", "a3"])
        swarm_id = result["swarm_id"]
        assert result["success"]

        # Gorev ata
        assign = orch.assign_task(swarm_id, "t1", "Search web")
        assert assign["success"]

        # Bilgi paylas
        orch.share_knowledge("a1", "trend:ai", "growing", 0.9)

        # Oylama
        vote = orch.vote_on_decision(
            swarm_id, "focus_area",
            ["ai", "blockchain", "iot"],
            {"a1": "ai", "a2": "ai", "a3": "blockchain"},
        )
        assert vote["winner"] == "ai"

        # Snapshot
        snap = orch.get_snapshot()
        assert snap.active_swarms >= 1

        # Dagit
        orch.dissolve_mission(swarm_id)
        snap2 = orch.get_snapshot()
        assert snap2.active_swarms == 0

    def test_fault_recovery_flow(self):
        """Hata kurtarma akisi."""
        orch = SwarmOrchestrator()
        orch.create_mission("Work", "Build", ["a1", "a2", "a3"])

        # a1 basarisiz
        result = orch.handle_failure("a1", "t1", "timeout")
        assert result["success"]

        # Optimize ile iyilestir
        opt = orch.optimize()
        assert "a1" in opt["healed"]

    def test_auction_flow(self):
        """Acik artirma akisi."""
        orch = SwarmOrchestrator()
        orch.create_mission("Team", "Deploy", ["a1", "a2"])
        swarm_id = orch.coordinator.list_swarms()[0].swarm_id

        # Artirma olustur
        result = orch.assign_task(swarm_id, "t1", use_auction=True)
        auction_id = result["auction_id"]

        # Teklifler
        orch.auction.place_bid(auction_id, "a1", 0.7)
        orch.auction.place_bid(auction_id, "a2", 0.9)

        # Kapat
        winner = orch.auction.close_auction(auction_id)
        assert winner == "a2"

    def test_pheromone_guided_behavior(self):
        """Feromon yonlendirmeli davranis."""
        orch = SwarmOrchestrator(pheromone_decay_rate=0.1)

        # Basari feromon birak
        orch.pheromones.leave_marker("a1", "path:A", PheromoneType.SUCCESS, 0.9)
        orch.pheromones.leave_marker("a2", "path:B", PheromoneType.REPULSION, 0.8)

        # Cekim kontrol
        score_a = orch.pheromones.get_attraction_score("path:A")
        score_b = orch.pheromones.get_attraction_score("path:B")
        assert score_a > score_b

    def test_collective_decision_with_knowledge(self):
        """Kolektif bilgi ile karar alma."""
        orch = SwarmOrchestrator()

        # Bilgi topla
        orch.share_knowledge("a1", "market:price", 100, 0.8)
        orch.share_knowledge("a2", "market:price", 105, 0.9)
        orch.share_knowledge("a3", "market:trend", "up", 0.95)

        # Bilgi sorgula
        market_data = orch.get_collective_knowledge("market")
        assert len(market_data) >= 1

    def test_load_balance_with_failure(self):
        """Yuk dengeleme + hata toleransi."""
        orch = SwarmOrchestrator()
        orch.create_mission("M1", "Work", ["a1", "a2", "a3"])

        # Gorev ata
        for i in range(5):
            orch.assign_task(
                orch.coordinator.list_swarms()[0].swarm_id,
                f"task-{i}",
            )

        # Bir agent basarisiz
        orch.handle_failure("a1", "task-0")

        # Optimize
        opt = orch.optimize()
        assert isinstance(opt, dict)
