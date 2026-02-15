"""ATLAS Konfigurasyon Deposu modulu.

Anahtar-deger depolama, hiyerarsik
konfigurasyon, namespace destegi,
surum gecmisi ve sifreleme.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConfigStore:
    """Konfigurasyon deposu.

    Konfigurasyon degerlerini depolar.

    Attributes:
        _store: Anahtar-deger deposu.
        _history: Surum gecmisi.
    """

    def __init__(self) -> None:
        """Konfigurasyon deposunu baslatir."""
        self._store: dict[
            str, dict[str, Any]
        ] = {}
        self._history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._namespaces: dict[
            str, set[str]
        ] = {}
        self._encrypted_keys: set[str] = set()

        logger.info("ConfigStore baslatildi")

    def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        encrypt: bool = False,
    ) -> dict[str, Any]:
        """Deger ayarlar.

        Args:
            key: Anahtar.
            value: Deger.
            namespace: Ad alani.
            encrypt: Sifrele.

        Returns:
            Kayit bilgisi.
        """
        full_key = f"{namespace}.{key}"
        existing = self._store.get(full_key)
        version = (
            existing["version"] + 1
            if existing else 1
        )

        # Gecmisi kaydet
        if existing:
            if full_key not in self._history:
                self._history[full_key] = []
            self._history[full_key].append(
                dict(existing),
            )

        stored_value = value
        if encrypt:
            stored_value = self._encrypt(value)
            self._encrypted_keys.add(full_key)

        entry = {
            "key": key,
            "full_key": full_key,
            "value": stored_value,
            "namespace": namespace,
            "version": version,
            "encrypted": encrypt,
            "updated_at": time.time(),
        }
        self._store[full_key] = entry

        # Namespace takibi
        if namespace not in self._namespaces:
            self._namespaces[namespace] = set()
        self._namespaces[namespace].add(full_key)

        return {
            "key": full_key,
            "version": version,
        }

    def get(
        self,
        key: str,
        namespace: str = "default",
        default: Any = None,
    ) -> Any:
        """Deger getirir.

        Args:
            key: Anahtar.
            namespace: Ad alani.
            default: Varsayilan deger.

        Returns:
            Deger.
        """
        full_key = f"{namespace}.{key}"
        entry = self._store.get(full_key)
        if not entry:
            return default

        value = entry["value"]
        if entry.get("encrypted"):
            value = self._decrypt(value)

        return value

    def delete(
        self,
        key: str,
        namespace: str = "default",
    ) -> bool:
        """Deger siler.

        Args:
            key: Anahtar.
            namespace: Ad alani.

        Returns:
            Basarili mi.
        """
        full_key = f"{namespace}.{key}"
        if full_key in self._store:
            # Gecmise ekle
            if full_key not in self._history:
                self._history[full_key] = []
            self._history[full_key].append(
                dict(self._store[full_key]),
            )
            del self._store[full_key]
            self._encrypted_keys.discard(full_key)
            ns_keys = self._namespaces.get(
                namespace, set(),
            )
            ns_keys.discard(full_key)
            return True
        return False

    def get_namespace(
        self,
        namespace: str,
    ) -> dict[str, Any]:
        """Namespace altindaki tum degerleri getirir.

        Args:
            namespace: Ad alani.

        Returns:
            Anahtar-deger eslesmesi.
        """
        keys = self._namespaces.get(
            namespace, set(),
        )
        result = {}
        for full_key in keys:
            entry = self._store.get(full_key)
            if entry:
                result[entry["key"]] = entry["value"]
        return result

    def get_history(
        self,
        key: str,
        namespace: str = "default",
    ) -> list[dict[str, Any]]:
        """Surum gecmisini getirir.

        Args:
            key: Anahtar.
            namespace: Ad alani.

        Returns:
            Gecmis listesi.
        """
        full_key = f"{namespace}.{key}"
        return list(
            self._history.get(full_key, []),
        )

    def get_version(
        self,
        key: str,
        namespace: str = "default",
    ) -> int:
        """Surum numarasini getirir.

        Args:
            key: Anahtar.
            namespace: Ad alani.

        Returns:
            Surum numarasi.
        """
        full_key = f"{namespace}.{key}"
        entry = self._store.get(full_key)
        return entry["version"] if entry else 0

    def set_hierarchical(
        self,
        path: str,
        value: Any,
        namespace: str = "default",
    ) -> dict[str, Any]:
        """Hiyerarsik deger ayarlar.

        Args:
            path: Hiyerarsik yol (a.b.c).
            value: Deger.
            namespace: Ad alani.

        Returns:
            Kayit bilgisi.
        """
        return self.set(path, value, namespace)

    def get_hierarchical(
        self,
        path: str,
        namespace: str = "default",
    ) -> Any:
        """Hiyerarsik deger getirir.

        Args:
            path: Hiyerarsik yol.
            namespace: Ad alani.

        Returns:
            Deger.
        """
        # Tam eslesme
        val = self.get(path, namespace)
        if val is not None:
            return val

        # Alt anahtarlar
        prefix = f"{namespace}.{path}."
        children = {}
        for fk, entry in self._store.items():
            if fk.startswith(prefix):
                suffix = fk[len(prefix):]
                children[suffix] = entry["value"]

        return children if children else None

    def _encrypt(self, value: Any) -> str:
        """Basit sifreleme (hash).

        Args:
            value: Deger.

        Returns:
            Sifreli deger.
        """
        raw = str(value)
        return f"enc:{hashlib.sha256(raw.encode()).hexdigest()[:16]}:{raw}"

    def _decrypt(self, value: Any) -> Any:
        """Basit sifre cozme.

        Args:
            value: Sifreli deger.

        Returns:
            Orijinal deger.
        """
        if isinstance(value, str) and value.startswith("enc:"):
            parts = value.split(":", 2)
            if len(parts) == 3:
                return parts[2]
        return value

    def list_namespaces(self) -> list[str]:
        """Namespace listesi getirir.

        Returns:
            Namespace listesi.
        """
        return list(self._namespaces.keys())

    @property
    def config_count(self) -> int:
        """Konfigurasyon sayisi."""
        return len(self._store)

    @property
    def namespace_count(self) -> int:
        """Namespace sayisi."""
        return len(self._namespaces)

    @property
    def encrypted_count(self) -> int:
        """Sifreli anahtar sayisi."""
        return len(self._encrypted_keys)
