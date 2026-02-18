"""
Config Hot Reloader modulu.

Config yeniden yukleme, dogrulama,
degisiklik uygulama, hata geri alma,
bildirim.
"""

import copy
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConfigHotReloader:
    """Config hot reloader.

    Attributes:
        _current: Aktif konfigurasyonlar.
        _previous: Onceki konfigurasyonlar.
        _history: Degisiklik gecmisi.
        _listeners: Degisiklik dinleyicileri.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Reloader'i baslatir."""
        self._current: dict[str, Any] = {}
        self._previous: dict[str, Any] = {}
        self._history: list[dict] = []
        self._listeners: list[Any] = []
        self._stats: dict[str, int] = {
            "reloads_attempted": 0,
            "reloads_successful": 0,
            "reloads_failed": 0,
            "rollbacks_performed": 0,
            "notifications_sent": 0,
        }
        logger.info("ConfigHotReloader baslatildi")

    @property
    def reload_count(self) -> int:
        """Basarili yeniden yukleme sayisi."""
        return self._stats["reloads_successful"]

    @property
    def has_previous(self) -> bool:
        """Onceki konfigurasyonun olup olmadigi."""
        return bool(self._previous)

    def load_initial(
        self,
        config: dict | None = None,
    ) -> dict[str, Any]:
        """Ilk konfigurasyonu yukler.

        Args:
            config: Baslangic konfigurasyonu.

        Returns:
            Yukleme bilgisi.
        """
        try:
            if config is None:
                return {"loaded": False, "error": "konfig_gerekli"}

            self._current = copy.deepcopy(config)
            logger.info("Baslangic konfig yuklendi (%d anahtar)", len(config))
            return {
                "loaded": True,
                "key_count": len(self._current),
            }
        except Exception as e:
            logger.error("Ilk yukleme hatasi: %s", e)
            return {"loaded": False, "error": str(e)}

    def reload(
        self,
        new_config: dict | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Konfigurasyonu yeniden yukler.

        Args:
            new_config: Yeni konfigurasyonlar.
            source: Degisiklik kaynagi (file/api/telegram/manual).

        Returns:
            Yeniden yukleme sonucu.
        """
        try:
            self._stats["reloads_attempted"] += 1

            if new_config is None:
                return {"reloaded": False, "error": "yeni_konfig_gerekli"}

            # Degisiklikleri bul
            changes = self._find_changes(self._current, new_config)
            if not changes:
                return {
                    "reloaded": True,
                    "changed": False,
                    "reason": "degisiklik_yok",
                }

            # Onceki kaydedilir
            self._previous = copy.deepcopy(self._current)

            # Yeni konfig uygula
            self._current = copy.deepcopy(new_config)
            self._stats["reloads_successful"] += 1

            # Gecmis kaydi
            record = {
                "timestamp": time.time(),
                "source": source,
                "changes": changes,
                "key_count": len(new_config),
            }
            self._history.append(record)

            # Dinleyicileri bilgilendir
            self._notify(changes, source)

            logger.info(
                "Konfig yeniden yuklendi: %d degisiklik (%s)",
                len(changes), source
            )
            return {
                "reloaded": True,
                "changed": True,
                "changes": changes,
                "source": source,
            }
        except Exception as e:
            logger.error("Yeniden yukleme hatasi: %s", e)
            self._stats["reloads_failed"] += 1
            return {"reloaded": False, "error": str(e)}

    def apply_change(
        self,
        key: str = "",
        value: Any = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Tek bir konfig degerini gunceller.

        Args:
            key: Konfig anahtari.
            value: Yeni deger.
            source: Degisiklik kaynagi.

        Returns:
            Guncelleme sonucu.
        """
        try:
            if not key:
                return {"applied": False, "error": "anahtar_gerekli"}

            old_value = self._current.get(key)
            self._previous = copy.deepcopy(self._current)
            self._current[key] = value

            change = {
                "key": key,
                "old": old_value,
                "new": value,
                "type": "update" if key in self._current else "add",
            }
            self._history.append({
                "timestamp": time.time(),
                "source": source,
                "changes": [change],
                "key_count": len(self._current),
            })
            self._stats["reloads_successful"] += 1
            self._notify([change], source)

            return {
                "applied": True,
                "key": key,
                "old_value": old_value,
                "new_value": value,
            }
        except Exception as e:
            logger.error("Degisiklik uygulama hatasi: %s", e)
            return {"applied": False, "error": str(e)}

    def rollback(self) -> dict[str, Any]:
        """Onceki konfigurasyona geri doner.

        Returns:
            Geri alma sonucu.
        """
        try:
            if not self._previous:
                return {"rolled_back": False, "reason": "onceki_yok"}

            changes = self._find_changes(self._current, self._previous)
            self._current = copy.deepcopy(self._previous)
            self._previous = {}
            self._stats["rollbacks_performed"] += 1

            self._history.append({
                "timestamp": time.time(),
                "source": "rollback",
                "changes": changes,
                "key_count": len(self._current),
            })

            self._notify(changes, "rollback")
            logger.info("Konfig geri alindi: %d degisiklik", len(changes))
            return {
                "rolled_back": True,
                "changes_reverted": len(changes),
            }
        except Exception as e:
            logger.error("Geri alma hatasi: %s", e)
            return {"rolled_back": False, "error": str(e)}

    def get_value(self, key: str = "") -> dict[str, Any]:
        """Konfig degeri dondurur.

        Args:
            key: Anahtar.

        Returns:
            Deger bilgisi.
        """
        try:
            if not key:
                return {"found": False, "error": "anahtar_gerekli"}

            if key not in self._current:
                return {"found": False, "key": key}

            return {
                "found": True,
                "key": key,
                "value": self._current[key],
            }
        except Exception as e:
            logger.error("Deger alma hatasi: %s", e)
            return {"found": False, "error": str(e)}

    def get_all(self) -> dict[str, Any]:
        """Tum konfig degerlerini dondurur.

        Returns:
            Konfigurasyonlar.
        """
        try:
            return {
                "retrieved": True,
                "config": dict(self._current),
                "key_count": len(self._current),
            }
        except Exception as e:
            logger.error("Tum konfig alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def add_listener(self, listener: Any) -> dict[str, Any]:
        """Degisiklik dinleyicisi ekler.

        Args:
            listener: Cagrilacak fonksiyon (changes, source).

        Returns:
            Kayit bilgisi.
        """
        try:
            if listener is None:
                return {"added": False, "error": "dinleyici_gerekli"}

            if listener not in self._listeners:
                self._listeners.append(listener)

            return {
                "added": True,
                "total_listeners": len(self._listeners),
            }
        except Exception as e:
            logger.error("Dinleyici ekleme hatasi: %s", e)
            return {"added": False, "error": str(e)}

    def remove_listener(self, listener: Any) -> dict[str, Any]:
        """Dinleyiciyi kaldirir.

        Args:
            listener: Cikarilacak fonksiyon.

        Returns:
            Islem bilgisi.
        """
        try:
            if listener in self._listeners:
                self._listeners.remove(listener)
                return {"removed": True}
            return {"removed": False, "reason": "kayitli_degil"}
        except Exception as e:
            logger.error("Dinleyici kaldirma hatasi: %s", e)
            return {"removed": False, "error": str(e)}

    def get_history(
        self,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Degisiklik gecmisini dondurur.

        Args:
            limit: En son kac kayit.

        Returns:
            Gecmis listesi.
        """
        try:
            recent = self._history[-limit:] if limit > 0 else self._history
            return {
                "retrieved": True,
                "history": recent,
                "total": len(self._history),
                "returned": len(recent),
            }
        except Exception as e:
            logger.error("Gecmis alma hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def get_diff(
        self,
        other_config: dict | None = None,
    ) -> dict[str, Any]:
        """Mevcut konfig ile baska bir konfig arasindaki farki dondurur.

        Args:
            other_config: Karsilastirilacak konfig.

        Returns:
            Fark bilgisi.
        """
        try:
            if other_config is None:
                return {"compared": False, "error": "konfig_gerekli"}

            changes = self._find_changes(self._current, other_config)
            return {
                "compared": True,
                "changes": changes,
                "change_count": len(changes),
                "has_changes": len(changes) > 0,
            }
        except Exception as e:
            logger.error("Diff hatasi: %s", e)
            return {"compared": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "key_count": len(self._current),
                "has_previous": self.has_previous,
                "reload_count": self.reload_count,
                "history_count": len(self._history),
                "listener_count": len(self._listeners),
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    # ── Ozel yardimci metodlar ────────────────────────────────────────────────

    def _find_changes(
        self,
        old: dict,
        new: dict,
    ) -> list[dict]:
        """Iki konfig arasindaki degisiklikleri bulur."""
        changes = []
        all_keys = set(old) | set(new)

        for key in all_keys:
            if key not in old:
                changes.append({
                    "key": key,
                    "old": None,
                    "new": new[key],
                    "type": "add",
                })
            elif key not in new:
                changes.append({
                    "key": key,
                    "old": old[key],
                    "new": None,
                    "type": "remove",
                })
            elif old[key] != new[key]:
                changes.append({
                    "key": key,
                    "old": old[key],
                    "new": new[key],
                    "type": "update",
                })
        return changes

    def _notify(self, changes: list[dict], source: str) -> None:
        """Kayitli dinleyicileri bilgilendirir."""
        self._stats["notifications_sent"] += 1
        for listener in list(self._listeners):
            try:
                listener(changes, source)
            except Exception as e:
                logger.warning("Dinleyici bildirim hatasi: %s", e)
