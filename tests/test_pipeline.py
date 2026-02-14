"""Data Pipeline & ETL System testleri.

DataExtractor, DataTransformer,
DataLoader, PipelineBuilder,
DataValidator, StreamProcessor,
PipelineJobScheduler, LineageTracker,
PipelineOrchestrator testleri.
"""

import time

import pytest

from app.models.pipeline import (
    JobFrequency,
    LineageEntry,
    PipelineRecord,
    PipelineSnapshot,
    PipelineStatus,
    SourceType,
    StepRecord,
    StepType,
    ValidationLevel,
    WindowType,
)

from app.core.pipeline.data_extractor import (
    DataExtractor,
)
from app.core.pipeline.data_transformer import (
    DataTransformer,
)
from app.core.pipeline.data_loader import DataLoader
from app.core.pipeline.pipeline_builder import (
    PipelineBuilder,
)
from app.core.pipeline.data_validator import (
    DataValidator,
)
from app.core.pipeline.stream_processor import (
    StreamProcessor,
)
from app.core.pipeline.job_scheduler import (
    PipelineJobScheduler,
)
from app.core.pipeline.lineage_tracker import (
    LineageTracker,
)
from app.core.pipeline.pipeline_orchestrator import (
    PipelineOrchestrator,
)


# ===================== Models =====================


class TestPipelineModels:
    """Model testleri."""

    def test_source_type_values(self) -> None:
        assert SourceType.DATABASE == "database"
        assert SourceType.API == "api"
        assert SourceType.FILE == "file"
        assert SourceType.WEB == "web"
        assert SourceType.STREAM == "stream"

    def test_pipeline_status_values(self) -> None:
        assert PipelineStatus.PENDING == "pending"
        assert PipelineStatus.RUNNING == "running"
        assert PipelineStatus.COMPLETED == "completed"
        assert PipelineStatus.FAILED == "failed"
        assert PipelineStatus.PAUSED == "paused"
        assert PipelineStatus.CANCELLED == "cancelled"

    def test_step_type_values(self) -> None:
        assert StepType.EXTRACT == "extract"
        assert StepType.TRANSFORM == "transform"
        assert StepType.LOAD == "load"
        assert StepType.VALIDATE == "validate"
        assert StepType.BRANCH == "branch"
        assert StepType.MERGE == "merge"

    def test_validation_level_values(self) -> None:
        assert ValidationLevel.STRICT == "strict"
        assert ValidationLevel.MODERATE == "moderate"
        assert ValidationLevel.LENIENT == "lenient"

    def test_window_type_values(self) -> None:
        assert WindowType.TUMBLING == "tumbling"
        assert WindowType.SLIDING == "sliding"
        assert WindowType.SESSION == "session"
        assert WindowType.GLOBAL == "global"

    def test_job_frequency_values(self) -> None:
        assert JobFrequency.MINUTELY == "minutely"
        assert JobFrequency.HOURLY == "hourly"
        assert JobFrequency.DAILY == "daily"
        assert JobFrequency.CRON == "cron"

    def test_pipeline_record_defaults(self) -> None:
        rec = PipelineRecord()
        assert rec.pipeline_id
        assert rec.name == ""
        assert rec.status == PipelineStatus.PENDING

    def test_step_record_defaults(self) -> None:
        rec = StepRecord()
        assert rec.step_id
        assert rec.step_type == StepType.EXTRACT
        assert rec.input_count == 0
        assert rec.output_count == 0

    def test_lineage_entry_defaults(self) -> None:
        entry = LineageEntry(
            source="src", target="dst",
        )
        assert entry.entry_id
        assert entry.source == "src"
        assert entry.target == "dst"

    def test_pipeline_snapshot(self) -> None:
        snap = PipelineSnapshot(
            total_pipelines=5,
            running=2,
            completed=3,
            total_records_processed=1000,
        )
        assert snap.total_pipelines == 5
        assert snap.total_records_processed == 1000


# ============= DataExtractor =============


class TestDataExtractor:
    """DataExtractor testleri."""

    def test_register_source(self) -> None:
        ext = DataExtractor()
        src = ext.register_source(
            "db1", SourceType.DATABASE,
        )
        assert src["name"] == "db1"
        assert src["type"] == "database"
        assert ext.source_count == 1

    def test_register_source_with_config(self) -> None:
        ext = DataExtractor()
        src = ext.register_source(
            "api1", SourceType.API,
            {"url": "https://api.test.com"},
        )
        assert src["config"]["url"] == "https://api.test.com"

    def test_extract(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        result = ext.extract("db1")
        assert result["success"]
        assert result["record_count"] == 5
        assert ext.extraction_count == 1

    def test_extract_with_limit(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        result = ext.extract("db1", limit=10)
        assert result["record_count"] == 10

    def test_extract_nonexistent(self) -> None:
        ext = DataExtractor()
        result = ext.extract("invalid")
        assert not result["success"]
        assert result["reason"] == "source_not_found"

    def test_extract_disabled(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        ext.disable_source("db1")
        result = ext.extract("db1")
        assert not result["success"]

    def test_extract_batch(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        results = ext.extract_batch(
            "db1", ["q1", "q2", "q3"],
        )
        assert len(results) == 3
        assert ext.extraction_count == 3

    def test_extract_incremental(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        result = ext.extract_incremental(
            "db1", since="2024-01-01",
        )
        assert result["success"]
        assert result["incremental"]
        assert result["since"] == "2024-01-01"

    def test_enable_disable_source(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        assert ext.disable_source("db1")
        assert ext.enable_source("db1")
        result = ext.extract("db1")
        assert result["success"]

    def test_remove_source(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        assert ext.remove_source("db1")
        assert ext.source_count == 0

    def test_remove_nonexistent(self) -> None:
        ext = DataExtractor()
        assert not ext.remove_source("invalid")

    def test_total_records(self) -> None:
        ext = DataExtractor()
        ext.register_source(
            "db1", SourceType.DATABASE,
        )
        ext.extract("db1", limit=3)
        ext.extract("db1", limit=7)
        assert ext.total_records == 10


# ============ DataTransformer ============


class TestDataTransformer:
    """DataTransformer testleri."""

    def test_add_mapping(self) -> None:
        tf = DataTransformer()
        m = tf.add_mapping(
            "user_map",
            {"name": "full_name", "age": "years"},
        )
        assert m["fields"] == 2
        assert tf.mapping_count == 1

    def test_apply_mapping(self) -> None:
        tf = DataTransformer()
        tf.add_mapping(
            "m1", {"name": "full_name", "age": "years"},
        )
        data = [
            {"name": "Ali", "age": 30},
            {"name": "Veli", "age": 25},
        ]
        result = tf.apply_mapping(data, "m1")
        assert result[0]["full_name"] == "Ali"
        assert result[0]["years"] == 30
        assert tf.transform_count == 1

    def test_apply_mapping_nonexistent(self) -> None:
        tf = DataTransformer()
        data = [{"a": 1}]
        result = tf.apply_mapping(data, "invalid")
        assert result == data

    def test_clean_strip(self) -> None:
        tf = DataTransformer()
        data = [
            {"name": "  Ali  ", "city": " Istanbul "},
        ]
        result = tf.clean(data)
        assert result[0]["name"] == "Ali"
        assert result[0]["city"] == "Istanbul"

    def test_clean_remove_nulls(self) -> None:
        tf = DataTransformer()
        data = [
            {"name": "Ali", "age": None, "x": 1},
        ]
        result = tf.clean(
            data, {"remove_nulls": True},
        )
        assert "age" not in result[0]
        assert result[0]["name"] == "Ali"

    def test_clean_lowercase_keys(self) -> None:
        tf = DataTransformer()
        data = [{"Name": "Ali", "AGE": 30}]
        result = tf.clean(
            data, {"lowercase_keys": True},
        )
        assert "name" in result[0]
        assert "age" in result[0]

    def test_convert_types(self) -> None:
        tf = DataTransformer()
        data = [
            {"id": "1", "score": "95.5", "active": "1"},
        ]
        result = tf.convert_types(
            data, {"id": "int", "score": "float"},
        )
        assert result[0]["id"] == 1
        assert result[0]["score"] == 95.5

    def test_convert_types_invalid(self) -> None:
        tf = DataTransformer()
        data = [{"id": "abc"}]
        result = tf.convert_types(
            data, {"id": "int"},
        )
        assert result[0]["id"] == "abc"

    def test_aggregate_sum(self) -> None:
        tf = DataTransformer()
        data = [
            {"dept": "A", "salary": 100},
            {"dept": "A", "salary": 200},
            {"dept": "B", "salary": 150},
        ]
        result = tf.aggregate(
            data, "dept", "salary", "sum",
        )
        a_row = next(
            r for r in result if r["dept"] == "A"
        )
        assert a_row["sum_salary"] == 300

    def test_aggregate_count(self) -> None:
        tf = DataTransformer()
        data = [
            {"dept": "A", "salary": 100},
            {"dept": "A", "salary": 200},
            {"dept": "B", "salary": 150},
        ]
        result = tf.aggregate(
            data, "dept", "salary", "count",
        )
        a_row = next(
            r for r in result if r["dept"] == "A"
        )
        assert a_row["count_salary"] == 2.0

    def test_aggregate_avg(self) -> None:
        tf = DataTransformer()
        data = [
            {"dept": "A", "salary": 100},
            {"dept": "A", "salary": 200},
        ]
        result = tf.aggregate(
            data, "dept", "salary", "avg",
        )
        assert result[0]["avg_salary"] == 150.0

    def test_aggregate_min_max(self) -> None:
        tf = DataTransformer()
        data = [
            {"g": "X", "v": 10},
            {"g": "X", "v": 50},
            {"g": "X", "v": 30},
        ]
        r_min = tf.aggregate(data, "g", "v", "min")
        r_max = tf.aggregate(data, "g", "v", "max")
        assert r_min[0]["min_v"] == 10.0
        assert r_max[0]["max_v"] == 50.0

    def test_enrich(self) -> None:
        tf = DataTransformer()
        tf.add_enrichment(
            "defaults",
            {"country": "TR", "active": True},
        )
        data = [{"name": "Ali"}]
        result = tf.enrich(data, "defaults")
        assert result[0]["country"] == "TR"
        assert result[0]["active"] is True
        assert result[0]["name"] == "Ali"

    def test_enrich_no_overwrite(self) -> None:
        tf = DataTransformer()
        tf.add_enrichment(
            "e1", {"country": "TR"},
        )
        data = [{"name": "Ali", "country": "DE"}]
        result = tf.enrich(data, "e1")
        assert result[0]["country"] == "DE"

    def test_enrich_nonexistent(self) -> None:
        tf = DataTransformer()
        data = [{"a": 1}]
        result = tf.enrich(data, "invalid")
        assert result == data

    def test_add_cleaner(self) -> None:
        tf = DataTransformer()
        c = tf.add_cleaner(
            "basic", {"strip_whitespace": True},
        )
        assert c["name"] == "basic"


# ============== DataLoader ==============


class TestDataLoader:
    """DataLoader testleri."""

    def test_register_target(self) -> None:
        loader = DataLoader()
        t = loader.register_target(
            "db1", SourceType.DATABASE,
        )
        assert t["name"] == "db1"
        assert loader.target_count == 1

    def test_load(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        data = [{"id": 1}, {"id": 2}]
        result = loader.load("db1", data)
        assert result["success"]
        assert result["loaded"] == 2
        assert loader.load_count == 1

    def test_load_with_mode(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        result = loader.load(
            "db1", [{"id": 1}], "replace",
        )
        assert result["mode"] == "replace"

    def test_load_nonexistent(self) -> None:
        loader = DataLoader()
        result = loader.load("invalid", [])
        assert not result["success"]

    def test_load_disabled(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        loader.disable_target("db1")
        result = loader.load("db1", [{"id": 1}])
        assert not result["success"]

    def test_load_batch(self) -> None:
        loader = DataLoader(default_batch_size=3)
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        data = [{"id": i} for i in range(10)]
        result = loader.load_batch("db1", data)
        assert result["success"]
        assert result["total_loaded"] == 10
        assert result["batch_count"] == 4

    def test_load_batch_custom_size(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        data = [{"id": i} for i in range(5)]
        result = loader.load_batch(
            "db1", data, batch_size=2,
        )
        assert result["batch_count"] == 3

    def test_load_incremental(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        result = loader.load_incremental(
            "db1", [{"id": 1}], "id",
        )
        assert result["success"]
        assert result["incremental"]
        assert result["key_field"] == "id"

    def test_enable_disable_target(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        assert loader.disable_target("db1")
        assert loader.enable_target("db1")

    def test_remove_target(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        assert loader.remove_target("db1")
        assert loader.target_count == 0

    def test_total_loaded(self) -> None:
        loader = DataLoader()
        loader.register_target(
            "db1", SourceType.DATABASE,
        )
        loader.load("db1", [{"id": 1}, {"id": 2}])
        loader.load("db1", [{"id": 3}])
        assert loader.total_loaded == 3


# =========== PipelineBuilder ===========


class TestPipelineBuilder:
    """PipelineBuilder testleri."""

    def test_create_pipeline(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("etl_1")
        assert p.name == "etl_1"
        assert builder.pipeline_count == 1

    def test_add_step(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        step = builder.add_step(
            p.pipeline_id, "extract",
            StepType.EXTRACT,
        )
        assert step is not None
        assert step.name == "extract"
        assert builder.total_steps == 1

    def test_add_step_invalid_pipeline(self) -> None:
        builder = PipelineBuilder()
        step = builder.add_step(
            "invalid", "s1", StepType.EXTRACT,
        )
        assert step is None

    def test_chain_steps(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        s1 = builder.add_step(
            p.pipeline_id, "e", StepType.EXTRACT,
        )
        s2 = builder.add_step(
            p.pipeline_id, "t", StepType.TRANSFORM,
        )
        s3 = builder.add_step(
            p.pipeline_id, "l", StepType.LOAD,
        )
        assert builder.chain_steps(
            p.pipeline_id,
            [s1.step_id, s2.step_id, s3.step_id],
        )

    def test_add_branch(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        s1 = builder.add_step(
            p.pipeline_id, "e", StepType.EXTRACT,
        )
        s2 = builder.add_step(
            p.pipeline_id, "t1", StepType.TRANSFORM,
        )
        s3 = builder.add_step(
            p.pipeline_id, "t2", StepType.TRANSFORM,
        )
        assert builder.add_branch(
            p.pipeline_id, s1.step_id,
            [s2.step_id, s3.step_id],
        )

    def test_add_merge(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        s1 = builder.add_step(
            p.pipeline_id, "t1", StepType.TRANSFORM,
        )
        s2 = builder.add_step(
            p.pipeline_id, "t2", StepType.TRANSFORM,
        )
        s3 = builder.add_step(
            p.pipeline_id, "load", StepType.LOAD,
        )
        assert builder.add_merge(
            p.pipeline_id,
            [s1.step_id, s2.step_id],
            s3.step_id,
        )

    def test_add_condition(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        s1 = builder.add_step(
            p.pipeline_id, "v", StepType.VALIDATE,
        )
        assert builder.add_condition(
            p.pipeline_id, s1.step_id,
            "quality > 0.8",
            on_true="load", on_false="reject",
        )

    def test_get_pipeline(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        found = builder.get_pipeline(p.pipeline_id)
        assert found is not None
        assert found.name == "p1"

    def test_get_pipeline_nonexistent(self) -> None:
        builder = PipelineBuilder()
        assert builder.get_pipeline("x") is None

    def test_get_steps(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        builder.add_step(
            p.pipeline_id, "s1", StepType.EXTRACT,
        )
        builder.add_step(
            p.pipeline_id, "s2", StepType.LOAD,
        )
        steps = builder.get_steps(p.pipeline_id)
        assert len(steps) == 2

    def test_get_execution_order(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        s1 = builder.add_step(
            p.pipeline_id, "e", StepType.EXTRACT,
        )
        s2 = builder.add_step(
            p.pipeline_id, "t", StepType.TRANSFORM,
        )
        builder.chain_steps(
            p.pipeline_id,
            [s1.step_id, s2.step_id],
        )
        order = builder.get_execution_order(
            p.pipeline_id,
        )
        assert len(order) == 2
        assert order[0] == s1.step_id

    def test_delete_pipeline(self) -> None:
        builder = PipelineBuilder()
        p = builder.create_pipeline("p1")
        assert builder.delete_pipeline(
            p.pipeline_id,
        )
        assert builder.pipeline_count == 0

    def test_delete_nonexistent(self) -> None:
        builder = PipelineBuilder()
        assert not builder.delete_pipeline("x")


# ============ DataValidator ============


class TestDataValidator:
    """DataValidator testleri."""

    def test_init_level(self) -> None:
        v = DataValidator(ValidationLevel.STRICT)
        assert v.level == ValidationLevel.STRICT

    def test_add_schema(self) -> None:
        v = DataValidator()
        s = v.add_schema(
            "user",
            {"name": "str", "age": "int"},
            required=["name"],
        )
        assert s["name"] == "user"
        assert v.schema_count == 1

    def test_validate_schema_valid(self) -> None:
        v = DataValidator()
        v.add_schema(
            "user",
            {"name": "str", "age": "int"},
            required=["name"],
        )
        data = [
            {"name": "Ali", "age": 30},
            {"name": "Veli", "age": 25},
        ]
        result = v.validate_schema(data, "user")
        assert result["valid"]
        assert result["checked"] == 2

    def test_validate_schema_missing_required(self) -> None:
        v = DataValidator()
        v.add_schema(
            "user",
            {"name": "str"},
            required=["name"],
        )
        data = [{"age": 30}]
        result = v.validate_schema(data, "user")
        assert not result["valid"]
        assert len(result["errors"]) > 0

    def test_validate_schema_type_mismatch(self) -> None:
        v = DataValidator()
        v.add_schema(
            "user",
            {"name": "str", "age": "int"},
        )
        data = [{"name": "Ali", "age": "thirty"}]
        result = v.validate_schema(data, "user")
        assert not result["valid"]

    def test_validate_schema_not_found(self) -> None:
        v = DataValidator()
        result = v.validate_schema([], "invalid")
        assert not result["valid"]

    def test_check_nulls(self) -> None:
        v = DataValidator()
        data = [
            {"name": "Ali", "age": 30},
            {"name": None, "age": 25},
            {"name": "Veli", "age": None},
        ]
        result = v.check_nulls(
            data, ["name", "age"],
        )
        assert not result["valid"]
        assert result["null_counts"]["name"] == 1
        assert result["null_counts"]["age"] == 1
        assert result["total_nulls"] == 2

    def test_check_nulls_clean(self) -> None:
        v = DataValidator()
        data = [
            {"name": "Ali", "age": 30},
        ]
        result = v.check_nulls(
            data, ["name", "age"],
        )
        assert result["valid"]

    def test_check_range(self) -> None:
        v = DataValidator()
        data = [
            {"age": 25}, {"age": 150}, {"age": -5},
        ]
        result = v.check_range(
            data, "age", min_val=0, max_val=120,
        )
        assert not result["valid"]
        assert len(result["violations"]) == 2

    def test_check_range_valid(self) -> None:
        v = DataValidator()
        data = [{"age": 25}, {"age": 50}]
        result = v.check_range(
            data, "age", min_val=0, max_val=120,
        )
        assert result["valid"]

    def test_check_uniqueness(self) -> None:
        v = DataValidator()
        data = [
            {"id": 1}, {"id": 2}, {"id": 1},
        ]
        result = v.check_uniqueness(data, "id")
        assert not result["valid"]
        assert len(result["duplicates"]) == 1

    def test_check_uniqueness_valid(self) -> None:
        v = DataValidator()
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = v.check_uniqueness(data, "id")
        assert result["valid"]
        assert result["unique_count"] == 3

    def test_check_quality(self) -> None:
        v = DataValidator()
        data = [
            {"name": "Ali", "age": 30},
            {"name": "Veli", "age": None},
        ]
        result = v.check_quality(data)
        assert result["total_rows"] == 2
        assert result["completeness"] == 0.75

    def test_check_quality_empty(self) -> None:
        v = DataValidator()
        result = v.check_quality([])
        assert result["total_rows"] == 0
        assert result["score"] == 0.0

    def test_check_quality_full(self) -> None:
        v = DataValidator()
        data = [{"name": "Ali", "age": 30}]
        result = v.check_quality(data)
        assert result["completeness"] == 1.0

    def test_add_rule(self) -> None:
        v = DataValidator()
        r = v.add_rule(
            "age_range", "age", "range",
            {"min": 0, "max": 120},
        )
        assert r["name"] == "age_range"
        assert v.rule_count == 1

    def test_result_count(self) -> None:
        v = DataValidator()
        v.check_quality([{"a": 1}])
        v.check_quality([{"b": 2}])
        assert v.result_count == 2


# =========== StreamProcessor ===========


class TestStreamProcessor:
    """StreamProcessor testleri."""

    def test_register_stream(self) -> None:
        sp = StreamProcessor()
        s = sp.register_stream("events")
        assert s["name"] == "events"
        assert sp.stream_count == 1

    def test_emit(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        result = sp.emit(
            "events", {"type": "click", "page": "/"},
        )
        assert result["processed"]
        assert sp.processed_count == 1

    def test_emit_nonexistent(self) -> None:
        sp = StreamProcessor()
        result = sp.emit(
            "invalid", {"type": "click"},
        )
        assert not result["processed"]

    def test_emit_paused(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        sp.pause_stream("events")
        result = sp.emit(
            "events", {"type": "click"},
        )
        assert not result["processed"]

    def test_handler(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        results: list[str] = []
        sp.register_handler(
            "click",
            lambda e: results.append("handled"),
        )
        sp.emit("events", {"type": "click"})
        assert len(results) == 1

    def test_add_window(self) -> None:
        sp = StreamProcessor()
        w = sp.add_window(
            "1min", WindowType.TUMBLING, 60,
        )
        assert w["name"] == "1min"
        assert sp.window_count == 1

    def test_add_sliding_window(self) -> None:
        sp = StreamProcessor()
        w = sp.add_window(
            "slide", WindowType.SLIDING,
            size_seconds=60,
            slide_seconds=30,
        )
        assert w["slide"] == 30

    def test_process_window(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        sp.add_window(
            "w1", WindowType.TUMBLING, 9999,
        )
        sp.emit("events", {"type": "a"})
        sp.emit("events", {"type": "b"})
        result = sp.process_window("w1", "count")
        assert result["result"] == 2

    def test_process_window_nonexistent(self) -> None:
        sp = StreamProcessor()
        result = sp.process_window("invalid")
        assert result["result"] is None

    def test_handle_late_event(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        event = {
            "type": "click",
            "_timestamp": time.time() - 100,
        }
        result = sp.handle_late_event(
            "events", event, max_lateness=300,
        )
        assert result["processed"]
        assert sp.late_count == 1

    def test_handle_too_late(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        event = {
            "type": "click",
            "_timestamp": time.time() - 1000,
        }
        result = sp.handle_late_event(
            "events", event, max_lateness=300,
        )
        assert not result["processed"]
        assert result["reason"] == "too_late"

    def test_pause_resume(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        assert sp.pause_stream("events")
        assert sp.resume_stream("events")
        result = sp.emit(
            "events", {"type": "a"},
        )
        assert result["processed"]

    def test_clear_window(self) -> None:
        sp = StreamProcessor()
        sp.register_stream("events")
        sp.add_window(
            "w1", WindowType.TUMBLING, 60,
        )
        sp.emit("events", {"type": "a"})
        cleared = sp.clear_window("w1")
        assert cleared == 1

    def test_buffer_limit(self) -> None:
        sp = StreamProcessor(buffer_size=3)
        sp.register_stream("events")
        for i in range(5):
            sp.emit("events", {"id": i})
        assert sp.buffer_count == 3


# ========= PipelineJobScheduler =========


class TestPipelineJobScheduler:
    """PipelineJobScheduler testleri."""

    def test_schedule(self) -> None:
        sched = PipelineJobScheduler()
        job = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        assert job["pipeline_id"] == "p1"
        assert job["frequency"] == "daily"
        assert sched.job_count == 1

    def test_schedule_cron(self) -> None:
        sched = PipelineJobScheduler()
        job = sched.schedule(
            "p1", JobFrequency.CRON,
            cron_expr="0 */6 * * *",
        )
        assert job["cron_expr"] == "0 */6 * * *"

    def test_schedule_with_deps(self) -> None:
        sched = PipelineJobScheduler()
        j1 = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        j2 = sched.schedule(
            "p2", JobFrequency.DAILY,
            depends_on=[j1["job_id"]],
        )
        assert j1["job_id"] in j2["depends_on"]

    def test_run_job(self) -> None:
        sched = PipelineJobScheduler()
        job = sched.schedule(
            "p1", JobFrequency.HOURLY,
        )
        result = sched.run_job(job["job_id"])
        assert result["success"]
        assert sched.history_count == 1

    def test_run_nonexistent(self) -> None:
        sched = PipelineJobScheduler()
        result = sched.run_job("invalid")
        assert not result["success"]

    def test_run_disabled(self) -> None:
        sched = PipelineJobScheduler()
        job = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        sched.disable_job(job["job_id"])
        result = sched.run_job(job["job_id"])
        assert not result["success"]

    def test_run_blocked_by_dependency(self) -> None:
        sched = PipelineJobScheduler()
        j1 = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        j2 = sched.schedule(
            "p2", JobFrequency.DAILY,
            depends_on=[j1["job_id"]],
        )
        result = sched.run_job(j2["job_id"])
        assert not result["success"]
        assert result["reason"] == "dependency_pending"

    def test_run_after_dependency(self) -> None:
        sched = PipelineJobScheduler()
        j1 = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        j2 = sched.schedule(
            "p2", JobFrequency.DAILY,
            depends_on=[j1["job_id"]],
        )
        sched.run_job(j1["job_id"])
        result = sched.run_job(j2["job_id"])
        assert result["success"]

    def test_retry_job(self) -> None:
        sched = PipelineJobScheduler(max_retries=3)
        job = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        result = sched.retry_job(job["job_id"])
        assert result["success"]

    def test_retry_max_exceeded(self) -> None:
        sched = PipelineJobScheduler(max_retries=1)
        job = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        # run_job succeeds and resets retries,
        # so manually set failed state
        j = sched.get_job(job["job_id"])
        j["retries"] = 1
        j["status"] = "failed"
        result = sched.retry_job(job["job_id"])
        assert not result["success"]
        assert result["reason"] == "max_retries_exceeded"

    def test_enable_disable(self) -> None:
        sched = PipelineJobScheduler()
        job = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        assert sched.disable_job(job["job_id"])
        assert sched.enable_job(job["job_id"])

    def test_cancel_job(self) -> None:
        sched = PipelineJobScheduler()
        job = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        assert sched.cancel_job(job["job_id"])
        j = sched.get_job(job["job_id"])
        assert j["status"] == "cancelled"

    def test_get_pending(self) -> None:
        sched = PipelineJobScheduler()
        sched.schedule("p1", JobFrequency.DAILY)
        sched.schedule("p2", JobFrequency.HOURLY)
        pending = sched.get_pending()
        assert len(pending) == 2

    def test_get_failed(self) -> None:
        sched = PipelineJobScheduler()
        sched.schedule("p1", JobFrequency.DAILY)
        assert len(sched.get_failed()) == 0

    def test_remove_job(self) -> None:
        sched = PipelineJobScheduler()
        job = sched.schedule(
            "p1", JobFrequency.DAILY,
        )
        assert sched.remove_job(job["job_id"])
        assert sched.job_count == 0

    def test_active_count(self) -> None:
        sched = PipelineJobScheduler()
        sched.schedule("p1", JobFrequency.DAILY)
        sched.schedule("p2", JobFrequency.HOURLY)
        assert sched.active_count == 2


# ============ LineageTracker ============


class TestLineageTracker:
    """LineageTracker testleri."""

    def test_record(self) -> None:
        lt = LineageTracker()
        entry = lt.record(
            "raw_data", "clean_data",
            "cleaning",
        )
        assert entry.source == "raw_data"
        assert entry.target == "clean_data"
        assert lt.entry_count == 1

    def test_get_downstream(self) -> None:
        lt = LineageTracker()
        lt.record("A", "B")
        lt.record("B", "C")
        lt.record("B", "D")
        downstream = lt.get_lineage(
            "A", "downstream",
        )
        assert "B" in downstream
        assert "C" in downstream
        assert "D" in downstream

    def test_get_upstream(self) -> None:
        lt = LineageTracker()
        lt.record("A", "C")
        lt.record("B", "C")
        upstream = lt.get_lineage("C", "upstream")
        assert "A" in upstream
        assert "B" in upstream

    def test_get_impact(self) -> None:
        lt = LineageTracker()
        lt.record("A", "B")
        lt.record("B", "C")
        lt.record("X", "B")
        impact = lt.get_impact("B")
        assert impact["downstream_count"] == 1
        assert impact["upstream_count"] == 2
        assert "A" in impact["upstream"]
        assert "X" in impact["upstream"]

    def test_transformation_history(self) -> None:
        lt = LineageTracker()
        lt.record("A", "B", "clean")
        lt.record("B", "C", "aggregate")
        history = lt.get_transformation_history("B")
        assert len(history) == 2

    def test_audit_trail(self) -> None:
        lt = LineageTracker()
        lt.record("A", "B")
        lt.record("C", "D")
        trail = lt.get_audit_trail()
        assert len(trail) == 2

    def test_audit_trail_limit(self) -> None:
        lt = LineageTracker()
        for i in range(10):
            lt.record(f"s{i}", f"t{i}")
        trail = lt.get_audit_trail(limit=5)
        assert len(trail) == 5

    def test_delete_entry(self) -> None:
        lt = LineageTracker()
        entry = lt.record("A", "B")
        assert lt.delete_entry(entry.entry_id)
        assert lt.entry_count == 0

    def test_delete_nonexistent(self) -> None:
        lt = LineageTracker()
        assert not lt.delete_entry("invalid")

    def test_entity_count(self) -> None:
        lt = LineageTracker()
        lt.record("A", "B")
        lt.record("B", "C")
        assert lt.entity_count == 3

    def test_audit_count(self) -> None:
        lt = LineageTracker()
        lt.record("A", "B")
        assert lt.audit_count == 1

    def test_record_with_metadata(self) -> None:
        lt = LineageTracker()
        entry = lt.record(
            "A", "B", "transform",
            {"rows": 100},
        )
        assert entry.transformation == "transform"


# ======== PipelineOrchestrator ========


class TestPipelineOrchestrator:
    """PipelineOrchestrator testleri."""

    def test_init(self) -> None:
        orch = PipelineOrchestrator()
        assert orch.extractor is not None
        assert orch.transformer is not None
        assert orch.loader is not None
        assert orch.execution_count == 0

    def test_run_etl(self) -> None:
        orch = PipelineOrchestrator()
        orch.extractor.register_source(
            "src", SourceType.DATABASE,
        )
        orch.loader.register_target(
            "dst", SourceType.DATABASE,
        )
        result = orch.run_etl("src", "dst")
        assert result["success"]
        assert result["extracted"] > 0
        assert result["loaded"] > 0
        assert orch.execution_count == 1

    def test_run_etl_with_mapping(self) -> None:
        orch = PipelineOrchestrator()
        orch.extractor.register_source(
            "src", SourceType.DATABASE,
        )
        orch.loader.register_target(
            "dst", SourceType.DATABASE,
        )
        orch.transformer.add_mapping(
            "m1", {"id": "user_id"},
        )
        result = orch.run_etl(
            "src", "dst", mapping_name="m1",
        )
        assert result["success"]

    def test_run_etl_source_not_found(self) -> None:
        orch = PipelineOrchestrator()
        orch.loader.register_target(
            "dst", SourceType.DATABASE,
        )
        result = orch.run_etl("invalid", "dst")
        assert not result["success"]
        assert result["stage"] == "extract"

    def test_run_etl_target_not_found(self) -> None:
        orch = PipelineOrchestrator()
        orch.extractor.register_source(
            "src", SourceType.DATABASE,
        )
        result = orch.run_etl("src", "invalid")
        assert not result["success"]
        assert result["stage"] == "load"

    def test_run_etl_lineage(self) -> None:
        orch = PipelineOrchestrator()
        orch.extractor.register_source(
            "src", SourceType.DATABASE,
        )
        orch.loader.register_target(
            "dst", SourceType.DATABASE,
        )
        orch.run_etl("src", "dst")
        assert orch.lineage.entry_count == 1

    def test_run_pipeline(self) -> None:
        orch = PipelineOrchestrator()
        p = orch.builder.create_pipeline("test")
        orch.builder.add_step(
            p.pipeline_id, "e", StepType.EXTRACT,
        )
        orch.builder.add_step(
            p.pipeline_id, "l", StepType.LOAD,
        )
        result = orch.run_pipeline(p.pipeline_id)
        assert result["success"]
        assert result["steps_completed"] == 2

    def test_run_pipeline_not_found(self) -> None:
        orch = PipelineOrchestrator()
        result = orch.run_pipeline("invalid")
        assert not result["success"]

    def test_get_analytics(self) -> None:
        orch = PipelineOrchestrator()
        orch.extractor.register_source(
            "src", SourceType.DATABASE,
        )
        orch.loader.register_target(
            "dst", SourceType.DATABASE,
        )
        orch.run_etl("src", "dst")
        analytics = orch.get_analytics()
        assert analytics["total_executions"] == 1
        assert analytics["successful"] == 1
        assert analytics["success_rate"] == 1.0

    def test_get_snapshot(self) -> None:
        orch = PipelineOrchestrator()
        orch.extractor.register_source(
            "src", SourceType.DATABASE,
        )
        orch.loader.register_target(
            "dst", SourceType.DATABASE,
        )
        orch.run_etl("src", "dst")
        snap = orch.get_snapshot()
        assert isinstance(snap, PipelineSnapshot)
        assert snap.completed == 1
        assert snap.total_records_processed > 0

    def test_scheduler_integration(self) -> None:
        orch = PipelineOrchestrator()
        job = orch.scheduler.schedule(
            "p1", JobFrequency.DAILY,
        )
        result = orch.scheduler.run_job(
            job["job_id"],
        )
        assert result["success"]

    def test_validator_integration(self) -> None:
        orch = PipelineOrchestrator()
        data = [
            {"name": "Ali", "age": 30},
            {"name": "Veli", "age": 25},
        ]
        quality = orch.validator.check_quality(data)
        assert quality["completeness"] == 1.0


# ============ Config ============


class TestPipelineConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import settings
        assert hasattr(settings, "pipeline_enabled")
        assert hasattr(settings, "max_parallel_jobs")
        assert hasattr(settings, "default_batch_size")
        assert hasattr(settings, "retry_attempts")
        assert hasattr(
            settings, "lineage_retention_days",
        )

    def test_config_values(self) -> None:
        from app.config import settings
        assert settings.pipeline_enabled is True
        assert settings.max_parallel_jobs == 5
        assert settings.default_batch_size == 100
        assert settings.retry_attempts == 3
        assert settings.lineage_retention_days == 90


# ============ Imports ============


class TestPipelineImports:
    """Import testleri."""

    def test_import_all(self) -> None:
        from app.core.pipeline import (
            DataExtractor,
            DataLoader,
            DataTransformer,
            DataValidator,
            LineageTracker,
            PipelineBuilder,
            PipelineJobScheduler,
            PipelineOrchestrator,
            StreamProcessor,
        )
        assert DataExtractor is not None
        assert DataLoader is not None
        assert DataTransformer is not None
        assert DataValidator is not None
        assert LineageTracker is not None
        assert PipelineBuilder is not None
        assert PipelineJobScheduler is not None
        assert PipelineOrchestrator is not None
        assert StreamProcessor is not None

    def test_import_models(self) -> None:
        from app.models.pipeline import (
            JobFrequency,
            LineageEntry,
            PipelineRecord,
            PipelineSnapshot,
            PipelineStatus,
            SourceType,
            StepRecord,
            StepType,
            ValidationLevel,
            WindowType,
        )
        assert SourceType is not None
        assert PipelineStatus is not None
        assert StepType is not None
        assert ValidationLevel is not None
        assert WindowType is not None
        assert JobFrequency is not None
        assert PipelineRecord is not None
        assert StepRecord is not None
        assert LineageEntry is not None
        assert PipelineSnapshot is not None
