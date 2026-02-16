"""ATLAS Görsel Zeka Orkestratörü.

Tam görsel zeka yönetim pipeline,
Capture → Analyze → Detect → Extract,
çoklu kamera desteği, analitik.
"""

import logging
from typing import Any

from app.core.visualintel.document_scanner import (
    DocumentScanner,
)
from app.core.visualintel.image_analyzer import (
    ImageAnalyzer,
)
from app.core.visualintel.object_detector import (
    ObjectDetector,
)
from app.core.visualintel.ocr_engine import (
    OCREngine,
)
from app.core.visualintel.scene_classifier import (
    SceneClassifier,
)
from app.core.visualintel.video_stream_processor import (
    VideoStreamProcessor,
)
from app.core.visualintel.visual_anomaly_detector import (
    VisualAnomalyDetector,
)
from app.core.visualintel.visual_search import (
    VisualSearch,
)

logger = logging.getLogger(__name__)


class VisualIntelOrchestrator:
    """Görsel zeka orkestratörü.

    Tüm görsel zeka bileşenlerini koordine eder.

    Attributes:
        analyzer: Görüntü analizcisi.
        ocr: OCR motoru.
        detector: Nesne tespitçisi.
        classifier: Sahne sınıflandırıcı.
        anomaly: Anomali tespitçisi.
        scanner: Doküman tarayıcı.
        video: Video işleyici.
        search: Görsel arama.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.analyzer = ImageAnalyzer()
        self.ocr = OCREngine()
        self.detector = ObjectDetector()
        self.classifier = (
            SceneClassifier()
        )
        self.anomaly = (
            VisualAnomalyDetector()
        )
        self.scanner = DocumentScanner()
        self.video = (
            VideoStreamProcessor()
        )
        self.search = VisualSearch()
        self._stats = {
            "pipelines_run": 0,
            "cameras_active": 0,
        }

        logger.info(
            "VisualIntelOrchestrator "
            "baslatildi",
        )

    def analyze_image(
        self,
        image_id: str,
        width: int = 1920,
        height: int = 1080,
        extract_text: bool = False,
        detect_objects: bool = True,
    ) -> dict[str, Any]:
        """Capture → Analyze → Detect → Extract pipeline.

        Args:
            image_id: Görüntü kimliği.
            width: Genişlik.
            height: Yükseklik.
            extract_text: Metin çıkar.
            detect_objects: Nesne tespit et.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Analyze
        analysis = (
            self.analyzer.process_image(
                image_id=image_id,
                width=width,
                height=height,
            )
        )

        # 2. Classify scene
        scene = (
            self.classifier.recognize_scene(
                image_id=image_id,
            )
        )

        # 3. Detect objects
        objects = {}
        if detect_objects:
            objects = (
                self.detector.detect_objects(
                    image_id=image_id,
                )
            )

        # 4. Extract text
        text = {}
        if extract_text:
            text = self.ocr.extract_text(
                image_id=image_id,
            )

        # 5. Index for search
        self.search.index_image(
            image_id=image_id,
        )

        self._stats[
            "pipelines_run"
        ] += 1

        return {
            "image_id": image_id,
            "scene": scene.get(
                "scene", "",
            ),
            "objects_found": objects.get(
                "objects_found", 0,
            ),
            "text_extracted": bool(text),
            "indexed": True,
            "pipeline_complete": True,
        }

    def setup_camera(
        self,
        stream_url: str,
        camera_id: str = "",
    ) -> dict[str, Any]:
        """Kamera kurulumu yapar.

        Args:
            stream_url: Akış URL'si.
            camera_id: Kamera kimliği.

        Returns:
            Kurulum bilgisi.
        """
        stream = (
            self.video.handle_stream(
                stream_url=stream_url,
                camera_id=camera_id,
            )
        )

        self._stats[
            "cameras_active"
        ] += 1

        return {
            "camera_id": camera_id,
            "stream_id": stream[
                "stream_id"
            ],
            "status": "active",
            "setup": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": (
                self._stats[
                    "pipelines_run"
                ]
            ),
            "cameras_active": (
                self._stats[
                    "cameras_active"
                ]
            ),
            "images_analyzed": (
                self.analyzer
                .analysis_count
            ),
            "texts_extracted": (
                self.ocr
                .extraction_count
            ),
            "objects_detected": (
                self.detector
                .detection_count
            ),
            "scenes_classified": (
                self.classifier
                .classification_count
            ),
            "anomalies_found": (
                self.anomaly
                .anomaly_count
            ),
            "documents_scanned": (
                self.scanner.scan_count
            ),
            "streams_handled": (
                self.video.stream_count
            ),
            "images_indexed": (
                self.search.index_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def camera_count(self) -> int:
        """Aktif kamera sayısı."""
        return self._stats[
            "cameras_active"
        ]
