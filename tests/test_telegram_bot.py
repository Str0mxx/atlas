"""ATLAS Telegram Bot unit testleri.

Bildirim seviyesi, alert, admin dogrulamasi, komut handler'lari,
callback query isleme, mesaj gonderme ve formatlama testleri.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.tools.telegram_bot import AlertSeverity, NotificationLevel, TelegramBot


# === Yardimci Fonksiyonlar ===


def _make_bot(admin_chat_id: str = "12345") -> TelegramBot:
    """Test icin TelegramBot olusturur (token olmadan).

    Args:
        admin_chat_id: Admin kullanici chat ID'si.

    Returns:
        Yapilandirilmis TelegramBot nesnesi.
    """
    with patch("app.tools.telegram_bot.settings") as mock_settings:
        mock_settings.telegram_bot_token.get_secret_value.return_value = ""
        mock_settings.telegram_admin_chat_id = admin_chat_id
        bot = TelegramBot()

    bot.admin_chat_id = admin_chat_id
    bot.app = MagicMock()
    bot.app.bot.send_message = AsyncMock()
    return bot


def _make_update(
    chat_id: int = 12345,
    text: str = "test",
    message_id: int = 1,
) -> MagicMock:
    """Test icin sahte Update nesnesi.

    Args:
        chat_id: Sahte chat ID.
        text: Mesaj metni.
        message_id: Mesaj ID.

    Returns:
        Sahte Telegram Update nesnesi.
    """
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_message.text = text
    update.effective_message.message_id = message_id
    update.effective_message.reply_text = AsyncMock()
    return update


def _make_callback_update(
    chat_id: int = 12345,
    data: str = "approve_abc",
    message_text: str = "ONAY BEKLENIYOR",
) -> MagicMock:
    """Callback query iceren sahte Update.

    Args:
        chat_id: Sahte chat ID.
        data: Callback data.
        message_text: Callback mesaj metni.

    Returns:
        Callback query iceren sahte Update nesnesi.
    """
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.text = message_text
    update.callback_query.message.reply_text = AsyncMock()
    update.callback_query.message.edit_text = AsyncMock()
    return update


def _make_context(args: list[str] | None = None) -> MagicMock:
    """Sahte context nesnesi.

    Args:
        args: Komut argumanlari.

    Returns:
        Sahte ContextTypes.DEFAULT_TYPE nesnesi.
    """
    context = MagicMock()
    context.args = args
    return context


def _make_master_agent(
    agents: list[dict] | None = None,
    approvals: list | None = None,
    history: list | None = None,
) -> MagicMock:
    """Sahte MasterAgent.

    Args:
        agents: Kayitli agent bilgileri listesi.
        approvals: Bekleyen onay listesi.
        history: Karar gecmisi listesi.

    Returns:
        Sahte MasterAgent nesnesi.
    """
    master = MagicMock()
    master.get_registered_agents.return_value = agents or []
    master.get_pending_approvals.return_value = approvals or []
    master.get_decision_history.return_value = history or []
    master.handle_approval_response = AsyncMock(
        return_value=TaskResult(success=True, message="ok"),
    )
    master.run = AsyncMock(
        return_value=TaskResult(success=True, message="tamamlandi"),
    )
    master.report = AsyncMock(return_value="Rapor metni")
    master.status = MagicMock()
    master.status.value = "idle"
    return master


def _make_decision_entry(**kwargs) -> MagicMock:
    """Sahte DecisionAuditEntry.

    Args:
        **kwargs: DecisionAuditEntry alanlari.

    Returns:
        Sahte DecisionAuditEntry nesnesi.
    """
    entry = MagicMock()
    entry.task_description = kwargs.get("task_description", "test gorevi")
    entry.risk = kwargs.get("risk", "low")
    entry.urgency = kwargs.get("urgency", "low")
    entry.action = kwargs.get("action", "log")
    entry.confidence = kwargs.get("confidence", 0.9)
    entry.agent_selected = kwargs.get("agent_selected", "TestAgent")
    entry.outcome_success = kwargs.get("outcome_success", True)
    entry.timestamp = kwargs.get(
        "timestamp", datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
    )
    return entry


def _make_approval(**kwargs) -> MagicMock:
    """Sahte ApprovalRequest.

    Args:
        **kwargs: ApprovalRequest alanlari.

    Returns:
        Sahte ApprovalRequest nesnesi.
    """
    approval = MagicMock()
    approval.id = kwargs.get("id", "abc12345-6789-0123-4567-890abcdef012")
    approval.task = kwargs.get("task", {"description": "test gorevi"})
    approval.action = kwargs.get("action", "auto_fix")
    approval.timeout_seconds = kwargs.get("timeout_seconds", 300)
    return approval


# === TestNotificationLevel ===


class TestNotificationLevel:
    """NotificationLevel enum testleri."""

    def test_info_value(self) -> None:
        """INFO degeri 'info' olmalidir."""
        assert NotificationLevel.INFO.value == "info"

    def test_warning_value(self) -> None:
        """WARNING degeri 'warning' olmalidir."""
        assert NotificationLevel.WARNING.value == "warning"

    def test_error_value(self) -> None:
        """ERROR degeri 'error' olmalidir."""
        assert NotificationLevel.ERROR.value == "error"

    def test_critical_value(self) -> None:
        """CRITICAL degeri 'critical' olmalidir."""
        assert NotificationLevel.CRITICAL.value == "critical"


# === TestAlertSeverity ===


class TestAlertSeverity:
    """AlertSeverity enum testleri."""

    def test_low_value(self) -> None:
        """LOW degeri 'low' olmalidir."""
        assert AlertSeverity.LOW.value == "low"

    def test_medium_value(self) -> None:
        """MEDIUM degeri 'medium' olmalidir."""
        assert AlertSeverity.MEDIUM.value == "medium"

    def test_high_value(self) -> None:
        """HIGH degeri 'high' olmalidir."""
        assert AlertSeverity.HIGH.value == "high"

    def test_critical_value(self) -> None:
        """CRITICAL degeri 'critical' olmalidir."""
        assert AlertSeverity.CRITICAL.value == "critical"


# === TestIsAdmin ===


class TestIsAdmin:
    """Admin dogrulama testleri."""

    def test_admin_returns_true(self) -> None:
        """Admin chat_id eslesmesi True donmelidir."""
        bot = _make_bot(admin_chat_id="12345")
        update = _make_update(chat_id=12345)
        assert bot._is_admin(update) is True

    def test_non_admin_returns_false(self) -> None:
        """Farkli chat_id False donmelidir."""
        bot = _make_bot(admin_chat_id="12345")
        update = _make_update(chat_id=99999)
        assert bot._is_admin(update) is False

    def test_no_effective_chat(self) -> None:
        """effective_chat None ise False donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_chat = None
        assert bot._is_admin(update) is False

    def test_string_int_comparison(self) -> None:
        """chat_id int 12345, admin_chat_id str '12345' eslesmeli."""
        bot = _make_bot(admin_chat_id="12345")
        update = _make_update(chat_id=12345)
        # _is_admin icinde str() donusumu yapiliyor
        assert bot._is_admin(update) is True

    def test_different_admin_chat_id(self) -> None:
        """Farkli admin_chat_id ile eslesmemeli."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_update(chat_id=12345)
        assert bot._is_admin(update) is False

    def test_zero_chat_id(self) -> None:
        """chat_id=0, admin_chat_id='0' eslesmeli."""
        bot = _make_bot(admin_chat_id="0")
        update = _make_update(chat_id=0)
        assert bot._is_admin(update) is True

    def test_negative_chat_id(self) -> None:
        """Negatif chat_id negatif admin_chat_id ile eslesmeli."""
        bot = _make_bot(admin_chat_id="-100")
        update = _make_update(chat_id=-100)
        assert bot._is_admin(update) is True

    def test_empty_admin_chat_id(self) -> None:
        """Bos admin_chat_id ile hic eslesme olmamali."""
        bot = _make_bot(admin_chat_id="")
        update = _make_update(chat_id=12345)
        assert bot._is_admin(update) is False


# === TestCmdStart ===


class TestCmdStart:
    """'/start' komutu testleri."""

    async def test_sends_welcome(self) -> None:
        """Hos geldiniz mesaji gonderilmeli."""
        bot = _make_bot()
        update = _make_update()
        context = _make_context()
        await bot._cmd_start(update, context)
        update.effective_message.reply_text.assert_called_once()
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "ATLAS Otonom AI Sistemi aktif" in call_text

    async def test_no_effective_message(self) -> None:
        """effective_message None ise hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message = None
        context = _make_context()
        await bot._cmd_start(update, context)
        # Hata olmadan tamamlanmali

    async def test_non_admin_still_works(self) -> None:
        """/start komutu admin olmayan kullanicilarda da calismali."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_start(update, context)
        update.effective_message.reply_text.assert_called_once()
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "ATLAS Otonom AI Sistemi aktif" in call_text


# === TestCmdStatus ===


class TestCmdStatus:
    """'/status' komutu testleri."""

    async def test_admin_with_master_agent(self) -> None:
        """Admin master agent varsa durum bilgisi gostermeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(
            agents=[{"name": "SecurityAgent", "status": "idle", "task_count": 3}],
        )
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_status(update, context)
        update.effective_message.reply_text.assert_called_once()
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "ATLAS Durum Raporu" in call_text
        assert "Aktif" in call_text

    async def test_admin_without_master_agent(self) -> None:
        """Master agent yoksa 'Baslamamis' gostermeli."""
        bot = _make_bot()
        bot.master_agent = None
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_status(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Baslamamis" in call_text

    async def test_non_admin_rejected(self) -> None:
        """Admin olmayan kullanici reddedilmeli."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_status(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "yetkiniz yok" in call_text

    async def test_no_effective_message(self) -> None:
        """effective_message None ise hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message = None
        context = _make_context()
        await bot._cmd_status(update, context)

    async def test_shows_agent_count(self) -> None:
        """Agent sayisi gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(
            agents=[
                {"name": "Agent1", "status": "idle", "task_count": 0},
                {"name": "Agent2", "status": "running", "task_count": 2},
            ],
        )
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_status(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "2" in call_text


# === TestCmdHelp ===


class TestCmdHelp:
    """'/help' komutu testleri."""

    async def test_admin_shows_commands(self) -> None:
        """Admin icin komut listesi gosterilmeli."""
        bot = _make_bot()
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_help(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "/start" in call_text
        assert "/status" in call_text
        assert "/help" in call_text

    async def test_non_admin_rejected(self) -> None:
        """Admin olmayan kullanici reddedilmeli."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_help(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "yetkiniz yok" in call_text

    async def test_includes_new_commands(self) -> None:
        """Yeni komutlar (/agents, /history, /approvals) gosterilmeli."""
        bot = _make_bot()
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_help(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "/agents" in call_text
        assert "/history" in call_text
        assert "/approvals" in call_text

    async def test_no_effective_message(self) -> None:
        """effective_message None ise hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message = None
        context = _make_context()
        await bot._cmd_help(update, context)


# === TestCmdAgents ===


class TestCmdAgents:
    """'/agents' komutu testleri."""

    async def test_with_agents(self) -> None:
        """Agent listesi formatlanmis gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(
            agents=[{"name": "SecurityAgent", "status": "idle", "task_count": 5}],
        )
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_agents(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "SecurityAgent" in call_text

    async def test_no_agents(self) -> None:
        """Agent yoksa uyari mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(agents=[])
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_agents(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Kayitli agent bulunamadi" in call_text

    async def test_no_master_agent(self) -> None:
        """Master Agent yoksa uyari mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = None
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_agents(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Master Agent henuz baslamadi" in call_text

    async def test_non_admin_rejected(self) -> None:
        """Admin olmayan kullanici reddedilmeli."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_agents(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "yetkiniz yok" in call_text

    async def test_no_effective_message(self) -> None:
        """effective_message None ise hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message = None
        context = _make_context()
        await bot._cmd_agents(update, context)

    async def test_agent_count_in_header(self) -> None:
        """Baslikta agent sayisi gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(
            agents=[
                {"name": "Agent1", "status": "idle", "task_count": 0},
                {"name": "Agent2", "status": "idle", "task_count": 0},
                {"name": "Agent3", "status": "idle", "task_count": 0},
            ],
        )
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_agents(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "(3)" in call_text

    async def test_multiple_agents(self) -> None:
        """Birden fazla agent listelenebilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(
            agents=[
                {"name": "SecurityAgent", "status": "idle", "task_count": 2},
                {"name": "MarketingAgent", "status": "running", "task_count": 1},
            ],
        )
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_agents(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "SecurityAgent" in call_text
        assert "MarketingAgent" in call_text


# === TestCmdHistory ===


class TestCmdHistory:
    """'/history' komutu testleri."""

    async def test_default_limit(self) -> None:
        """Varsayilan limit 5 olmalidir."""
        bot = _make_bot()
        entry = _make_decision_entry()
        bot.master_agent = _make_master_agent(history=[entry])
        update = _make_update(chat_id=12345)
        context = _make_context(args=None)
        await bot._cmd_history(update, context)
        bot.master_agent.get_decision_history.assert_called_once_with(limit=5)

    async def test_custom_limit(self) -> None:
        """Ozel limit degeri kullanilmali (args=['10'])."""
        bot = _make_bot()
        entry = _make_decision_entry()
        bot.master_agent = _make_master_agent(history=[entry])
        update = _make_update(chat_id=12345)
        context = _make_context(args=["10"])
        await bot._cmd_history(update, context)
        bot.master_agent.get_decision_history.assert_called_once_with(limit=10)

    async def test_limit_clamped_max(self) -> None:
        """Limit 50'yi gecmemeli (args=['100'] -> 50)."""
        bot = _make_bot()
        entry = _make_decision_entry()
        bot.master_agent = _make_master_agent(history=[entry])
        update = _make_update(chat_id=12345)
        context = _make_context(args=["100"])
        await bot._cmd_history(update, context)
        bot.master_agent.get_decision_history.assert_called_once_with(limit=50)

    async def test_limit_clamped_min(self) -> None:
        """Limit 1'den kucuk olmamali (args=['0'] -> 1)."""
        bot = _make_bot()
        entry = _make_decision_entry()
        bot.master_agent = _make_master_agent(history=[entry])
        update = _make_update(chat_id=12345)
        context = _make_context(args=["0"])
        await bot._cmd_history(update, context)
        bot.master_agent.get_decision_history.assert_called_once_with(limit=1)

    async def test_invalid_limit_uses_default(self) -> None:
        """Gecersiz limit varsayilan 5 kullanmali (args=['abc'])."""
        bot = _make_bot()
        entry = _make_decision_entry()
        bot.master_agent = _make_master_agent(history=[entry])
        update = _make_update(chat_id=12345)
        context = _make_context(args=["abc"])
        await bot._cmd_history(update, context)
        bot.master_agent.get_decision_history.assert_called_once_with(limit=5)

    async def test_empty_history(self) -> None:
        """Bos gecmis mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(history=[])
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_history(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Karar gecmisi bos" in call_text

    async def test_no_master_agent(self) -> None:
        """Master Agent yoksa uyari mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = None
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_history(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Master Agent henuz baslamadi" in call_text

    async def test_non_admin_rejected(self) -> None:
        """Admin olmayan kullanici reddedilmeli."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_history(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "yetkiniz yok" in call_text

    async def test_no_effective_message(self) -> None:
        """effective_message None ise hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message = None
        context = _make_context()
        await bot._cmd_history(update, context)


# === TestCmdApprovals ===


class TestCmdApprovals:
    """'/approvals' komutu testleri."""

    async def test_with_pending(self) -> None:
        """Bekleyen onaylar butonlu mesaj olarak gonderilmeli."""
        bot = _make_bot()
        approval = _make_approval()
        bot.master_agent = _make_master_agent(approvals=[approval])
        # send_buttons'u mock'la
        bot.send_buttons = AsyncMock()
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_approvals(update, context)
        bot.send_buttons.assert_called_once()

    async def test_no_pending(self) -> None:
        """Bekleyen onay yoksa bilgi mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent(approvals=[])
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_approvals(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Bekleyen onay istegi yok" in call_text

    async def test_no_master_agent(self) -> None:
        """Master Agent yoksa uyari mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = None
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_approvals(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Master Agent henuz baslamadi" in call_text

    async def test_non_admin_rejected(self) -> None:
        """Admin olmayan kullanici reddedilmeli."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_approvals(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "yetkiniz yok" in call_text

    async def test_no_effective_message(self) -> None:
        """effective_message None ise hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message = None
        context = _make_context()
        await bot._cmd_approvals(update, context)

    async def test_sends_buttons_for_each(self) -> None:
        """Her onay istegi icin ayri butonlu mesaj gonderilmeli."""
        bot = _make_bot()
        approval1 = _make_approval(id="aaaa1111-2222-3333-4444-555566667777")
        approval2 = _make_approval(id="bbbb1111-2222-3333-4444-555566667777")
        bot.master_agent = _make_master_agent(approvals=[approval1, approval2])
        bot.send_buttons = AsyncMock()
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_approvals(update, context)
        assert bot.send_buttons.call_count == 2

    async def test_approval_format(self) -> None:
        """Onay mesajinda ID'nin ilk 8 karakteri olmalidir."""
        bot = _make_bot()
        approval = _make_approval(id="abcdef12-3456-7890-abcd-ef1234567890")
        bot.master_agent = _make_master_agent(approvals=[approval])
        bot.send_buttons = AsyncMock()
        update = _make_update(chat_id=12345)
        context = _make_context()
        await bot._cmd_approvals(update, context)
        call_kwargs = bot.send_buttons.call_args
        text = call_kwargs.kwargs.get("text", call_kwargs[1].get("text", ""))
        assert "abcdef12" in text


# === TestHandleCallback ===


class TestHandleCallback:
    """Callback query isleyici testleri."""

    async def test_no_callback_query(self) -> None:
        """callback_query yoksa sessizce donmeli."""
        bot = _make_bot()
        update = MagicMock()
        update.callback_query = None
        context = _make_context()
        await bot._handle_callback(update, context)

    async def test_non_admin_rejected(self) -> None:
        """Admin olmayan kullanici reddedilmeli."""
        bot = _make_bot(admin_chat_id="99999")
        update = _make_callback_update(chat_id=12345)
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.reply_text.assert_called_once()
        call_text = update.callback_query.message.reply_text.call_args[0][0]
        assert "yetkiniz yok" in call_text

    async def test_no_master_agent(self) -> None:
        """Master Agent yoksa uyari mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = None
        update = _make_callback_update(chat_id=12345, data="approve_abc123")
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.reply_text.assert_called_once()
        call_text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Master Agent henuz baslamadi" in call_text

    async def test_approve_valid_id(self) -> None:
        """Gecerli approve callback'i handle_approval_response'u approved=True ile cagirmali."""
        bot = _make_bot()
        master = _make_master_agent()
        bot.master_agent = master
        update = _make_callback_update(
            chat_id=12345,
            data="approve_test-id-123",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        master.handle_approval_response.assert_called_once_with(
            "test-id-123", approved=True,
        )

    async def test_reject_valid_id(self) -> None:
        """Gecerli reject callback'i handle_approval_response'u approved=False ile cagirmali."""
        bot = _make_bot()
        master = _make_master_agent()
        bot.master_agent = master
        update = _make_callback_update(
            chat_id=12345,
            data="reject_test-id-456",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        master.handle_approval_response.assert_called_once_with(
            "test-id-456", approved=False,
        )

    async def test_approve_edits_message(self) -> None:
        """Onay sonrasi mesaj 'ONAYLANDI' ile duzenlenmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(
            chat_id=12345,
            data="approve_xyz",
            message_text="Orijinal mesaj",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.edit_text.assert_called_once()
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "ONAYLANDI" in edit_text

    async def test_reject_edits_message(self) -> None:
        """Red sonrasi mesaj 'REDDEDILDI' ile duzenlenmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(
            chat_id=12345,
            data="reject_xyz",
            message_text="Orijinal mesaj",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.edit_text.assert_called_once()
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "REDDEDILDI" in edit_text

    async def test_approve_immediate(self) -> None:
        """approve_immediate callback'i mesaji 'ONAYLANDI' ile duzenlenmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(
            chat_id=12345,
            data="approve_immediate",
            message_text="Acil islem",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.edit_text.assert_called_once()
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "ONAYLANDI" in edit_text

    async def test_reject_immediate(self) -> None:
        """reject_immediate callback'i mesaji 'REDDEDILDI' ile duzenlenmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(
            chat_id=12345,
            data="reject_immediate",
            message_text="Acil islem",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.edit_text.assert_called_once()
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "REDDEDILDI" in edit_text

    async def test_approve_immediate_no_master_call(self) -> None:
        """approve_immediate callback'i handle_approval_response cagirmamali."""
        bot = _make_bot()
        master = _make_master_agent()
        bot.master_agent = master
        update = _make_callback_update(
            chat_id=12345,
            data="approve_immediate",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        master.handle_approval_response.assert_not_called()

    async def test_unknown_callback(self) -> None:
        """Bilinmeyen callback data icin uyari mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(
            chat_id=12345,
            data="unknown_action",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.reply_text.assert_called_once()
        call_text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Bilinmeyen islem" in call_text

    async def test_approve_failure_shows_error(self) -> None:
        """Onay basarisiz olursa 'HATA' gosterilmeli."""
        bot = _make_bot()
        master = _make_master_agent()
        master.handle_approval_response = AsyncMock(
            return_value=TaskResult(success=False, message="islemiyor"),
        )
        bot.master_agent = master
        update = _make_callback_update(
            chat_id=12345,
            data="approve_fail-id",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "HATA" in edit_text

    async def test_reject_failure_shows_error(self) -> None:
        """Red basarisiz olursa 'HATA' gosterilmeli."""
        bot = _make_bot()
        master = _make_master_agent()
        master.handle_approval_response = AsyncMock(
            return_value=TaskResult(success=False, message="red hatasi"),
        )
        bot.master_agent = master
        update = _make_callback_update(
            chat_id=12345,
            data="reject_fail-id",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "HATA" in edit_text

    async def test_callback_answer_called(self) -> None:
        """Her callback'te query.answer() cagrilmali."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(chat_id=12345, data="approve_test")
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.answer.assert_called_once()

    async def test_empty_callback_data(self) -> None:
        """Bos callback data icin 'Bilinmeyen islem' gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(chat_id=12345, data="")
        # Bos data durumunda query.data "" olacak, MagicMock'tan override et
        update.callback_query.data = ""
        context = _make_context()
        await bot._handle_callback(update, context)
        update.callback_query.message.reply_text.assert_called_once()
        call_text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Bilinmeyen islem" in call_text

    async def test_no_query_message(self) -> None:
        """query.message None ise hatasiz donmeli."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = MagicMock()
        update.effective_chat.id = 12345
        update.callback_query.data = "approve_test"
        update.callback_query.answer = AsyncMock()
        update.callback_query.message = None
        context = _make_context()
        # Hata olmadan tamamlanmali
        await bot._handle_callback(update, context)
        update.callback_query.answer.assert_called_once()

    async def test_approve_id_extracted_correctly(self) -> None:
        """approve_ sonrasi ID dogru cikarilmali."""
        bot = _make_bot()
        master = _make_master_agent()
        bot.master_agent = master
        update = _make_callback_update(
            chat_id=12345,
            data="approve_my-special-id-123",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        master.handle_approval_response.assert_called_once_with(
            "my-special-id-123", approved=True,
        )

    async def test_reject_id_extracted_correctly(self) -> None:
        """reject_ sonrasi ID dogru cikarilmali."""
        bot = _make_bot()
        master = _make_master_agent()
        bot.master_agent = master
        update = _make_callback_update(
            chat_id=12345,
            data="reject_my-special-id-456",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        master.handle_approval_response.assert_called_once_with(
            "my-special-id-456", approved=False,
        )

    async def test_approve_preserves_original_text(self) -> None:
        """Onay sonrasi orijinal mesaj metni korunmali."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(
            chat_id=12345,
            data="approve_xyz",
            message_text="Orijinal icerik burada",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "Orijinal icerik burada" in edit_text
        assert "ONAYLANDI" in edit_text

    async def test_reject_preserves_original_text(self) -> None:
        """Red sonrasi orijinal mesaj metni korunmali."""
        bot = _make_bot()
        bot.master_agent = _make_master_agent()
        update = _make_callback_update(
            chat_id=12345,
            data="reject_xyz",
            message_text="Orijinal icerik burada",
        )
        context = _make_context()
        await bot._handle_callback(update, context)
        edit_text = update.callback_query.message.edit_text.call_args[0][0]
        assert "Orijinal icerik burada" in edit_text
        assert "REDDEDILDI" in edit_text


# === TestFormatDecisionEntry ===


class TestFormatDecisionEntry:
    """Karar formatlama testleri."""

    def test_success_outcome(self) -> None:
        """Basarili sonuc 'Basarili' gostermeli."""
        bot = _make_bot()
        entry = _make_decision_entry(outcome_success=True)
        result = bot._format_decision_entry(entry)
        assert "Basarili" in result

    def test_failure_outcome(self) -> None:
        """Basarisiz sonuc 'Basarisiz' gostermeli."""
        bot = _make_bot()
        entry = _make_decision_entry(outcome_success=False)
        result = bot._format_decision_entry(entry)
        assert "Basarisiz" in result

    def test_pending_outcome(self) -> None:
        """outcome_success=None 'Bekliyor' gostermeli."""
        bot = _make_bot()
        entry = _make_decision_entry(outcome_success=None)
        result = bot._format_decision_entry(entry)
        assert "Bekliyor" in result

    def test_no_agent(self) -> None:
        """agent_selected=None 'Atanmadi' gostermeli."""
        bot = _make_bot()
        entry = _make_decision_entry(agent_selected=None)
        result = bot._format_decision_entry(entry)
        assert "Atanmadi" in result

    def test_long_description_truncated(self) -> None:
        """80 karakterden uzun aciklama kesilmeli."""
        bot = _make_bot()
        long_desc = "A" * 100
        entry = _make_decision_entry(task_description=long_desc)
        result = bot._format_decision_entry(entry)
        # [:80] yapilacak, yani tam 80 karakter icermeli
        assert "A" * 80 in result
        assert "A" * 100 not in result

    def test_format_contains_all_fields(self) -> None:
        """Formatlama tum alanlari icermeli."""
        bot = _make_bot()
        entry = _make_decision_entry(
            task_description="Onemli gorev",
            risk="high",
            urgency="medium",
            action="auto_fix",
            confidence=0.85,
            agent_selected="SecurityAgent",
            outcome_success=True,
        )
        result = bot._format_decision_entry(entry)
        assert "Onemli gorev" in result
        assert "high" in result
        assert "medium" in result
        assert "auto_fix" in result
        assert "85%" in result
        assert "SecurityAgent" in result
        assert "Basarili" in result
        assert "15/01" in result  # Tarih formati: dd/mm


# === TestFormatAgentInfo ===


class TestFormatAgentInfo:
    """Agent bilgi formatlama testleri."""

    def test_basic_format(self) -> None:
        """Temel formatlama dogru olmalidir."""
        bot = _make_bot()
        info = {"name": "SecurityAgent", "status": "idle", "task_count": 5}
        result = bot._format_agent_info(info)
        assert "SecurityAgent" in result
        assert "IDLE" in result
        assert "5" in result

    def test_status_uppercased(self) -> None:
        """Status buyuk harfe cevirilmeli."""
        bot = _make_bot()
        info = {"name": "TestAgent", "status": "running", "task_count": 0}
        result = bot._format_agent_info(info)
        assert "RUNNING" in result

    def test_missing_fields_defaults(self) -> None:
        """Eksik alanlar varsayilan deger almali."""
        bot = _make_bot()
        info = {}
        result = bot._format_agent_info(info)
        assert "Bilinmeyen" in result
        assert "UNKNOWN" in result
        assert "0" in result

    def test_zero_task_count(self) -> None:
        """task_count=0 dogru gosterilmeli."""
        bot = _make_bot()
        info = {"name": "IdleAgent", "status": "idle", "task_count": 0}
        result = bot._format_agent_info(info)
        assert "gorev: 0" in result


# === TestSendNotification ===


class TestSendNotification:
    """Bildirim gonderme testleri."""

    async def test_info_level(self) -> None:
        """INFO seviyesi '[INFO]' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_notification("Baslik", "Mesaj", level="info")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "[INFO]" in text

    async def test_warning_level(self) -> None:
        """WARNING seviyesi '[UYARI]' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_notification("Baslik", "Mesaj", level="warning")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "[UYARI]" in text

    async def test_error_level(self) -> None:
        """ERROR seviyesi '[HATA]' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_notification("Baslik", "Mesaj", level="error")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "[HATA]" in text

    async def test_critical_level(self) -> None:
        """CRITICAL seviyesi '[KRITIK]' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_notification("Baslik", "Mesaj", level="critical")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "[KRITIK]" in text

    async def test_unknown_level_defaults(self) -> None:
        """Bilinmeyen seviye varsayilan '[INFO]' olmali."""
        bot = _make_bot()
        await bot.send_notification("Baslik", "Mesaj", level="bilinmeyen")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "[INFO]" in text

    async def test_custom_chat_id(self) -> None:
        """Ozel chat_id kullanilabilmeli."""
        bot = _make_bot()
        await bot.send_notification("Baslik", "Mesaj", chat_id="67890")
        call_args = bot.app.bot.send_message.call_args
        target = call_args.kwargs.get("chat_id", call_args[1].get("chat_id", ""))
        assert target == "67890"

    async def test_bot_not_started(self) -> None:
        """Bot baslatilmamissa (app=None) hata olmamali."""
        bot = _make_bot()
        bot.app = None
        # Hata olmadan tamamlanmali
        await bot.send_notification("Baslik", "Mesaj")


# === TestSendAlert ===


class TestSendAlert:
    """Alert gonderme testleri."""

    async def test_low_severity(self) -> None:
        """LOW seviyesi 'DUSUK' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_alert("Baslik", "Mesaj", severity="low")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "DUSUK" in text

    async def test_medium_severity(self) -> None:
        """MEDIUM seviyesi 'ORTA' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_alert("Baslik", "Mesaj", severity="medium")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "ORTA" in text

    async def test_high_severity(self) -> None:
        """HIGH seviyesi 'YUKSEK' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_alert("Baslik", "Mesaj", severity="high")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "YUKSEK" in text

    async def test_critical_severity(self) -> None:
        """CRITICAL seviyesi 'KRITIK' etiketi icermeli."""
        bot = _make_bot()
        await bot.send_alert("Baslik", "Mesaj", severity="critical")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "KRITIK" in text

    async def test_unknown_severity(self) -> None:
        """Bilinmeyen severity 'BILINMEYEN' olmali."""
        bot = _make_bot()
        await bot.send_alert("Baslik", "Mesaj", severity="xyz")
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "BILINMEYEN" in text

    async def test_custom_chat_id(self) -> None:
        """Ozel chat_id kullanilabilmeli."""
        bot = _make_bot()
        await bot.send_alert("Baslik", "Mesaj", chat_id="67890")
        call_args = bot.app.bot.send_message.call_args
        target = call_args.kwargs.get("chat_id", call_args[1].get("chat_id", ""))
        assert target == "67890"

    async def test_bot_not_started(self) -> None:
        """Bot baslatilmamissa (app=None) hata olmamali."""
        bot = _make_bot()
        bot.app = None
        await bot.send_alert("Baslik", "Mesaj")


# === TestSendApprovalResult ===


class TestSendApprovalResult:
    """Onay sonucu gonderme testleri."""

    async def test_approved(self) -> None:
        """Onaylanan sonuc 'ONAYLANDI' icermeli."""
        bot = _make_bot()
        await bot.send_approval_result("abc12345-6789", approved=True)
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "ONAYLANDI" in text

    async def test_rejected(self) -> None:
        """Reddedilen sonuc 'REDDEDILDI' icermeli."""
        bot = _make_bot()
        await bot.send_approval_result("abc12345-6789", approved=False)
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "REDDEDILDI" in text

    async def test_with_details(self) -> None:
        """Detay bilgisi metinde yer almali."""
        bot = _make_bot()
        await bot.send_approval_result(
            "abc12345-6789", approved=True, details="Ek bilgi",
        )
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "Ek bilgi" in text

    async def test_without_details(self) -> None:
        """Detay yoksa sadece durum mesaji olmali."""
        bot = _make_bot()
        await bot.send_approval_result("abc12345-6789", approved=True)
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "Detay" not in text

    async def test_custom_chat_id(self) -> None:
        """Ozel chat_id kullanilabilmeli."""
        bot = _make_bot()
        await bot.send_approval_result(
            "abc12345-6789", approved=True, chat_id="67890",
        )
        call_args = bot.app.bot.send_message.call_args
        target = call_args.kwargs.get("chat_id", call_args[1].get("chat_id", ""))
        assert target == "67890"

    async def test_id_truncated(self) -> None:
        """Approval ID ilk 8 karaktere kesilmeli."""
        bot = _make_bot()
        full_id = "abcdefgh-1234-5678-9012-ijklmnopqrst"
        await bot.send_approval_result(full_id, approved=True)
        call_args = bot.app.bot.send_message.call_args
        text = call_args.kwargs.get("text", call_args[1].get("text", ""))
        assert "abcdefgh" in text
        assert full_id not in text


# === TestSendMessage ===


class TestSendMessage:
    """Mesaj gonderme testleri."""

    async def test_basic_send(self) -> None:
        """Temel mesaj admin'e gonderilmeli."""
        bot = _make_bot()
        await bot.send_message("Merhaba")
        bot.app.bot.send_message.assert_called_once_with(
            chat_id="12345", text="Merhaba",
        )

    async def test_custom_chat_id(self) -> None:
        """Ozel chat_id kullanilabilmeli."""
        bot = _make_bot()
        await bot.send_message("Test", chat_id="67890")
        bot.app.bot.send_message.assert_called_once_with(
            chat_id="67890", text="Test",
        )

    async def test_no_target(self) -> None:
        """admin_chat_id ve chat_id yoksa mesaj gonderilmemeli."""
        bot = _make_bot(admin_chat_id="")
        await bot.send_message("Test")
        bot.app.bot.send_message.assert_not_called()

    async def test_bot_not_started(self) -> None:
        """Bot baslatilmamissa (app=None) hata olmamali."""
        bot = _make_bot()
        bot.app = None
        await bot.send_message("Test")


# === TestSendButtons ===


class TestSendButtons:
    """Butonlu mesaj gonderme testleri."""

    async def test_basic_buttons(self) -> None:
        """Temel butonlu mesaj gonderilmeli."""
        bot = _make_bot()
        buttons = [
            {"text": "Onayla", "callback_data": "approve"},
            {"text": "Reddet", "callback_data": "reject"},
        ]
        await bot.send_buttons(text="Secim yapin", buttons=buttons)
        bot.app.bot.send_message.assert_called_once()
        call_kwargs = bot.app.bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == "12345"
        assert call_kwargs["text"] == "Secim yapin"
        assert call_kwargs["reply_markup"] is not None

    async def test_custom_chat_id(self) -> None:
        """Ozel chat_id kullanilabilmeli."""
        bot = _make_bot()
        buttons = [{"text": "Test", "callback_data": "test"}]
        await bot.send_buttons(text="Test", buttons=buttons, chat_id="67890")
        call_kwargs = bot.app.bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == "67890"

    async def test_bot_not_started(self) -> None:
        """Bot baslatilmamissa (app=None) hata olmamali."""
        bot = _make_bot()
        bot.app = None
        buttons = [{"text": "Test", "callback_data": "test"}]
        await bot.send_buttons(text="Test", buttons=buttons)

    async def test_button_format(self) -> None:
        """Her buton InlineKeyboardMarkup formatinda olmali."""
        bot = _make_bot()
        buttons = [
            {"text": "Buton1", "callback_data": "data1"},
            {"text": "Buton2", "callback_data": "data2"},
        ]
        await bot.send_buttons(text="Test", buttons=buttons)
        call_kwargs = bot.app.bot.send_message.call_args.kwargs
        reply_markup = call_kwargs["reply_markup"]
        # InlineKeyboardMarkup nesnesi olmali
        assert reply_markup is not None


# === TestHandleMessage ===


class TestHandleMessage:
    """Metin mesaj isleyici testleri."""

    async def test_with_master_agent(self) -> None:
        """Master agent varsa run ve report cagrilmali."""
        bot = _make_bot()
        master = _make_master_agent()
        bot.master_agent = master
        update = _make_update(chat_id=12345, text="Sunucu durumu nedir?")
        context = _make_context()
        await bot._handle_message(update, context)
        master.run.assert_called_once()
        master.report.assert_called_once()
        update.effective_message.reply_text.assert_called_once_with("Rapor metni")

    async def test_without_master_agent(self) -> None:
        """Master agent yoksa kuyruk mesaji gosterilmeli."""
        bot = _make_bot()
        bot.master_agent = None
        update = _make_update(chat_id=12345, text="Test mesaji")
        context = _make_context()
        await bot._handle_message(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "kuyruguna eklendi" in call_text

    async def test_master_agent_error(self) -> None:
        """Master agent hata verirse hata mesaji gosterilmeli."""
        bot = _make_bot()
        master = _make_master_agent()
        master.run = AsyncMock(side_effect=Exception("islem hatasi"))
        bot.master_agent = master
        update = _make_update(chat_id=12345, text="Hata tetikle")
        context = _make_context()
        await bot._handle_message(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "hata olustu" in call_text.lower()

    async def test_no_effective_message(self) -> None:
        """effective_message None ise hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message = None
        context = _make_context()
        await bot._handle_message(update, context)

    async def test_no_text(self) -> None:
        """Metin icermeyen mesajda hatasiz donmelidir."""
        bot = _make_bot()
        update = MagicMock()
        update.effective_message.text = None
        context = _make_context()
        await bot._handle_message(update, context)


# === TestRegisterHandlers ===


class TestRegisterHandlers:
    """Handler kayit testleri."""

    def test_handlers_registered(self) -> None:
        """8 handler kaydedilmeli (6 komut + 1 callback + 1 mesaj)."""
        bot = _make_bot()
        # app.add_handler zaten MagicMock oldugu icin cagri sayisini kontrol et
        bot.app.add_handler.reset_mock()
        bot._register_handlers()
        assert bot.app.add_handler.call_count == 8

    def test_no_app_skips(self) -> None:
        """app=None ise handler kaydi atlanmali."""
        bot = _make_bot()
        bot.app = None
        # Hata olmadan tamamlanmali
        bot._register_handlers()

    def test_register_does_not_crash_twice(self) -> None:
        """Handler'lar iki kez kaydedildiginde hata olmamali."""
        bot = _make_bot()
        bot._register_handlers()
        bot._register_handlers()
        # Toplamda en az 16 cagri (2x8)
        assert bot.app.add_handler.call_count >= 16


# === TestBotInit ===


class TestBotInit:
    """TelegramBot baslatma testleri."""

    def test_empty_token_no_app(self) -> None:
        """Bos token ile app None olmalidir."""
        with patch("app.tools.telegram_bot.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = ""
            mock_settings.telegram_admin_chat_id = "12345"
            bot = TelegramBot()
        assert bot.app is None

    def test_admin_chat_id_set(self) -> None:
        """admin_chat_id dogru ayarlanmalidir."""
        with patch("app.tools.telegram_bot.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = ""
            mock_settings.telegram_admin_chat_id = "54321"
            bot = TelegramBot()
        assert bot.admin_chat_id == "54321"

    def test_master_agent_initially_none(self) -> None:
        """master_agent baslangicta None olmalidir."""
        with patch("app.tools.telegram_bot.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = ""
            mock_settings.telegram_admin_chat_id = ""
            bot = TelegramBot()
        assert bot.master_agent is None

    def test_notification_level_is_str_enum(self) -> None:
        """NotificationLevel str enum'dan turetilmeli."""
        assert isinstance(NotificationLevel.INFO, str)
        assert NotificationLevel.INFO == "info"

    def test_alert_severity_is_str_enum(self) -> None:
        """AlertSeverity str enum'dan turetilmeli."""
        assert isinstance(AlertSeverity.LOW, str)
        assert AlertSeverity.LOW == "low"
