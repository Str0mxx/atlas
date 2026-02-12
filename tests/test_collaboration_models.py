"""Collaboration modelleri testleri.

AgentMessage, Bid, Negotiation, Team, Vote, ConsensusSession,
WorkflowNode, WorkflowDefinition testleri.
"""

from app.models.collaboration import (
    AgentMessage,
    Bid,
    BidStatus,
    ConsensusMethod,
    ConsensusSession,
    MessagePriority,
    MessageType,
    Negotiation,
    NegotiationState,
    Subscription,
    Team,
    TeamMember,
    TeamRole,
    TeamStatus,
    Vote,
    VoteType,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowNodeType,
    WorkflowResult,
    WorkflowStatus,
)


# === Enum Testleri ===


class TestMessageType:
    def test_values(self) -> None:
        assert MessageType.REQUEST == "request"
        assert MessageType.RESPONSE == "response"
        assert MessageType.INFORM == "inform"
        assert MessageType.CFP == "call_for_proposal"
        assert MessageType.BROADCAST == "broadcast"
        assert MessageType.PROPOSE == "propose"
        assert MessageType.ACCEPT == "accept"
        assert MessageType.REJECT == "reject"


class TestMessagePriority:
    def test_values(self) -> None:
        assert MessagePriority.LOW == "low"
        assert MessagePriority.NORMAL == "normal"
        assert MessagePriority.HIGH == "high"
        assert MessagePriority.URGENT == "urgent"


class TestNegotiationState:
    def test_values(self) -> None:
        assert NegotiationState.OPEN == "open"
        assert NegotiationState.BIDDING == "bidding"
        assert NegotiationState.AWARDED == "awarded"
        assert NegotiationState.COMPLETED == "completed"
        assert NegotiationState.FAILED == "failed"
        assert NegotiationState.CANCELLED == "cancelled"


class TestBidStatus:
    def test_values(self) -> None:
        assert BidStatus.PENDING == "pending"
        assert BidStatus.ACCEPTED == "accepted"
        assert BidStatus.REJECTED == "rejected"
        assert BidStatus.WITHDRAWN == "withdrawn"


class TestTeamRole:
    def test_values(self) -> None:
        assert TeamRole.LEADER == "leader"
        assert TeamRole.MEMBER == "member"
        assert TeamRole.SPECIALIST == "specialist"
        assert TeamRole.OBSERVER == "observer"


class TestTeamStatus:
    def test_values(self) -> None:
        assert TeamStatus.FORMING == "forming"
        assert TeamStatus.ACTIVE == "active"
        assert TeamStatus.EXECUTING == "executing"
        assert TeamStatus.COMPLETED == "completed"
        assert TeamStatus.DISBANDED == "disbanded"


class TestVoteType:
    def test_values(self) -> None:
        assert VoteType.APPROVE == "approve"
        assert VoteType.REJECT == "reject"
        assert VoteType.ABSTAIN == "abstain"


class TestConsensusMethod:
    def test_values(self) -> None:
        assert ConsensusMethod.MAJORITY == "majority"
        assert ConsensusMethod.UNANIMOUS == "unanimous"
        assert ConsensusMethod.WEIGHTED == "weighted"
        assert ConsensusMethod.QUORUM == "quorum"


class TestWorkflowNodeType:
    def test_values(self) -> None:
        assert WorkflowNodeType.TASK == "task"
        assert WorkflowNodeType.PARALLEL == "parallel"
        assert WorkflowNodeType.SEQUENCE == "sequence"
        assert WorkflowNodeType.CONDITIONAL == "conditional"
        assert WorkflowNodeType.MERGE == "merge"


class TestWorkflowStatus:
    def test_values(self) -> None:
        assert WorkflowStatus.PENDING == "pending"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"
        assert WorkflowStatus.PAUSED == "paused"
        assert WorkflowStatus.CANCELLED == "cancelled"


# === Model Testleri ===


class TestAgentMessage:
    def test_default(self) -> None:
        msg = AgentMessage(sender="agent_a")
        assert msg.sender == "agent_a"
        assert msg.receiver is None
        assert msg.message_type == MessageType.INFORM
        assert msg.priority == MessagePriority.NORMAL
        assert msg.content == {}
        assert msg.ttl == 0
        assert msg.id

    def test_request(self) -> None:
        msg = AgentMessage(
            sender="a",
            receiver="b",
            message_type=MessageType.REQUEST,
            priority=MessagePriority.HIGH,
            content={"query": "status"},
        )
        assert msg.receiver == "b"
        assert msg.message_type == MessageType.REQUEST

    def test_unique_ids(self) -> None:
        a = AgentMessage(sender="x")
        b = AgentMessage(sender="x")
        assert a.id != b.id


class TestSubscription:
    def test_default(self) -> None:
        sub = Subscription(agent_name="agent_a", topic="server_events")
        assert sub.agent_name == "agent_a"
        assert sub.topic == "server_events"


class TestBid:
    def test_default(self) -> None:
        bid = Bid(agent_name="agent_a")
        assert bid.price == 0.0
        assert bid.capability_score == 0.5
        assert bid.status == BidStatus.PENDING

    def test_custom(self) -> None:
        bid = Bid(
            agent_name="agent_a",
            price=100.0,
            capability_score=0.9,
            estimated_duration=60.0,
            proposal={"approach": "fast"},
        )
        assert bid.price == 100.0
        assert bid.proposal == {"approach": "fast"}


class TestNegotiation:
    def test_default(self) -> None:
        neg = Negotiation()
        assert neg.state == NegotiationState.OPEN
        assert neg.bids == []
        assert neg.winner is None
        assert neg.deadline == 30.0

    def test_default_criteria(self) -> None:
        neg = Negotiation()
        assert "capability_score" in neg.criteria
        assert "price" in neg.criteria


class TestTeamMember:
    def test_default(self) -> None:
        m = TeamMember(agent_name="agent_a")
        assert m.role == TeamRole.MEMBER
        assert m.capabilities == []
        assert m.workload == 0.0


class TestTeam:
    def test_default(self) -> None:
        t = Team(name="Alpha")
        assert t.name == "Alpha"
        assert t.status == TeamStatus.FORMING
        assert t.members == []

    def test_with_members(self) -> None:
        m = TeamMember(agent_name="a", role=TeamRole.LEADER)
        t = Team(name="Alpha", members=[m])
        assert len(t.members) == 1


class TestVote:
    def test_default(self) -> None:
        v = Vote(agent_name="agent_a")
        assert v.vote_type == VoteType.APPROVE
        assert v.weight == 1.0

    def test_custom(self) -> None:
        v = Vote(
            agent_name="a",
            vote_type=VoteType.REJECT,
            weight=2.0,
            reason="Too risky",
        )
        assert v.vote_type == VoteType.REJECT
        assert v.weight == 2.0


class TestConsensusSession:
    def test_default(self) -> None:
        s = ConsensusSession()
        assert s.method == ConsensusMethod.MAJORITY
        assert s.votes == []
        assert s.resolved is False
        assert s.result is None
        assert s.quorum == 0.5


class TestWorkflowNode:
    def test_default(self) -> None:
        n = WorkflowNode(name="step1")
        assert n.node_type == WorkflowNodeType.TASK
        assert n.agent_name is None
        assert n.children == []
        assert n.status == WorkflowStatus.PENDING

    def test_parallel(self) -> None:
        n = WorkflowNode(name="fork", node_type=WorkflowNodeType.PARALLEL)
        assert n.node_type == WorkflowNodeType.PARALLEL


class TestWorkflowDefinition:
    def test_default(self) -> None:
        w = WorkflowDefinition(name="pipeline")
        assert w.name == "pipeline"
        assert w.nodes == {}
        assert w.root_id is None
        assert w.status == WorkflowStatus.PENDING


class TestWorkflowResult:
    def test_default(self) -> None:
        r = WorkflowResult(workflow_id="w1")
        assert r.success is True
        assert r.node_results == {}
        assert r.failed_nodes == []

    def test_failed(self) -> None:
        r = WorkflowResult(
            workflow_id="w1",
            success=False,
            failed_nodes=["n1"],
        )
        assert r.success is False
