"""
Telegram Config Interface modulu.

/config komutu, ayar gosterimi,
deger guncelleme, onay akisi,
degisiklik gecmisi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TelegramConfigInterface:
    """Telegram uzerinden konfig yonetimi.

    Attributes:
        _config: Mevcut konfigurasyonlar.
        _pending: Onay bekleyen degisiklikler.
        _history: Islem gecmisi.
        _masked_keys: Maskeli anahtarlar (API key vb.).
        _stats: Istatistikler.
    """

    # Otomatik maskelenecek anahtar isimleri
    SENSITIVE_KEYS: set[str] = {
        "api_key", "secret", "password", "token",
        "private_key", "auth", "credential",
    }

    def __init__(self) -> None:
        """Arayuzu baslatir."""
        self._config: dict[str, Any] = {}
        self._pending: dict[str, dict] = {}
        self._history: list[dict] = []
        self._masked_keys: set[str] = set()
        self._stats: dict[str, int] = {
            "commands_received": 0,
            "settings_displayed": 0,
            "updates_requested": 0,
            "updates_confirmed": 0,
            "updates_cancelled": 0,
            "history_views": 0,
        }
        logger.info("TelegramConfigInterface baslatildi")

    @property
    def pending_count(self) -> int:
        """Onay bekleyen degisiklik sayisi."""
        return len(self._pending)

    @property
    def history_count(self) -> int:
        """Islem gecmisi kaydi sayisi."""
        return len(self._history)

    def load_config(
        self,
        config: dict | None = None,
    ) -> dict[str, Any]:
        """Konfigurasyonu yukler.

        Args:
            config: Yuklenecek konfig.

        Returns:
            Yukleme bilgisi.
        """
        try:
            if config is None:
                return {"loaded": False, "error": "konfig_gerekli"}

            self._config = dict(config)
            return {
                "loaded": True,
                "key_count": len(self._config),
            }
        except Exception as e:
            logger.error("Konfig yukleme hatasi: %s", e)
            return {"loaded": False, "error": str(e)}

    def handle_config_command(
        self,
        chat_id: str = "",
        args: list[str] | None = None,
    ) -> dict[str, Any]:
        """/config komutunu isler.

        Args:
            chat_id: Telegram chat ID.
            args: Komut argumanları (/config, /config get key, /config set key val).

        Returns:
            Komut yaniti.
        """
        try:
            self._stats["commands_received"] += 1

            if not chat_id:
                return {"handled": False, "error": "chat_id_gerekli"}

            args = args or []
            subcommand = args[0].lower() if args else "list"

            if subcommand == "list":
                return self._cmd_list(chat_id)
            elif subcommand == "get" and len(args) >= 2:
                return self._cmd_get(chat_id, args[1])
            elif subcommand == "set" and len(args) >= 3:
                return self._cmd_set(chat_id, args[1], " ".join(args[2:]))
            elif subcommand == "history":
                return self._cmd_history(chat_id)
            elif subcommand == "help":
                return self._cmd_help(chat_id)
            else:
                return {
                    "handled": True,
                    "chat_id": chat_id,
                    "message": (
                        "Kullanim: /config [list|get <key>|set <key> <val>|history|help]"
                    ),
                    "action": "usage_hint",
                }
        except Exception as e:
            logger.error("/config komut hatasi: %s", e)
            return {"handled": False, "error": str(e)}

    def display_settings(
        self,
        chat_id: str = "",
        filter_prefix: str = "",
    ) -> dict[str, Any]:
        """Ayarlari gosterir.

        Args:
            chat_id: Telegram chat ID.
            filter_prefix: Filtre oneki (orn: 'hotreload_').

        Returns:
            Gosterim bilgisi.
        """
        try:
            self._stats["settings_displayed"] += 1

            if not chat_id:
                return {"displayed": False, "error": "chat_id_gerekli"}

            entries = []
            for key, value in sorted(self._config.items()):
                if filter_prefix and not key.startswith(filter_prefix):
                    continue
                entries.append({
                    "key": key,
                    "value": self._mask_value(key, value),
                    "masked": self._is_sensitive(key),
                })

            # Telegram mesaj formati
            lines = ["*ATLAS Konfigurasyonlari*\n"]
            for e in entries:
                indicator = "[gizli]" if e["masked"] else ""
                lines.append(f"`{e['key']}` = `{e['value']}` {indicator}")

            return {
                "displayed": True,
                "chat_id": chat_id,
                "message": "\n".join(lines),
                "entry_count": len(entries),
                "filter_prefix": filter_prefix,
            }
        except Exception as e:
            logger.error("Ayar gosterim hatasi: %s", e)
            return {"displayed": False, "error": str(e)}

    def request_update(
        self,
        chat_id: str = "",
        key: str = "",
        new_value: str = "",
    ) -> dict[str, Any]:
        """Konfig guncelleme talebini olusturur (onay bekler).

        Args:
            chat_id: Telegram chat ID.
            key: Guncellenecek anahtar.
            new_value: Yeni deger (string).

        Returns:
            Talep bilgisi.
        """
        try:
            self._stats["updates_requested"] += 1

            if not chat_id or not key:
                return {"requested": False, "error": "chat_id_ve_anahtar_gerekli"}

            if key not in self._config:
                return {
                    "requested": False,
                    "error": "bilinmeyen_anahtar",
                    "key": key,
                }

            old_value = self._config.get(key)
            request_id = f"{chat_id}_{key}_{int(time.time())}"

            self._pending[request_id] = {
                "chat_id": chat_id,
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "requested_at": time.time(),
            }

            return {
                "requested": True,
                "request_id": request_id,
                "key": key,
                "old_value": self._mask_value(key, old_value),
                "new_value": self._mask_value(key, new_value),
                "message": (
                    f"*Onay Gerekli*\n"
                    f"`{key}` degeri degistirilecek.\n"
                    f"Eski: `{self._mask_value(key, old_value)}`\n"
                    f"Yeni: `{self._mask_value(key, new_value)}`\n"
                    f"Onaylamak icin: /confirm {request_id}"
                ),
            }
        except Exception as e:
            logger.error("Guncelleme talep hatasi: %s", e)
            return {"requested": False, "error": str(e)}

    def confirm_update(
        self,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Bekleyen guncellemeyi onaylar.

        Args:
            request_id: Talep ID.

        Returns:
            Onay sonucu.
        """
        try:
            if not request_id:
                return {"confirmed": False, "error": "talep_id_gerekli"}

            if request_id not in self._pending:
                return {
                    "confirmed": False,
                    "reason": "talep_bulunamadi",
                    "request_id": request_id,
                }

            pending = self._pending.pop(request_id)
            key = pending["key"]
            new_value = pending["new_value"]

            # Tip donusumu dene
            converted = self._convert_value(key, new_value)
            old_value = self._config.get(key)
            self._config[key] = converted

            # Gecmis kaydi
            self._history.append({
                "request_id": request_id,
                "chat_id": pending["chat_id"],
                "key": key,
                "old_value": old_value,
                "new_value": converted,
                "timestamp": time.time(),
                "action": "confirmed",
            })
            self._stats["updates_confirmed"] += 1

            return {
                "confirmed": True,
                "key": key,
                "old_value": old_value,
                "new_value": converted,
                "message": f"`{key}` guncellendi.",
            }
        except Exception as e:
            logger.error("Onay hatasi: %s", e)
            return {"confirmed": False, "error": str(e)}

    def cancel_update(
        self,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Bekleyen guncellemeyi iptal eder.

        Args:
            request_id: Talep ID.

        Returns:
            Iptal sonucu.
        """
        try:
            if not request_id:
                return {"cancelled": False, "error": "talep_id_gerekli"}

            if request_id not in self._pending:
                return {
                    "cancelled": False,
                    "reason": "talep_bulunamadi",
                }

            pending = self._pending.pop(request_id)
            self._history.append({
                "request_id": request_id,
                "chat_id": pending["chat_id"],
                "key": pending["key"],
                "timestamp": time.time(),
                "action": "cancelled",
            })
            self._stats["updates_cancelled"] += 1

            return {
                "cancelled": True,
                "key": pending["key"],
                "message": "Guncelleme iptal edildi.",
            }
        except Exception as e:
            logger.error("Iptal hatasi: %s", e)
            return {"cancelled": False, "error": str(e)}

    def get_history(
        self,
        limit: int = 10,
        chat_id: str = "",
    ) -> dict[str, Any]:
        """Islem gecmisini dondurur.

        Args:
            limit: En son kac kayit.
            chat_id: Belirli bir chat'in gecmisi (bos = hepsi).

        Returns:
            Gecmis listesi.
        """
        try:
            self._stats["history_views"] += 1
            records = self._history

            if chat_id:
                records = [r for r in records if r.get("chat_id") == chat_id]

            recent = records[-limit:] if limit > 0 else records
            return {
                "retrieved": True,
                "history": recent,
                "total": len(records),
                "returned": len(recent),
            }
        except Exception as e:
            logger.error("Gecmis alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def mask_key(self, key: str = "") -> dict[str, Any]:
        """Anahtari maskeli olarak isaretler.

        Args:
            key: Maskelenecek anahtar.

        Returns:
            Islem bilgisi.
        """
        try:
            if not key:
                return {"masked": False, "error": "anahtar_gerekli"}

            self._masked_keys.add(key)
            return {"masked": True, "key": key}
        except Exception as e:
            logger.error("Maskeleme hatasi: %s", e)
            return {"masked": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "config_keys": len(self._config),
                "pending_count": self.pending_count,
                "history_count": self.history_count,
                "masked_keys": len(self._masked_keys),
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    # ── Ozel yardimci metodlar ────────────────────────────────────────────────

    def _cmd_list(self, chat_id: str) -> dict[str, Any]:
        """Ayarlari listeler."""
        result = self.display_settings(chat_id)
        result["handled"] = result.get("displayed", False)
        return result

    def _cmd_get(self, chat_id: str, key: str) -> dict[str, Any]:
        """Tek ayar gosterir."""
        if key not in self._config:
            return {
                "handled": True,
                "chat_id": chat_id,
                "message": f"`{key}` bulunamadi.",
                "action": "get",
            }
        val = self._mask_value(key, self._config[key])
        return {
            "handled": True,
            "chat_id": chat_id,
            "message": f"`{key}` = `{val}`",
            "action": "get",
            "key": key,
        }

    def _cmd_set(
        self, chat_id: str, key: str, value: str
    ) -> dict[str, Any]:
        """Deger guncelleme talebi olusturur."""
        result = self.request_update(chat_id, key, value)
        result["action"] = "set_requested"
        result["handled"] = result.get("requested", False)
        return result

    def _cmd_history(self, chat_id: str) -> dict[str, Any]:
        """Gecmis gosterir."""
        hist = self.get_history(limit=5, chat_id=chat_id)
        lines = ["*Son Degisiklikler*\n"]
        for r in hist.get("history", []):
            ts = int(r.get("timestamp", 0))
            lines.append(
                f"`{r.get('key','?')}`: {r.get('action','?')} @ {ts}"
            )
        return {
            "handled": True,
            "chat_id": chat_id,
            "message": "\n".join(lines) if len(lines) > 1 else "Gecmis bos.",
            "action": "history",
        }

    def _cmd_help(self, chat_id: str) -> dict[str, Any]:
        """Yardim gosterir."""
        return {
            "handled": True,
            "chat_id": chat_id,
            "message": (
                "*ATLAS Konfig Komutlari*\n"
                "/config list — Tum ayarlari goster\n"
                "/config get <anahtar> — Ayar degerini goster\n"
                "/config set <anahtar> <deger> — Ayar guncelle\n"
                "/config history — Son degisiklikleri goster\n"
                "/config help — Bu yardimi goster"
            ),
            "action": "help",
        }

    def _is_sensitive(self, key: str) -> bool:
        """Anahtarin hassas olup olmadigini kontrol eder."""
        if key in self._masked_keys:
            return True
        key_lower = key.lower()
        return any(s in key_lower for s in self.SENSITIVE_KEYS)

    def _mask_value(self, key: str, value: Any) -> Any:
        """Hassas degerleri maskeler."""
        if self._is_sensitive(key) and value:
            return "***"
        return value

    def _convert_value(self, key: str, value: str) -> Any:
        """String degeri uygun tipe donusturur."""
        current = self._config.get(key)
        if isinstance(current, bool):
            return value.lower() in ("true", "1", "yes", "on")
        if isinstance(current, int):
            try:
                return int(value)
            except ValueError:
                return value
        if isinstance(current, float):
            try:
                return float(value)
            except ValueError:
                return value
        return value
