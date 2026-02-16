"""ATLAS Nesne Tespitçisi modülü.

Nesne tespiti, sınıflandırma,
sınırlayıcı kutular, sayım,
takip.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ObjectDetector:
    """Nesne tespitçisi.

    Görüntülerde nesne tespiti yapar.

    Attributes:
        _detections: Tespit kayıtları.
        _tracked: Takip edilen nesneler.
    """

    def __init__(self) -> None:
        """Tespitçiyi başlatır."""
        self._detections: list[
            dict[str, Any]
        ] = []
        self._tracked: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "detections_done": 0,
            "objects_tracked": 0,
        }

        logger.info(
            "ObjectDetector baslatildi",
        )

    def detect_objects(
        self,
        image_id: str,
        confidence_threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Nesne tespiti yapar.

        Args:
            image_id: Görüntü kimliği.
            confidence_threshold: Güven eşiği.

        Returns:
            Tespit bilgisi.
        """
        objects = [
            {
                "label": "person",
                "confidence": 0.95,
                "bbox": {
                    "x": 100, "y": 50,
                    "w": 200, "h": 400,
                },
            },
            {
                "label": "car",
                "confidence": 0.88,
                "bbox": {
                    "x": 400, "y": 200,
                    "w": 300, "h": 150,
                },
            },
            {
                "label": "dog",
                "confidence": 0.42,
                "bbox": {
                    "x": 50, "y": 300,
                    "w": 100, "h": 80,
                },
            },
        ]

        filtered = [
            o
            for o in objects
            if o["confidence"]
            >= confidence_threshold
        ]

        for obj in filtered:
            self._detections.append({
                "image_id": image_id,
                **obj,
                "timestamp": time.time(),
            })

        self._stats[
            "detections_done"
        ] += 1

        return {
            "image_id": image_id,
            "objects_found": len(
                filtered,
            ),
            "objects": filtered,
            "threshold": (
                confidence_threshold
            ),
            "detected": True,
        }

    def classify(
        self,
        image_id: str,
        categories: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Sınıflandırma yapar.

        Args:
            image_id: Görüntü kimliği.
            categories: Kategori listesi.

        Returns:
            Sınıflandırma bilgisi.
        """
        categories = categories or [
            "vehicle",
            "person",
            "animal",
            "object",
        ]

        scores = []
        for i, cat in enumerate(
            categories
        ):
            score = round(
                0.9 - i * 0.15, 2,
            )
            scores.append({
                "category": cat,
                "score": max(score, 0.1),
            })

        top = max(
            scores,
            key=lambda s: s["score"],
        )

        return {
            "image_id": image_id,
            "top_category": top[
                "category"
            ],
            "top_score": top["score"],
            "all_scores": scores,
            "classified": True,
        }

    def get_bounding_boxes(
        self,
        image_id: str,
    ) -> dict[str, Any]:
        """Sınırlayıcı kutuları döndürür.

        Args:
            image_id: Görüntü kimliği.

        Returns:
            Kutu bilgisi.
        """
        boxes = [
            {
                "label": d["label"],
                "bbox": d["bbox"],
                "confidence": d[
                    "confidence"
                ],
            }
            for d in self._detections
            if d["image_id"] == image_id
        ]

        return {
            "image_id": image_id,
            "boxes": len(boxes),
            "data": boxes,
            "retrieved": True,
        }

    def count_objects(
        self,
        image_id: str,
        label: str = "",
    ) -> dict[str, Any]:
        """Nesne sayar.

        Args:
            image_id: Görüntü kimliği.
            label: Etiket filtresi.

        Returns:
            Sayım bilgisi.
        """
        matching = [
            d
            for d in self._detections
            if d["image_id"] == image_id
            and (
                not label
                or d["label"] == label
            )
        ]

        return {
            "image_id": image_id,
            "label": label or "all",
            "count": len(matching),
            "counted": True,
        }

    def track_object(
        self,
        object_id: str,
        image_id: str,
        bbox: dict[str, int]
        | None = None,
    ) -> dict[str, Any]:
        """Nesne takibi yapar.

        Args:
            object_id: Nesne kimliği.
            image_id: Görüntü kimliği.
            bbox: Sınırlayıcı kutu.

        Returns:
            Takip bilgisi.
        """
        bbox = bbox or {}
        is_new = (
            object_id
            not in self._tracked
        )

        self._tracked[object_id] = {
            "object_id": object_id,
            "last_image": image_id,
            "bbox": bbox,
            "updated_at": time.time(),
        }

        if is_new:
            self._stats[
                "objects_tracked"
            ] += 1

        return {
            "object_id": object_id,
            "image_id": image_id,
            "tracked": True,
        }

    @property
    def detection_count(self) -> int:
        """Tespit sayısı."""
        return self._stats[
            "detections_done"
        ]

    @property
    def tracked_count(self) -> int:
        """Takip edilen nesne sayısı."""
        return self._stats[
            "objects_tracked"
        ]
