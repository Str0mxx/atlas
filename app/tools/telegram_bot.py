"""ATLAS Telegram Bot modulu.

Admin ile iletisim icin kullanilir:
mesaj alma, gonderme, butonlu mesajlar ve onay is akisi.
Callback query isleme ile MasterAgent onay entegrasyonu saglar.
"""

import logging
from enum import Enum
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """Bildirim seviyesi tanimlari."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    """Alert onem seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TelegramBot:
    """ATLAS Telegram bot sinifi.

    Admin ile iki yonlu iletisim saglar. Callback query isleme
    ile MasterAgent onay is akisini destekler.

    Attributes:
        app: Telegram Application nesnesi.
        admin_chat_id: Admin kullanicinin chat ID'si.
        master_agent: MasterAgent referansi (dis bagimliliklardan atanir).
    """

    def __init__(self) -> None:
        """Telegram bot'u baslatir."""
        token = settings.telegram_bot_token.get_secret_value()
        self.admin_chat_id = settings.telegram_admin_chat_id
        self.app: Application | None = None  # type: ignore[type-arg]

        self.master_agent: Any = None

        if not token:
            logger.warning("Telegram bot token ayarlanmamis!")
            return

        self.app = Application.builder().token(token).build()
        self._register_handlers()
        logger.info("Telegram bot hazir")

    def _register_handlers(self) -> None:
        """Komut ve mesaj handler'larini kaydeder."""
        if not self.app:
            return

        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("agents", self._cmd_agents))
        self.app.add_handler(CommandHandler("history", self._cmd_history))
        self.app.add_handler(CommandHandler("approvals", self._cmd_approvals))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message),
        )

        logger.info("Telegram handler'lari kaydedildi")

    # === Admin Dogrulamasi ===

    def _is_admin(self, update: Update) -> bool:
        """Gonderenin admin olup olmadigini kontrol eder.

        Telegram chat ID (int) ile config admin_chat_id (str) karsilastirir.

        Args:
            update: Telegram Update nesnesi.

        Returns:
            Admin ise True, degilse False.
        """
        if not update.effective_chat:
            return False
        chat_id = str(update.effective_chat.id)
        return chat_id == self.admin_chat_id

    # === Komut handler'lari ===

    async def _cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """'/start' komutu."""
        if not update.effective_message:
            return
        await update.effective_message.reply_text(
            "ATLAS Otonom AI Sistemi aktif.\n"
            "Komutlar icin /help yazin.",
        )
        logger.info("Start komutu alindi: chat_id=%s", update.effective_chat)

    async def _cmd_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """'/status' komutu - sistem durumunu gosterir."""
        if not update.effective_message:
            return

        if not self._is_admin(update):
            await update.effective_message.reply_text(
                "Bu komutu kullanma yetkiniz yok.",
            )
            return

        if self.master_agent:
            agents = self.master_agent.get_registered_agents()
            agent_lines = "\n".join(
                f"  - {a['name']}: {a['status']} (gorev: {a['task_count']})"
                for a in agents
            )
            text = (
                "ATLAS Durum Raporu:\n"
                f"- Sistem: Aktif\n"
                f"- Master Agent: {self.master_agent.status.value}\n"
                f"- Kayitli agent: {len(agents)}\n"
                f"{agent_lines}"
            )
        else:
            text = (
                "ATLAS Durum Raporu:\n"
                "- Sistem: Aktif\n"
                "- Master Agent: Baslamamis"
            )

        await update.effective_message.reply_text(text)

    async def _cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """'/help' komutu - yardim mesaji gosterir."""
        if not update.effective_message:
            return

        if not self._is_admin(update):
            await update.effective_message.reply_text(
                "Bu komutu kullanma yetkiniz yok.",
            )
            return

        await update.effective_message.reply_text(
            "ATLAS Komutlari:\n"
            "/start - Bot'u baslat\n"
            "/status - Sistem durumu\n"
            "/agents - Kayitli agent listesi\n"
            "/history [limit] - Son karar gecmisi\n"
            "/approvals - Bekleyen onay istekleri\n"
            "/help - Bu yardim mesaji",
        )

    async def _cmd_agents(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """'/agents' komutu - kayitli agent listesini gosterir."""
        if not update.effective_message:
            return

        if not self._is_admin(update):
            await update.effective_message.reply_text(
                "Bu komutu kullanma yetkiniz yok.",
            )
            return

        if not self.master_agent:
            await update.effective_message.reply_text(
                "Master Agent henuz baslamadi.",
            )
            return

        agents = self.master_agent.get_registered_agents()
        if not agents:
            await update.effective_message.reply_text("Kayitli agent bulunamadi.")
            return

        lines = [self._format_agent_info(a) for a in agents]
        text = f"Kayitli Agent'lar ({len(agents)}):\n\n" + "\n".join(lines)
        await update.effective_message.reply_text(text)

    async def _cmd_history(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """'/history [limit]' komutu - son karar gecmisini gosterir."""
        if not update.effective_message:
            return

        if not self._is_admin(update):
            await update.effective_message.reply_text(
                "Bu komutu kullanma yetkiniz yok.",
            )
            return

        if not self.master_agent:
            await update.effective_message.reply_text(
                "Master Agent henuz baslamadi.",
            )
            return

        # Limit parametresini al (varsayilan 5)
        limit = 5
        if context.args:
            try:
                limit = int(context.args[0])
                limit = max(1, min(limit, 50))
            except (ValueError, IndexError):
                pass

        entries = self.master_agent.get_decision_history(limit=limit)
        if not entries:
            await update.effective_message.reply_text("Karar gecmisi bos.")
            return

        lines = [self._format_decision_entry(e) for e in entries]
        text = f"Son {len(entries)} Karar:\n\n" + "\n---\n".join(lines)
        await update.effective_message.reply_text(text)

    async def _cmd_approvals(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """'/approvals' komutu - bekleyen onay isteklerini gosterir."""
        if not update.effective_message:
            return

        if not self._is_admin(update):
            await update.effective_message.reply_text(
                "Bu komutu kullanma yetkiniz yok.",
            )
            return

        if not self.master_agent:
            await update.effective_message.reply_text(
                "Master Agent henuz baslamadi.",
            )
            return

        approvals = self.master_agent.get_pending_approvals()
        if not approvals:
            await update.effective_message.reply_text("Bekleyen onay istegi yok.")
            return

        for approval in approvals:
            desc = approval.task.get("description", "Tanimsiz gorev")
            text = (
                f"Onay Bekliyor:\n"
                f"ID: {approval.id[:8]}...\n"
                f"Gorev: {desc}\n"
                f"Aksiyon: {approval.action}\n"
                f"Zaman asimi: {approval.timeout_seconds}s"
            )
            await self.send_buttons(
                text=text,
                buttons=[
                    {"text": "Onayla", "callback_data": f"approve_{approval.id}"},
                    {"text": "Reddet", "callback_data": f"reject_{approval.id}"},
                ],
            )

    # === Mesaj handler'lari ===

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Gelen metin mesajlarini isler."""
        if not update.effective_message or not update.effective_message.text:
            return

        text = update.effective_message.text
        chat_id = str(update.effective_chat.id) if update.effective_chat else ""

        logger.info("Mesaj alindi: chat_id=%s, text=%s", chat_id, text[:50])

        if self.master_agent:
            try:
                result = await self.master_agent.run({
                    "description": text,
                    "source": "telegram",
                    "chat_id": chat_id,
                })
                report = await self.master_agent.report(result)
                await update.effective_message.reply_text(report)
            except Exception as exc:
                logger.error("Master Agent islem hatasi: %s", exc)
                await update.effective_message.reply_text(
                    f"Islem sirasinda hata olustu: {exc}",
                )
        else:
            await update.effective_message.reply_text(
                f"Mesajiniz alindi: '{text[:100]}'\nIslem kuyruguna eklendi.",
            )

    async def _handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Buton tiklamalarini isler.

        approve_{id} / reject_{id} formatindaki callback'leri
        MasterAgent onay is akisina yonlendirir.

        Args:
            update: Telegram Update nesnesi.
            context: Callback context'i.
        """
        query = update.callback_query
        if not query:
            return

        await query.answer()

        # Admin dogrulamasi
        if not self._is_admin(update):
            if query.message:
                await query.message.reply_text("Bu islemi yapma yetkiniz yok.")
            return

        data = query.data or ""
        logger.info("Buton tiklandi: data=%s", data)

        if not self.master_agent:
            if query.message:
                await query.message.reply_text("Master Agent henuz baslamadi.")
            return

        # approve_immediate / reject_immediate
        if data == "approve_immediate":
            if query.message:
                await query.message.edit_text(
                    f"{query.message.text}\n\n--- ONAYLANDI ---",
                )
            return

        if data == "reject_immediate":
            if query.message:
                await query.message.edit_text(
                    f"{query.message.text}\n\n--- REDDEDILDI ---",
                )
            return

        # approve_{approval_id} / reject_{approval_id}
        if data.startswith("approve_"):
            approval_id = data[len("approve_"):]
            result = await self.master_agent.handle_approval_response(
                approval_id, approved=True,
            )
            status_text = "ONAYLANDI" if result.success else f"HATA: {result.message}"
            if query.message:
                await query.message.edit_text(
                    f"{query.message.text}\n\n--- {status_text} ---",
                )
            return

        if data.startswith("reject_"):
            approval_id = data[len("reject_"):]
            result = await self.master_agent.handle_approval_response(
                approval_id, approved=False,
            )
            status_text = "REDDEDILDI" if result.success else f"HATA: {result.message}"
            if query.message:
                await query.message.edit_text(
                    f"{query.message.text}\n\n--- {status_text} ---",
                )
            return

        # Bilinmeyen callback
        if query.message:
            await query.message.reply_text(f"Bilinmeyen islem: {data}")

    # === Mesaj gonderme metodlari ===

    async def send_message(self, text: str, chat_id: str | None = None) -> None:
        """Mesaj gonderir.

        Args:
            text: Gonderilecek mesaj metni.
            chat_id: Hedef chat ID. None ise admin'e gonderir.
        """
        if not self.app:
            logger.error("Bot baslamamis, mesaj gonderilemedi")
            return

        target = chat_id or self.admin_chat_id
        if not target:
            logger.error("Hedef chat_id belirtilmemis")
            return

        await self.app.bot.send_message(chat_id=target, text=text)
        logger.info("Mesaj gonderildi: chat_id=%s", target)

    async def send_buttons(
        self,
        text: str,
        buttons: list[dict[str, str]],
        chat_id: str | None = None,
    ) -> None:
        """Butonlu mesaj gonderir.

        Args:
            text: Mesaj metni.
            buttons: Buton listesi. Her buton {"text": "...", "callback_data": "..."} formatinda.
            chat_id: Hedef chat ID. None ise admin'e gonderir.

        Example:
            await bot.send_buttons(
                text="Ne yapmak istersiniz?",
                buttons=[
                    {"text": "Onayla", "callback_data": "approve"},
                    {"text": "Reddet", "callback_data": "reject"},
                ]
            )
        """
        if not self.app:
            logger.error("Bot baslamamis, butonlu mesaj gonderilemedi")
            return

        target = chat_id or self.admin_chat_id
        if not target:
            logger.error("Hedef chat_id belirtilmemis")
            return

        keyboard = [
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
            for btn in buttons
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.app.bot.send_message(
            chat_id=target,
            text=text,
            reply_markup=reply_markup,
        )
        logger.info(
            "Butonlu mesaj gonderildi: chat_id=%s, buton_sayisi=%d",
            target, len(buttons),
        )

    async def send_notification(
        self,
        title: str,
        message: str,
        level: str = "info",
        chat_id: str | None = None,
    ) -> None:
        """Formatli bildirim mesaji gonderir.

        Seviyeye gore etiket ve baslik formati uygular.

        Args:
            title: Bildirim basligi.
            message: Bildirim mesaji.
            level: Bildirim seviyesi (info/warning/error/critical).
            chat_id: Hedef chat ID. None ise admin'e gonderir.
        """
        level_icons = {
            "info": "[INFO]",
            "warning": "[UYARI]",
            "error": "[HATA]",
            "critical": "[KRITIK]",
        }
        icon = level_icons.get(level, "[INFO]")
        text = f"{icon} {title}\n{message}"
        await self.send_message(text, chat_id=chat_id)
        logger.info("Bildirim gonderildi: level=%s, title=%s", level, title)

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "medium",
        chat_id: str | None = None,
    ) -> None:
        """Alert bildirimi gonderir.

        Severity'ye gore formatlama uygular.

        Args:
            title: Alert basligi.
            message: Alert mesaji.
            severity: Onem seviyesi (low/medium/high/critical).
            chat_id: Hedef chat ID. None ise admin'e gonderir.
        """
        severity_labels = {
            "low": "DUSUK",
            "medium": "ORTA",
            "high": "YUKSEK",
            "critical": "KRITIK",
        }
        label = severity_labels.get(severity, "BILINMEYEN")
        text = (
            f"ALERT [{label}]\n"
            f"Baslik: {title}\n"
            f"Detay: {message}"
        )
        await self.send_message(text, chat_id=chat_id)
        logger.info("Alert gonderildi: severity=%s, title=%s", severity, title)

    async def send_approval_result(
        self,
        approval_id: str,
        approved: bool,
        details: str = "",
        chat_id: str | None = None,
    ) -> None:
        """Onay sonucu bildirimi gonderir.

        Args:
            approval_id: Onay istegi ID'si.
            approved: Onaylandi mi reddedildi mi.
            details: Ek detay mesaji.
            chat_id: Hedef chat ID. None ise admin'e gonderir.
        """
        status = "ONAYLANDI" if approved else "REDDEDILDI"
        text = f"Onay Sonucu: {status}\nID: {approval_id[:8]}..."
        if details:
            text += f"\nDetay: {details}"
        await self.send_message(text, chat_id=chat_id)
        logger.info(
            "Onay sonucu gonderildi: id=%s, approved=%s",
            approval_id[:8], approved,
        )

    # === Formatlama yardimcilari ===

    def _format_decision_entry(self, entry: Any) -> str:
        """Karar denetim kaydini formatli metne donusturur.

        Args:
            entry: DecisionAuditEntry nesnesi.

        Returns:
            Formatlanmis karar metni.
        """
        outcome = "Bekliyor"
        if entry.outcome_success is True:
            outcome = "Basarili"
        elif entry.outcome_success is False:
            outcome = "Basarisiz"

        agent_text = entry.agent_selected or "Atanmadi"
        return (
            f"Gorev: {entry.task_description[:80]}\n"
            f"Risk: {entry.risk} | Aciliyet: {entry.urgency}\n"
            f"Aksiyon: {entry.action} | Guven: {entry.confidence:.0%}\n"
            f"Agent: {agent_text}\n"
            f"Sonuc: {outcome}\n"
            f"Zaman: {entry.timestamp.strftime('%d/%m %H:%M')}"
        )

    def _format_agent_info(self, agent_info: dict[str, Any]) -> str:
        """Agent bilgisini formatli metne donusturur.

        Args:
            agent_info: Agent.get_info() sonucu sozluk.

        Returns:
            Formatlanmis agent bilgi metni.
        """
        status = agent_info.get("status", "unknown")
        task_count = agent_info.get("task_count", 0)
        name = agent_info.get("name", "Bilinmeyen")
        return f"  [{status.upper()}] {name} (gorev: {task_count})"

    # === Yasam dongusu ===

    async def start_polling(self) -> None:
        """Bot'u polling modunda baslatir."""
        if not self.app:
            logger.error("Bot baslatilmadi: token eksik")
            return

        logger.info("Telegram bot polling baslatiliyor...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()  # type: ignore[union-attr]

    async def stop(self) -> None:
        """Bot'u durdurur."""
        if not self.app:
            return

        logger.info("Telegram bot durduruluyor...")
        await self.app.updater.stop()  # type: ignore[union-attr]
        await self.app.stop()
        await self.app.shutdown()
