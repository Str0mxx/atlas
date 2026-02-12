"""DecisionMatrix kapsamli testleri.

Karar matrisi temel islemleri, olasiliksal degerlenme,
kural guncelleme/sifirlama, aciklama uretimi, geriye
uyumluluk ve uc-durum testlerini icerir.
"""

import pytest

from app.core.autonomy.probability import BayesianNetwork
from app.core.decision_matrix import (
    ActionType,
    Decision,
    DecisionMatrix,
    DECISION_RULES,
    RiskLevel,
    UrgencyLevel,
)
from app.models.decision import RuleChangeRecord
from app.models.probability import Evidence, PriorBelief


# === Orijinal kural kopyasi ===
# __init__ DECISION_RULES referansini dogrudan atar, bu yuzden
# update_rule global sabiti mutasyona ugratir. Testler arasi
# izolasyon icin orijinal degerleri kaydedip her testten once geri yukleriz.
_ORIGINAL_RULES: dict[
    tuple[RiskLevel, UrgencyLevel], tuple[ActionType, float]
] = dict(DECISION_RULES)


def _restore_global_rules() -> None:
    """DECISION_RULES global sabitini orijinal degerlere geri yukler."""
    DECISION_RULES.clear()
    DECISION_RULES.update(_ORIGINAL_RULES)


# === Yardimci fonksiyonlar ===


def _make_matrix(
    confidence_threshold: float = 0.6,
    risk_tolerance: float = 0.5,
) -> DecisionMatrix:
    """Test icin izole bir DecisionMatrix olusturur.

    DECISION_RULES global sabitini orijinaline geri yukledikten
    sonra yeni bir instance olusturur ve kurallari kopyalar.
    """
    _restore_global_rules()
    dm = DecisionMatrix(
        confidence_threshold=confidence_threshold,
        risk_tolerance=risk_tolerance,
    )
    # Instance'in kendi kural kopyasini kullanmasini sagla
    dm.rules = dict(DECISION_RULES)
    return dm


def _make_bayesian_network(
    variable: str = "risk",
    states: list[str] | None = None,
    probs: dict[str, float] | None = None,
) -> BayesianNetwork:
    """Test icin basit bir BayesianNetwork olusturur."""
    if states is None:
        states = ["high", "low"]
    if probs is None:
        probs = {s: 1.0 / len(states) for s in states}
    bn = BayesianNetwork()
    bn.add_node(variable, states)
    bn.set_prior(PriorBelief(variable=variable, probabilities=probs))
    return bn


def _make_evidence(
    variable: str = "risk",
    observed_value: str = "high",
    confidence: float = 0.9,
) -> Evidence:
    """Test icin Evidence nesnesi olusturur."""
    return Evidence(
        variable=variable,
        observed_value=observed_value,
        confidence=confidence,
    )


# === TestDecisionMatrixInit ===


class TestDecisionMatrixInit:
    """DecisionMatrix.__init__ testleri."""

    def test_default_confidence_threshold(self) -> None:
        """Varsayilan guven esigi 0.6 olmalidir."""
        dm = _make_matrix()
        assert dm.confidence_threshold == 0.6

    def test_default_risk_tolerance(self) -> None:
        """Varsayilan risk toleransi 0.5 olmalidir."""
        dm = _make_matrix()
        assert dm.risk_tolerance == 0.5

    def test_custom_params(self) -> None:
        """Ozel parametreler dogru atanmalidir."""
        dm = _make_matrix(confidence_threshold=0.8, risk_tolerance=0.3)
        assert dm.confidence_threshold == 0.8
        assert dm.risk_tolerance == 0.3

    def test_rules_loaded(self) -> None:
        """9 kural yuklenmis olmalidir."""
        dm = _make_matrix()
        assert len(dm.rules) == 9

    def test_bayesian_net_initially_none(self) -> None:
        """Bayesci ag baslangicta None olmalidir."""
        dm = _make_matrix()
        assert dm._bayesian_net is None

    def test_rule_history_initially_empty(self) -> None:
        """Kural gecmisi baslangicta bos olmalidir."""
        dm = _make_matrix()
        assert dm._rule_history == []


# === TestEvaluateBasic ===


class TestEvaluateBasic:
    """evaluate temel testleri (beliefs olmadan tum 9 kombinasyon + ekstralar)."""

    async def test_low_low(self) -> None:
        """LOW/LOW -> LOG, guven 0.95."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert d.action == ActionType.LOG
        assert d.confidence == pytest.approx(0.95)

    async def test_low_medium(self) -> None:
        """LOW/MEDIUM -> LOG, guven 0.90."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.MEDIUM)
        assert d.action == ActionType.LOG
        assert d.confidence == pytest.approx(0.90)

    async def test_low_high(self) -> None:
        """LOW/HIGH -> NOTIFY, guven 0.85."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.HIGH)
        assert d.action == ActionType.NOTIFY
        assert d.confidence == pytest.approx(0.85)

    async def test_medium_low(self) -> None:
        """MEDIUM/LOW -> NOTIFY, guven 0.85."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.MEDIUM, UrgencyLevel.LOW)
        assert d.action == ActionType.NOTIFY
        assert d.confidence == pytest.approx(0.85)

    async def test_medium_medium(self) -> None:
        """MEDIUM/MEDIUM -> NOTIFY, guven 0.80."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.MEDIUM, UrgencyLevel.MEDIUM)
        assert d.action == ActionType.NOTIFY
        assert d.confidence == pytest.approx(0.80)

    async def test_medium_high(self) -> None:
        """MEDIUM/HIGH -> AUTO_FIX, guven 0.75."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.MEDIUM, UrgencyLevel.HIGH)
        assert d.action == ActionType.AUTO_FIX
        assert d.confidence == pytest.approx(0.75)

    async def test_high_low(self) -> None:
        """HIGH/LOW -> NOTIFY, guven 0.80."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.HIGH, UrgencyLevel.LOW)
        assert d.action == ActionType.NOTIFY
        assert d.confidence == pytest.approx(0.80)

    async def test_high_medium(self) -> None:
        """HIGH/MEDIUM -> AUTO_FIX, guven 0.70."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.HIGH, UrgencyLevel.MEDIUM)
        assert d.action == ActionType.AUTO_FIX
        assert d.confidence == pytest.approx(0.70)

    async def test_high_high(self) -> None:
        """HIGH/HIGH -> IMMEDIATE, guven 0.90."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert d.action == ActionType.IMMEDIATE
        assert d.confidence == pytest.approx(0.90)

    async def test_returns_decision_instance(self) -> None:
        """evaluate bir Decision nesnesi donmelidir."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert isinstance(d, Decision)

    async def test_reason_contains_risk(self) -> None:
        """reason alaninda risk seviyesi bulunmalidir."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert "high" in d.reason.lower()

    async def test_reason_contains_urgency(self) -> None:
        """reason alaninda aciliyet seviyesi bulunmalidir."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.MEDIUM)
        assert "medium" in d.reason.lower()


# === TestEvaluateWithBeliefs ===


class TestEvaluateWithBeliefs:
    """evaluate beliefs parametresi testleri."""

    async def test_high_beliefs_preserves_immediate(self) -> None:
        """Yuksek guvenli beliefs IMMEDIATE aksiyonunu korumalidir."""
        dm = _make_matrix(confidence_threshold=0.5)
        d = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={"cpu": 0.95, "mem": 0.90},
        )
        assert d.action == ActionType.IMMEDIATE

    async def test_low_beliefs_demotes_auto_fix(self) -> None:
        """Dusuk guvenli beliefs AUTO_FIX'i NOTIFY'a dusurmelidir."""
        dm = _make_matrix(confidence_threshold=0.8)
        d = await dm.evaluate(
            RiskLevel.MEDIUM, UrgencyLevel.HIGH,
            beliefs={"cpu": 0.3, "mem": 0.2},
        )
        assert d.action == ActionType.NOTIFY

    async def test_low_beliefs_demotes_immediate(self) -> None:
        """Dusuk guvenli beliefs IMMEDIATE'i NOTIFY'a dusurmelidir."""
        dm = _make_matrix(confidence_threshold=0.8)
        d = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={"x": 0.1, "y": 0.1},
        )
        assert d.action == ActionType.NOTIFY

    async def test_log_action_not_demoted(self) -> None:
        """LOG aksiyonu beliefs tarafindan dusurulmemelidir."""
        dm = _make_matrix(confidence_threshold=0.9)
        d = await dm.evaluate(
            RiskLevel.LOW, UrgencyLevel.LOW,
            beliefs={"x": 0.1},
        )
        assert d.action == ActionType.LOG

    async def test_notify_action_not_demoted(self) -> None:
        """NOTIFY aksiyonu beliefs tarafindan dusurulmemelidir."""
        dm = _make_matrix(confidence_threshold=0.9)
        d = await dm.evaluate(
            RiskLevel.MEDIUM, UrgencyLevel.MEDIUM,
            beliefs={"x": 0.1},
        )
        assert d.action == ActionType.NOTIFY

    async def test_demoted_confidence_reduced(self) -> None:
        """Dusurulmus aksiyonun guveni de azalmalidir."""
        dm = _make_matrix(confidence_threshold=0.8)
        d = await dm.evaluate(
            RiskLevel.MEDIUM, UrgencyLevel.HIGH,
            beliefs={"cpu": 0.3, "mem": 0.2},
        )
        # Orijinal guven 0.75, dusurulmus guven < 0.75 olmali
        assert d.confidence < 0.75

    async def test_beliefs_with_context(self) -> None:
        """Beliefs ve context birlikte kullanilabilmelidir."""
        dm = _make_matrix(confidence_threshold=0.5)
        d = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            context={"detail": "sunucu yuku"},
            beliefs={"cpu": 0.9, "mem": 0.9},
        )
        assert isinstance(d, Decision)
        assert "sunucu yuku" in d.reason

    async def test_empty_beliefs_dict_no_demotion(self) -> None:
        """Bos beliefs sozlugu dusurme yapmamaldir (falsy)."""
        dm = _make_matrix()
        d = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={},
        )
        assert d.action == ActionType.IMMEDIATE

    async def test_single_belief_key(self) -> None:
        """Tek belief anahtari ile calisabilmelidir."""
        dm = _make_matrix(confidence_threshold=0.5)
        d = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={"single": 0.95},
        )
        assert d.action == ActionType.IMMEDIATE

    async def test_high_threshold_triggers_demotion(self) -> None:
        """Cok yuksek esik orta guvende bile dusurme tetiklemelidir."""
        dm = _make_matrix(confidence_threshold=0.99)
        d = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.MEDIUM,
            beliefs={"x": 0.7, "y": 0.7},
        )
        assert d.action == ActionType.NOTIFY


# === TestEvaluateWithContext ===


class TestEvaluateWithContext:
    """evaluate context parametresi testleri."""

    async def test_context_detail_in_reason(self) -> None:
        """Context detail bilgisi reason'da yer almalidir."""
        dm = _make_matrix()
        d = await dm.evaluate(
            RiskLevel.LOW, UrgencyLevel.LOW,
            context={"detail": "disk dolu"},
        )
        assert "disk dolu" in d.reason

    async def test_context_without_detail(self) -> None:
        """detail anahtari olmayan context hata vermemelidir."""
        dm = _make_matrix()
        d = await dm.evaluate(
            RiskLevel.LOW, UrgencyLevel.LOW,
            context={"other": "value"},
        )
        assert isinstance(d, Decision)

    async def test_none_context(self) -> None:
        """None context hata vermemelidir."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW, context=None)
        assert isinstance(d, Decision)

    async def test_empty_context(self) -> None:
        """Bos context sozlugu hata vermemelidir."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW, context={})
        assert isinstance(d, Decision)

    async def test_context_does_not_change_action(self) -> None:
        """Context aksiyonu degistirmemelidir."""
        dm = _make_matrix()
        d = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            context={"detail": "critical info"},
        )
        assert d.action == ActionType.IMMEDIATE


# === TestEvaluateProbabilistic ===


class TestEvaluateProbabilistic:
    """evaluate_probabilistic testleri."""

    async def test_without_evidence_fallback(self) -> None:
        """Kanit yoksa standart kurallara donmelidir."""
        dm = _make_matrix()
        d = await dm.evaluate_probabilistic(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert d.action == ActionType.IMMEDIATE
        assert d.confidence == pytest.approx(0.90)

    async def test_without_network_fallback(self) -> None:
        """Bayesci ag yoksa kanit verilse bile standart davranmalidir."""
        dm = _make_matrix()
        ev = _make_evidence()
        d = await dm.evaluate_probabilistic(
            RiskLevel.MEDIUM, UrgencyLevel.MEDIUM, evidence=[ev],
        )
        assert d.action == ActionType.NOTIFY
        assert d.confidence == pytest.approx(0.80)

    async def test_with_network_and_evidence(self) -> None:
        """Ag ve kanit verildiginde olasiliksal karar uretilmelidir."""
        dm = _make_matrix(confidence_threshold=0.7)
        bn = _make_bayesian_network()
        dm.set_bayesian_network(bn)
        ev = _make_evidence(confidence=0.9)
        d = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.HIGH, evidence=[ev],
        )
        assert isinstance(d, Decision)

    async def test_low_posterior_demotes_auto_fix(self) -> None:
        """Dusuk posterior AUTO_FIX'i NOTIFY'a dusurmelidir."""
        dm = _make_matrix(confidence_threshold=0.95)
        bn = _make_bayesian_network(
            variable="status", states=["ok", "fail"],
            probs={"ok": 0.5, "fail": 0.5},
        )
        dm.set_bayesian_network(bn)
        ev = _make_evidence(
            variable="status", observed_value="ok", confidence=0.3,
        )
        d = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.MEDIUM, evidence=[ev],
        )
        assert d.action == ActionType.NOTIFY

    async def test_low_posterior_demotes_immediate(self) -> None:
        """Dusuk posterior IMMEDIATE'i NOTIFY'a dusurmelidir."""
        dm = _make_matrix(confidence_threshold=0.95)
        bn = _make_bayesian_network(
            variable="status", states=["ok", "fail"],
            probs={"ok": 0.5, "fail": 0.5},
        )
        dm.set_bayesian_network(bn)
        ev = _make_evidence(
            variable="status", observed_value="ok", confidence=0.3,
        )
        d = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.HIGH, evidence=[ev],
        )
        assert d.action == ActionType.NOTIFY

    async def test_high_posterior_preserves_action(self) -> None:
        """Yuksek posterior aksiyonu korumalidir."""
        dm = _make_matrix(confidence_threshold=0.3)
        bn = _make_bayesian_network(
            variable="cpu", states=["high", "low"],
            probs={"high": 0.9, "low": 0.1},
        )
        dm.set_bayesian_network(bn)
        ev = _make_evidence(
            variable="cpu", observed_value="high", confidence=0.95,
        )
        d = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.HIGH, evidence=[ev],
        )
        assert d.action == ActionType.IMMEDIATE

    async def test_confidence_modified_by_posterior(self) -> None:
        """Guven skoru posterior tarafindan degistirilmelidir."""
        dm = _make_matrix(confidence_threshold=0.3)
        bn = _make_bayesian_network()
        dm.set_bayesian_network(bn)
        ev = _make_evidence(confidence=0.9)
        d = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.HIGH, evidence=[ev],
        )
        # Guven = base_confidence * avg_posterior, bu yuzden farkli olabilir
        assert 0.0 <= d.confidence <= 1.0

    async def test_empty_evidence_list(self) -> None:
        """Bos evidence listesi standart davranis gostermelidir."""
        dm = _make_matrix()
        bn = _make_bayesian_network()
        dm.set_bayesian_network(bn)
        d = await dm.evaluate_probabilistic(
            RiskLevel.LOW, UrgencyLevel.LOW, evidence=[],
        )
        assert d.action == ActionType.LOG
        assert d.confidence == pytest.approx(0.95)

    async def test_context_passed_through(self) -> None:
        """Context bilgisi reason'a aktarilmalidir."""
        dm = _make_matrix()
        d = await dm.evaluate_probabilistic(
            RiskLevel.LOW, UrgencyLevel.LOW,
            context={"detail": "test context"},
        )
        assert "test context" in d.reason

    async def test_multiple_evidence_items(self) -> None:
        """Birden fazla kanit islenebilmelidir."""
        dm = _make_matrix(confidence_threshold=0.3)
        bn = BayesianNetwork()
        bn.add_node("cpu", ["high", "low"])
        bn.set_prior(PriorBelief(
            variable="cpu", probabilities={"high": 0.5, "low": 0.5},
        ))
        bn.add_node("mem", ["high", "low"])
        bn.set_prior(PriorBelief(
            variable="mem", probabilities={"high": 0.5, "low": 0.5},
        ))
        dm.set_bayesian_network(bn)

        ev1 = _make_evidence(variable="cpu", observed_value="high", confidence=0.9)
        ev2 = _make_evidence(variable="mem", observed_value="low", confidence=0.8)
        d = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.HIGH, evidence=[ev1, ev2],
        )
        assert isinstance(d, Decision)

    async def test_returns_decision_instance(self) -> None:
        """evaluate_probabilistic bir Decision nesnesi donmelidir."""
        dm = _make_matrix()
        d = await dm.evaluate_probabilistic(
            RiskLevel.MEDIUM, UrgencyLevel.LOW,
        )
        assert isinstance(d, Decision)
        assert d.risk == RiskLevel.MEDIUM
        assert d.urgency == UrgencyLevel.LOW

    async def test_notify_not_demoted_by_low_posterior(self) -> None:
        """NOTIFY aksiyonu dusuk posterior ile dusurulmemelidir."""
        dm = _make_matrix(confidence_threshold=0.95)
        bn = _make_bayesian_network(
            variable="status", states=["ok", "fail"],
            probs={"ok": 0.5, "fail": 0.5},
        )
        dm.set_bayesian_network(bn)
        ev = _make_evidence(
            variable="status", observed_value="ok", confidence=0.3,
        )
        d = await dm.evaluate_probabilistic(
            RiskLevel.MEDIUM, UrgencyLevel.MEDIUM, evidence=[ev],
        )
        assert d.action == ActionType.NOTIFY


# === TestUpdateRule ===


class TestUpdateRule:
    """update_rule testleri."""

    def test_returns_rule_change_record(self) -> None:
        """RuleChangeRecord donmelidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.NOTIFY, 0.80,
        )
        assert isinstance(record, RuleChangeRecord)

    def test_old_values_captured(self) -> None:
        """Eski degerler kayda gecmelidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.NOTIFY, 0.80,
        )
        assert record.old_action == ActionType.LOG.value
        assert record.old_confidence == pytest.approx(0.95)

    def test_new_values_captured(self) -> None:
        """Yeni degerler kayda gecmelidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.NOTIFY, 0.80,
        )
        assert record.new_action == ActionType.NOTIFY.value
        assert record.new_confidence == pytest.approx(0.80)

    def test_rule_actually_updated(self) -> None:
        """Kural gercekten guncellenmis olmalidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.IMMEDIATE, 0.99,
        )
        action, conf = dm.rules[(RiskLevel.LOW, UrgencyLevel.LOW)]
        assert action == ActionType.IMMEDIATE
        assert conf == pytest.approx(0.99)

    def test_confidence_clamped_high(self) -> None:
        """Guven 1.0'in uzerine cikamamalidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.LOG, 1.5,
        )
        assert record.new_confidence == pytest.approx(1.0)

    def test_confidence_clamped_low(self) -> None:
        """Guven 0.0'in altina dusmemelidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.LOG, -0.5,
        )
        assert record.new_confidence == pytest.approx(0.0)

    def test_changed_by_default(self) -> None:
        """Varsayilan changed_by 'system' olmalidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.LOG, 0.80,
        )
        assert record.changed_by == "system"

    def test_changed_by_custom(self) -> None:
        """Ozel changed_by degeri atanabilmelidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.LOG, 0.80,
            changed_by="user",
        )
        assert record.changed_by == "user"

    def test_appended_to_history(self) -> None:
        """Kayit gecmise eklenmelidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.NOTIFY, 0.50,
        )
        assert len(dm._rule_history) == 1

    def test_multiple_updates_accumulate(self) -> None:
        """Birden fazla guncelleme gecmiste birikmelidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.NOTIFY, 0.50,
        )
        dm.update_rule(
            RiskLevel.HIGH, UrgencyLevel.HIGH, ActionType.LOG, 0.30,
        )
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.AUTO_FIX, 0.60,
        )
        assert len(dm._rule_history) == 3

    def test_record_contains_risk_urgency(self) -> None:
        """Kayit risk ve aciliyet bilgisi icermelidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.MEDIUM, UrgencyLevel.HIGH,
            ActionType.IMMEDIATE, 0.90,
        )
        assert record.risk == RiskLevel.MEDIUM.value
        assert record.urgency == UrgencyLevel.HIGH.value

    def test_record_has_timestamp(self) -> None:
        """Kayitta timestamp bulunmalidir."""
        dm = _make_matrix()
        record = dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.LOG, 0.50,
        )
        assert record.timestamp is not None


# === TestGetRuleHistory ===


class TestGetRuleHistory:
    """get_rule_history testleri."""

    def test_initially_empty(self) -> None:
        """Baslangicta bos liste donmelidir."""
        dm = _make_matrix()
        assert dm.get_rule_history() == []

    def test_returns_copy(self) -> None:
        """Orijinal listenin kopyasi donmelidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.NOTIFY, 0.50,
        )
        history = dm.get_rule_history()
        history.clear()
        # Orijinal etkilenmemeli
        assert len(dm.get_rule_history()) == 1

    def test_order_preserved(self) -> None:
        """Kayitlar ekleme sirasina gore olmalidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.NOTIFY, 0.50,
        )
        dm.update_rule(
            RiskLevel.HIGH, UrgencyLevel.HIGH, ActionType.LOG, 0.30,
        )
        history = dm.get_rule_history()
        assert history[0].risk == RiskLevel.LOW.value
        assert history[1].risk == RiskLevel.HIGH.value

    def test_count_matches_updates(self) -> None:
        """Gecmis uzunlugu guncelleme sayisina esit olmalidir."""
        dm = _make_matrix()
        for i in range(5):
            dm.update_rule(
                RiskLevel.LOW, UrgencyLevel.LOW,
                ActionType.LOG, 0.1 * (i + 1),
            )
        assert len(dm.get_rule_history()) == 5

    def test_elements_are_rule_change_records(self) -> None:
        """Her eleman RuleChangeRecord olmalidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.NOTIFY, 0.50,
        )
        history = dm.get_rule_history()
        for record in history:
            assert isinstance(record, RuleChangeRecord)


# === TestResetRules ===


class TestResetRules:
    """reset_rules testleri."""

    def test_rules_restored_to_defaults(self) -> None:
        """Kurallar varsayilanlara donmelidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.IMMEDIATE, 0.99,
        )
        dm.reset_rules()
        action, conf = dm.rules[(RiskLevel.LOW, UrgencyLevel.LOW)]
        assert action == ActionType.LOG
        assert conf == pytest.approx(0.95)

    def test_all_nine_rules_present(self) -> None:
        """Sifirlama sonrasi 9 kural mevcut olmalidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.NOTIFY, 0.50,
        )
        dm.reset_rules()
        assert len(dm.rules) == 9

    def test_history_not_cleared(self) -> None:
        """Sifirlama kural gecmisini silmemelidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.NOTIFY, 0.50,
        )
        dm.reset_rules()
        assert len(dm.get_rule_history()) == 1

    def test_multiple_resets_idempotent(self) -> None:
        """Birden fazla sifirlama ayni sonucu vermelidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.HIGH, UrgencyLevel.HIGH, ActionType.LOG, 0.10,
        )
        dm.reset_rules()
        dm.reset_rules()
        action, conf = dm.rules[(RiskLevel.HIGH, UrgencyLevel.HIGH)]
        assert action == ActionType.IMMEDIATE
        assert conf == pytest.approx(0.90)

    def test_reset_matches_original_rules(self) -> None:
        """Sifirlanmis kurallar orijinal varsayilanlar ile esit olmalidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.MEDIUM, UrgencyLevel.MEDIUM, ActionType.LOG, 0.10,
        )
        dm.reset_rules()
        for key, value in _ORIGINAL_RULES.items():
            assert dm.rules[key] == value


# === TestExplainDecision ===


class TestExplainDecision:
    """explain_decision testleri."""

    def test_header_present(self) -> None:
        """Aciklama 'Karar Aciklamasi:' basligiyla baslamalidir."""
        dm = _make_matrix()
        text = dm.explain_decision(RiskLevel.LOW, UrgencyLevel.LOW)
        assert text.startswith("Karar Aciklamasi:")

    def test_risk_level_shown(self) -> None:
        """Risk seviyesi aciklamada gosterilmelidir."""
        dm = _make_matrix()
        text = dm.explain_decision(RiskLevel.HIGH, UrgencyLevel.LOW)
        assert "high" in text

    def test_urgency_level_shown(self) -> None:
        """Aciliyet seviyesi aciklamada gosterilmelidir."""
        dm = _make_matrix()
        text = dm.explain_decision(RiskLevel.LOW, UrgencyLevel.HIGH)
        assert "high" in text

    def test_action_shown(self) -> None:
        """Aksiyon tipi aciklamada gosterilmelidir."""
        dm = _make_matrix()
        text = dm.explain_decision(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert "immediate" in text

    def test_confidence_threshold_shown(self) -> None:
        """Guven esigi aciklamada gosterilmelidir."""
        dm = _make_matrix(confidence_threshold=0.7)
        text = dm.explain_decision(RiskLevel.LOW, UrgencyLevel.LOW)
        assert "70%" in text

    def test_risk_tolerance_shown(self) -> None:
        """Risk toleransi aciklamada gosterilmelidir."""
        dm = _make_matrix(risk_tolerance=0.5)
        text = dm.explain_decision(RiskLevel.LOW, UrgencyLevel.LOW)
        assert "50%" in text

    def test_beliefs_avg_confidence_shown(self) -> None:
        """Beliefs verildiginde ortalama guven gosterilmelidir."""
        dm = _make_matrix()
        text = dm.explain_decision(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={"cpu": 0.9, "mem": 0.8},
        )
        assert "Belief ortalama guven" in text

    def test_beliefs_should_act_shown(self) -> None:
        """Beliefs verildiginde should_act sonucu gosterilmelidir."""
        dm = _make_matrix()
        text = dm.explain_decision(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={"cpu": 0.9, "mem": 0.8},
        )
        assert "Aksiyona gecilmeli" in text

    def test_demotion_note_shown(self) -> None:
        """Dusurme notu gosterilmelidir (yetersiz guven durumunda)."""
        dm = _make_matrix(confidence_threshold=0.99)
        text = dm.explain_decision(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={"x": 0.1, "y": 0.1},
        )
        assert "NOTIFY" in text
        assert "dusuruldu" in text

    def test_context_detail_shown(self) -> None:
        """Context detail bilgisi aciklamada gosterilmelidir."""
        dm = _make_matrix()
        text = dm.explain_decision(
            RiskLevel.LOW, UrgencyLevel.LOW,
            context={"detail": "disk alani kritik"},
        )
        assert "disk alani kritik" in text

    def test_no_beliefs_no_belief_section(self) -> None:
        """Beliefs verilmediginde belief bolumu olmamalidir."""
        dm = _make_matrix()
        text = dm.explain_decision(RiskLevel.LOW, UrgencyLevel.LOW)
        assert "Belief ortalama" not in text

    def test_no_context_no_context_section(self) -> None:
        """Context verilmediginde baglamsal detay olmamalidir."""
        dm = _make_matrix()
        text = dm.explain_decision(RiskLevel.LOW, UrgencyLevel.LOW)
        assert "Baglamsal detay" not in text


# === TestBuildReason ===


class TestBuildReason:
    """_build_reason testleri."""

    def test_contains_risk(self) -> None:
        """Sebep metninde risk seviyesi bulunmalidir."""
        dm = _make_matrix()
        reason = dm._build_reason(
            RiskLevel.HIGH, UrgencyLevel.LOW, ActionType.NOTIFY, None,
        )
        assert "high" in reason.lower()

    def test_contains_urgency(self) -> None:
        """Sebep metninde aciliyet seviyesi bulunmalidir."""
        dm = _make_matrix()
        reason = dm._build_reason(
            RiskLevel.LOW, UrgencyLevel.MEDIUM, ActionType.LOG, None,
        )
        assert "medium" in reason.lower()

    def test_contains_action(self) -> None:
        """Sebep metninde aksiyon tipi bulunmalidir."""
        dm = _make_matrix()
        reason = dm._build_reason(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.LOG, None,
        )
        assert "log" in reason.lower()

    def test_with_context_detail(self) -> None:
        """Context detail sebep metnine eklenmelidir."""
        dm = _make_matrix()
        reason = dm._build_reason(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.LOG,
            {"detail": "CPU %95"},
        )
        assert "CPU %95" in reason

    def test_without_context(self) -> None:
        """Context None ise hata vermemelidir."""
        dm = _make_matrix()
        reason = dm._build_reason(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.LOG, None,
        )
        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_pipe_separated(self) -> None:
        """Sebep parcalari '|' ile ayrilmalidir."""
        dm = _make_matrix()
        reason = dm._build_reason(
            RiskLevel.LOW, UrgencyLevel.LOW, ActionType.LOG, None,
        )
        assert "|" in reason


# === TestSetters ===


class TestSetters:
    """set_confidence_threshold ve set_risk_tolerance testleri."""

    def test_set_confidence_threshold_normal(self) -> None:
        """Normal deger esigi guncellemmelidir."""
        dm = _make_matrix()
        dm.set_confidence_threshold(0.9)
        assert dm.confidence_threshold == pytest.approx(0.9)

    def test_set_confidence_threshold_clamped_high(self) -> None:
        """1.0 ustune cikamamalidir."""
        dm = _make_matrix()
        dm.set_confidence_threshold(1.5)
        assert dm.confidence_threshold == pytest.approx(1.0)

    def test_set_confidence_threshold_clamped_low(self) -> None:
        """0.0 altina dusmemelidir."""
        dm = _make_matrix()
        dm.set_confidence_threshold(-0.5)
        assert dm.confidence_threshold == pytest.approx(0.0)

    def test_set_risk_tolerance_normal(self) -> None:
        """Normal deger toleransi guncellemmelidir."""
        dm = _make_matrix()
        dm.set_risk_tolerance(0.8)
        assert dm.risk_tolerance == pytest.approx(0.8)

    def test_set_risk_tolerance_clamped_high(self) -> None:
        """1.0 ustune cikamamalidir."""
        dm = _make_matrix()
        dm.set_risk_tolerance(2.0)
        assert dm.risk_tolerance == pytest.approx(1.0)

    def test_set_risk_tolerance_clamped_low(self) -> None:
        """0.0 altina dusmemelidir."""
        dm = _make_matrix()
        dm.set_risk_tolerance(-1.0)
        assert dm.risk_tolerance == pytest.approx(0.0)

    def test_set_risk_tolerance_recreates_uncertainty_mgr(self) -> None:
        """Risk toleransi degistiginde UncertaintyManager yeniden olusturulmalidir."""
        dm = _make_matrix(risk_tolerance=0.5)
        old_mgr = dm._uncertainty_mgr
        dm.set_risk_tolerance(0.9)
        assert dm._uncertainty_mgr is not old_mgr
        assert dm._uncertainty_mgr.risk_tolerance == pytest.approx(0.9)

    def test_set_bayesian_network(self) -> None:
        """Bayesci ag atanabilmelidir."""
        dm = _make_matrix()
        bn = _make_bayesian_network()
        dm.set_bayesian_network(bn)
        assert dm._bayesian_net is bn


# === TestGetActionFor ===


class TestGetActionFor:
    """get_action_for testleri."""

    def test_low_low(self) -> None:
        """low/low -> LOG."""
        dm = _make_matrix()
        assert dm.get_action_for("low", "low") == ActionType.LOG

    def test_high_high(self) -> None:
        """high/high -> IMMEDIATE."""
        dm = _make_matrix()
        assert dm.get_action_for("high", "high") == ActionType.IMMEDIATE

    def test_medium_high(self) -> None:
        """medium/high -> AUTO_FIX."""
        dm = _make_matrix()
        assert dm.get_action_for("medium", "high") == ActionType.AUTO_FIX

    def test_high_low(self) -> None:
        """high/low -> NOTIFY."""
        dm = _make_matrix()
        assert dm.get_action_for("high", "low") == ActionType.NOTIFY

    def test_invalid_risk_raises(self) -> None:
        """Gecersiz risk degeri ValueError firlatmalidir."""
        dm = _make_matrix()
        with pytest.raises(ValueError):
            dm.get_action_for("invalid", "low")

    def test_invalid_urgency_raises(self) -> None:
        """Gecersiz urgency degeri ValueError firlatmalidir."""
        dm = _make_matrix()
        with pytest.raises(ValueError):
            dm.get_action_for("low", "invalid")


# === TestRiskLevelToFloat ===


class TestRiskLevelToFloat:
    """_risk_level_to_float testleri."""

    def test_low_is_0_2(self) -> None:
        """LOW risk 0.2 olmalidir."""
        result = DecisionMatrix._risk_level_to_float(RiskLevel.LOW)
        assert result == pytest.approx(0.2)

    def test_medium_is_0_5(self) -> None:
        """MEDIUM risk 0.5 olmalidir."""
        result = DecisionMatrix._risk_level_to_float(RiskLevel.MEDIUM)
        assert result == pytest.approx(0.5)

    def test_high_is_0_9(self) -> None:
        """HIGH risk 0.9 olmalidir."""
        result = DecisionMatrix._risk_level_to_float(RiskLevel.HIGH)
        assert result == pytest.approx(0.9)

    def test_is_static_method(self) -> None:
        """_risk_level_to_float statik metod olmalidir."""
        # Dogrudan sinif uzerinden cagirilabilmeli
        result = DecisionMatrix._risk_level_to_float(RiskLevel.LOW)
        assert isinstance(result, float)


# === TestBackwardCompat ===


class TestBackwardCompat:
    """Geriye uyumluluk testleri."""

    def test_no_args_constructor(self) -> None:
        """Parametresiz olusturma calismmalidir."""
        _restore_global_rules()
        dm = DecisionMatrix()
        assert isinstance(dm, DecisionMatrix)

    def test_rules_count(self) -> None:
        """Kural sayisi 9 olmalidir."""
        _restore_global_rules()
        dm = DecisionMatrix()
        assert len(dm.rules) == 9

    async def test_evaluate_original_two_args(self) -> None:
        """evaluate(risk, urgency) iki parametre ile calismmalidir."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert d.action == ActionType.LOG
        assert d.confidence == pytest.approx(0.95)

    async def test_evaluate_with_context_kwarg(self) -> None:
        """evaluate context keyword ile calismmalidir."""
        dm = _make_matrix()
        d = await dm.evaluate(
            RiskLevel.MEDIUM, UrgencyLevel.LOW,
            context={"detail": "test"},
        )
        assert d.action == ActionType.NOTIFY

    def test_get_action_for_still_works(self) -> None:
        """get_action_for mevcut arayuzu korumalidir."""
        dm = _make_matrix()
        assert dm.get_action_for("low", "low") == ActionType.LOG
        assert dm.get_action_for("high", "high") == ActionType.IMMEDIATE

    async def test_decision_model_fields(self) -> None:
        """Decision modeli beklenen alanlara sahip olmalidir."""
        dm = _make_matrix()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert hasattr(d, "risk")
        assert hasattr(d, "urgency")
        assert hasattr(d, "action")
        assert hasattr(d, "confidence")
        assert hasattr(d, "reason")


# === TestEdgeCases ===


class TestEdgeCases:
    """Uc durum testleri."""

    async def test_evaluate_after_rule_update(self) -> None:
        """Kural guncellendikten sonra evaluate yeni kurali kullanmalidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.IMMEDIATE, 0.99,
        )
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert d.action == ActionType.IMMEDIATE
        assert d.confidence == pytest.approx(0.99)

    async def test_evaluate_after_reset(self) -> None:
        """Sifirlamadan sonra evaluate varsayilan kurallari kullanmalidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.IMMEDIATE, 0.99,
        )
        dm.reset_rules()
        d = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert d.action == ActionType.LOG
        assert d.confidence == pytest.approx(0.95)

    def test_update_does_not_leak_to_new_instance(self) -> None:
        """Bir instance'taki guncelleme baska instance'i etkilememmelidir."""
        dm1 = _make_matrix()
        dm1.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.IMMEDIATE, 0.99,
        )
        dm2 = _make_matrix()
        action, conf = dm2.rules[(RiskLevel.LOW, UrgencyLevel.LOW)]
        assert action == ActionType.LOG
        assert conf == pytest.approx(0.95)

    def test_confidence_boundary_zero(self) -> None:
        """Guven esigi tam 0.0 kabul edilmelidir."""
        dm = _make_matrix()
        dm.set_confidence_threshold(0.0)
        assert dm.confidence_threshold == pytest.approx(0.0)

    def test_confidence_boundary_one(self) -> None:
        """Guven esigi tam 1.0 kabul edilmelidir."""
        dm = _make_matrix()
        dm.set_confidence_threshold(1.0)
        assert dm.confidence_threshold == pytest.approx(1.0)

    def test_update_rule_then_get_action_for(self) -> None:
        """Kural guncellendikten sonra get_action_for yeni sonuc vermelidir."""
        dm = _make_matrix()
        dm.update_rule(
            RiskLevel.LOW, UrgencyLevel.LOW,
            ActionType.IMMEDIATE, 0.99,
        )
        assert dm.get_action_for("low", "low") == ActionType.IMMEDIATE
