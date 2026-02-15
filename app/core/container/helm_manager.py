"""ATLAS Helm Yoneticisi modulu.

Chart yonetimi, release takibi,
deger gecersiz kilmalari, bagimlil
ik yonetimi ve yukseltme/geri alma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class HelmManager:
    """Helm yoneticisi.

    Helm chart'lari ve release'leri yonetir.

    Attributes:
        _charts: Kayitli chart'lar.
        _releases: Aktif release'ler.
    """

    def __init__(self) -> None:
        """Yoneticiyi baslatir."""
        self._charts: dict[
            str, dict[str, Any]
        ] = {}
        self._releases: dict[
            str, dict[str, Any]
        ] = {}
        self._repos: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "installs": 0,
            "upgrades": 0,
            "rollbacks": 0,
            "uninstalls": 0,
        }

        logger.info(
            "HelmManager baslatildi",
        )

    def add_repo(
        self,
        name: str,
        url: str,
    ) -> dict[str, Any]:
        """Chart deposu ekler.

        Args:
            name: Depo adi.
            url: Depo URL.

        Returns:
            Depo bilgisi.
        """
        self._repos[name] = {
            "name": name,
            "url": url,
            "added_at": time.time(),
        }

        return {"name": name, "url": url}

    def register_chart(
        self,
        name: str,
        version: str = "0.1.0",
        app_version: str = "1.0.0",
        description: str = "",
        dependencies: list[str] | None = None,
        values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Chart kaydeder.

        Args:
            name: Chart adi.
            version: Chart surumu.
            app_version: Uygulama surumu.
            description: Aciklama.
            dependencies: Bagimliliklar.
            values: Varsayilan degerler.

        Returns:
            Chart bilgisi.
        """
        self._charts[name] = {
            "name": name,
            "version": version,
            "app_version": app_version,
            "description": description,
            "dependencies": dependencies or [],
            "values": values or {},
            "registered_at": time.time(),
        }

        return {
            "name": name,
            "version": version,
        }

    def get_chart(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Chart bilgisini getirir.

        Args:
            name: Chart adi.

        Returns:
            Chart bilgisi veya None.
        """
        return self._charts.get(name)

    def install(
        self,
        release_name: str,
        chart_name: str,
        namespace: str = "default",
        values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Chart yukler (install).

        Args:
            release_name: Release adi.
            chart_name: Chart adi.
            namespace: Isim alani.
            values: Deger gecersiz kilmalari.

        Returns:
            Release bilgisi.
        """
        chart = self._charts.get(chart_name)
        merged_values = {}
        if chart:
            merged_values.update(
                chart.get("values", {}),
            )
        if values:
            merged_values.update(values)

        self._releases[release_name] = {
            "name": release_name,
            "chart": chart_name,
            "namespace": namespace,
            "version": chart["version"] if chart else "0.0.0",
            "revision": 1,
            "status": "deployed",
            "values": merged_values,
            "history": [{
                "revision": 1,
                "status": "deployed",
                "values": dict(merged_values),
                "timestamp": time.time(),
            }],
            "installed_at": time.time(),
            "updated_at": time.time(),
        }

        self._stats["installs"] += 1

        return {
            "release": release_name,
            "chart": chart_name,
            "status": "deployed",
            "revision": 1,
        }

    def upgrade(
        self,
        release_name: str,
        values: dict[str, Any] | None = None,
        chart_version: str | None = None,
    ) -> dict[str, Any]:
        """Release yukseltir.

        Args:
            release_name: Release adi.
            values: Yeni degerler.
            chart_version: Yeni chart surumu.

        Returns:
            Yukseltme bilgisi.
        """
        rel = self._releases.get(release_name)
        if not rel:
            return {"error": "not_found"}

        rel["revision"] += 1
        if values:
            rel["values"].update(values)
        if chart_version:
            rel["version"] = chart_version

        rel["status"] = "deployed"
        rel["updated_at"] = time.time()

        rel["history"].append({
            "revision": rel["revision"],
            "status": "deployed",
            "values": dict(rel["values"]),
            "timestamp": time.time(),
        })

        self._stats["upgrades"] += 1

        return {
            "release": release_name,
            "revision": rel["revision"],
            "status": "deployed",
        }

    def rollback(
        self,
        release_name: str,
        to_revision: int | None = None,
    ) -> dict[str, Any]:
        """Release geri alir.

        Args:
            release_name: Release adi.
            to_revision: Hedef revizyon.

        Returns:
            Geri alma bilgisi.
        """
        rel = self._releases.get(release_name)
        if not rel:
            return {"error": "not_found"}

        history = rel["history"]

        if to_revision is not None:
            target = None
            for h in history:
                if h["revision"] == to_revision:
                    target = h
                    break
            if not target:
                return {"error": "revision_not_found"}
        else:
            if len(history) < 2:
                return {"error": "no_previous"}
            target = history[-2]

        rel["revision"] += 1
        rel["values"] = dict(target["values"])
        rel["status"] = "deployed"
        rel["updated_at"] = time.time()

        rel["history"].append({
            "revision": rel["revision"],
            "status": "deployed",
            "values": dict(target["values"]),
            "rollback_from": rel["revision"] - 1,
            "timestamp": time.time(),
        })

        self._stats["rollbacks"] += 1

        return {
            "release": release_name,
            "rolled_back_to": target["revision"],
            "new_revision": rel["revision"],
        }

    def uninstall(
        self,
        release_name: str,
    ) -> bool:
        """Release kaldirir.

        Args:
            release_name: Release adi.

        Returns:
            Basarili mi.
        """
        if release_name not in self._releases:
            return False

        del self._releases[release_name]
        self._stats["uninstalls"] += 1
        return True

    def get_release(
        self,
        release_name: str,
    ) -> dict[str, Any] | None:
        """Release bilgisini getirir.

        Args:
            release_name: Release adi.

        Returns:
            Release bilgisi veya None.
        """
        return self._releases.get(release_name)

    def get_release_history(
        self,
        release_name: str,
    ) -> list[dict[str, Any]]:
        """Release gecmisini getirir.

        Args:
            release_name: Release adi.

        Returns:
            Gecmis listesi.
        """
        rel = self._releases.get(release_name)
        if not rel:
            return []
        return list(rel["history"])

    def get_values(
        self,
        release_name: str,
    ) -> dict[str, Any]:
        """Release degerlerini getirir.

        Args:
            release_name: Release adi.

        Returns:
            Degerler.
        """
        rel = self._releases.get(release_name)
        if not rel:
            return {}
        return dict(rel["values"])

    def list_releases(
        self,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Release'leri listeler.

        Args:
            namespace: Isim alani filtresi.

        Returns:
            Release listesi.
        """
        rels = list(self._releases.values())
        if namespace:
            rels = [
                r for r in rels
                if r["namespace"] == namespace
            ]
        return rels

    @property
    def chart_count(self) -> int:
        """Chart sayisi."""
        return len(self._charts)

    @property
    def release_count(self) -> int:
        """Release sayisi."""
        return len(self._releases)

    @property
    def repo_count(self) -> int:
        """Depo sayisi."""
        return len(self._repos)

    @property
    def install_count(self) -> int:
        """Yukleme sayisi."""
        return self._stats["installs"]

    @property
    def upgrade_count(self) -> int:
        """Yukseltme sayisi."""
        return self._stats["upgrades"]
