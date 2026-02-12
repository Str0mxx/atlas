"""MasterAgent unit testleri.

Akilli agent secimi, karar matrisi entegrasyonu, eskalasyon mantigi,
karar denetim izi, onay is akisi ve rapor formatlama testleri.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.decision_matrix import ActionType, Decision, DecisionMatrix, RiskLevel, UrgencyLevel
from app.core.master_agent import AGENT_KEYWORDS, MasterAgent
from app.models.decision import (
    ApprovalRequest,
    ApprovalStatus,
    DecisionAuditEntry,
    DecisionCreate,
    EscalationLevel,
    EscalationRecord,
)


# === Yardimci Fonksiyonlar ===


def _make_master(enable_escalation: bool = False) -> MasterAgent:
    """Test icin temiz MasterAgent olusturur."""
    return MasterAgent(enable_escalation=enable_escalation)


def _make_mock_agent(name: str = "TestAgent", success: bool = True) -> MagicMock:
    """Test icin sahte agent olusturur."""
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    if success:
        agent.run = AsyncMock(return_value=TaskResult(success=True, message="ok"))
    else:
        agent.run = AsyncMock(
            return_value=TaskResult(success=False, message="hata", errors=["test_error"]),
        )
    return agent


def _make_task(
    description: str = "test gorevi",
    risk: str = "low",
    urgency: str = "low",
    target_agent: str | None = None,
) -> dict:
    """Test icin gorev sozlugu olusturur."""
    task: dict = {"description": description, "risk": risk, "urgency": urgency}
    if target_agent:
        task["target_agent"] = target_agent
    return task


def _make_telegram_bot() -> MagicMock:
    """Test icin sahte Telegram bot olusturur."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_buttons = AsyncMock()
    return bot


def _make_decision(
    risk: RiskLevel = RiskLevel.LOW,
    urgency: UrgencyLevel = UrgencyLevel.LOW,
    action: ActionType = ActionType.LOG,
    confidence: float = 0.9,
    reason: str = "test karari",
) -> Decision:
    """Test icin karar nesnesi olusturur."""
    return Decision(
        risk=risk,
        urgency=urgency,
        action=action,
        confidence=confidence,
        reason=reason,
    )


# === TestMasterAgentInit ===


class TestMasterAgentInit:
    """MasterAgent baslatma testleri."""

    def test_default_name(self) -> None:
        """Varsayilan isim 'MasterAgent' olmalidir."""
        master = _make_master()
        assert master.name == "MasterAgent"

    def test_decision_matrix_created(self) -> None:
        """DecisionMatrix otomatik olusturulmalidir."""
        master = _make_master()
        assert isinstance(master.decision_matrix, DecisionMatrix)

    def test_agents_dict_empty(self) -> None:
        """Baslangicta kayitli agent olmamalidir."""
        master = _make_master()
        assert master.agents == {}

    def test_telegram_bot_none(self) -> None:
        """Baslangicta telegram_bot None olmalidir."""
        master = _make_master()
        assert master.telegram_bot is None

    def test_escalation_disabled_by_default(self) -> None:
        """Varsayilan olarak eskalasyon kapali olmalidir."""
        master = _make_master()
        assert master.enable_escalation is False

    def test_escalation_enabled(self) -> None:
        """enable_escalation=True ile aktif olmalidir."""
        master = _make_master(enable_escalation=True)
        assert master.enable_escalation is True

    def test_decision_history_empty(self) -> None:
        """Baslangicta karar gecmisi bos olmalidir."""
        master = _make_master()
        assert master.decision_history == []

    def test_max_history_default(self) -> None:
        """Maks gecmis boyutu 1000 olmalidir."""
        master = _make_master()
        assert master._max_history == 1000

    def test_pending_approvals_empty(self) -> None:
        """Baslangicta bekleyen onay olmamalidir."""
        master = _make_master()
        assert master.pending_approvals == {}

    def test_escalation_history_empty(self) -> None:
        """Baslangicta eskalasyon gecmisi bos olmalidir."""
        master = _make_master()
        assert master.escalation_history == []


# === TestRegisterAgent ===


class TestRegisterAgent:
    """Agent kayit testleri."""

    def test_register_single_agent(self) -> None:
        """Tek agent kaydi basarili olmalidir."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        assert "SecurityAgent" in master.agents

    def test_register_overwrites_same_name(self) -> None:
        """Ayni isimli agent kaydi ustune yazilmalidir."""
        master = _make_master()
        agent1 = _make_mock_agent("SecurityAgent")
        agent2 = _make_mock_agent("SecurityAgent")
        master.register_agent(agent1)
        master.register_agent(agent2)
        assert master.agents["SecurityAgent"] is agent2

    def test_register_multiple_agents(self) -> None:
        """Birden fazla agent kaydedilebilmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("AgentA"))
        master.register_agent(_make_mock_agent("AgentB"))
        master.register_agent(_make_mock_agent("AgentC"))
        assert len(master.agents) == 3

    def test_get_registered_agents_empty(self) -> None:
        """Agent yokken bos liste donmelidir."""
        master = _make_master()
        result = master.get_registered_agents()
        assert result == []

    def test_get_registered_agents_full(self) -> None:
        """Kayitli agent'lar get_info ile listelenmelidir."""
        master = _make_master()
        agent = _make_mock_agent("TestAgent")
        agent.get_info = MagicMock(return_value={"name": "TestAgent", "status": "idle"})
        master.register_agent(agent)
        result = master.get_registered_agents()
        assert len(result) == 1
        assert result[0]["name"] == "TestAgent"

    def test_registered_agent_accessible_by_name(self) -> None:
        """Kayitli agent isim ile erisilebilir olmalidir."""
        master = _make_master()
        agent = _make_mock_agent("MarketingAgent")
        master.register_agent(agent)
        assert master.agents["MarketingAgent"] is agent


# === TestSelectAgent ===


class TestSelectAgent:
    """Akilli agent secim testleri."""

    def test_explicit_target_agent(self) -> None:
        """target_agent acikca belirtilmisse onu donmelidir."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        task = _make_task(target_agent="SecurityAgent")
        result = master.select_agent(task)
        assert result == "SecurityAgent"

    def test_explicit_target_unregistered(self) -> None:
        """Kayitli olmayan target_agent icin None donmelidir."""
        master = _make_master()
        task = _make_task(target_agent="GhostAgent")
        result = master.select_agent(task)
        # target_agent kayitli degil, keyword matching'e duser
        # Agent kayitli olmadigi icin None donecek
        assert result is None

    def test_keyword_security(self) -> None:
        """Guvenlik anahtar kelimeleri SecurityAgent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("SecurityAgent"))
        task = _make_task(description="firewall kurallari guncelle")
        result = master.select_agent(task)
        assert result == "SecurityAgent"

    def test_keyword_server_monitor(self) -> None:
        """Sunucu anahtar kelimeleri server_monitor agent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("server_monitor_agent"))
        task = _make_task(description="CPU kullanimi cok yuksek")
        result = master.select_agent(task)
        assert result == "server_monitor_agent"

    def test_keyword_marketing(self) -> None:
        """Pazarlama anahtar kelimeleri MarketingAgent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("MarketingAgent"))
        task = _make_task(description="Google Ads kampanya optimizasyonu")
        result = master.select_agent(task)
        assert result == "MarketingAgent"

    def test_keyword_research(self) -> None:
        """Arastirma anahtar kelimeleri ResearchAgent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("ResearchAgent"))
        task = _make_task(description="tedarikci arastirmasi yap")
        result = master.select_agent(task)
        assert result == "ResearchAgent"

    def test_keyword_communication(self) -> None:
        """Iletisim anahtar kelimeleri CommunicationAgent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("CommunicationAgent"))
        task = _make_task(description="email gonder musteri yaniti")
        result = master.select_agent(task)
        assert result == "CommunicationAgent"

    def test_keyword_coding(self) -> None:
        """Kod anahtar kelimeleri CodingAgent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("CodingAgent"))
        task = _make_task(description="bug fix deployment yapilacak")
        result = master.select_agent(task)
        assert result == "CodingAgent"

    def test_keyword_analysis(self) -> None:
        """Analiz anahtar kelimeleri AnalysisAgent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("AnalysisAgent"))
        task = _make_task(description="satis raporu ve performans analizi")
        result = master.select_agent(task)
        assert result == "AnalysisAgent"

    def test_keyword_creative(self) -> None:
        """Yaratici anahtar kelimeleri CreativeAgent'i secmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("CreativeAgent"))
        task = _make_task(description="yeni logo tasarimi yapilacak")
        result = master.select_agent(task)
        assert result == "CreativeAgent"

    def test_no_match_returns_none(self) -> None:
        """Hicbir anahtar kelime eslesmezse None donmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("SecurityAgent"))
        task = _make_task(description="tamamen alakasiz bir cumle xyz")
        result = master.select_agent(task)
        assert result is None

    def test_multiple_keywords_best_score(self) -> None:
        """Birden fazla anahtar kelime olan agent yuksek skorla secilmelidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("SecurityAgent"))
        master.register_agent(_make_mock_agent("CodingAgent"))
        # Guvenlik kelimeleri daha fazla: firewall, ssl, hack
        task = _make_task(description="firewall ssl hack kontrol et")
        result = master.select_agent(task)
        assert result == "SecurityAgent"

    def test_turkish_keywords(self) -> None:
        """Turkce anahtar kelimeler de eslesmeli."""
        master = _make_master()
        master.register_agent(_make_mock_agent("SecurityAgent"))
        task = _make_task(description="guvenlik saldiri tespit edildi")
        result = master.select_agent(task)
        assert result == "SecurityAgent"

    def test_case_insensitive_description(self) -> None:
        """Buyuk/kucuk harf duyarsiz esleme yapmalidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("SecurityAgent"))
        task = _make_task(description="FIREWALL kurallari guncelleniyor")
        result = master.select_agent(task)
        assert result == "SecurityAgent"

    def test_no_agents_registered(self) -> None:
        """Kayitli agent yoksa keyword match bile None donmelidir."""
        master = _make_master()
        task = _make_task(description="firewall kontrolu")
        result = master.select_agent(task)
        assert result is None

    def test_agent_type_in_name_matching(self) -> None:
        """Agent adi, agent_type'i iceriyorsa eslesmelidir."""
        master = _make_master()
        # 'security' anahtar kelimesi 'MySecurityBot' icinde var
        master.register_agent(_make_mock_agent("MySecurityBot"))
        task = _make_task(description="hack denemesi tespit edildi")
        result = master.select_agent(task)
        assert result == "MySecurityBot"


# === TestExecuteEnhanced ===


class TestExecuteEnhanced:
    """Gelistirilmis execute testleri."""

    async def test_low_risk_low_urgency_logs(self) -> None:
        """Dusuk risk + dusuk aciliyet = LOG aksiyonu."""
        master = _make_master()
        task = _make_task(risk="low", urgency="low")
        result = await master.execute(task)
        assert result.success is True
        assert "kaydedildi" in result.message.lower()

    async def test_low_risk_high_urgency_notifies(self) -> None:
        """Dusuk risk + yuksek aciliyet = NOTIFY aksiyonu."""
        master = _make_master()
        task = _make_task(risk="low", urgency="high")
        result = await master.execute(task)
        assert result.success is True
        assert "bildirim" in result.message.lower()

    async def test_medium_risk_high_urgency_auto_fix(self) -> None:
        """Orta risk + yuksek aciliyet = AUTO_FIX aksiyonu."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        task = _make_task(
            description="firewall acik guvenlik",
            risk="medium",
            urgency="high",
            target_agent="SecurityAgent",
        )
        result = await master.execute(task)
        assert result.success is True

    async def test_high_risk_high_urgency_immediate(self) -> None:
        """Yuksek risk + yuksek aciliyet = IMMEDIATE aksiyonu."""
        master = _make_master()
        task = _make_task(risk="high", urgency="high")
        result = await master.execute(task)
        assert result.success is True

    async def test_high_risk_medium_urgency_auto_fix(self) -> None:
        """Yuksek risk + orta aciliyet = AUTO_FIX aksiyonu."""
        master = _make_master()
        task = _make_task(risk="high", urgency="medium")
        result = await master.execute(task)
        # Agent yoksa basarisiz donecek
        assert result.success is False

    async def test_medium_risk_low_urgency_notify(self) -> None:
        """Orta risk + dusuk aciliyet = NOTIFY aksiyonu."""
        master = _make_master()
        task = _make_task(risk="medium", urgency="low")
        result = await master.execute(task)
        assert result.success is True
        assert "bildirim" in result.message.lower()

    async def test_auto_agent_selection_in_execute(self) -> None:
        """Execute sirasinda otomatik agent secimi yapilmalidir."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        task = _make_task(
            description="firewall guvenlik kontrolu",
            risk="medium",
            urgency="high",
        )
        result = await master.execute(task)
        assert result.success is True
        agent.run.assert_called_once()

    async def test_audit_trail_recorded(self) -> None:
        """Her execute cagrisinda denetim izi kaydedilmelidir."""
        master = _make_master()
        task = _make_task(description="test denetim izi")
        await master.execute(task)
        assert len(master.decision_history) == 1
        entry = master.decision_history[0]
        assert entry.task_description == "test denetim izi"

    async def test_audit_outcome_success(self) -> None:
        """Basarili gorevde audit outcome_success True olmalidir."""
        master = _make_master()
        task = _make_task(risk="low", urgency="low")
        await master.execute(task)
        assert master.decision_history[0].outcome_success is True

    async def test_audit_outcome_failure(self) -> None:
        """Basarisiz gorevde audit outcome_success False olmalidir."""
        master = _make_master()
        # high risk, medium urgency -> AUTO_FIX, agent yok -> basarisiz
        task = _make_task(risk="high", urgency="medium")
        await master.execute(task)
        assert master.decision_history[0].outcome_success is False

    async def test_escalation_triggered_on_failure(self) -> None:
        """Eskalasyon aktifken basarisiz AUTO_FIX eskalasyon tetiklemeli."""
        master = _make_master(enable_escalation=True)
        failing = _make_mock_agent("SecurityAgent", success=False)
        master.register_agent(failing)
        task = _make_task(
            description="guvenlik kontrolu",
            risk="medium",
            urgency="high",
            target_agent="SecurityAgent",
        )
        result = await master.execute(task)
        # AUTO_FIX basarisiz -> IMMEDIATE'a eskalasyon
        assert len(master.escalation_history) == 1

    async def test_escalation_not_triggered_when_disabled(self) -> None:
        """Eskalasyon kapaliyken basarisiz gorev eskalasyon tetiklememeli."""
        master = _make_master(enable_escalation=False)
        failing = _make_mock_agent("SecurityAgent", success=False)
        master.register_agent(failing)
        task = _make_task(
            description="guvenlik kontrolu",
            risk="medium",
            urgency="high",
            target_agent="SecurityAgent",
        )
        await master.execute(task)
        assert len(master.escalation_history) == 0


# === TestRouteAction ===


class TestRouteAction:
    """Aksiyon yonlendirme testleri."""

    async def test_route_log(self) -> None:
        """LOG aksiyonu _handle_log'a yonlendirmeli."""
        master = _make_master()
        task = _make_task()
        result = await master._route_action(task, ActionType.LOG)
        assert result.success is True
        assert "kaydedildi" in result.message.lower()

    async def test_route_notify(self) -> None:
        """NOTIFY aksiyonu _handle_notify'a yonlendirmeli."""
        master = _make_master()
        task = _make_task()
        result = await master._route_action(task, ActionType.NOTIFY)
        assert result.success is True
        assert "bildirim" in result.message.lower()

    async def test_route_auto_fix_with_agent(self) -> None:
        """AUTO_FIX aksiyonu hedef agent'i calistirmali."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        task = _make_task(target_agent="SecurityAgent")
        result = await master._route_action(task, ActionType.AUTO_FIX)
        assert result.success is True
        agent.run.assert_called_once()

    async def test_route_auto_fix_no_agent(self) -> None:
        """AUTO_FIX aksiyonu agent yoksa basarisiz olmali."""
        master = _make_master()
        task = _make_task(target_agent="GhostAgent")
        result = await master._route_action(task, ActionType.AUTO_FIX)
        assert result.success is False

    async def test_route_immediate(self) -> None:
        """IMMEDIATE aksiyonu _handle_immediate'a yonlendirmeli."""
        master = _make_master()
        task = _make_task()
        result = await master._route_action(task, ActionType.IMMEDIATE)
        assert result.success is True

    async def test_route_immediate_with_agent(self) -> None:
        """IMMEDIATE aksiyonu hedef agent varsa calistirmali."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        task = _make_task(target_agent="SecurityAgent")
        result = await master._route_action(task, ActionType.IMMEDIATE)
        assert result.success is True
        agent.run.assert_called_once()

    async def test_route_notify_with_telegram(self) -> None:
        """NOTIFY aksiyonunda telegram varsa mesaj gondermeli."""
        master = _make_master()
        bot = _make_telegram_bot()
        master.telegram_bot = bot
        task = _make_task(description="onemli bildirim")
        await master._route_action(task, ActionType.NOTIFY)
        bot.send_message.assert_called_once()

    async def test_route_notify_without_telegram(self) -> None:
        """NOTIFY aksiyonunda telegram yoksa hata olmamali."""
        master = _make_master()
        task = _make_task()
        result = await master._route_action(task, ActionType.NOTIFY)
        assert result.success is True


# === TestHandleAutoFix ===


class TestHandleAutoFix:
    """Otomatik duzeltme isleyici testleri."""

    async def test_with_target_agent(self) -> None:
        """Hedef agent varsa calistirilmalidir."""
        master = _make_master()
        agent = _make_mock_agent("FixerAgent")
        master.register_agent(agent)
        task = _make_task(target_agent="FixerAgent")
        result = await master._handle_auto_fix(task)
        assert result.success is True
        agent.run.assert_called_once_with(task)

    async def test_no_target_with_fallback(self) -> None:
        """Hedef agent yoksa otomatik secim ile fallback yapilmalidir."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        task = _make_task(description="firewall guvenlik acigi")
        result = await master._handle_auto_fix(task)
        assert result.success is True
        agent.run.assert_called_once()

    async def test_no_target_no_fallback(self) -> None:
        """Hedef agent ve fallback yoksa basarisiz donmeli."""
        master = _make_master()
        task = _make_task(description="tamamen bilinmeyen gorev xyz")
        result = await master._handle_auto_fix(task)
        assert result.success is False
        assert "bulunamadi" in result.message.lower()

    async def test_agent_returns_error(self) -> None:
        """Agent hata dondururse sonuc basarisiz olmalidir."""
        master = _make_master()
        agent = _make_mock_agent("FailAgent", success=False)
        master.register_agent(agent)
        task = _make_task(target_agent="FailAgent")
        result = await master._handle_auto_fix(task)
        assert result.success is False
        assert result.message == "hata"

    async def test_unregistered_target_tries_auto_select(self) -> None:
        """Kayitli olmayan target_agent icin otomatik secim denenmeli."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        # target_agent kayitli degil ama description security kelimesi iceriyor
        task = _make_task(
            description="security firewall kontrol",
            target_agent="GhostAgent",
        )
        result = await master._handle_auto_fix(task)
        assert result.success is True
        agent.run.assert_called_once()

    async def test_with_target_agent_returns_data(self) -> None:
        """Agent'in dondurdugu TaskResult korunmalidir."""
        master = _make_master()
        agent = _make_mock_agent("WorkerAgent")
        agent.run = AsyncMock(
            return_value=TaskResult(
                success=True, message="fix tamamlandi", data={"fixed": True},
            ),
        )
        master.register_agent(agent)
        task = _make_task(target_agent="WorkerAgent")
        result = await master._handle_auto_fix(task)
        assert result.data == {"fixed": True}


# === TestHandleImmediate ===


class TestHandleImmediate:
    """Acil mudahale isleyici testleri."""

    async def test_without_telegram(self) -> None:
        """Telegram olmadan acil mudahale basarili olmalidir."""
        master = _make_master()
        task = _make_task(description="acil durum")
        result = await master._handle_immediate(task)
        assert result.success is True
        assert "acil" in result.message.lower()

    async def test_with_telegram_sends_buttons(self) -> None:
        """Telegram varsa butonlu mesaj gondermeli."""
        master = _make_master()
        bot = _make_telegram_bot()
        master.telegram_bot = bot
        task = _make_task(description="kritik durum")
        await master._handle_immediate(task)
        bot.send_buttons.assert_called_once()
        call_kwargs = bot.send_buttons.call_args
        assert "ACIL" in call_kwargs.kwargs.get("text", call_kwargs[1].get("text", ""))

    async def test_with_target_agent_runs_agent(self) -> None:
        """Hedef agent varsa acil mudahale sirasinda calistirilmali."""
        master = _make_master()
        agent = _make_mock_agent("SecurityAgent")
        master.register_agent(agent)
        task = _make_task(target_agent="SecurityAgent")
        result = await master._handle_immediate(task)
        assert result.success is True
        agent.run.assert_called_once()

    async def test_without_target_agent_no_run(self) -> None:
        """Hedef agent yoksa agent calistirilmadan basarili donmeli."""
        master = _make_master()
        task = _make_task(description="genel acil durum")
        result = await master._handle_immediate(task)
        assert result.success is True
        assert "baslatildi" in result.message.lower()

    async def test_telegram_error_handled(self) -> None:
        """Telegram hatasi yakalanaarak islem surmelidir."""
        master = _make_master()
        bot = _make_telegram_bot()
        bot.send_buttons = AsyncMock(side_effect=Exception("telegram baglanti hatasi"))
        master.telegram_bot = bot
        task = _make_task(description="acil durum telegram hata")
        result = await master._handle_immediate(task)
        # Telegram hatasi sonucu etkilememeli
        assert result.success is True


# === TestEscalation ===


class TestEscalation:
    """Eskalasyon mantigi testleri."""

    async def test_auto_fix_escalates_to_immediate(self) -> None:
        """AUTO_FIX basarisiz olursa IMMEDIATE'a yukselmelidir."""
        master = _make_master(enable_escalation=True)
        task = _make_task(description="sistem hatasi")
        result = await master._escalate(
            task, ActionType.AUTO_FIX, "TestAgent", "agent basarisiz",
        )
        # IMMEDIATE handler cagrilmali
        assert result.success is True

    async def test_auto_fix_escalation_record(self) -> None:
        """AUTO_FIX eskalasyonu gecmise kaydedilmelidir."""
        master = _make_master(enable_escalation=True)
        task = _make_task(description="sistem hatasi")
        await master._escalate(task, ActionType.AUTO_FIX, "TestAgent", "hata")
        assert len(master.escalation_history) == 1
        record = master.escalation_history[0]
        assert record.original_action == "auto_fix"
        assert record.escalated_action == "immediate"
        assert record.level == EscalationLevel.NOTIFY_HUMAN

    async def test_immediate_finds_alternate_agent(self) -> None:
        """IMMEDIATE basarisiz olursa alternatif agent denenmeli."""
        master = _make_master(enable_escalation=True)
        alt_agent = _make_mock_agent("SecurityBackup")
        master.register_agent(alt_agent)
        task = _make_task(description="guvenlik security hatasi")
        result = await master._escalate(
            task, ActionType.IMMEDIATE, "OriginalAgent", "hata",
        )
        assert result.success is True
        alt_agent.run.assert_called_once()

    async def test_alternate_agent_escalation_record(self) -> None:
        """Alternatif agent eskalasyonu gecmise kaydedilmelidir."""
        master = _make_master(enable_escalation=True)
        alt_agent = _make_mock_agent("SecurityBackup")
        master.register_agent(alt_agent)
        task = _make_task(description="guvenlik security hatasi")
        await master._escalate(
            task, ActionType.IMMEDIATE, "OriginalAgent", "agent_hata",
        )
        assert len(master.escalation_history) == 1
        record = master.escalation_history[0]
        assert record.level == EscalationLevel.ALTERNATE_AGENT
        assert record.escalated_agent == "SecurityBackup"

    async def test_no_alternate_falls_to_notify(self) -> None:
        """Alternatif agent yoksa NOTIFY'a dusmelidir."""
        master = _make_master(enable_escalation=True)
        task = _make_task(description="tamamen bilinmeyen gorev xyz")
        result = await master._escalate(
            task, ActionType.IMMEDIATE, "OriginalAgent", "hata",
        )
        assert result.success is True
        assert "bildirim" in result.message.lower()

    async def test_no_alternate_notify_record(self) -> None:
        """Notify'a dusme eskalasyonu gecmise kaydedilmelidir."""
        master = _make_master(enable_escalation=True)
        task = _make_task(description="bilinmeyen gorev xyz")
        await master._escalate(
            task, ActionType.IMMEDIATE, "OriginalAgent", "hata",
        )
        record = master.escalation_history[0]
        assert record.escalated_action == "notify"
        assert record.level == EscalationLevel.NOTIFY_HUMAN

    async def test_escalation_history_tracking_multiple(self) -> None:
        """Birden fazla eskalasyon gecmiste izlenebilmeli."""
        master = _make_master(enable_escalation=True)
        task1 = _make_task(description="hata 1")
        task2 = _make_task(description="hata 2")
        await master._escalate(task1, ActionType.AUTO_FIX, "A1", "err1")
        await master._escalate(task2, ActionType.AUTO_FIX, "A2", "err2")
        assert len(master.escalation_history) == 2

    async def test_escalation_record_reason_preserved(self) -> None:
        """Eskalasyon nedeni kayitta korunmalidir."""
        master = _make_master(enable_escalation=True)
        task = _make_task(description="test hatasi")
        await master._escalate(
            task, ActionType.AUTO_FIX, "TestAgent", "bellek yetersiz",
        )
        record = master.escalation_history[0]
        assert record.reason == "bellek yetersiz"

    async def test_escalation_record_original_agent(self) -> None:
        """Eskalasyon kaydinda orijinal agent saklanmalidir."""
        master = _make_master(enable_escalation=True)
        task = _make_task(description="orijinal agent hatasi")
        await master._escalate(
            task, ActionType.AUTO_FIX, "OriginalAgent", "hata",
        )
        record = master.escalation_history[0]
        assert record.original_agent == "OriginalAgent"

    def test_find_alternate_agent_found(self) -> None:
        """Keyword eslesen alternatif agent bulunmalidir."""
        master = _make_master()
        master.register_agent(_make_mock_agent("SecurityPrimary"))
        master.register_agent(_make_mock_agent("SecurityBackup"))
        task = _make_task(description="guvenlik security kontrol")
        alt = master._find_alternate_agent(task, "SecurityPrimary")
        assert alt == "SecurityBackup"

    def test_find_alternate_agent_not_found(self) -> None:
        """Keyword eslesen alternatif agent yoksa None donmeli."""
        master = _make_master()
        task = _make_task(description="tamamen bilinmeyen xyz")
        alt = master._find_alternate_agent(task, "SomeAgent")
        assert alt is None

    def test_find_alternate_excludes_original(self) -> None:
        """Alternatif agent aranirken orijinal agent haric tutulmali."""
        master = _make_master()
        master.register_agent(_make_mock_agent("SecurityAgent"))
        task = _make_task(description="guvenlik security kontrol")
        alt = master._find_alternate_agent(task, "SecurityAgent")
        # Tek security agent var ve o haric tutuluyor
        assert alt is None


# === TestDecisionAudit ===


class TestDecisionAudit:
    """Karar denetim izi testleri."""

    def test_record_creates_entry(self) -> None:
        """_record_decision gecerli bir DecisionAuditEntry olusturmalidir."""
        master = _make_master()
        decision = _make_decision()
        task = _make_task(description="denetim testi")
        entry = master._record_decision(task, decision, "TestAgent", "explicit")
        assert isinstance(entry, DecisionAuditEntry)
        assert entry.task_description == "denetim testi"

    def test_record_populates_fields(self) -> None:
        """Denetim kaydinda tum alanlar doldurulmalidir."""
        master = _make_master()
        decision = _make_decision(
            risk=RiskLevel.HIGH, urgency=UrgencyLevel.MEDIUM,
            action=ActionType.AUTO_FIX, confidence=0.75,
        )
        task = _make_task(description="alan testi")
        entry = master._record_decision(task, decision, "AgentX", "keyword")
        assert entry.risk == "high"
        assert entry.urgency == "medium"
        assert entry.action == "auto_fix"
        assert entry.confidence == 0.75
        assert entry.agent_selected == "AgentX"
        assert entry.agent_selection_method == "keyword"

    def test_record_appends_to_history(self) -> None:
        """Her kayit decision_history'ye eklenmeli."""
        master = _make_master()
        decision = _make_decision()
        task = _make_task()
        master._record_decision(task, decision, None, "none")
        master._record_decision(task, decision, None, "none")
        assert len(master.decision_history) == 2

    def test_history_limit_enforced(self) -> None:
        """Gecmis boyutu _max_history'yi gecmemeli."""
        master = _make_master()
        master._max_history = 5
        decision = _make_decision()
        for i in range(10):
            task = _make_task(description=f"gorev_{i}")
            master._record_decision(task, decision, None, "none")
        assert len(master.decision_history) == 5
        # Son 5 kayit kalmiyor olmali
        assert master.decision_history[0].task_description == "gorev_5"

    def test_get_history_default_limit(self) -> None:
        """Varsayilan limit ile gecmis dondurulmeli."""
        master = _make_master()
        decision = _make_decision()
        for i in range(60):
            task = _make_task(description=f"gorev_{i}")
            master._record_decision(task, decision, None, "none")
        result = master.get_decision_history()  # varsayilan limit=50
        assert len(result) == 50

    def test_get_history_custom_limit(self) -> None:
        """Ozel limit ile gecmis dondurulmeli."""
        master = _make_master()
        decision = _make_decision()
        for i in range(20):
            task = _make_task(description=f"gorev_{i}")
            master._record_decision(task, decision, None, "none")
        result = master.get_decision_history(limit=5)
        assert len(result) == 5

    def test_get_history_filter_by_action(self) -> None:
        """Aksiyon filtresi ile gecmis filtrelenmeli."""
        master = _make_master()
        log_decision = _make_decision(action=ActionType.LOG)
        notify_decision = _make_decision(action=ActionType.NOTIFY)
        for _ in range(3):
            master._record_decision(_make_task(), log_decision, None, "none")
        for _ in range(2):
            master._record_decision(_make_task(), notify_decision, None, "none")
        result = master.get_decision_history(action_filter="log")
        assert len(result) == 3
        assert all(e.action == "log" for e in result)

    def test_get_history_filter_returns_empty(self) -> None:
        """Eslesmayan filtre bos liste dondurmeli."""
        master = _make_master()
        decision = _make_decision(action=ActionType.LOG)
        master._record_decision(_make_task(), decision, None, "none")
        result = master.get_decision_history(action_filter="immediate")
        assert result == []

    def test_escalated_from_recorded(self) -> None:
        """Eskalasyon kaynagi kayitta saklanmalidir."""
        master = _make_master()
        decision = _make_decision(action=ActionType.IMMEDIATE)
        task = _make_task()
        entry = master._record_decision(
            task, decision, "AgentX", "keyword", escalated_from="auto_fix",
        )
        assert entry.escalated_from == "auto_fix"

    def test_selection_method_none(self) -> None:
        """Agent secilmediginde method 'none' olmalidir."""
        master = _make_master()
        decision = _make_decision()
        task = _make_task()
        entry = master._record_decision(task, decision, None, "none")
        assert entry.agent_selection_method == "none"
        assert entry.agent_selected is None


# === TestApprovalWorkflow ===


class TestApprovalWorkflow:
    """Onay is akisi testleri."""

    async def test_request_creates_approval(self) -> None:
        """Onay istegi basarili olusturulmalidir."""
        master = _make_master()
        task = _make_task(description="onayli gorev")
        decision = _make_decision(action=ActionType.AUTO_FIX)
        approval = await master.request_approval(
            task, ActionType.AUTO_FIX, decision,
        )
        assert isinstance(approval, ApprovalRequest)
        assert approval.status == ApprovalStatus.PENDING

    async def test_request_stored_in_pending(self) -> None:
        """Onay istegi pending_approvals'a eklenmeli."""
        master = _make_master()
        task = _make_task()
        decision = _make_decision()
        approval = await master.request_approval(task, ActionType.LOG, decision)
        assert approval.id in master.pending_approvals

    async def test_request_approval_task_preserved(self) -> None:
        """Onay istegindeki gorev bilgisi korunmalidir."""
        master = _make_master()
        task = _make_task(description="kritik gorev")
        decision = _make_decision()
        approval = await master.request_approval(task, ActionType.AUTO_FIX, decision)
        assert approval.task["description"] == "kritik gorev"

    async def test_approval_executes_action(self) -> None:
        """Onay verilince aksiyon calistirilmalidir."""
        master = _make_master()
        task = _make_task(description="onaylanan gorev", risk="low", urgency="low")
        decision = _make_decision(action=ActionType.LOG)
        approval = await master.request_approval(task, ActionType.LOG, decision)
        result = await master.handle_approval_response(approval.id, approved=True)
        assert result.success is True

    async def test_rejection_returns_success(self) -> None:
        """Red yaniti basarili donmeli ve 'reddedildi' icermeli."""
        master = _make_master()
        task = _make_task(description="reddedilecek gorev")
        decision = _make_decision()
        approval = await master.request_approval(task, ActionType.LOG, decision)
        result = await master.handle_approval_response(approval.id, approved=False)
        assert result.success is True
        assert "reddedildi" in result.message.lower()

    async def test_rejection_sets_status(self) -> None:
        """Red yaniti ApprovalStatus.REJECTED ayarlamali."""
        master = _make_master()
        task = _make_task()
        decision = _make_decision()
        approval = await master.request_approval(task, ActionType.LOG, decision)
        await master.handle_approval_response(approval.id, approved=False)
        assert approval.status == ApprovalStatus.REJECTED

    async def test_unknown_approval_id(self) -> None:
        """Bilinmeyen approval_id basarisiz donmeli."""
        master = _make_master()
        result = await master.handle_approval_response("nonexistent-id", approved=True)
        assert result.success is False
        assert "bulunamadi" in result.message.lower()

    async def test_telegram_notification_on_request(self) -> None:
        """Onay isteginde Telegram butonlu bildirim gondermeli."""
        master = _make_master()
        bot = _make_telegram_bot()
        master.telegram_bot = bot
        task = _make_task(description="telegram onayli gorev")
        decision = _make_decision(action=ActionType.AUTO_FIX, confidence=0.8)
        await master.request_approval(task, ActionType.AUTO_FIX, decision)
        bot.send_buttons.assert_called_once()

    async def test_get_pending_approvals_empty(self) -> None:
        """Bekleyen onay yoksa bos liste donmeli."""
        master = _make_master()
        result = master.get_pending_approvals()
        assert result == []

    async def test_get_pending_approvals_returns_list(self) -> None:
        """Bekleyen onaylar liste olarak donmeli."""
        master = _make_master()
        task = _make_task()
        decision = _make_decision()
        await master.request_approval(task, ActionType.LOG, decision)
        await master.request_approval(task, ActionType.NOTIFY, decision)
        result = master.get_pending_approvals()
        assert len(result) == 2

    async def test_auto_execute_flag(self) -> None:
        """auto_execute flag'i onay istegine kaydedilmeli."""
        master = _make_master()
        task = _make_task()
        decision = _make_decision()
        approval = await master.request_approval(
            task, ActionType.AUTO_FIX, decision,
            auto_execute=True,
        )
        assert approval.auto_execute_on_timeout is True

    async def test_timeout_seconds_custom(self) -> None:
        """Ozel timeout_seconds degeri kaydedilmeli."""
        master = _make_master()
        task = _make_task()
        decision = _make_decision()
        approval = await master.request_approval(
            task, ActionType.LOG, decision,
            timeout_seconds=600,
        )
        assert approval.timeout_seconds == 600

    async def test_approval_removed_from_pending(self) -> None:
        """Onay yaniti sonrasi pending_approvals'dan silinmeli."""
        master = _make_master()
        task = _make_task()
        decision = _make_decision()
        approval = await master.request_approval(task, ActionType.LOG, decision)
        await master.handle_approval_response(approval.id, approved=True)
        assert approval.id not in master.pending_approvals


# === TestAnalyze ===


class TestAnalyze:
    """Analiz metodu testleri."""

    async def test_default_values(self) -> None:
        """Varsayilan degerler dogru donmeli."""
        master = _make_master()
        result = await master.analyze({})
        assert result["risk"] == "low"
        assert result["urgency"] == "low"
        assert result["suggested_action"] == "log"

    async def test_provided_values(self) -> None:
        """Saglanan degerler kullanilmalidir."""
        master = _make_master()
        data = {"risk": "high", "urgency": "medium", "description": "test"}
        result = await master.analyze(data)
        assert result["risk"] == "high"
        assert result["urgency"] == "medium"

    async def test_description_in_summary(self) -> None:
        """Aciklama summary alaninda yer almalidir."""
        master = _make_master()
        data = {"description": "sunucu disk doldu"}
        result = await master.analyze(data)
        assert "sunucu disk doldu" in result["summary"]


# === TestReport ===


class TestReport:
    """Rapor formatlama testleri."""

    async def test_success_report(self) -> None:
        """Basarili sonuc 'OK' icermeli."""
        master = _make_master()
        result = TaskResult(success=True, message="gorev tamamlandi")
        report = await master.report(result)
        assert "[OK]" in report
        assert "Basarili" in report
        assert "gorev tamamlandi" in report

    async def test_failure_report(self) -> None:
        """Basarisiz sonuc 'HATA' icermeli."""
        master = _make_master()
        result = TaskResult(success=False, message="gorev basarisiz")
        report = await master.report(result)
        assert "[HATA]" in report
        assert "Basarisiz" in report

    async def test_errors_in_report(self) -> None:
        """Hatalar raporda goruntulenmeli."""
        master = _make_master()
        result = TaskResult(
            success=False, message="hata olustu",
            errors=["hata1", "hata2"],
        )
        report = await master.report(result)
        assert "hata1" in report
        assert "hata2" in report
        assert "Hatalar:" in report

    async def test_timestamp_in_report(self) -> None:
        """Zaman damgasi ISO formatinda raporda olmalidir."""
        master = _make_master()
        result = TaskResult(success=True, message="tamam")
        report = await master.report(result)
        assert "Zaman:" in report
        # ISO format: YYYY-MM-DD formatinda tarih icermeli
        timestamp_str = result.timestamp.isoformat()
        assert timestamp_str in report


# === TestAgentKeywords ===


class TestAgentKeywords:
    """AGENT_KEYWORDS sabiti testleri."""

    def test_all_agent_types_present(self) -> None:
        """Tum beklenen agent tipleri AGENT_KEYWORDS'de olmalidir."""
        expected = {
            "security", "server_monitor", "marketing", "research",
            "communication", "coding", "analysis", "creative",
        }
        assert set(AGENT_KEYWORDS.keys()) == expected

    def test_each_type_has_keywords(self) -> None:
        """Her agent tipinin en az bir anahtar kelimesi olmalidir."""
        for agent_type, keywords in AGENT_KEYWORDS.items():
            assert len(keywords) > 0, f"{agent_type} icin anahtar kelime yok"

    def test_keywords_are_lowercase(self) -> None:
        """Tum anahtar kelimeler kucuk harf olmalidir."""
        for agent_type, keywords in AGENT_KEYWORDS.items():
            for kw in keywords:
                assert kw == kw.lower(), (
                    f"{agent_type} icin '{kw}' kucuk harf degil"
                )

    def test_security_keywords_include_turkish(self) -> None:
        """Guvenlik anahtar kelimeleri Turkce terimler icermeli."""
        assert "guvenlik" in AGENT_KEYWORDS["security"]
        assert "saldiri" in AGENT_KEYWORDS["security"]

    def test_marketing_keywords(self) -> None:
        """Pazarlama anahtar kelimeleri beklenen terimleri icermeli."""
        assert "google ads" in AGENT_KEYWORDS["marketing"]
        assert "kampanya" in AGENT_KEYWORDS["marketing"]
