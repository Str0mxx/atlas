"""
Anahtar envanteri modulu.

Anahtar kataloglama, sahiplik takibi,
kapsam esleme, kullanim istatistikleri,
sure takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class KeyInventory:
    """Anahtar envanteri.

    Attributes:
        _keys: Anahtar kayitlari.
        _owners: Sahiplik esleme.
        _scopes: Kapsam esleme.
        _stats: Istatistikler.
    """

    KEY_TYPES: list[str] = [
        "api_key",
        "oauth_token",
        "service_account",
        "ssh_key",
        "tls_cert",
        "jwt_secret",
        "encryption_key",
    ]

    KEY_STATUSES: list[str] = [
        "active",
        "inactive",
        "expired",
        "revoked",
        "rotating",
    ]

    def __init__(self) -> None:
        """Envanteri baslatir."""
        self._keys: dict[
            str, dict
        ] = {}
        self._owners: dict[
            str, list[str]
        ] = {}
        self._scopes: dict[
            str, list[str]
        ] = {}
        self._stats: dict[str, int] = {
            "keys_registered": 0,
            "keys_expired": 0,
            "keys_revoked": 0,
            "lookups": 0,
            "scope_updates": 0,
        }
        logger.info(
            "KeyInventory baslatildi"
        )

    @property
    def key_count(self) -> int:
        """Aktif anahtar sayisi."""
        return sum(
            1
            for k in self._keys.values()
            if k["status"] == "active"
        )

    def register_key(
        self,
        name: str = "",
        key_type: str = "api_key",
        owner: str = "",
        service: str = "",
        scopes: list[str] | None = None,
        expires_days: int = 90,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Anahtar kaydeder.

        Args:
            name: Anahtar adi.
            key_type: Anahtar tipi.
            owner: Sahip.
            service: Servis adi.
            scopes: Kapsam listesi.
            expires_days: Gecerlilik suresi.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            if (
                key_type
                not in self.KEY_TYPES
            ):
                return {
                    "registered": False,
                    "error": (
                        f"Gecersiz tip: "
                        f"{key_type}"
                    ),
                }

            kid = f"ki_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()
            sc = scopes or []

            self._keys[kid] = {
                "key_id": kid,
                "name": name,
                "key_type": key_type,
                "owner": owner,
                "service": service,
                "scopes": sc,
                "status": "active",
                "expires_days": expires_days,
                "metadata": metadata or {},
                "usage_count": 0,
                "last_used": None,
                "created_at": now,
                "rotated_at": None,
            }

            if owner:
                if (
                    owner
                    not in self._owners
                ):
                    self._owners[owner] = []
                self._owners[owner].append(
                    kid
                )

            self._scopes[kid] = sc
            self._stats[
                "keys_registered"
            ] += 1

            return {
                "key_id": kid,
                "name": name,
                "key_type": key_type,
                "expires_days": expires_days,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def get_key(
        self,
        key_id: str = "",
    ) -> dict[str, Any]:
        """Anahtar bilgisi getirir.

        Args:
            key_id: Anahtar ID.

        Returns:
            Anahtar bilgisi.
        """
        try:
            self._stats["lookups"] += 1
            key = self._keys.get(key_id)
            if not key:
                return {
                    "found": False,
                    "error": (
                        "Anahtar bulunamadi"
                    ),
                }

            return {
                **key,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def update_status(
        self,
        key_id: str = "",
        status: str = "active",
    ) -> dict[str, Any]:
        """Durum gunceller.

        Args:
            key_id: Anahtar ID.
            status: Yeni durum.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            if (
                status
                not in self.KEY_STATUSES
            ):
                return {
                    "updated": False,
                    "error": (
                        f"Gecersiz: {status}"
                    ),
                }

            key = self._keys.get(key_id)
            if not key:
                return {
                    "updated": False,
                    "error": (
                        "Anahtar bulunamadi"
                    ),
                }

            old = key["status"]
            key["status"] = status
            if status == "expired":
                self._stats[
                    "keys_expired"
                ] += 1
            elif status == "revoked":
                self._stats[
                    "keys_revoked"
                ] += 1

            return {
                "key_id": key_id,
                "old_status": old,
                "new_status": status,
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def record_usage(
        self,
        key_id: str = "",
    ) -> dict[str, Any]:
        """Kullanim kaydeder.

        Args:
            key_id: Anahtar ID.

        Returns:
            Kayit bilgisi.
        """
        try:
            key = self._keys.get(key_id)
            if not key:
                return {
                    "recorded": False,
                    "error": (
                        "Anahtar bulunamadi"
                    ),
                }

            key["usage_count"] += 1
            key["last_used"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            return {
                "key_id": key_id,
                "usage_count": key[
                    "usage_count"
                ],
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def update_scopes(
        self,
        key_id: str = "",
        scopes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kapsam gunceller.

        Args:
            key_id: Anahtar ID.
            scopes: Yeni kapsamlar.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            key = self._keys.get(key_id)
            if not key:
                return {
                    "updated": False,
                    "error": (
                        "Anahtar bulunamadi"
                    ),
                }

            old_scopes = list(key["scopes"])
            new_scopes = scopes or []
            key["scopes"] = new_scopes
            self._scopes[key_id] = (
                new_scopes
            )
            self._stats[
                "scope_updates"
            ] += 1

            return {
                "key_id": key_id,
                "old_scopes": old_scopes,
                "new_scopes": new_scopes,
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def get_keys_by_owner(
        self,
        owner: str = "",
    ) -> dict[str, Any]:
        """Sahibe gore anahtarlari getirir.

        Args:
            owner: Sahip adi.

        Returns:
            Anahtar listesi.
        """
        try:
            kids = self._owners.get(
                owner, []
            )
            keys = [
                {
                    "key_id": kid,
                    "name": self._keys[kid][
                        "name"
                    ],
                    "status": self._keys[
                        kid
                    ]["status"],
                    "key_type": self._keys[
                        kid
                    ]["key_type"],
                }
                for kid in kids
                if kid in self._keys
            ]
            return {
                "owner": owner,
                "keys": keys,
                "count": len(keys),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_expiring_keys(
        self,
        within_days: int = 30,
    ) -> dict[str, Any]:
        """Suresi dolacak anahtarlari getirir.

        Args:
            within_days: Gun siniri.

        Returns:
            Anahtar listesi.
        """
        try:
            expiring: list[dict] = []
            for key in self._keys.values():
                if key["status"] != "active":
                    continue
                ed = key["expires_days"]
                if ed <= within_days:
                    expiring.append({
                        "key_id": key[
                            "key_id"
                        ],
                        "name": key["name"],
                        "expires_days": ed,
                        "owner": key["owner"],
                    })

            return {
                "expiring_keys": expiring,
                "count": len(expiring),
                "within_days": within_days,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_type: dict[str, int] = {}
            by_status: dict[str, int] = {}
            for key in self._keys.values():
                t = key["key_type"]
                s = key["status"]
                by_type[t] = (
                    by_type.get(t, 0) + 1
                )
                by_status[s] = (
                    by_status.get(s, 0) + 1
                )

            return {
                "total_keys": len(
                    self._keys
                ),
                "active_keys": (
                    self.key_count
                ),
                "by_type": by_type,
                "by_status": by_status,
                "total_owners": len(
                    self._owners
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
