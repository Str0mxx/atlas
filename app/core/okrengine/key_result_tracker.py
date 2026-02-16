"""ATLAS Anahtar Sonuç Takipçisi.

Anahtar sonuç tanımlama, metrik takibi,
ilerleme hesaplama, hedef yönetimi, güven skoru.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class KeyResultTracker:
    """Anahtar sonuç takipçisi.

    OKR anahtar sonuçlarını takip eder,
    metrikleri izler ve ilerleme hesaplar.

    Attributes:
        _key_results: Anahtar sonuç kayıtları.
        _checkins: Check-in kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._key_results: dict[
            str, dict
        ] = {}
        self._checkins: list[dict] = []
        self._stats = {
            "krs_created": 0,
        }
        logger.info(
            "KeyResultTracker baslatildi",
        )

    @property
    def kr_count(self) -> int:
        """Anahtar sonuç sayısı."""
        return self._stats["krs_created"]

    def define_kr(
        self,
        objective_id: str,
        description: str = "",
        target_value: float = 100.0,
        unit: str = "percent",
    ) -> dict[str, Any]:
        """Anahtar sonuç tanımlar.

        Args:
            objective_id: Hedef ID.
            description: Açıklama.
            target_value: Hedef değer.
            unit: Birim.

        Returns:
            Anahtar sonuç bilgisi.
        """
        kr_id = f"kr_{str(uuid4())[:8]}"

        self._key_results[kr_id] = {
            "objective_id": objective_id,
            "description": description,
            "target_value": target_value,
            "current_value": 0.0,
            "unit": unit,
            "confidence": 0.5,
        }

        self._stats["krs_created"] += 1

        logger.info(
            f"Anahtar sonuc tanimlandi: {kr_id}",
        )

        return {
            "kr_id": kr_id,
            "objective_id": objective_id,
            "description": description,
            "target_value": target_value,
            "unit": unit,
            "defined": True,
        }

    def track_metric(
        self,
        kr_id: str,
        value: float = 0.0,
        note: str = "",
    ) -> dict[str, Any]:
        """Metrik takip eder.

        Args:
            kr_id: Anahtar sonuç ID.
            value: Değer.
            note: Not.

        Returns:
            Takip bilgisi.
        """
        if kr_id in self._key_results:
            self._key_results[kr_id][
                "current_value"
            ] = value

        self._checkins.append(
            {
                "kr_id": kr_id,
                "value": value,
                "note": note,
            },
        )

        target = (
            self._key_results[kr_id][
                "target_value"
            ]
            if kr_id in self._key_results
            else 100.0
        )
        progress = min(
            round(
                value / max(target, 0.001) * 100,
                1,
            ),
            100.0,
        )

        logger.info(
            f"Metrik takip edildi: {kr_id} = {value}",
        )

        return {
            "kr_id": kr_id,
            "value": value,
            "progress_pct": progress,
            "note": note,
            "tracked": True,
        }

    def calculate_progress(
        self,
        kr_id: str,
    ) -> dict[str, Any]:
        """İlerleme hesaplar.

        Args:
            kr_id: Anahtar sonuç ID.

        Returns:
            İlerleme bilgisi.
        """
        if kr_id in self._key_results:
            current = self._key_results[
                kr_id
            ]["current_value"]
            target = self._key_results[
                kr_id
            ]["target_value"]
        else:
            current = 0.0
            target = 100.0

        progress_pct = round(
            current / max(target, 0.001) * 100,
            1,
        )

        if progress_pct >= 100:
            status = "completed"
        elif progress_pct >= 70:
            status = "on_track"
        elif progress_pct >= 40:
            status = "progressing"
        else:
            status = "at_risk"

        logger.info(
            f"Ilerleme hesaplandi: {kr_id} = {progress_pct}%",
        )

        return {
            "kr_id": kr_id,
            "current_value": current,
            "target_value": target,
            "progress_pct": progress_pct,
            "status": status,
            "calculated": True,
        }

    def manage_target(
        self,
        kr_id: str,
        new_target: float = 100.0,
    ) -> dict[str, Any]:
        """Hedef yönetir.

        Args:
            kr_id: Anahtar sonuç ID.
            new_target: Yeni hedef.

        Returns:
            Hedef güncelleme bilgisi.
        """
        if kr_id in self._key_results:
            old_target = self._key_results[
                kr_id
            ]["target_value"]
            self._key_results[kr_id][
                "target_value"
            ] = new_target
        else:
            old_target = 100.0

        change_pct = round(
            (new_target - old_target)
            / max(abs(old_target), 0.001)
            * 100,
            1,
        )

        logger.info(
            f"Hedef guncellendi: {kr_id} {old_target} -> {new_target}",
        )

        return {
            "kr_id": kr_id,
            "old_target": old_target,
            "new_target": new_target,
            "change_pct": change_pct,
            "updated": True,
        }

    def score_confidence(
        self,
        kr_id: str,
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Güven skoru verir.

        Args:
            kr_id: Anahtar sonuç ID.
            confidence: Güven skoru (0.0-1.0).

        Returns:
            Güven skoru bilgisi.
        """
        confidence = max(
            0.0, min(1.0, confidence),
        )

        if kr_id in self._key_results:
            self._key_results[kr_id][
                "confidence"
            ] = confidence

        if confidence >= 0.8:
            level = "high"
        elif confidence >= 0.5:
            level = "medium"
        else:
            level = "low"

        logger.info(
            f"Guven skoru verildi: {kr_id} = {confidence}",
        )

        return {
            "kr_id": kr_id,
            "confidence": confidence,
            "confidence_level": level,
            "scored": True,
        }
