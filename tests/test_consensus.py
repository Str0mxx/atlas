"""ConsensusBuilder testleri.

Oylama: cogunluk, oybirligi, agirlikli, yeter sayili
konsensus testleri.
"""

from app.core.collaboration.consensus import ConsensusBuilder
from app.models.collaboration import ConsensusMethod, VoteType


# === Yardimci fonksiyonlar ===


def _make_builder() -> ConsensusBuilder:
    return ConsensusBuilder()


# === Init Testleri ===


class TestConsensusBuilderInit:
    def test_default(self) -> None:
        cb = _make_builder()
        assert cb.sessions == {}
        assert cb.agent_weights == {}


# === Agent Weight Testleri ===


class TestConsensusWeights:
    def test_set_weight(self) -> None:
        cb = _make_builder()
        cb.set_agent_weight("agent_a", 2.0)
        assert cb.agent_weights["agent_a"] == 2.0

    def test_negative_clamped(self) -> None:
        cb = _make_builder()
        cb.set_agent_weight("agent_a", -1.0)
        assert cb.agent_weights["agent_a"] == 0.0


# === create_session Testleri ===


class TestConsensusCreateSession:
    async def test_create(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Deploy to prod?")
        assert session.topic == "Deploy to prod?"
        assert session.method == ConsensusMethod.MAJORITY
        assert session.id in cb.sessions

    async def test_custom_method(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Vote", method=ConsensusMethod.UNANIMOUS)
        assert session.method == ConsensusMethod.UNANIMOUS

    async def test_custom_quorum(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Vote", quorum=0.75)
        assert session.quorum == 0.75


# === cast_vote Testleri ===


class TestConsensusCastVote:
    async def test_vote(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        vote = await cb.cast_vote(session.id, "agent_a", VoteType.APPROVE)
        assert vote is not None
        assert vote.agent_name == "agent_a"
        assert vote.vote_type == VoteType.APPROVE

    async def test_vote_with_weight(self) -> None:
        cb = _make_builder()
        cb.set_agent_weight("agent_a", 3.0)
        session = await cb.create_session("Topic")
        vote = await cb.cast_vote(session.id, "agent_a", VoteType.APPROVE)
        assert vote is not None
        assert vote.weight == 3.0

    async def test_vote_nonexistent_session(self) -> None:
        cb = _make_builder()
        vote = await cb.cast_vote("nope", "agent_a", VoteType.APPROVE)
        assert vote is None

    async def test_duplicate_vote(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        await cb.cast_vote(session.id, "agent_a", VoteType.APPROVE)
        duplicate = await cb.cast_vote(session.id, "agent_a", VoteType.REJECT)
        assert duplicate is None

    async def test_vote_after_resolved(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.resolve(session.id)
        vote = await cb.cast_vote(session.id, "b", VoteType.APPROVE)
        assert vote is None

    async def test_vote_with_reason(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        vote = await cb.cast_vote(session.id, "a", VoteType.REJECT, reason="Too risky")
        assert vote is not None
        assert vote.reason == "Too risky"


# === Majority Resolve Testleri ===


class TestConsensusMajority:
    async def test_approve_majority(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.APPROVE)
        await cb.cast_vote(session.id, "c", VoteType.REJECT)
        result = await cb.resolve(session.id)
        assert result == VoteType.APPROVE

    async def test_reject_majority(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        await cb.cast_vote(session.id, "a", VoteType.REJECT)
        await cb.cast_vote(session.id, "b", VoteType.REJECT)
        await cb.cast_vote(session.id, "c", VoteType.APPROVE)
        result = await cb.resolve(session.id)
        assert result == VoteType.REJECT

    async def test_tie(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.REJECT)
        result = await cb.resolve(session.id)
        assert result == VoteType.ABSTAIN

    async def test_no_votes(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        result = await cb.resolve(session.id)
        assert result is None


# === Unanimous Resolve Testleri ===


class TestConsensusUnanimous:
    async def test_all_approve(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic", method=ConsensusMethod.UNANIMOUS)
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.APPROVE)
        result = await cb.resolve(session.id)
        assert result == VoteType.APPROVE

    async def test_one_reject(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic", method=ConsensusMethod.UNANIMOUS)
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.REJECT)
        result = await cb.resolve(session.id)
        assert result == VoteType.REJECT

    async def test_all_abstain(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic", method=ConsensusMethod.UNANIMOUS)
        await cb.cast_vote(session.id, "a", VoteType.ABSTAIN)
        result = await cb.resolve(session.id)
        assert result == VoteType.ABSTAIN


# === Weighted Resolve Testleri ===


class TestConsensusWeighted:
    async def test_weight_overrides(self) -> None:
        cb = _make_builder()
        cb.set_agent_weight("senior", 5.0)
        cb.set_agent_weight("junior", 1.0)
        session = await cb.create_session("Topic", method=ConsensusMethod.WEIGHTED)
        await cb.cast_vote(session.id, "senior", VoteType.REJECT)
        await cb.cast_vote(session.id, "junior", VoteType.APPROVE)
        result = await cb.resolve(session.id)
        assert result == VoteType.REJECT

    async def test_equal_weight_tie(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic", method=ConsensusMethod.WEIGHTED)
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.REJECT)
        result = await cb.resolve(session.id)
        assert result == VoteType.ABSTAIN


# === Quorum Resolve Testleri ===


class TestConsensusQuorum:
    async def test_quorum_met(self) -> None:
        cb = _make_builder()
        session = await cb.create_session(
            "Topic", method=ConsensusMethod.QUORUM, quorum=0.6,
        )
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.APPROVE)
        await cb.cast_vote(session.id, "c", VoteType.REJECT)
        result = await cb.resolve(session.id)
        # 2/3 = 0.667 >= 0.6
        assert result == VoteType.APPROVE

    async def test_quorum_not_met(self) -> None:
        cb = _make_builder()
        session = await cb.create_session(
            "Topic", method=ConsensusMethod.QUORUM, quorum=0.8,
        )
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.REJECT)
        await cb.cast_vote(session.id, "c", VoteType.REJECT)
        result = await cb.resolve(session.id)
        # 1/3 = 0.333 < 0.8
        assert result == VoteType.REJECT

    async def test_participation_quorum(self) -> None:
        cb = _make_builder()
        session = await cb.create_session(
            "Topic", method=ConsensusMethod.MAJORITY, quorum=0.5,
        )
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        # 1/10 = 0.1 < 0.5
        result = await cb.resolve(session.id, total_agents=10)
        assert result is None

    async def test_all_abstain_quorum(self) -> None:
        cb = _make_builder()
        session = await cb.create_session(
            "Topic", method=ConsensusMethod.QUORUM, quorum=0.5,
        )
        await cb.cast_vote(session.id, "a", VoteType.ABSTAIN)
        result = await cb.resolve(session.id)
        assert result == VoteType.ABSTAIN


# === Resolve Idempotent Testleri ===


class TestConsensusResolveIdempotent:
    async def test_resolve_twice(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Topic")
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        r1 = await cb.resolve(session.id)
        r2 = await cb.resolve(session.id)
        assert r1 == r2

    async def test_resolve_nonexistent(self) -> None:
        cb = _make_builder()
        result = await cb.resolve("nope")
        assert result is None


# === Summary Testleri ===


class TestConsensusSummary:
    async def test_summary(self) -> None:
        cb = _make_builder()
        session = await cb.create_session("Deploy?")
        await cb.cast_vote(session.id, "a", VoteType.APPROVE)
        await cb.cast_vote(session.id, "b", VoteType.REJECT)
        await cb.cast_vote(session.id, "c", VoteType.ABSTAIN)
        summary = cb.get_session_summary(session.id)
        assert summary is not None
        assert summary["topic"] == "Deploy?"
        assert summary["total_votes"] == 3
        assert summary["approve"] == 1
        assert summary["reject"] == 1
        assert summary["abstain"] == 1

    def test_summary_nonexistent(self) -> None:
        cb = _make_builder()
        assert cb.get_session_summary("nope") is None
