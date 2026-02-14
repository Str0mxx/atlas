"""ATLAS Distributed System Coordination testleri."""

import time

from app.models.distributed import (
    NodeStatus,
    LockState,
    ConsensusType,
    ReplicationMode,
    PartitionStrategy,
    QueuePriority,
    NodeRecord,
    LockRecord,
    ReplicationRecord,
    DistributedSnapshot,
)
from app.core.distributed.leader_election import (
    LeaderElection,
)
from app.core.distributed.distributed_lock import (
    DistributedLock,
)
from app.core.distributed.consensus_manager import (
    ConsensusManager,
)
from app.core.distributed.service_discovery import (
    ServiceDiscovery,
)
from app.core.distributed.partition_manager import (
    PartitionManager,
)
from app.core.distributed.replication_manager import (
    ReplicationManager,
)
from app.core.distributed.cluster_monitor import (
    ClusterMonitor,
)
from app.core.distributed.message_queue import (
    DistributedQueue,
)
from app.core.distributed.distributed_orchestrator import (
    DistributedOrchestrator,
)
from app.config import Settings


# ---- Model Testleri ----

class TestDistributedModels:
    def test_node_status_enum(self):
        assert NodeStatus.ACTIVE == "active"
        assert NodeStatus.INACTIVE == "inactive"
        assert NodeStatus.SUSPECT == "suspect"
        assert NodeStatus.FAILED == "failed"
        assert NodeStatus.JOINING == "joining"
        assert NodeStatus.LEAVING == "leaving"

    def test_lock_state_enum(self):
        assert LockState.FREE == "free"
        assert LockState.ACQUIRED == "acquired"
        assert LockState.WAITING == "waiting"
        assert LockState.EXPIRED == "expired"
        assert LockState.DEADLOCKED == "deadlocked"

    def test_consensus_type_enum(self):
        assert ConsensusType.MAJORITY == "majority"
        assert ConsensusType.UNANIMITY == "unanimity"
        assert ConsensusType.QUORUM == "quorum"
        assert ConsensusType.BYZANTINE == "byzantine"
        assert ConsensusType.RAFT == "raft"

    def test_replication_mode_enum(self):
        assert ReplicationMode.SYNC == "sync"
        assert ReplicationMode.ASYNC == "async"
        assert ReplicationMode.SEMI_SYNC == "semi_sync"
        assert ReplicationMode.EVENTUAL == "eventual"

    def test_partition_strategy_enum(self):
        assert PartitionStrategy.HASH == "hash"
        assert PartitionStrategy.RANGE == "range"
        assert PartitionStrategy.CONSISTENT_HASH == "consistent_hash"

    def test_queue_priority_enum(self):
        assert QueuePriority.CRITICAL == "critical"
        assert QueuePriority.HIGH == "high"
        assert QueuePriority.NORMAL == "normal"
        assert QueuePriority.LOW == "low"

    def test_node_record_defaults(self):
        r = NodeRecord()
        assert r.node_id
        assert r.status == NodeStatus.ACTIVE
        assert r.host == "localhost"

    def test_lock_record_defaults(self):
        r = LockRecord()
        assert r.lock_id
        assert r.state == LockState.FREE
        assert r.ttl == 30

    def test_replication_record_defaults(self):
        r = ReplicationRecord()
        assert r.replica_id
        assert r.mode == ReplicationMode.ASYNC
        assert r.lag_ms == 0.0

    def test_distributed_snapshot_defaults(self):
        s = DistributedSnapshot()
        assert s.total_nodes == 0
        assert s.active_nodes == 0
        assert s.total_locks == 0


# ---- LeaderElection Testleri ----

class TestLeaderElection:
    def test_init(self):
        le = LeaderElection("n0")
        assert le.node_count == 1
        assert le.leader_id is None

    def test_add_node(self):
        le = LeaderElection("n0")
        le.add_node("n1", priority=5)
        assert le.node_count == 2

    def test_remove_node(self):
        le = LeaderElection("n0")
        le.add_node("n1")
        assert le.remove_node("n1") is True
        assert le.node_count == 1

    def test_remove_node_not_found(self):
        le = LeaderElection("n0")
        assert le.remove_node("x") is False

    def test_elect_bully(self):
        le = LeaderElection("n0")
        le.add_node("n1", priority=10)
        le.add_node("n2", priority=5)
        r = le.elect_bully()
        assert r["leader"] == "n1"
        assert r["algorithm"] == "bully"
        assert le.leader_id == "n1"
        assert le.term == 1

    def test_elect_bully_no_active(self):
        le = LeaderElection("n0")
        le.remove_node("n0")
        r = le.elect_bully()
        assert r["leader"] is None

    def test_elect_raft(self):
        le = LeaderElection("n0")
        le.add_node("n1")
        le.add_node("n2")
        r = le.elect_raft()
        assert r["algorithm"] == "raft"
        assert r["leader"] is not None
        assert r["votes"] >= r["quorum"]

    def test_heartbeat(self):
        le = LeaderElection("n0")
        le.add_node("n1")
        assert le.heartbeat("n1") is True
        assert le.heartbeat("unknown") is False

    def test_check_leader_health_no_leader(self):
        le = LeaderElection("n0")
        r = le.check_leader_health()
        assert r["healthy"] is False
        assert r["reason"] == "no_leader"

    def test_check_leader_health(self):
        le = LeaderElection("n0")
        le.elect_bully()
        le.heartbeat("n0")
        r = le.check_leader_health()
        assert r["healthy"] is True

    def test_detect_split_brain(self):
        le = LeaderElection("n0")
        le.add_node("n1")
        le.add_node("n2")
        r = le.detect_split_brain()
        assert r["total_nodes"] == 3
        assert r["has_quorum"] is True

    def test_failover(self):
        le = LeaderElection("n0")
        le.add_node("n1", priority=10)
        le.elect_bully()
        assert le.leader_id == "n1"
        r = le.failover()
        assert r["old_leader"] == "n1"
        assert r["new_leader"] == "n0"

    def test_election_count(self):
        le = LeaderElection("n0")
        le.elect_bully()
        le.elect_raft()
        assert le.election_count == 2


# ---- DistributedLock Testleri ----

class TestDistributedLock:
    def test_acquire(self):
        dl = DistributedLock()
        r = dl.acquire("res1", "owner1")
        assert r["acquired"] is True
        assert dl.lock_count == 1

    def test_acquire_already_held(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        r = dl.acquire("res1", "owner2")
        assert r["acquired"] is False
        assert r["held_by"] == "owner1"

    def test_acquire_reentrant(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1", reentrant=True)
        r = dl.acquire(
            "res1", "owner1", reentrant=True,
        )
        assert r["acquired"] is True
        assert r["reentrant"] is True
        assert r["reentry_count"] == 2

    def test_release(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        r = dl.release("res1", "owner1")
        assert r["released"] is True
        assert dl.lock_count == 0

    def test_release_not_locked(self):
        dl = DistributedLock()
        r = dl.release("res1", "owner1")
        assert r["released"] is False
        assert r["reason"] == "not_locked"

    def test_release_not_owner(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        r = dl.release("res1", "owner2")
        assert r["released"] is False
        assert r["reason"] == "not_owner"

    def test_release_reentrant(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1", reentrant=True)
        dl.acquire("res1", "owner1", reentrant=True)
        r = dl.release("res1", "owner1")
        assert r["released"] is False
        assert r["reason"] == "reentrant_pending"
        r2 = dl.release("res1", "owner1")
        assert r2["released"] is True

    def test_waiter_promotion(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        dl.acquire("res1", "owner2")
        r = dl.release("res1", "owner1")
        assert r["next_owner"] == "owner2"
        assert dl.lock_count == 1

    def test_detect_deadlock_none(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        r = dl.detect_deadlock()
        assert r["deadlock_detected"] is False

    def test_force_release(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        assert dl.force_release("res1") is True
        assert dl.lock_count == 0

    def test_force_release_not_found(self):
        dl = DistributedLock()
        assert dl.force_release("x") is False

    def test_get_lock_info(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        info = dl.get_lock_info("res1")
        assert info["owner"] == "owner1"
        assert info["resource"] == "res1"

    def test_get_lock_info_none(self):
        dl = DistributedLock()
        assert dl.get_lock_info("x") is None

    def test_waiter_count(self):
        dl = DistributedLock()
        dl.acquire("res1", "owner1")
        dl.acquire("res1", "owner2")
        dl.acquire("res1", "owner3")
        assert dl.waiter_count == 2


# ---- ConsensusManager Testleri ----

class TestConsensusManager:
    def test_add_node(self):
        cm = ConsensusManager()
        cm.add_node("n1", weight=2.0)
        assert cm.node_count == 1

    def test_remove_node(self):
        cm = ConsensusManager()
        cm.add_node("n1")
        assert cm.remove_node("n1") is True
        assert cm.node_count == 0

    def test_remove_node_not_found(self):
        cm = ConsensusManager()
        assert cm.remove_node("x") is False

    def test_calculate_quorum_majority(self):
        cm = ConsensusManager()
        for i in range(5):
            cm.add_node(f"n{i}")
        r = cm.calculate_quorum("majority")
        assert r["needed"] == 3
        assert r["achievable"] is True

    def test_calculate_quorum_unanimity(self):
        cm = ConsensusManager()
        for i in range(3):
            cm.add_node(f"n{i}")
        r = cm.calculate_quorum("unanimity")
        assert r["needed"] == 3

    def test_calculate_quorum_byzantine(self):
        cm = ConsensusManager()
        for i in range(7):
            cm.add_node(f"n{i}")
        r = cm.calculate_quorum("byzantine")
        assert r["needed"] == 5

    def test_propose(self):
        cm = ConsensusManager()
        r = cm.propose("p1", "value1", "n1")
        assert r["status"] == "pending"
        assert cm.proposal_count == 1

    def test_vote(self):
        cm = ConsensusManager()
        cm.add_node("n1")
        cm.add_node("n2")
        cm.propose("p1", "val")
        r = cm.vote("p1", "n1", approve=True)
        assert r["vote"] == "for"
        assert r["total_for"] == 1

    def test_vote_proposal_not_found(self):
        cm = ConsensusManager()
        r = cm.vote("none", "n1")
        assert r["status"] == "error"

    def test_vote_invalid_node(self):
        cm = ConsensusManager()
        cm.propose("p1", "val")
        r = cm.vote("p1", "unknown")
        assert r["status"] == "error"

    def test_vote_already_voted(self):
        cm = ConsensusManager()
        cm.add_node("n1")
        cm.propose("p1", "val")
        cm.vote("p1", "n1")
        r = cm.vote("p1", "n1")
        assert r["reason"] == "already_voted"

    def test_check_consensus_accepted(self):
        cm = ConsensusManager()
        for i in range(3):
            cm.add_node(f"n{i}")
        cm.propose("p1", "val")
        cm.vote("p1", "n0")
        cm.vote("p1", "n1")
        r = cm.check_consensus("p1", "majority")
        assert r["reached"] is True
        assert r["decision"] == "accepted"
        assert cm.decision_count == 1

    def test_check_consensus_rejected(self):
        cm = ConsensusManager()
        for i in range(3):
            cm.add_node(f"n{i}")
        cm.propose("p1", "val")
        cm.vote("p1", "n0", approve=False)
        cm.vote("p1", "n1", approve=False)
        r = cm.check_consensus("p1", "majority")
        assert r["reached"] is True
        assert r["decision"] == "rejected"

    def test_check_consensus_pending(self):
        cm = ConsensusManager()
        for i in range(5):
            cm.add_node(f"n{i}")
        cm.propose("p1", "val")
        cm.vote("p1", "n0")
        r = cm.check_consensus("p1", "majority")
        assert r["reached"] is False

    def test_resolve_conflict_latest(self):
        cm = ConsensusManager()
        r = cm.resolve_conflict(
            ["a", "b", "c"], "latest",
        )
        assert r["winner"] == "c"

    def test_resolve_conflict_first(self):
        cm = ConsensusManager()
        r = cm.resolve_conflict(
            ["a", "b"], "first",
        )
        assert r["winner"] == "a"

    def test_resolve_conflict_majority(self):
        cm = ConsensusManager()
        r = cm.resolve_conflict(
            ["a", "b", "a", "a"], "majority",
        )
        assert r["winner"] == "a"

    def test_resolve_conflict_empty(self):
        cm = ConsensusManager()
        r = cm.resolve_conflict([], "latest")
        assert r["resolved"] is False


# ---- ServiceDiscovery Testleri ----

class TestServiceDiscovery:
    def test_register(self):
        sd = ServiceDiscovery()
        r = sd.register("s1", "api", "host1", 8080)
        assert r["status"] == "registered"
        assert sd.service_count == 1

    def test_deregister(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api")
        assert sd.deregister("s1") is True
        assert sd.service_count == 0

    def test_deregister_not_found(self):
        sd = ServiceDiscovery()
        assert sd.deregister("x") is False

    def test_discover_by_name(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api")
        sd.register("s2", "api")
        sd.register("s3", "web")
        r = sd.discover(name="api")
        assert len(r) == 2

    def test_discover_by_tags(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api", tags=["v1", "prod"])
        sd.register("s2", "api", tags=["v2"])
        r = sd.discover(tags=["v1"])
        assert len(r) == 1

    def test_discover_healthy_only(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api")
        sd.register("s2", "api")
        sd.health_check("s2", healthy=False)
        r = sd.discover(name="api", healthy_only=True)
        assert len(r) == 1

    def test_health_check(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api")
        r = sd.health_check("s1", healthy=False)
        assert r["status"] == "unhealthy"
        assert r["changed"] is True

    def test_health_check_not_found(self):
        sd = ServiceDiscovery()
        r = sd.health_check("x")
        assert r["status"] == "error"

    def test_load_balance_round_robin(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api", "h1", 8001)
        sd.register("s2", "api", "h2", 8002)
        r1 = sd.load_balance("api")
        r2 = sd.load_balance("api")
        ids = {r1["service_id"], r2["service_id"]}
        assert ids == {"s1", "s2"}

    def test_load_balance_no_services(self):
        sd = ServiceDiscovery()
        assert sd.load_balance("api") is None

    def test_resolve_dns(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api", "h1", 8001)
        r = sd.resolve_dns("api")
        assert len(r) == 1
        assert r[0]["host"] == "h1"

    def test_get_service(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api")
        svc = sd.get_service("s1")
        assert svc["name"] == "api"

    def test_healthy_count(self):
        sd = ServiceDiscovery()
        sd.register("s1", "api")
        sd.register("s2", "api")
        sd.health_check("s2", False)
        assert sd.healthy_count == 1


# ---- PartitionManager Testleri ----

class TestPartitionMgr:
    def test_add_node(self):
        pm = PartitionManager()
        pm.add_node("n1")
        assert pm.node_count == 1

    def test_remove_node(self):
        pm = PartitionManager()
        pm.add_node("n1")
        assert pm.remove_node("n1") is True
        assert pm.node_count == 0

    def test_remove_node_not_found(self):
        pm = PartitionManager()
        assert pm.remove_node("x") is False

    def test_create_partition(self):
        pm = PartitionManager()
        pm.add_node("n1")
        r = pm.create_partition("p1", "n1")
        assert r["partition_id"] == "p1"
        assert r["node_id"] == "n1"
        assert pm.partition_count == 1

    def test_create_partition_auto_node(self):
        pm = PartitionManager()
        pm.add_node("n1")
        pm.add_node("n2")
        r = pm.create_partition("p1")
        assert r["node_id"] in ("n1", "n2")

    def test_assign_key(self):
        pm = PartitionManager()
        pm.add_node("n1")
        r = pm.assign_key("user:123")
        assert r["assigned"] is True
        assert r["node_id"] == "n1"

    def test_assign_key_no_nodes(self):
        pm = PartitionManager()
        r = pm.assign_key("key1")
        assert r["assigned"] is False

    def test_lookup_key(self):
        pm = PartitionManager()
        pm.add_node("n1")
        pm.assign_key("k1")
        assert pm.lookup_key("k1") == "n1"

    def test_lookup_key_not_found(self):
        pm = PartitionManager()
        assert pm.lookup_key("x") is None

    def test_rebalance(self):
        pm = PartitionManager()
        pm.add_node("n1")
        pm.assign_key("k1")
        pm.assign_key("k2")
        pm.add_node("n2")
        r = pm.rebalance()
        assert r["total_keys"] == 2
        assert pm.rebalance_count == 1

    def test_rebalance_no_nodes(self):
        pm = PartitionManager()
        r = pm.rebalance()
        assert r["reason"] == "no_nodes"

    def test_recover_partition(self):
        pm = PartitionManager()
        pm.add_node("n1")
        pm.add_node("n2")
        pm.create_partition("p1", "n1")
        r = pm.recover_partition("p1", "n2")
        assert r["status"] == "recovered"
        assert r["new_node"] == "n2"

    def test_recover_partition_not_found(self):
        pm = PartitionManager()
        r = pm.recover_partition("none", "n1")
        assert r["status"] == "error"

    def test_get_partition_map(self):
        pm = PartitionManager()
        pm.add_node("n1")
        pm.create_partition("p1", "n1")
        pm.create_partition("p2", "n1")
        pmap = pm.get_partition_map()
        assert pmap["p1"] == "n1"

    def test_key_count(self):
        pm = PartitionManager()
        pm.add_node("n1")
        pm.assign_key("k1")
        pm.assign_key("k2")
        assert pm.key_count == 2


# ---- ReplicationManager Testleri ----

class TestReplicationMgr:
    def test_add_replica(self):
        rm = ReplicationManager()
        r = rm.add_replica("r1", "n1", "sync", "leader")
        assert r["replica_id"] == "r1"
        assert rm.replica_count == 1

    def test_remove_replica(self):
        rm = ReplicationManager()
        rm.add_replica("r1", "n1")
        assert rm.remove_replica("r1") is True
        assert rm.replica_count == 0

    def test_remove_replica_not_found(self):
        rm = ReplicationManager()
        assert rm.remove_replica("x") is False

    def test_replicate_sync(self):
        rm = ReplicationManager()
        rm.add_replica("r1", "n1", "sync")
        r = rm.replicate("key1", "val1", 1, "sync")
        assert r["synced"] == 1
        assert rm.data_count == 1

    def test_replicate_async(self):
        rm = ReplicationManager()
        rm.add_replica("r1", "n1", "async")
        r = rm.replicate("key1", "val1")
        assert r["synced"] == 1

    def test_read_eventual(self):
        rm = ReplicationManager()
        rm.replicate("k1", "v1")
        r = rm.read("k1", "eventual")
        assert r["found"] is True
        assert r["value"] == "v1"

    def test_read_strong_all_synced(self):
        rm = ReplicationManager()
        rm.add_replica("r1", "n1", "sync")
        rm.replicate("k1", "v1", 1, "sync")
        r = rm.read("k1", "strong")
        assert r["consistent"] is True

    def test_read_not_found(self):
        rm = ReplicationManager()
        r = rm.read("x")
        assert r["found"] is False

    def test_check_lag(self):
        rm = ReplicationManager()
        rm.add_replica("r1", "n1", "async")
        rm.replicate("k1", "v1")
        r = rm.check_lag()
        assert r["replicas"] == 1
        assert r["avg_lag_ms"] >= 0

    def test_detect_conflict(self):
        rm = ReplicationManager()
        r = rm.detect_conflict(
            "k1", "a", "b", 1, 1,
        )
        assert r["conflict"] is True
        assert rm.conflict_count == 1

    def test_detect_no_conflict(self):
        rm = ReplicationManager()
        r = rm.detect_conflict(
            "k1", "a", "a", 1, 1,
        )
        assert r["conflict"] is False

    def test_resolve_conflict(self):
        rm = ReplicationManager()
        rm.detect_conflict("k1", "a", "b", 1, 1)
        r = rm.resolve_conflict("k1")
        assert r["resolved"] is True
        assert r["winner"] == "b"
        assert rm.conflict_count == 0

    def test_resolve_no_conflict(self):
        rm = ReplicationManager()
        r = rm.resolve_conflict("k1")
        assert r["resolved"] is False

    def test_promote_replica(self):
        rm = ReplicationManager()
        rm.add_replica("r1", "n1", role="leader")
        rm.add_replica("r2", "n2", role="follower")
        r = rm.promote_replica("r2")
        assert r["role"] == "leader"
        assert rm.leader == "r2"

    def test_promote_not_found(self):
        rm = ReplicationManager()
        r = rm.promote_replica("x")
        assert r["status"] == "error"

    def test_leader_property(self):
        rm = ReplicationManager()
        rm.add_replica("r1", "n1", role="leader")
        assert rm.leader == "r1"

    def test_leader_none(self):
        rm = ReplicationManager()
        assert rm.leader is None


# ---- ClusterMonitor Testleri ----

class TestClusterMonitor:
    def test_register_node(self):
        cm = ClusterMonitor()
        cm.register_node("n1", "h1", "master")
        assert cm.node_count == 1

    def test_remove_node(self):
        cm = ClusterMonitor()
        cm.register_node("n1")
        assert cm.remove_node("n1") is True
        assert cm.node_count == 0

    def test_update_metrics(self):
        cm = ClusterMonitor()
        cm.register_node("n1")
        r = cm.update_metrics("n1", 0.5, 0.6, 0.3)
        assert r["status"] == "updated"

    def test_update_metrics_alerts(self):
        cm = ClusterMonitor(alert_threshold=0.7)
        cm.register_node("n1")
        r = cm.update_metrics("n1", 0.9, 0.9, 0.9)
        assert r["alerts"] == 3
        assert cm.alert_count == 3

    def test_update_metrics_not_found(self):
        cm = ClusterMonitor()
        r = cm.update_metrics("x", 0.5, 0.5, 0.5)
        assert r["status"] == "error"

    def test_check_health(self):
        cm = ClusterMonitor()
        cm.register_node("n1")
        cm.register_node("n2")
        r = cm.check_health()
        assert r["total_nodes"] == 2
        assert r["active"] == 2
        assert r["healthy"] is True

    def test_get_topology(self):
        cm = ClusterMonitor()
        cm.register_node("n1", role="master")
        cm.register_node("n2", role="worker")
        cm.register_node("n3", role="worker")
        t = cm.get_topology()
        assert t["role_count"]["master"] == 1
        assert t["role_count"]["worker"] == 2

    def test_detect_failures(self):
        cm = ClusterMonitor()
        cm.register_node("n1")
        n = cm.get_node("n1")
        n["last_seen"] = time.time() - 120
        r = cm.detect_failures(timeout=60)
        assert r["failed"] == 1

    def test_add_scaling_rule(self):
        cm = ClusterMonitor()
        r = cm.add_scaling_rule(
            "cpu", 0.8, "scale_up",
        )
        assert r["metric"] == "cpu"

    def test_evaluate_scaling(self):
        cm = ClusterMonitor()
        cm.register_node("n1")
        cm.update_metrics("n1", 0.9, 0.5, 0.3)
        cm.add_scaling_rule("cpu", 0.8, "scale_up")
        r = cm.evaluate_scaling()
        assert r["triggered"] == 1
        assert r["actions"][0]["action"] == "scale_up"

    def test_evaluate_scaling_no_trigger(self):
        cm = ClusterMonitor()
        cm.register_node("n1")
        cm.update_metrics("n1", 0.3, 0.3, 0.3)
        cm.add_scaling_rule("cpu", 0.8, "scale_up")
        r = cm.evaluate_scaling()
        assert r["triggered"] == 0

    def test_active_count(self):
        cm = ClusterMonitor()
        cm.register_node("n1")
        cm.register_node("n2")
        assert cm.active_count == 2


# ---- DistributedQueue Testleri ----

class TestDistQueue:
    def test_create_queue(self):
        q = DistributedQueue()
        r = q.create_queue("tasks")
        assert r["status"] == "created"
        assert q.queue_count == 1

    def test_enqueue(self):
        q = DistributedQueue()
        r = q.enqueue("tasks", {"k": "v"})
        assert r["status"] == "enqueued"
        assert q.total_depth == 1

    def test_enqueue_priority(self):
        q = DistributedQueue()
        q.enqueue("tasks", {"id": "low"}, priority=10)
        q.enqueue("tasks", {"id": "high"}, priority=1)
        msg = q.dequeue("tasks")
        assert msg["data"]["id"] == "high"

    def test_enqueue_dedup(self):
        q = DistributedQueue()
        q.enqueue("tasks", {}, dedup_id="d1")
        msg = q.dequeue("tasks")
        q.ack(msg["message_id"])
        r = q.enqueue("tasks", {}, dedup_id="d1")
        assert r["status"] == "duplicate"

    def test_dequeue(self):
        q = DistributedQueue()
        q.enqueue("tasks", {"x": 1})
        msg = q.dequeue("tasks")
        assert msg["data"]["x"] == 1
        assert q.in_flight_count == 1

    def test_dequeue_empty(self):
        q = DistributedQueue()
        assert q.dequeue("tasks") is None

    def test_ack(self):
        q = DistributedQueue()
        q.enqueue("tasks", {})
        msg = q.dequeue("tasks")
        assert q.ack(msg["message_id"]) is True
        assert q.in_flight_count == 0

    def test_ack_not_found(self):
        q = DistributedQueue()
        assert q.ack("x") is False

    def test_nack_requeue(self):
        q = DistributedQueue(max_retries=3)
        q.enqueue("tasks", {"x": 1})
        msg = q.dequeue("tasks")
        r = q.nack(msg["message_id"])
        assert r["status"] == "requeued"
        assert q.total_depth == 1

    def test_nack_dead_letter(self):
        q = DistributedQueue(max_retries=1)
        q.enqueue("tasks", {"x": 1})
        msg = q.dequeue("tasks")
        r = q.nack(msg["message_id"])
        assert r["status"] == "dead_lettered"
        assert q.dead_letter_count == 1

    def test_nack_not_in_flight(self):
        q = DistributedQueue()
        r = q.nack("x")
        assert r["status"] == "error"

    def test_peek(self):
        q = DistributedQueue()
        q.enqueue("tasks", {"x": 1})
        msg = q.peek("tasks")
        assert msg["data"]["x"] == 1
        assert q.total_depth == 1

    def test_peek_empty(self):
        q = DistributedQueue()
        assert q.peek("tasks") is None

    def test_get_queue_depth(self):
        q = DistributedQueue()
        q.enqueue("tasks", {})
        q.enqueue("tasks", {})
        assert q.get_queue_depth("tasks") == 2

    def test_purge_queue(self):
        q = DistributedQueue()
        q.enqueue("tasks", {})
        q.enqueue("tasks", {})
        count = q.purge_queue("tasks")
        assert count == 2
        assert q.total_depth == 0

    def test_purge_empty(self):
        q = DistributedQueue()
        assert q.purge_queue("tasks") == 0

    def test_retry_dead_letters(self):
        q = DistributedQueue(max_retries=1)
        q.enqueue("tasks", {"x": 1})
        msg = q.dequeue("tasks")
        q.nack(msg["message_id"])
        r = q.retry_dead_letters()
        assert r["retried"] == 1
        assert q.total_depth == 1

    def test_get_stats(self):
        q = DistributedQueue()
        q.enqueue("tasks", {})
        s = q.get_stats()
        assert s["enqueued"] == 1
        assert s["queues"] == 1


# ---- DistributedOrchestrator Testleri ----

class TestDistOrch:
    def test_init(self):
        o = DistributedOrchestrator("n0")
        assert o.election is not None
        assert o.lock is not None
        assert o.consensus is not None

    def test_add_node(self):
        o = DistributedOrchestrator("n0")
        r = o.add_node("n1", "h1", 8001, "worker")
        assert r["status"] == "added"

    def test_remove_node(self):
        o = DistributedOrchestrator("n0")
        o.add_node("n1")
        r = o.remove_node("n1")
        assert r["status"] == "removed"

    def test_elect_leader_bully(self):
        o = DistributedOrchestrator("n0")
        o.add_node("n1")
        r = o.elect_leader("bully")
        assert r["leader"] is not None

    def test_elect_leader_raft(self):
        o = DistributedOrchestrator("n0")
        o.add_node("n1")
        r = o.elect_leader("raft")
        assert r["leader"] is not None

    def test_failover(self):
        o = DistributedOrchestrator("n0")
        o.elect_leader()
        o.election.heartbeat("n0")
        r = o.failover()
        assert "leader_healthy" in r

    def test_send_message(self):
        o = DistributedOrchestrator("n0")
        r = o.send_message("q1", {"x": 1})
        assert r["status"] == "enqueued"

    def test_receive_message(self):
        o = DistributedOrchestrator("n0")
        o.send_message("q1", {"x": 1})
        msg = o.receive_message("q1")
        assert msg["data"]["x"] == 1

    def test_receive_empty(self):
        o = DistributedOrchestrator("n0")
        assert o.receive_message("q1") is None

    def test_get_analytics(self):
        o = DistributedOrchestrator("n0")
        o.add_node("n1")
        a = o.get_analytics()
        assert "cluster" in a
        assert a["cluster"]["total_nodes"] >= 1

    def test_snapshot(self):
        o = DistributedOrchestrator("n0")
        o.add_node("n1")
        s = o.snapshot()
        assert s["node_id"] == "n0"
        assert "uptime" in s
        assert s["nodes"] >= 1


# ---- Config Testleri ----

class TestDistConfig:
    def test_config_defaults(self):
        s = Settings()
        assert s.distributed_enabled is True
        assert s.cluster_size == 3
        assert s.replication_factor == 3
        assert s.consensus_timeout == 30
        assert s.heartbeat_interval == 5
