"""NegotiationManager testleri.

Contract Net Protocol: CFP, teklif, degerlendirme,
kazanan secimi testleri.
"""

from app.core.collaboration.negotiation import NegotiationManager
from app.models.collaboration import BidStatus, NegotiationState


# === Yardimci fonksiyonlar ===


def _make_manager() -> NegotiationManager:
    nm = NegotiationManager()
    nm.register_capabilities("research", ["web_search", "analysis"])
    nm.register_capabilities("security", ["scanning", "monitoring"])
    nm.register_capabilities("coding", ["analysis", "code_review"])
    return nm


# === Init Testleri ===


class TestNegotiationManagerInit:
    def test_default(self) -> None:
        nm = NegotiationManager()
        assert nm.negotiations == {}
        assert nm.agent_capabilities == {}


# === register_capabilities Testleri ===


class TestNegotiationCapabilities:
    def test_register(self) -> None:
        nm = NegotiationManager()
        nm.register_capabilities("agent_a", ["web", "search"])
        assert nm.agent_capabilities["agent_a"] == ["web", "search"]

    def test_overwrite(self) -> None:
        nm = NegotiationManager()
        nm.register_capabilities("agent_a", ["web"])
        nm.register_capabilities("agent_a", ["search"])
        assert nm.agent_capabilities["agent_a"] == ["search"]


# === get_eligible_agents Testleri ===


class TestNegotiationEligible:
    def test_no_requirements(self) -> None:
        nm = _make_manager()
        eligible = nm.get_eligible_agents()
        assert len(eligible) == 3

    def test_with_requirements(self) -> None:
        nm = _make_manager()
        eligible = nm.get_eligible_agents(["analysis"])
        assert "research" in eligible
        assert "coding" in eligible
        assert "security" not in eligible

    def test_no_match(self) -> None:
        nm = _make_manager()
        eligible = nm.get_eligible_agents(["voice_recognition"])
        assert eligible == []

    def test_multiple_requirements(self) -> None:
        nm = _make_manager()
        eligible = nm.get_eligible_agents(["web_search", "analysis"])
        assert eligible == ["research"]


# === create_cfp Testleri ===


class TestNegotiationCFP:
    async def test_create(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Analyze server logs")
        assert neg.initiator == "master"
        assert neg.state == NegotiationState.BIDDING
        assert neg.id in nm.negotiations

    async def test_custom_criteria(self) -> None:
        nm = _make_manager()
        criteria = {"capability_score": 0.8, "price": 0.2}
        neg = await nm.create_cfp("master", "Task", criteria=criteria)
        assert neg.criteria == criteria

    async def test_custom_deadline(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task", deadline=60.0)
        assert neg.deadline == 60.0


# === submit_bid Testleri ===


class TestNegotiationBid:
    async def test_submit(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        bid = await nm.submit_bid(neg.id, "research", price=10.0, capability_score=0.8)
        assert bid is not None
        assert bid.agent_name == "research"
        assert bid.status == BidStatus.PENDING
        assert len(neg.bids) == 1

    async def test_submit_nonexistent(self) -> None:
        nm = _make_manager()
        bid = await nm.submit_bid("nope", "research")
        assert bid is None

    async def test_submit_after_awarded(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.9)
        await nm.evaluate_bids(neg.id)
        bid = await nm.submit_bid(neg.id, "coding", capability_score=0.8)
        assert bid is None

    async def test_multiple_bids(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.7)
        await nm.submit_bid(neg.id, "coding", capability_score=0.9)
        assert len(neg.bids) == 2


# === evaluate_bids Testleri ===


class TestNegotiationEvaluate:
    async def test_evaluate_selects_best(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.6, price=50.0)
        await nm.submit_bid(neg.id, "coding", capability_score=0.9, price=30.0)
        winner = await nm.evaluate_bids(neg.id)
        assert winner == "coding"
        assert neg.state == NegotiationState.AWARDED
        assert neg.winner == "coding"

    async def test_evaluate_no_bids(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        winner = await nm.evaluate_bids(neg.id)
        assert winner is None
        assert neg.state == NegotiationState.FAILED

    async def test_evaluate_nonexistent(self) -> None:
        nm = _make_manager()
        winner = await nm.evaluate_bids("nope")
        assert winner is None

    async def test_bid_statuses_after_evaluate(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.5)
        await nm.submit_bid(neg.id, "coding", capability_score=0.9)
        await nm.evaluate_bids(neg.id)
        accepted = [b for b in neg.bids if b.status == BidStatus.ACCEPTED]
        rejected = [b for b in neg.bids if b.status == BidStatus.REJECTED]
        assert len(accepted) == 1
        assert len(rejected) == 1

    async def test_single_bid(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.7)
        winner = await nm.evaluate_bids(neg.id)
        assert winner == "research"

    async def test_price_matters(self) -> None:
        nm = _make_manager()
        criteria = {"capability_score": 0.0, "price": 1.0, "estimated_duration": 0.0}
        neg = await nm.create_cfp("master", "Task", criteria=criteria)
        await nm.submit_bid(neg.id, "cheap", price=10.0)
        await nm.submit_bid(neg.id, "expensive", price=100.0)
        nm.register_capabilities("cheap", [])
        nm.register_capabilities("expensive", [])
        winner = await nm.evaluate_bids(neg.id)
        assert winner == "cheap"

    async def test_duration_matters(self) -> None:
        nm = _make_manager()
        criteria = {"capability_score": 0.0, "price": 0.0, "estimated_duration": 1.0}
        neg = await nm.create_cfp("master", "Task", criteria=criteria)
        await nm.submit_bid(neg.id, "fast", estimated_duration=10.0)
        await nm.submit_bid(neg.id, "slow", estimated_duration=100.0)
        nm.register_capabilities("fast", [])
        nm.register_capabilities("slow", [])
        winner = await nm.evaluate_bids(neg.id)
        assert winner == "fast"


# === complete/cancel Testleri ===


class TestNegotiationLifecycle:
    async def test_complete(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.9)
        await nm.evaluate_bids(neg.id)
        result = await nm.complete_negotiation(neg.id)
        assert result is True
        assert neg.state == NegotiationState.COMPLETED

    async def test_complete_without_award(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        result = await nm.complete_negotiation(neg.id)
        assert result is False

    async def test_cancel(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research")
        result = await nm.cancel_negotiation(neg.id)
        assert result is True
        assert neg.state == NegotiationState.CANCELLED
        assert all(b.status == BidStatus.WITHDRAWN for b in neg.bids)

    async def test_cancel_completed(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.9)
        await nm.evaluate_bids(neg.id)
        await nm.complete_negotiation(neg.id)
        result = await nm.cancel_negotiation(neg.id)
        assert result is False

    async def test_cancel_nonexistent(self) -> None:
        nm = _make_manager()
        result = await nm.cancel_negotiation("nope")
        assert result is False

    async def test_complete_nonexistent(self) -> None:
        nm = _make_manager()
        result = await nm.complete_negotiation("nope")
        assert result is False


# === Yardimci Metot Testleri ===


class TestNegotiationHelpers:
    async def test_agent_wins(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.9)
        await nm.evaluate_bids(neg.id)
        assert nm.get_agent_wins("research") == 1
        assert nm.get_agent_wins("coding") == 0

    async def test_active_negotiations(self) -> None:
        nm = _make_manager()
        await nm.create_cfp("master", "Task 1")
        await nm.create_cfp("master", "Task 2")
        active = nm.get_active_negotiations()
        assert len(active) == 2

    async def test_active_excludes_completed(self) -> None:
        nm = _make_manager()
        neg = await nm.create_cfp("master", "Task")
        await nm.submit_bid(neg.id, "research", capability_score=0.9)
        await nm.evaluate_bids(neg.id)
        await nm.complete_negotiation(neg.id)
        active = nm.get_active_negotiations()
        assert len(active) == 0
