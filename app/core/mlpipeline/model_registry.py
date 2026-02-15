"""ATLAS Model Kayit Defteri modulu.

Model versiyonlama, metadata depolama,
model karsilastirma, soy takibi
ve dagitim durumu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Model kayit defteri.

    Modelleri kaydeder ve yonetir.

    Attributes:
        _models: Kayitli modeller.
        _lineage: Soy bilgisi.
    """

    def __init__(self) -> None:
        """Kayit defterini baslatir."""
        self._models: dict[
            str, dict[str, Any]
        ] = {}
        self._versions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._lineage: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._tags: dict[
            str, dict[str, str]
        ] = {}

        logger.info(
            "ModelRegistry baslatildi",
        )

    def register(
        self,
        name: str,
        version: str,
        metrics: dict[str, float]
            | None = None,
        metadata: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Model kaydeder.

        Args:
            name: Model adi.
            version: Versiyon.
            metrics: Metrikler.
            metadata: Ek bilgi.

        Returns:
            Kayit bilgisi.
        """
        model_key = f"{name}:{version}"

        record = {
            "name": name,
            "version": version,
            "metrics": metrics or {},
            "metadata": metadata or {},
            "status": "registered",
            "registered_at": time.time(),
            "updated_at": time.time(),
        }

        self._models[model_key] = record

        # Versiyon gecmisi
        if name not in self._versions:
            self._versions[name] = []
        self._versions[name].append({
            "version": version,
            "registered_at": time.time(),
        })

        # Soy takibi
        if name not in self._lineage:
            self._lineage[name] = []
        self._lineage[name].append({
            "action": "register",
            "version": version,
            "timestamp": time.time(),
        })

        return {
            "key": model_key,
            "name": name,
            "version": version,
        }

    def get_model(
        self,
        name: str,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        """Model getirir.

        Args:
            name: Model adi.
            version: Versiyon (None=son).

        Returns:
            Model bilgisi veya None.
        """
        if version:
            return self._models.get(
                f"{name}:{version}",
            )

        # Son versiyon
        versions = self._versions.get(name, [])
        if not versions:
            return None
        latest = versions[-1]["version"]
        return self._models.get(
            f"{name}:{latest}",
        )

    def update_status(
        self,
        name: str,
        version: str,
        status: str,
    ) -> dict[str, Any]:
        """Model durumunu gunceller.

        Args:
            name: Model adi.
            version: Versiyon.
            status: Yeni durum.

        Returns:
            Guncelleme sonucu.
        """
        key = f"{name}:{version}"
        model = self._models.get(key)
        if not model:
            return {"error": "not_found"}

        old_status = model["status"]
        model["status"] = status
        model["updated_at"] = time.time()

        self._lineage[name].append({
            "action": "status_change",
            "version": version,
            "from": old_status,
            "to": status,
            "timestamp": time.time(),
        })

        return {
            "key": key,
            "status": status,
            "previous": old_status,
        }

    def update_metrics(
        self,
        name: str,
        version: str,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Model metriklerini gunceller.

        Args:
            name: Model adi.
            version: Versiyon.
            metrics: Yeni metrikler.

        Returns:
            Guncelleme sonucu.
        """
        key = f"{name}:{version}"
        model = self._models.get(key)
        if not model:
            return {"error": "not_found"}

        model["metrics"].update(metrics)
        model["updated_at"] = time.time()

        return {
            "key": key,
            "metrics": model["metrics"],
        }

    def compare(
        self,
        name: str,
        version_a: str,
        version_b: str,
    ) -> dict[str, Any]:
        """Iki versiyonu karsilastirir.

        Args:
            name: Model adi.
            version_a: Birinci versiyon.
            version_b: Ikinci versiyon.

        Returns:
            Karsilastirma sonucu.
        """
        model_a = self.get_model(name, version_a)
        model_b = self.get_model(name, version_b)

        if not model_a or not model_b:
            return {"error": "not_found"}

        metrics_a = model_a.get("metrics", {})
        metrics_b = model_b.get("metrics", {})

        all_metrics = set(metrics_a) | set(metrics_b)
        comparison: dict[str, dict[str, Any]] = {}

        for m in all_metrics:
            va = metrics_a.get(m, 0.0)
            vb = metrics_b.get(m, 0.0)
            diff = vb - va
            comparison[m] = {
                version_a: va,
                version_b: vb,
                "diff": diff,
                "improved": diff > 0,
            }

        return {
            "name": name,
            "versions": [version_a, version_b],
            "comparison": comparison,
        }

    def get_lineage(
        self,
        name: str,
    ) -> list[dict[str, Any]]:
        """Soy bilgisini getirir.

        Args:
            name: Model adi.

        Returns:
            Soy kayitlari.
        """
        return list(
            self._lineage.get(name, []),
        )

    def get_versions(
        self,
        name: str,
    ) -> list[dict[str, Any]]:
        """Versiyonlari getirir.

        Args:
            name: Model adi.

        Returns:
            Versiyon listesi.
        """
        return list(
            self._versions.get(name, []),
        )

    def tag_model(
        self,
        name: str,
        version: str,
        tag: str,
    ) -> dict[str, Any]:
        """Modeli etiketler.

        Args:
            name: Model adi.
            version: Versiyon.
            tag: Etiket.

        Returns:
            Etiket bilgisi.
        """
        key = f"{name}:{version}"
        if key not in self._models:
            return {"error": "not_found"}

        if name not in self._tags:
            self._tags[name] = {}
        self._tags[name][tag] = version

        return {
            "name": name,
            "version": version,
            "tag": tag,
        }

    def get_by_tag(
        self,
        name: str,
        tag: str,
    ) -> dict[str, Any] | None:
        """Etikete gore model getirir.

        Args:
            name: Model adi.
            tag: Etiket.

        Returns:
            Model bilgisi veya None.
        """
        tags = self._tags.get(name, {})
        version = tags.get(tag)
        if not version:
            return None
        return self.get_model(name, version)

    def list_models(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Modelleri listeler.

        Args:
            status: Durum filtresi.

        Returns:
            Model listesi.
        """
        models = list(self._models.values())
        if status:
            models = [
                m for m in models
                if m["status"] == status
            ]
        return models

    def delete_model(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Modeli siler.

        Args:
            name: Model adi.
            version: Versiyon.

        Returns:
            Basarili mi.
        """
        key = f"{name}:{version}"
        if key in self._models:
            del self._models[key]
            return True
        return False

    @property
    def model_count(self) -> int:
        """Model sayisi."""
        return len(self._models)

    @property
    def deployed_count(self) -> int:
        """Dagitilmis model sayisi."""
        return sum(
            1 for m in self._models.values()
            if m["status"] == "deployed"
        )

    @property
    def version_count(self) -> int:
        """Toplam versiyon sayisi."""
        return sum(
            len(v)
            for v in self._versions.values()
        )
