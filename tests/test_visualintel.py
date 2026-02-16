"""ATLAS Camera & Visual Intelligence testleri."""

import pytest

from app.core.visualintel.image_analyzer import (
    ImageAnalyzer,
)
from app.core.visualintel.ocr_engine import (
    OCREngine,
)
from app.core.visualintel.object_detector import (
    ObjectDetector,
)
from app.core.visualintel.scene_classifier import (
    SceneClassifier,
)
from app.core.visualintel.visual_anomaly_detector import (
    VisualAnomalyDetector,
)
from app.core.visualintel.document_scanner import (
    DocumentScanner,
)
from app.core.visualintel.video_stream_processor import (
    VideoStreamProcessor,
)
from app.core.visualintel.visual_search import (
    VisualSearch,
)
from app.core.visualintel.visualintel_orchestrator import (
    VisualIntelOrchestrator,
)


# ==================== ImageAnalyzer ====================


class TestProcessImage:
    """process_image testleri."""

    def test_basic_process(self):
        ia = ImageAnalyzer()
        r = ia.process_image(
            "img1", 1920, 1080,
        )
        assert r["processed"] is True
        assert r["aspect_ratio"] == 1.78
        assert ia.analysis_count == 1

    def test_square(self):
        ia = ImageAnalyzer()
        r = ia.process_image(
            "img2", 500, 500,
        )
        assert r["aspect_ratio"] == 1.0


class TestExtractFeatures:
    """extract_features testleri."""

    def test_default_features(self):
        ia = ImageAnalyzer()
        r = ia.extract_features("img1")
        assert r["extracted"] is True
        assert r["features_count"] == 3

    def test_custom_features(self):
        ia = ImageAnalyzer()
        r = ia.extract_features(
            "img1",
            feature_types=["color", "edges"],
        )
        assert r["features_count"] == 2
        assert ia.feature_count == 2


class TestAssessQuality:
    """assess_quality testleri."""

    def test_full_hd(self):
        ia = ImageAnalyzer()
        r = ia.assess_quality(
            "img1", 1920, 1080, 500,
        )
        assert r["assessed"] is True
        assert r["resolution_grade"] == "full_hd"

    def test_low_res(self):
        ia = ImageAnalyzer()
        r = ia.assess_quality(
            "img2", 320, 240, 50,
        )
        assert r["resolution_grade"] == "low"

    def test_4k(self):
        ia = ImageAnalyzer()
        r = ia.assess_quality(
            "img3", 3840, 2160, 5000,
        )
        assert r["resolution_grade"] == "4k"


class TestExtractMetadata:
    """extract_metadata testleri."""

    def test_with_data(self):
        ia = ImageAnalyzer()
        r = ia.extract_metadata(
            "img1",
            raw_metadata={
                "camera": "Canon",
                "iso": 400,
            },
        )
        assert r["extracted"] is True
        assert r["fields_found"] >= 2

    def test_empty(self):
        ia = ImageAnalyzer()
        r = ia.extract_metadata("img1")
        assert r["extracted"] is True


class TestHandleFormat:
    """handle_format testleri."""

    def test_supported(self):
        ia = ImageAnalyzer()
        r = ia.handle_format(
            "img1", "jpeg", "png",
        )
        assert r["converted"] is True

    def test_unsupported(self):
        ia = ImageAnalyzer()
        r = ia.handle_format(
            "img1", "jpeg", "raw",
        )
        assert r["converted"] is False


# ==================== OCREngine ====================


class TestExtractText:
    """extract_text testleri."""

    def test_english(self):
        ocr = OCREngine()
        r = ocr.extract_text("img1", "en")
        assert r["extracted"] is True
        assert r["confidence"] == 0.92
        assert ocr.extraction_count == 1

    def test_turkish(self):
        ocr = OCREngine()
        r = ocr.extract_text("img1", "tr")
        assert r["confidence"] == 0.92

    def test_unsupported_lang(self):
        ocr = OCREngine()
        r = ocr.extract_text("img1", "xx")
        assert r["confidence"] == 0.0


class TestMultiLanguageOcr:
    """multi_language_ocr testleri."""

    def test_multi_lang(self):
        ocr = OCREngine()
        r = ocr.multi_language_ocr(
            "img1", ["en", "tr", "de"],
        )
        assert r["processed"] is True
        assert r["languages_tried"] == 3
        assert r["best_confidence"] == 0.92

    def test_default_langs(self):
        ocr = OCREngine()
        r = ocr.multi_language_ocr("img1")
        assert r["languages_tried"] == 2


class TestRecognizeHandwriting:
    """recognize_handwriting testleri."""

    def test_handwriting(self):
        ocr = OCREngine()
        r = ocr.recognize_handwriting(
            "img1",
        )
        assert r["recognized"] is True
        assert r["handwriting"] is True
        assert r["confidence"] == 0.75


class TestExtractTable:
    """extract_table testleri."""

    def test_table(self):
        ocr = OCREngine()
        r = ocr.extract_table("img1")
        assert r["extracted"] is True
        assert r["rows"] == 5
        assert r["cols"] == 3
        assert ocr.table_count == 1

    def test_custom_cols(self):
        ocr = OCREngine()
        r = ocr.extract_table(
            "img1", expected_cols=5,
        )
        assert r["cols"] == 5


class TestGetConfidenceScore:
    """get_confidence_score testleri."""

    def test_found(self):
        ocr = OCREngine()
        ocr.extract_text("img1", "en")
        r = ocr.get_confidence_score(
            "img1",
        )
        assert r["found"] is True
        assert r["grade"] == "excellent"

    def test_not_found(self):
        ocr = OCREngine()
        r = ocr.get_confidence_score(
            "none",
        )
        assert r["found"] is False


# ==================== ObjectDetector ====================


class TestDetectObjects:
    """detect_objects testleri."""

    def test_default_threshold(self):
        od = ObjectDetector()
        r = od.detect_objects("img1")
        assert r["detected"] is True
        assert r["objects_found"] == 2
        assert od.detection_count == 1

    def test_high_threshold(self):
        od = ObjectDetector()
        r = od.detect_objects(
            "img1",
            confidence_threshold=0.9,
        )
        assert r["objects_found"] == 1

    def test_low_threshold(self):
        od = ObjectDetector()
        r = od.detect_objects(
            "img1",
            confidence_threshold=0.1,
        )
        assert r["objects_found"] == 3


class TestClassify:
    """classify testleri."""

    def test_classify(self):
        od = ObjectDetector()
        r = od.classify("img1")
        assert r["classified"] is True
        assert r["top_category"] == "vehicle"
        assert r["top_score"] == 0.9


class TestGetBoundingBoxes:
    """get_bounding_boxes testleri."""

    def test_boxes(self):
        od = ObjectDetector()
        od.detect_objects("img1")
        r = od.get_bounding_boxes("img1")
        assert r["retrieved"] is True
        assert r["boxes"] == 2

    def test_empty(self):
        od = ObjectDetector()
        r = od.get_bounding_boxes("none")
        assert r["boxes"] == 0


class TestCountObjects:
    """count_objects testleri."""

    def test_count_all(self):
        od = ObjectDetector()
        od.detect_objects("img1")
        r = od.count_objects("img1")
        assert r["counted"] is True
        assert r["count"] == 2

    def test_count_by_label(self):
        od = ObjectDetector()
        od.detect_objects("img1")
        r = od.count_objects(
            "img1", label="person",
        )
        assert r["count"] == 1


class TestTrackObject:
    """track_object testleri."""

    def test_track(self):
        od = ObjectDetector()
        r = od.track_object(
            "obj1", "img1",
            bbox={"x": 10, "y": 20},
        )
        assert r["tracked"] is True
        assert od.tracked_count == 1

    def test_update(self):
        od = ObjectDetector()
        od.track_object("obj1", "img1")
        od.track_object("obj1", "img2")
        assert od.tracked_count == 1


# ==================== SceneClassifier ====================


class TestRecognizeScene:
    """recognize_scene testleri."""

    def test_recognize(self):
        sc = SceneClassifier()
        r = sc.recognize_scene("img1")
        assert r["recognized"] is True
        assert r["scene"] == "office"
        assert r["confidence"] == 0.85
        assert sc.classification_count == 1


class TestDetectContext:
    """detect_context testleri."""

    def test_context(self):
        sc = SceneClassifier()
        r = sc.detect_context("img1")
        assert r["detected"] is True
        assert "lighting" in r["context"]


class TestAnalyzeEnvironment:
    """analyze_environment testleri."""

    def test_analyze(self):
        sc = SceneClassifier()
        r = sc.analyze_environment("img1")
        assert r["analyzed"] is True
        assert r["environment"]["type"] == "indoor"


class TestDetectActivity:
    """detect_activity testleri."""

    def test_activity(self):
        sc = SceneClassifier()
        r = sc.detect_activity("img1")
        assert r["detected"] is True
        assert r["primary_activity"] == "working"
        assert sc.activity_count == 1


class TestTagImage:
    """tag_image testleri."""

    def test_auto_tags(self):
        sc = SceneClassifier()
        r = sc.tag_image("img1")
        assert r["tagged"] is True
        assert r["tag_count"] >= 3

    def test_manual_tags(self):
        sc = SceneClassifier()
        r = sc.tag_image(
            "img1",
            auto_tags=False,
            manual_tags=["test", "demo"],
        )
        assert r["tag_count"] == 2


# ==================== VisualAnomalyDetector ====================


class TestDetectAnomaly:
    """detect_anomaly testleri."""

    def test_no_baseline(self):
        vad = VisualAnomalyDetector()
        r = vad.detect_anomaly(
            "img1", zone_id="z1",
        )
        assert r["anomaly"] is False
        assert r["reason"] == "no_baseline"

    def test_with_baseline_high(self):
        vad = VisualAnomalyDetector()
        vad.set_baseline("z1", "ref1")
        r = vad.detect_anomaly(
            "img1",
            zone_id="z1",
            sensitivity="high",
        )
        assert r["detected"] is True
        assert r["anomaly"] is True
        assert vad.anomaly_count == 1

    def test_with_baseline_low(self):
        vad = VisualAnomalyDetector()
        vad.set_baseline("z1", "ref1")
        r = vad.detect_anomaly(
            "img1",
            zone_id="z1",
            sensitivity="low",
        )
        assert r["anomaly"] is False


class TestSetBaseline:
    """set_baseline testleri."""

    def test_set(self):
        vad = VisualAnomalyDetector()
        r = vad.set_baseline("z1", "ref1")
        assert r["baseline_set"] is True


class TestDetectChange:
    """detect_change testleri."""

    def test_change(self):
        vad = VisualAnomalyDetector()
        r = vad.detect_change(
            "img1", "img2",
        )
        assert r["detected"] is True
        assert r["significant"] is True
        assert r["change_pct"] == 15.5


class TestDetectIntrusion:
    """detect_intrusion testleri."""

    def test_with_baseline(self):
        vad = VisualAnomalyDetector()
        vad.set_baseline("z1", "ref1")
        r = vad.detect_intrusion(
            "img1", zone_id="z1",
        )
        assert r["intrusion_detected"] is True

    def test_no_baseline(self):
        vad = VisualAnomalyDetector()
        r = vad.detect_intrusion(
            "img1", zone_id="z2",
        )
        assert r["intrusion_detected"] is False


class TestDetectDefect:
    """detect_defect testleri."""

    def test_defect(self):
        vad = VisualAnomalyDetector()
        r = vad.detect_defect(
            "img1", product_type="bottle",
        )
        assert r["detected"] is True
        assert r["defects_found"] == 1
        assert r["quality_pass"] is True


class TestVisualGenerateAlert:
    """generate_alert testleri."""

    def test_generate(self):
        vad = VisualAnomalyDetector()
        r = vad.generate_alert(
            "img1",
            alert_type="intrusion",
            severity="high",
        )
        assert r["generated"] is True
        assert vad.alert_count == 1


# ==================== DocumentScanner ====================


class TestDetectDocument:
    """detect_document testleri."""

    def test_detect(self):
        ds = DocumentScanner()
        r = ds.detect_document("img1")
        assert r["detected"] is True
        assert r["document_found"] is True
        assert len(r["corners"]) == 4


class TestCorrectPerspective:
    """correct_perspective testleri."""

    def test_correct(self):
        ds = DocumentScanner()
        r = ds.correct_perspective(
            "img1",
            corners=[
                {"x": 0, "y": 0},
                {"x": 800, "y": 0},
            ],
        )
        assert r["corrected"] is True
        assert r["corners_used"] == 2


class TestEnhanceDocument:
    """enhance_document testleri."""

    def test_enhance(self):
        ds = DocumentScanner()
        r = ds.enhance_document(
            "img1",
            contrast=1.5,
            sharpen=True,
        )
        assert r["enhanced"] is True
        assert "contrast" in r["enhancements"]
        assert "sharpen" in r["enhancements"]


class TestHandleMultipage:
    """handle_multipage testleri."""

    def test_multipage(self):
        ds = DocumentScanner()
        r = ds.handle_multipage(
            "doc1",
            page_images=[
                "p1", "p2", "p3",
            ],
        )
        assert r["processed"] is True
        assert r["total_pages"] == 3
        assert ds.scan_count == 1


class TestGeneratePdf:
    """generate_pdf testleri."""

    def test_generate(self):
        ds = DocumentScanner()
        ds.handle_multipage(
            "doc1", page_images=["p1"],
        )
        r = ds.generate_pdf(
            "doc1", title="Test Doc",
        )
        assert r["generated"] is True
        assert r["pages"] == 1
        assert ds.pdf_count == 1


# ==================== VideoStreamProcessor ====================


class TestHandleStream:
    """handle_stream testleri."""

    def test_start(self):
        vsp = VideoStreamProcessor()
        r = vsp.handle_stream(
            "rtsp://cam1",
            camera_id="cam1",
            fps=25,
        )
        assert r["started"] is True
        assert r["fps"] == 25
        assert vsp.stream_count == 1


class TestExtractFrame:
    """extract_frame testleri."""

    def test_extract(self):
        vsp = VideoStreamProcessor()
        s = vsp.handle_stream(
            "rtsp://cam1",
        )
        r = vsp.extract_frame(
            s["stream_id"], 42,
        )
        assert r["extracted"] is True
        assert r["frame_number"] == 42
        assert vsp.frame_count == 1

    def test_unknown_stream(self):
        vsp = VideoStreamProcessor()
        r = vsp.extract_frame("none")
        assert r["found"] is False


class TestDetectMotion:
    """detect_motion testleri."""

    def test_motion(self):
        vsp = VideoStreamProcessor()
        s = vsp.handle_stream(
            "rtsp://cam1",
        )
        r = vsp.detect_motion(
            s["stream_id"],
            sensitivity=0.5,
        )
        assert r["detected"] is True
        assert r["motion_detected"] is True
        assert vsp.motion_count == 1

    def test_high_sensitivity(self):
        vsp = VideoStreamProcessor()
        s = vsp.handle_stream(
            "rtsp://cam1",
        )
        r = vsp.detect_motion(
            s["stream_id"],
            sensitivity=0.9,
        )
        assert r["motion_detected"] is False


class TestStartRecording:
    """start_recording testleri."""

    def test_record(self):
        vsp = VideoStreamProcessor()
        s = vsp.handle_stream(
            "rtsp://cam1",
        )
        r = vsp.start_recording(
            s["stream_id"],
            duration_sec=120,
        )
        assert r["recording"] is True
        assert r["duration_sec"] == 120

    def test_unknown_stream(self):
        vsp = VideoStreamProcessor()
        r = vsp.start_recording("none")
        assert r["found"] is False


class TestGetPlayback:
    """get_playback testleri."""

    def test_playback(self):
        vsp = VideoStreamProcessor()
        s = vsp.handle_stream(
            "rtsp://cam1",
        )
        vsp.start_recording(
            s["stream_id"],
        )
        r = vsp.get_playback(
            stream_id=s["stream_id"],
        )
        assert r["retrieved"] is True
        assert r["recordings"] == 1


# ==================== VisualSearch ====================


class TestSearchSimilar:
    """search_similar testleri."""

    def test_search(self):
        vs = VisualSearch()
        vs.index_image("img1", ["cat"])
        vs.index_image("img2", ["dog"])
        r = vs.search_similar("img3")
        assert r["searched"] is True
        assert r["results_count"] == 2
        assert vs.search_count == 1

    def test_empty_index(self):
        vs = VisualSearch()
        r = vs.search_similar("img1")
        assert r["results_count"] == 0


class TestReverseSearch:
    """reverse_search testleri."""

    def test_reverse(self):
        vs = VisualSearch()
        vs.index_image("img1")
        vs.index_image("img2")
        r = vs.reverse_search("img1")
        assert r["searched"] is True
        assert r["matches_found"] == 1


class TestMatchVisual:
    """match_visual testleri."""

    def test_both_indexed(self):
        vs = VisualSearch()
        vs.index_image("a")
        vs.index_image("b")
        r = vs.match_visual("a", "b")
        assert r["matched"] is True
        assert r["is_match"] is True

    def test_none_indexed(self):
        vs = VisualSearch()
        r = vs.match_visual("x", "y")
        assert r["is_match"] is False


class TestRecognizeProduct:
    """recognize_product testleri."""

    def test_with_catalog(self):
        vs = VisualSearch()
        catalog = [
            {
                "product_id": "p1",
                "name": "Widget",
            },
        ]
        r = vs.recognize_product(
            "img1", catalog,
        )
        assert r["recognized"] is True
        assert r["product_name"] == "Widget"

    def test_empty_catalog(self):
        vs = VisualSearch()
        r = vs.recognize_product("img1")
        assert r["recognized"] is False


class TestIndexImage:
    """index_image testleri."""

    def test_index(self):
        vs = VisualSearch()
        r = vs.index_image(
            "img1",
            tags=["outdoor"],
            source="cam1",
        )
        assert r["indexed"] is True
        assert r["feature_hash"]
        assert vs.index_count == 1


# ==================== VisualIntelOrchestrator ====================


class TestAnalyzeImagePipeline:
    """analyze_image testleri."""

    def test_full_pipeline(self):
        vio = VisualIntelOrchestrator()
        r = vio.analyze_image(
            "img1",
            extract_text=True,
            detect_objects=True,
        )
        assert r["pipeline_complete"] is True
        assert r["scene"] == "office"
        assert r["objects_found"] == 2
        assert r["text_extracted"] is True
        assert r["indexed"] is True
        assert vio.pipeline_count == 1

    def test_minimal_pipeline(self):
        vio = VisualIntelOrchestrator()
        r = vio.analyze_image(
            "img2",
            detect_objects=False,
            extract_text=False,
        )
        assert r["pipeline_complete"] is True
        assert r["objects_found"] == 0


class TestSetupCamera:
    """setup_camera testleri."""

    def test_setup(self):
        vio = VisualIntelOrchestrator()
        r = vio.setup_camera(
            "rtsp://cam1",
            camera_id="cam1",
        )
        assert r["setup"] is True
        assert r["status"] == "active"
        assert vio.camera_count == 1


class TestVisualIntelAnalytics:
    """get_analytics testleri."""

    def test_analytics(self):
        vio = VisualIntelOrchestrator()
        vio.analyze_image("img1")
        vio.setup_camera("rtsp://c1")
        a = vio.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["cameras_active"] == 1
        assert a["images_analyzed"] >= 1
        assert a["scenes_classified"] >= 1
        assert "objects_detected" in a
        assert "images_indexed" in a
