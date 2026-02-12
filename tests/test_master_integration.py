"""Master Agent startup entegrasyonu testleri.

main.py lifespan, Master Agent karar yonlendirmesi,
Telegram bot entegrasyonu ve endpoint'leri test eder.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.base_agent import AgentStatus, BaseAgent, TaskResult
from app.core.decision_matrix import ActionType, DecisionMatrix, RiskLevel, UrgencyLevel
from app.core.master_agent import MasterAgent


def _ensure_telegram_mock():
    """telegram modulu yoksa mock olarak ekler."""
    if "telegram" not in sys.modules:
        mock_telegram = MagicMock()
        mock_telegram_ext = MagicMock()
        sys.modules["telegram"] = mock_telegram
        sys.modules["telegram.ext"] = mock_telegram_ext


# === Fixtures ===


@pytest.fixture
def master_agent():
    """Temiz MasterAgent nesnesi."""
    return MasterAgent()


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_buttons = AsyncMock()
    bot.start_polling = AsyncMock()
    bot.stop = AsyncMock()
    bot.master_agent = None
    return bot


@pytest.fixture
def dummy_agent():
    """Test icin basit bir agent."""

    class DummyAgent(BaseAgent):
        async def execute(self, task):
            return TaskResult(success=True, message="dummy tamamlandi")

        async def analyze(self, data):
            return {"summary": "dummy analiz"}

        async def report(self, result):
            return f"Dummy rapor: {result.message}"

    return DummyAgent(name="DummyAgent")


@pytest.fixture
def failing_agent():
    """Hata atan agent."""

    class FailingAgent(BaseAgent):
        async def execute(self, task):
            raise RuntimeError("agent patladı")

        async def analyze(self, data):
            return {}

        async def report(self, result):
            return ""

    return FailingAgent(name="FailingAgent")


# === TestMasterAgentInit ===


class TestMasterAgentInit:
    """MasterAgent baslatma testleri."""

    def test_init_defaults(self, master_agent):
        """Varsayilan degerlerle olusturulur."""
        assert master_agent.name == "MasterAgent"
        assert master_agent.status == AgentStatus.IDLE
        assert master_agent.agents == {}
        assert master_agent.telegram_bot is None
        assert master_agent.decision_matrix is not None

    def test_register_agent(self, master_agent, dummy_agent):
        """Agent kaydi basarili."""
        master_agent.register_agent(dummy_agent)

        assert "DummyAgent" in master_agent.agents
        assert master_agent.agents["DummyAgent"] is dummy_agent

    def test_register_multiple_agents(self, master_agent):
        """Birden fazla agent kaydedilir."""

        class AgentA(BaseAgent):
            async def execute(self, task):
                return TaskResult(success=True, message="A")

            async def analyze(self, data):
                return {}

            async def report(self, result):
                return ""

        class AgentB(BaseAgent):
            async def execute(self, task):
                return TaskResult(success=True, message="B")

            async def analyze(self, data):
                return {}

            async def report(self, result):
                return ""

        master_agent.register_agent(AgentA(name="AgentA"))
        master_agent.register_agent(AgentB(name="AgentB"))

        assert len(master_agent.agents) == 2
        assert "AgentA" in master_agent.agents
        assert "AgentB" in master_agent.agents

    def test_register_overwrites_same_name(self, master_agent, dummy_agent):
        """Ayni isimli agent kaydi ustune yazilir."""
        master_agent.register_agent(dummy_agent)

        class NewDummy(BaseAgent):
            async def execute(self, task):
                return TaskResult(success=True, message="new")

            async def analyze(self, data):
                return {}

            async def report(self, result):
                return ""

        new = NewDummy(name="DummyAgent")
        master_agent.register_agent(new)

        assert master_agent.agents["DummyAgent"] is new

    def test_get_registered_agents_empty(self, master_agent):
        """Agent yokken bos liste doner."""
        assert master_agent.get_registered_agents() == []

    def test_get_registered_agents(self, master_agent, dummy_agent):
        """Kayitli agent bilgileri dogru."""
        master_agent.register_agent(dummy_agent)
        agents = master_agent.get_registered_agents()

        assert len(agents) == 1
        assert agents[0]["name"] == "DummyAgent"
        assert agents[0]["status"] == "idle"
        assert agents[0]["task_count"] == 0


# === TestMasterAgentExecute ===


class TestMasterAgentExecute:
    """MasterAgent gorev calistirma testleri."""

    @pytest.mark.asyncio
    async def test_execute_low_risk_low_urgency_logs(self, master_agent):
        """Dusuk risk + dusuk aciliyet = LOG aksiyonu."""
        result = await master_agent.run({
            "description": "rutin kontrol",
            "risk": "low",
            "urgency": "low",
        })
        assert result.success is True
        assert "kaydedildi" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_low_risk_high_urgency_notifies(self, master_agent):
        """Dusuk risk + yuksek aciliyet = NOTIFY aksiyonu."""
        result = await master_agent.run({
            "description": "acil bildirim",
            "risk": "low",
            "urgency": "high",
        })
        assert result.success is True
        assert "bildirim" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_medium_risk_high_urgency_auto_fix(self, master_agent, dummy_agent):
        """Orta risk + yuksek aciliyet = AUTO_FIX aksiyonu."""
        master_agent.register_agent(dummy_agent)
        result = await master_agent.run({
            "description": "otomatik duzeltme",
            "risk": "medium",
            "urgency": "high",
            "target_agent": "DummyAgent",
        })
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_high_risk_high_urgency_immediate(self, master_agent):
        """Yuksek risk + yuksek aciliyet = IMMEDIATE aksiyonu."""
        result = await master_agent.run({
            "description": "kritik sorun",
            "risk": "high",
            "urgency": "high",
        })
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_auto_fix_no_target_agent(self, master_agent):
        """Hedef agent yoksa auto_fix basarisiz."""
        result = await master_agent.run({
            "description": "duzeltme",
            "risk": "medium",
            "urgency": "high",
            "target_agent": "NonExistentAgent",
        })
        assert result.success is False
        assert "bulunamadi" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_auto_fix_with_failing_agent(self, master_agent, failing_agent):
        """Agent hata atarsa TaskResult basarisiz doner."""
        master_agent.register_agent(failing_agent)
        result = await master_agent.run({
            "description": "hatali gorev",
            "risk": "medium",
            "urgency": "high",
            "target_agent": "FailingAgent",
        })
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_default_risk_urgency(self, master_agent):
        """Risk ve aciliyet belirtilmezse varsayilan (low) kullanilir."""
        result = await master_agent.run({"description": "basit gorev"})
        assert result.success is True


# === TestMasterAgentAnalyze ===


class TestMasterAgentAnalyze:
    """MasterAgent analiz testleri."""

    @pytest.mark.asyncio
    async def test_analyze_returns_defaults(self, master_agent):
        """Analiz varsayilan degerleri dondurur."""
        analysis = await master_agent.analyze({"description": "test"})

        assert analysis["risk"] == "low"
        assert analysis["urgency"] == "low"
        assert analysis["suggested_action"] == "log"
        assert "test" in analysis["summary"]

    @pytest.mark.asyncio
    async def test_analyze_respects_given_values(self, master_agent):
        """Verilen risk ve aciliyet degerleri korunur."""
        analysis = await master_agent.analyze({
            "description": "onemli",
            "risk": "high",
            "urgency": "medium",
        })
        assert analysis["risk"] == "high"
        assert analysis["urgency"] == "medium"


# === TestMasterAgentReport ===


class TestMasterAgentReport:
    """MasterAgent rapor testleri."""

    @pytest.mark.asyncio
    async def test_report_success(self, master_agent):
        """Basarili sonuc raporu."""
        result = TaskResult(success=True, message="Gorev tamamlandi")
        report = await master_agent.report(result)

        assert "OK" in report
        assert "Basarili" in report
        assert "Gorev tamamlandi" in report

    @pytest.mark.asyncio
    async def test_report_failure(self, master_agent):
        """Basarisiz sonuc raporu."""
        result = TaskResult(
            success=False,
            message="Gorev basarisiz",
            errors=["hata1", "hata2"],
        )
        report = await master_agent.report(result)

        assert "HATA" in report
        assert "Basarisiz" in report
        assert "hata1" in report
        assert "hata2" in report


# === TestTelegramIntegration ===


class TestTelegramIntegration:
    """MasterAgent Telegram entegrasyonu testleri."""

    @pytest.mark.asyncio
    async def test_notify_sends_telegram_message(self, master_agent, mock_telegram_bot):
        """NOTIFY aksiyonu Telegram mesaji gonderir."""
        master_agent.telegram_bot = mock_telegram_bot

        result = await master_agent.run({
            "description": "onemli bilgi",
            "risk": "low",
            "urgency": "high",
        })

        assert result.success is True
        mock_telegram_bot.send_message.assert_called_once()
        call_text = mock_telegram_bot.send_message.call_args[0][0]
        assert "onemli bilgi" in call_text

    @pytest.mark.asyncio
    async def test_notify_without_telegram(self, master_agent):
        """Telegram bot yokken notify hata vermez."""
        master_agent.telegram_bot = None

        result = await master_agent.run({
            "description": "bildirim",
            "risk": "low",
            "urgency": "high",
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_immediate_sends_telegram_buttons(self, master_agent, mock_telegram_bot):
        """IMMEDIATE aksiyonu butonlu Telegram mesaji gonderir."""
        master_agent.telegram_bot = mock_telegram_bot

        result = await master_agent.run({
            "description": "sunucu coktu",
            "risk": "high",
            "urgency": "high",
        })

        assert result.success is True
        mock_telegram_bot.send_buttons.assert_called_once()
        call_kwargs = mock_telegram_bot.send_buttons.call_args
        assert "sunucu coktu" in call_kwargs[1]["text"] or "sunucu coktu" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_immediate_with_target_agent(self, master_agent, mock_telegram_bot, dummy_agent):
        """IMMEDIATE + hedef agent varsa agent calistirilir."""
        master_agent.telegram_bot = mock_telegram_bot
        master_agent.register_agent(dummy_agent)

        result = await master_agent.run({
            "description": "acil duzeltme",
            "risk": "high",
            "urgency": "high",
            "target_agent": "DummyAgent",
        })

        assert result.success is True
        assert result.message == "dummy tamamlandi"
        mock_telegram_bot.send_buttons.assert_called_once()

    @pytest.mark.asyncio
    async def test_telegram_error_handled(self, master_agent):
        """Telegram hatasi gorev sonucunu etkilemez."""
        bot = MagicMock()
        bot.send_message = AsyncMock(side_effect=Exception("Telegram hatasi"))
        master_agent.telegram_bot = bot

        result = await master_agent.run({
            "description": "bilgi",
            "risk": "low",
            "urgency": "high",
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_immediate_telegram_error_handled(self, master_agent):
        """IMMEDIATE Telegram hatasi gorev sonucunu etkilemez."""
        bot = MagicMock()
        bot.send_buttons = AsyncMock(side_effect=Exception("Telegram hatasi"))
        master_agent.telegram_bot = bot

        result = await master_agent.run({
            "description": "acil",
            "risk": "high",
            "urgency": "high",
        })

        assert result.success is True


# === TestTelegramBotMasterAgent ===


class TestTelegramBotMasterAgent:
    """TelegramBot -> MasterAgent entegrasyon testleri."""

    @pytest.fixture(autouse=True)
    def _mock_telegram_module(self):
        """telegram modulu mock'lanir."""
        _ensure_telegram_mock()

    def _make_bot(self):
        """Mock'lanmis TelegramBot olusturur."""
        from app.tools.telegram_bot import TelegramBot

        with patch.object(TelegramBot, "__init__", lambda self: None):
            bot = TelegramBot()
            bot.master_agent = None
            bot.admin_chat_id = "12345"
            bot.app = None
        return bot

    @pytest.mark.asyncio
    async def test_handle_message_routes_to_master_agent(self):
        """Mesaj geldiginde Master Agent'a iletilir."""
        bot = self._make_bot()

        mock_master = MagicMock()
        mock_result = TaskResult(success=True, message="islem tamam")
        mock_master.run = AsyncMock(return_value=mock_result)
        mock_master.report = AsyncMock(return_value="[OK] rapor")
        bot.master_agent = mock_master

        mock_update = MagicMock()
        mock_update.effective_message.text = "test mesaji"
        mock_update.effective_message.reply_text = AsyncMock()
        mock_update.effective_chat.id = 12345

        await bot._handle_message(mock_update, MagicMock())

        mock_master.run.assert_called_once()
        call_task = mock_master.run.call_args[0][0]
        assert call_task["description"] == "test mesaji"
        assert call_task["source"] == "telegram"
        mock_update.effective_message.reply_text.assert_called_once_with("[OK] rapor")

    @pytest.mark.asyncio
    async def test_handle_message_without_master_agent(self):
        """Master Agent yokken mesaj kuyruga eklenir."""
        bot = self._make_bot()

        mock_update = MagicMock()
        mock_update.effective_message.text = "merhaba"
        mock_update.effective_message.reply_text = AsyncMock()
        mock_update.effective_chat.id = 12345

        await bot._handle_message(mock_update, MagicMock())

        reply_text = mock_update.effective_message.reply_text.call_args[0][0]
        assert "merhaba" in reply_text
        assert "kuyruguna" in reply_text

    @pytest.mark.asyncio
    async def test_handle_message_master_agent_error(self):
        """Master Agent hatasi kullaniciya bildirilir."""
        bot = self._make_bot()

        mock_master = MagicMock()
        mock_master.run = AsyncMock(side_effect=RuntimeError("islem hatasi"))
        bot.master_agent = mock_master

        mock_update = MagicMock()
        mock_update.effective_message.text = "sorunlu mesaj"
        mock_update.effective_message.reply_text = AsyncMock()
        mock_update.effective_chat.id = 12345

        await bot._handle_message(mock_update, MagicMock())

        reply_text = mock_update.effective_message.reply_text.call_args[0][0]
        assert "hata" in reply_text.lower()

    @pytest.mark.asyncio
    async def test_cmd_status_with_master_agent(self):
        """Status komutu Master Agent bilgilerini gosterir."""
        bot = self._make_bot()

        mock_master = MagicMock()
        mock_master.status.value = "idle"
        mock_master.get_registered_agents.return_value = [
            {"name": "SecurityAgent", "status": "idle", "task_count": 5},
            {"name": "ResearchAgent", "status": "running", "task_count": 3},
        ]
        bot.master_agent = mock_master

        mock_update = MagicMock()
        mock_update.effective_chat.id = 12345
        mock_update.effective_message.reply_text = AsyncMock()

        await bot._cmd_status(mock_update, MagicMock())

        reply_text = mock_update.effective_message.reply_text.call_args[0][0]
        assert "SecurityAgent" in reply_text
        assert "ResearchAgent" in reply_text
        assert "idle" in reply_text
        assert "2" in reply_text  # kayitli agent sayisi

    @pytest.mark.asyncio
    async def test_cmd_status_without_master_agent(self):
        """Status komutu Master Agent yokken bilgi verir."""
        bot = self._make_bot()

        mock_update = MagicMock()
        mock_update.effective_chat.id = 12345
        mock_update.effective_message.reply_text = AsyncMock()

        await bot._cmd_status(mock_update, MagicMock())

        reply_text = mock_update.effective_message.reply_text.call_args[0][0]
        assert "Baslamamis" in reply_text


# === TestDecisionMatrix ===


class TestDecisionMatrix:
    """Karar matrisi testleri."""

    @pytest.fixture
    def matrix(self):
        return DecisionMatrix()

    @pytest.mark.asyncio
    async def test_low_low_returns_log(self, matrix):
        decision = await matrix.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert decision.action == ActionType.LOG

    @pytest.mark.asyncio
    async def test_low_high_returns_notify(self, matrix):
        decision = await matrix.evaluate(RiskLevel.LOW, UrgencyLevel.HIGH)
        assert decision.action == ActionType.NOTIFY

    @pytest.mark.asyncio
    async def test_medium_high_returns_auto_fix(self, matrix):
        decision = await matrix.evaluate(RiskLevel.MEDIUM, UrgencyLevel.HIGH)
        assert decision.action == ActionType.AUTO_FIX

    @pytest.mark.asyncio
    async def test_high_high_returns_immediate(self, matrix):
        decision = await matrix.evaluate(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert decision.action == ActionType.IMMEDIATE

    @pytest.mark.asyncio
    async def test_high_low_returns_notify(self, matrix):
        decision = await matrix.evaluate(RiskLevel.HIGH, UrgencyLevel.LOW)
        assert decision.action == ActionType.NOTIFY

    @pytest.mark.asyncio
    async def test_high_medium_returns_auto_fix(self, matrix):
        decision = await matrix.evaluate(RiskLevel.HIGH, UrgencyLevel.MEDIUM)
        assert decision.action == ActionType.AUTO_FIX

    @pytest.mark.asyncio
    async def test_confidence_range(self, matrix):
        """Guven skoru 0-1 arasinda."""
        for risk in RiskLevel:
            for urgency in UrgencyLevel:
                decision = await matrix.evaluate(risk, urgency)
                assert 0.0 <= decision.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_reason_includes_context(self, matrix):
        """Karar aciklamasi baglamsal bilgi icerir."""
        decision = await matrix.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            context={"detail": "sunucu hatasi"},
        )
        assert "sunucu hatasi" in decision.reason

    def test_get_action_for_string(self, matrix):
        """String arayuz dogru calisiyor."""
        assert matrix.get_action_for("low", "low") == ActionType.LOG
        assert matrix.get_action_for("high", "high") == ActionType.IMMEDIATE


# === TestRouteAction ===


class TestRouteAction:
    """Aksiyon yonlendirme testleri."""

    @pytest.mark.asyncio
    async def test_route_log(self, master_agent):
        result = await master_agent._route_action(
            {"description": "test"}, ActionType.LOG,
        )
        assert result.success is True
        assert "kaydedildi" in result.message.lower()

    @pytest.mark.asyncio
    async def test_route_notify(self, master_agent):
        result = await master_agent._route_action(
            {"description": "bildirim testi"}, ActionType.NOTIFY,
        )
        assert result.success is True
        assert "bildirim" in result.message.lower()

    @pytest.mark.asyncio
    async def test_route_auto_fix_with_agent(self, master_agent, dummy_agent):
        master_agent.register_agent(dummy_agent)
        result = await master_agent._route_action(
            {"description": "fix", "target_agent": "DummyAgent"},
            ActionType.AUTO_FIX,
        )
        assert result.success is True
        assert result.message == "dummy tamamlandi"

    @pytest.mark.asyncio
    async def test_route_auto_fix_no_agent(self, master_agent):
        result = await master_agent._route_action(
            {"description": "fix", "target_agent": "YokAgent"},
            ActionType.AUTO_FIX,
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_route_immediate_no_target(self, master_agent):
        result = await master_agent._route_action(
            {"description": "acil"}, ActionType.IMMEDIATE,
        )
        assert result.success is True
        assert "mudahale" in result.message.lower()


# === TestEndpoints ===


class TestEndpoints:
    """FastAPI endpoint testleri (httpx + mock lifespan)."""

    @pytest.fixture
    def mock_app(self):
        """Lifespan olmadan test app'i."""
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse

        test_app = FastAPI()
        test_app.state.master_agent = MasterAgent()

        @test_app.get("/health")
        async def health_check():
            return {"status": "ok", "service": "atlas"}

        @test_app.get("/status")
        async def system_status(request: Request):
            master_agent = getattr(request.app.state, "master_agent", None)
            agents_info = {"master": "idle"}
            if master_agent:
                agents_info = {
                    "master": master_agent.status.value,
                    "registered": master_agent.get_registered_agents(),
                    "count": len(master_agent.agents),
                }
            return {
                "service": "atlas",
                "version": "0.1.0",
                "agents": agents_info,
            }

        @test_app.post("/tasks")
        async def create_task(request: Request, payload: dict):
            master_agent = getattr(request.app.state, "master_agent", None)
            if not master_agent:
                return JSONResponse(status_code=503, content={"status": "error"})
            result = await master_agent.run(payload)
            return JSONResponse(
                status_code=200 if result.success else 500,
                content={
                    "success": result.success,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat(),
                },
            )

        return test_app

    @pytest.mark.asyncio
    async def test_health_endpoint(self, mock_app):
        """Health endpoint basarili."""
        transport = ASGITransport(app=mock_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_status_endpoint_with_agents(self, mock_app, dummy_agent):
        """Status endpoint agent bilgilerini gosterir."""
        mock_app.state.master_agent.register_agent(dummy_agent)

        transport = ASGITransport(app=mock_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/status")

        data = resp.json()
        assert resp.status_code == 200
        assert data["agents"]["count"] == 1
        assert len(data["agents"]["registered"]) == 1
        assert data["agents"]["registered"][0]["name"] == "DummyAgent"

    @pytest.mark.asyncio
    async def test_status_endpoint_no_master(self, mock_app):
        """Status endpoint Master Agent yokken varsayilan gosterir."""
        mock_app.state.master_agent = None

        transport = ASGITransport(app=mock_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/status")

        data = resp.json()
        assert data["agents"]["master"] == "idle"

    @pytest.mark.asyncio
    async def test_tasks_endpoint_success(self, mock_app):
        """Tasks endpoint basarili gorev isler."""
        transport = ASGITransport(app=mock_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/tasks", json={
                "description": "test gorevi",
                "risk": "low",
                "urgency": "low",
            })

        data = resp.json()
        assert resp.status_code == 200
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_tasks_endpoint_no_master(self, mock_app):
        """Tasks endpoint Master Agent yokken 503 doner."""
        mock_app.state.master_agent = None

        transport = ASGITransport(app=mock_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/tasks", json={
                "description": "test",
            })

        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_tasks_endpoint_auto_fix_fail(self, mock_app):
        """Tasks endpoint basarisiz gorevde 500 doner."""
        transport = ASGITransport(app=mock_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/tasks", json={
                "description": "duzeltme",
                "risk": "medium",
                "urgency": "high",
                "target_agent": "NonExistent",
            })

        data = resp.json()
        assert resp.status_code == 500
        assert data["success"] is False


# === TestBidirectionalLink ===


class TestBidirectionalLink:
    """MasterAgent <-> TelegramBot cift yonlu baglanti testleri."""

    def test_bidirectional_setup(self, master_agent, mock_telegram_bot):
        """Cift yonlu baglanti kurulur."""
        master_agent.telegram_bot = mock_telegram_bot
        mock_telegram_bot.master_agent = master_agent

        assert master_agent.telegram_bot is mock_telegram_bot
        assert mock_telegram_bot.master_agent is master_agent

    @pytest.mark.asyncio
    async def test_full_flow_message_to_notify(self, master_agent, mock_telegram_bot):
        """Tam akim: Mesaj -> MasterAgent -> NOTIFY -> Telegram."""
        master_agent.telegram_bot = mock_telegram_bot

        result = await master_agent.run({
            "description": "sunucu yavas",
            "risk": "medium",
            "urgency": "low",
        })

        # medium/low -> NOTIFY
        assert result.success is True
        mock_telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_flow_immediate_with_agent(
        self, master_agent, mock_telegram_bot, dummy_agent,
    ):
        """Tam akim: Acil gorev -> Telegram buton + Agent calistir."""
        master_agent.telegram_bot = mock_telegram_bot
        master_agent.register_agent(dummy_agent)

        result = await master_agent.run({
            "description": "sunucu coktu",
            "risk": "high",
            "urgency": "high",
            "target_agent": "DummyAgent",
        })

        assert result.success is True
        assert result.message == "dummy tamamlandi"
        mock_telegram_bot.send_buttons.assert_called_once()


# === TestCoreExports ===


class TestCoreExports:
    """app.core export testleri."""

    def test_master_agent_export(self):
        from app.core import MasterAgent
        assert MasterAgent is not None

    def test_decision_matrix_export(self):
        from app.core import DecisionMatrix
        assert DecisionMatrix is not None

    def test_risk_level_export(self):
        from app.core import RiskLevel
        assert RiskLevel.LOW.value == "low"

    def test_urgency_level_export(self):
        from app.core import UrgencyLevel
        assert UrgencyLevel.HIGH.value == "high"

    def test_action_type_export(self):
        from app.core import ActionType
        assert ActionType.IMMEDIATE.value == "immediate"


# === TestAgentStatusFlow ===


class TestAgentStatusFlow:
    """Agent durum gecisleri testleri."""

    @pytest.mark.asyncio
    async def test_status_idle_after_success(self, master_agent):
        """Basarili gorev sonrasi status IDLE."""
        await master_agent.run({"description": "test"})
        assert master_agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_task_count_increments(self, master_agent):
        """Her gorevde sayac artar."""
        assert master_agent._task_count == 0

        await master_agent.run({"description": "1"})
        assert master_agent._task_count == 1

        await master_agent.run({"description": "2"})
        assert master_agent._task_count == 2

    @pytest.mark.asyncio
    async def test_get_info_after_tasks(self, master_agent):
        """Gorev sonrasi info dogru."""
        await master_agent.run({"description": "test"})
        info = master_agent.get_info()

        assert info["name"] == "MasterAgent"
        assert info["status"] == "idle"
        assert info["task_count"] == 1
