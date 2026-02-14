"""ATLAS Projeksiyon Yoneticisi modulu.

Okuma modeli insa, gercek zamanli
guncelleme, yeniden insa, tutarlilik
kontrolu ve coklu projeksiyon.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ProjectionManager:
    """Projeksiyon yoneticisi.

    Okuma modellerini yonetir.

    Attributes:
        _projections: Projeksiyon tanimlari.
        _read_models: Okuma modelleri.
    """

    def __init__(self) -> None:
        """Projeksiyon yoneticisini baslatir."""
        self._projections: dict[
            str, dict[str, Any]
        ] = {}
        self._read_models: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._rebuild_log: list[
            dict[str, Any]
        ] = []

        logger.info(
            "ProjectionManager baslatildi",
        )

    def register_projection(
        self,
        name: str,
        handler: Callable[..., Any],
        event_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Projeksiyon kaydeder.

        Args:
            name: Projeksiyon adi.
            handler: Projeksiyon isleyicisi.
            event_types: Dinlenecek olaylar.

        Returns:
            Kayit bilgisi.
        """
        projection = {
            "name": name,
            "handler": handler,
            "event_types": event_types or [],
            "status": "active",
            "events_processed": 0,
            "last_updated": time.time(),
        }
        self._projections[name] = projection
        self._read_models[name] = []
        return {
            "name": name,
            "status": "active",
        }

    def project_event(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Olagi projeksiyonlara uygular.

        Args:
            event_type: Olay tipi.
            data: Olay verisi.

        Returns:
            Uygulama sonucu.
        """
        applied = 0
        skipped = 0

        for name, proj in self._projections.items():
            if proj["status"] != "active":
                skipped += 1
                continue

            event_types = proj["event_types"]
            if (
                event_types
                and event_type not in event_types
            ):
                skipped += 1
                continue

            try:
                result = proj["handler"](
                    event_type, data or {},
                )
                if result is not None:
                    self._read_models[name].append(
                        {
                            "event_type": event_type,
                            "data": result,
                            "timestamp": time.time(),
                        }
                    )
                proj["events_processed"] += 1
                proj["last_updated"] = time.time()
                applied += 1
            except Exception as e:
                proj["status"] = "error"
                logger.warning(
                    "Projeksiyon hatasi %s: %s",
                    name, e,
                )

        return {
            "event_type": event_type,
            "applied": applied,
            "skipped": skipped,
        }

    def rebuild(
        self,
        name: str,
        events: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """Projeksiyonu yeniden insa eder.

        Args:
            name: Projeksiyon adi.
            events: Olay listesi.
            batch_size: Toplu boyutu.

        Returns:
            Yeniden insa sonucu.
        """
        proj = self._projections.get(name)
        if not proj:
            return {
                "name": name,
                "status": "not_found",
            }

        proj["status"] = "rebuilding"
        self._read_models[name] = []
        proj["events_processed"] = 0

        processed = 0
        errors = 0

        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            for event in batch:
                try:
                    result = proj["handler"](
                        event.get(
                            "event_type", "",
                        ),
                        event.get("data", {}),
                    )
                    if result is not None:
                        self._read_models[
                            name
                        ].append({
                            "event_type": event.get(
                                "event_type", "",
                            ),
                            "data": result,
                            "timestamp": time.time(),
                        })
                    processed += 1
                except Exception:
                    errors += 1

        proj["events_processed"] = processed
        proj["status"] = "active"
        proj["last_updated"] = time.time()

        rebuild_record = {
            "name": name,
            "status": "completed",
            "processed": processed,
            "errors": errors,
            "timestamp": time.time(),
        }
        self._rebuild_log.append(rebuild_record)
        return rebuild_record

    def check_consistency(
        self,
        name: str,
        expected_count: int,
    ) -> dict[str, Any]:
        """Tutarlilik kontrol eder.

        Args:
            name: Projeksiyon adi.
            expected_count: Beklenen sayi.

        Returns:
            Kontrol sonucu.
        """
        proj = self._projections.get(name)
        if not proj:
            return {
                "name": name,
                "consistent": False,
                "reason": "not_found",
            }

        actual = proj["events_processed"]
        consistent = actual == expected_count

        return {
            "name": name,
            "consistent": consistent,
            "expected": expected_count,
            "actual": actual,
            "drift": abs(
                expected_count - actual,
            ),
        }

    def get_read_model(
        self,
        name: str,
    ) -> list[dict[str, Any]]:
        """Okuma modelini getirir.

        Args:
            name: Projeksiyon adi.

        Returns:
            Okuma modeli kayitlari.
        """
        return list(
            self._read_models.get(name, []),
        )

    def pause_projection(
        self,
        name: str,
    ) -> bool:
        """Projeksiyonu duraklatir.

        Args:
            name: Projeksiyon adi.

        Returns:
            Basarili mi.
        """
        proj = self._projections.get(name)
        if proj and proj["status"] == "active":
            proj["status"] = "paused"
            return True
        return False

    def resume_projection(
        self,
        name: str,
    ) -> bool:
        """Projeksiyonu devam ettirir.

        Args:
            name: Projeksiyon adi.

        Returns:
            Basarili mi.
        """
        proj = self._projections.get(name)
        if proj and proj["status"] in (
            "paused", "error",
        ):
            proj["status"] = "active"
            return True
        return False

    def get_projection_status(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Projeksiyon durumunu getirir.

        Args:
            name: Projeksiyon adi.

        Returns:
            Durum bilgisi veya None.
        """
        proj = self._projections.get(name)
        if not proj:
            return None
        return {
            "name": proj["name"],
            "status": proj["status"],
            "events_processed": proj[
                "events_processed"
            ],
            "last_updated": proj["last_updated"],
        }

    @property
    def projection_count(self) -> int:
        """Projeksiyon sayisi."""
        return len(self._projections)

    @property
    def active_count(self) -> int:
        """Aktif projeksiyon sayisi."""
        return sum(
            1 for p in self._projections.values()
            if p["status"] == "active"
        )

    @property
    def rebuild_count(self) -> int:
        """Yeniden insa sayisi."""
        return len(self._rebuild_log)
