"""ATLAS Telegram Bot modulu.

Admin ile iletisim icin kullanilir:
mesaj alma, gonderme ve butonlu mesajlar.
"""

import logging
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


class TelegramBot:
    """ATLAS Telegram bot sinifi.

    Admin ile iki yonlu iletisim saglar.

    Attributes:
        app: Telegram Application nesnesi.
        admin_chat_id: Admin kullanicinin chat ID'si.
    """

    def __init__(self) -> None:
        """Telegram bot'u baslatir."""
        token = settings.telegram_bot_token.get_secret_value()
        self.admin_chat_id = settings.telegram_admin_chat_id
        self.app: Application | None = None  # type: ignore[type-arg]

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
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        logger.info("Telegram handler'lari kaydedildi")

    # === Komut handler'lari ===

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """'/start' komutu."""
        if not update.effective_message:
            return
        await update.effective_message.reply_text(
            "ATLAS Otonom AI Sistemi aktif.\n"
            "Komutlar icin /help yazin."
        )
        logger.info("Start komutu alindi: chat_id=%s", update.effective_chat)

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """'/status' komutu - sistem durumunu gosterir."""
        if not update.effective_message:
            return
        # TODO: Gercek sistem durumunu goster
        await update.effective_message.reply_text(
            "ATLAS Durum Raporu:\n"
            "- Sistem: Aktif\n"
            "- Master Agent: Hazir\n"
            "- Aktif gorev: 0"
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """'/help' komutu - yardim mesaji gosterir."""
        if not update.effective_message:
            return
        await update.effective_message.reply_text(
            "ATLAS Komutlari:\n"
            "/start - Bot'u baslat\n"
            "/status - Sistem durumu\n"
            "/help - Bu yardim mesaji"
        )

    # === Mesaj handler'lari ===

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Gelen metin mesajlarini isler."""
        if not update.effective_message or not update.effective_message.text:
            return

        text = update.effective_message.text
        chat_id = str(update.effective_chat.id) if update.effective_chat else ""

        logger.info("Mesaj alindi: chat_id=%s, text=%s", chat_id, text[:50])

        # TODO: Master Agent'a ilet
        await update.effective_message.reply_text(
            f"Mesajiniz alindi: '{text[:100]}'\nIslem kuyruguna eklendi."
        )

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Buton tiklamalarini isler."""
        query = update.callback_query
        if not query:
            return

        await query.answer()
        logger.info("Buton tiklandi: data=%s", query.data)

        # TODO: Callback verilerine gore islem yap
        if query.message:
            await query.message.reply_text(f"Secim alindi: {query.data}")

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
        logger.info("Butonlu mesaj gonderildi: chat_id=%s, buton_sayisi=%d", target, len(buttons))

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
