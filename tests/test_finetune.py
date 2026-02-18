"""
Fine-Tuning & Custom Model Manager testleri.
"""

import pytest

from app.core.finetune.training_data_preparer import (
    TrainingDataPreparer,
)
from app.core.finetune.finetune_orchestrator import (
    FineTuneJobOrchestrator,
)
from app.core.finetune.ft_model_evaluator import (
    FTModelEvaluator,
)
from app.core.finetune.ft_model_version_manager import (
    FTModelVersionManager,
)
from app.core.finetune.dataset_curator import (
    DatasetCurator,
)
from app.core.finetune.ft_performance_benchmarker import (
    FTPerformanceBenchmarker,
)
from app.core.finetune.ft_model_deployer import (
    FTModelDeployer,
)
from app.core.finetune.ft_drift_monitor import (
    FTDriftMonitor,
)
from app.core.finetune.finetune_manager_orchestrator import (
    FineTuneManagerOrchestrator,
)
from app.models.finetune_models import (
    FTProvider,
    FTJobStatus,
    FTModelStage,
    FTDeployStrategy,
    FTDriftType,
    FTAlertSeverity,
    FTDataFormat,
    SamplingStrategy,
    AugmentationType,
    FTMetricType,
    TrainingDataset,
    FineTuneJob,
    FTHyperparameters,
    FTModelVersion,
    FTEvaluation,
    FTBenchmarkResult,
    FTDeployment,
    FTEndpoint,
    FTDriftAlert,
    FTSummary,
)


# ==========================================
# TrainingDataPreparer Testleri
# ==========================================


class TestTrainingDataPreparer:
    """TrainingDataPreparer testleri."""

    def setup_method(self):
        self.prep = TrainingDataPreparer()

    def test_init(self):
        assert self.prep.dataset_count == 0

    def test_create_dataset(self):
        r = self.prep.create_dataset(
            name="test_ds",
            format_type="chat",
        )
        assert r["created"] is True
        assert r["name"] == "test_ds"
        assert self.prep.dataset_count == 1

    def test_create_dataset_formats(self):
        for fmt in TrainingDataPreparer.FORMATS:
            r = self.prep.create_dataset(
                format_type=fmt
            )
            assert r["created"] is True

    def test_add_sample(self):
        ds = self.prep.create_dataset()
        r = self.prep.add_sample(
            dataset_id=ds["dataset_id"],
            input_text="hello",
            output_text="world",
        )
        assert r["added"] is True
        assert r["sample_index"] == 0

    def test_add_sample_quality_filter(self):
        ds = self.prep.create_dataset()
        r = self.prep.add_sample(
            dataset_id=ds["dataset_id"],
            input_text="hello",
            output_text="world",
            quality_score=0.1,
        )
        assert r["added"] is False
        assert r["reason"] == "low_quality"

    def test_add_sample_duplicate(self):
        ds = self.prep.create_dataset()
        self.prep.add_sample(
            dataset_id=ds["dataset_id"],
            input_text="hello",
            output_text="world",
        )
        r = self.prep.add_sample(
            dataset_id=ds["dataset_id"],
            input_text="hello",
            output_text="world",
        )
        assert r["added"] is False
        assert r["reason"] == "duplicate"

    def test_add_sample_invalid_dataset(self):
        r = self.prep.add_sample(
            dataset_id="invalid"
        )
        assert r["added"] is False

    def test_add_samples_bulk(self):
        ds = self.prep.create_dataset()
        r = self.prep.add_samples_bulk(
            dataset_id=ds["dataset_id"],
            samples=[
                {"input": "a", "output": "b"},
                {"input": "c", "output": "d"},
                {"input": "a", "output": "b"},
            ],
        )
        assert r["processed"] is True
        assert r["added"] == 2
        assert r["duplicates"] == 1

    def test_validate_dataset(self):
        ds = self.prep.create_dataset()
        r = self.prep.validate_dataset(
            dataset_id=ds["dataset_id"]
        )
        assert r["validated"] is True
        assert "too_few_samples" in r["issues"]

    def test_validate_dataset_with_data(self):
        ds = self.prep.create_dataset()
        for i in range(15):
            self.prep.add_sample(
                dataset_id=ds["dataset_id"],
                input_text=f"input_{i}",
                output_text=f"output_{i}",
            )
        r = self.prep.validate_dataset(
            dataset_id=ds["dataset_id"]
        )
        assert r["valid"] is True

    def test_split_dataset(self):
        ds = self.prep.create_dataset(
            validation_split=0.2
        )
        for i in range(10):
            self.prep.add_sample(
                dataset_id=ds["dataset_id"],
                input_text=f"in_{i}",
                output_text=f"out_{i}",
            )
        r = self.prep.split_dataset(
            dataset_id=ds["dataset_id"]
        )
        assert r["split"] is True
        assert r["total"] == 10

    def test_export_jsonl_chat(self):
        ds = self.prep.create_dataset(
            format_type="chat"
        )
        self.prep.add_sample(
            dataset_id=ds["dataset_id"],
            input_text="hello",
            output_text="hi",
            system_prompt="sys",
        )
        r = self.prep.export_jsonl(
            dataset_id=ds["dataset_id"]
        )
        assert r["exported"] is True
        assert '"messages"' in r["content"]

    def test_export_jsonl_completion(self):
        ds = self.prep.create_dataset(
            format_type="completion"
        )
        self.prep.add_sample(
            dataset_id=ds["dataset_id"],
            input_text="hello",
            output_text="hi",
        )
        r = self.prep.export_jsonl(
            dataset_id=ds["dataset_id"]
        )
        assert r["exported"] is True
        assert '"prompt"' in r["content"]

    def test_export_jsonl_instruction(self):
        ds = self.prep.create_dataset(
            format_type="instruction"
        )
        self.prep.add_sample(
            dataset_id=ds["dataset_id"],
            input_text="hello",
            output_text="hi",
        )
        r = self.prep.export_jsonl(
            dataset_id=ds["dataset_id"]
        )
        assert r["exported"] is True
        assert '"instruction"' in r["content"]

    def test_get_dataset_info(self):
        ds = self.prep.create_dataset(
            name="myds"
        )
        r = self.prep.get_dataset_info(
            dataset_id=ds["dataset_id"]
        )
        assert r["retrieved"] is True
        assert r["name"] == "myds"

    def test_get_summary(self):
        self.prep.create_dataset()
        r = self.prep.get_summary()
        assert r["retrieved"] is True
        assert r["total_datasets"] == 1


# ==========================================
# FineTuneJobOrchestrator Testleri
# ==========================================


class TestFineTuneJobOrchestrator:
    """FineTuneJobOrchestrator testleri."""

    def setup_method(self):
        self.orch = FineTuneJobOrchestrator()

    def test_init(self):
        assert self.orch.job_count == 0

    def test_create_job(self):
        r = self.orch.create_job(
            name="test_job",
            base_model="gpt-4",
        )
        assert r["created"] is True
        assert r["provider"] == "openai"

    def test_start_job(self):
        job = self.orch.create_job(
            name="j1"
        )
        r = self.orch.start_job(
            job_id=job["job_id"]
        )
        assert r["started"] is True
        assert r["status"] == "training"

    def test_start_job_invalid(self):
        r = self.orch.start_job(
            job_id="invalid"
        )
        assert r["started"] is False

    def test_start_job_max_concurrent(self):
        orch = FineTuneJobOrchestrator(
            max_concurrent=1
        )
        j1 = orch.create_job(name="j1")
        orch.start_job(job_id=j1["job_id"])
        j2 = orch.create_job(name="j2")
        r = orch.start_job(
            job_id=j2["job_id"]
        )
        assert r["started"] is False

    def test_update_progress(self):
        job = self.orch.create_job()
        self.orch.start_job(
            job_id=job["job_id"]
        )
        r = self.orch.update_progress(
            job_id=job["job_id"],
            progress=0.5,
            metrics={"loss": 0.3},
            log_message="halfway",
        )
        assert r["updated"] is True
        assert r["progress"] == 0.5

    def test_complete_job(self):
        job = self.orch.create_job()
        self.orch.start_job(
            job_id=job["job_id"]
        )
        r = self.orch.complete_job(
            job_id=job["job_id"],
            model_id="ft_model_1",
            actual_cost=1.5,
        )
        assert r["completed"] is True
        assert r["model_id"] == "ft_model_1"

    def test_cancel_job(self):
        job = self.orch.create_job()
        r = self.orch.cancel_job(
            job_id=job["job_id"],
            reason="test",
        )
        assert r["cancelled"] is True

    def test_cancel_completed_job(self):
        job = self.orch.create_job()
        self.orch.start_job(
            job_id=job["job_id"]
        )
        self.orch.complete_job(
            job_id=job["job_id"]
        )
        r = self.orch.cancel_job(
            job_id=job["job_id"]
        )
        assert r["cancelled"] is False

    def test_estimate_cost(self):
        r = self.orch.estimate_cost(
            dataset_size=100,
            epochs=3,
        )
        assert r["estimated"] is True
        assert r["estimated_cost"] > 0

    def test_get_job_info(self):
        job = self.orch.create_job(
            name="info_test"
        )
        r = self.orch.get_job_info(
            job_id=job["job_id"]
        )
        assert r["retrieved"] is True
        assert r["name"] == "info_test"

    def test_get_summary(self):
        self.orch.create_job()
        r = self.orch.get_summary()
        assert r["retrieved"] is True
        assert r["total_jobs"] == 1


# ==========================================
# FTModelEvaluator Testleri
# ==========================================


class TestFTModelEvaluator:
    """FTModelEvaluator testleri."""

    def setup_method(self):
        self.eval = FTModelEvaluator()

    def test_init(self):
        assert self.eval.evaluation_count == 0

    def test_evaluate_model(self):
        r = self.eval.evaluate_model(
            model_id="m1",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
                {
                    "predicted": "b",
                    "expected": "b",
                    "f1": 0.8,
                },
            ],
        )
        assert r["evaluated"] is True
        assert r["passed"] is True

    def test_evaluate_model_fail(self):
        ev = FTModelEvaluator(
            pass_threshold=0.9
        )
        r = ev.evaluate_model(
            model_id="m1",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "b",
                    "f1": 0.3,
                },
            ],
        )
        assert r["passed"] is False

    def test_evaluate_empty(self):
        r = self.eval.evaluate_model(
            model_id="m1"
        )
        assert r["evaluated"] is True

    def test_run_benchmark(self):
        r = self.eval.run_benchmark(
            model_id="m1",
            benchmark_name="basic",
            test_cases=[
                {"score": 0.8, "latency_ms": 50},
                {"score": 0.9, "latency_ms": 60},
            ],
        )
        assert r["completed"] is True
        assert r["avg_score"] > 0

    def test_compare_models(self):
        self.eval.evaluate_model(
            model_id="m1",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
            ],
        )
        self.eval.evaluate_model(
            model_id="m2",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "b",
                    "f1": 0.5,
                },
            ],
        )
        r = self.eval.compare_models(
            model_ids=["m1", "m2"]
        )
        assert r["compared"] is True
        assert r["best_model"] == "m1"

    def test_detect_regression(self):
        e1 = self.eval.evaluate_model(
            model_id="m1",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
            ],
            metrics=["accuracy", "f1"],
        )
        e2 = self.eval.evaluate_model(
            model_id="m1",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "b",
                    "f1": 0.3,
                },
            ],
            metrics=["accuracy", "f1"],
        )
        r = self.eval.detect_regression(
            model_id="m1",
            baseline_eval_id=e1["eval_id"],
            new_eval_id=e2["eval_id"],
        )
        assert r["detected"] is True
        assert r["regression_found"] is True

    def test_detect_regression_none(self):
        e1 = self.eval.evaluate_model(
            model_id="m1",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
            ],
        )
        e2 = self.eval.evaluate_model(
            model_id="m1",
            test_dataset=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
            ],
        )
        r = self.eval.detect_regression(
            model_id="m1",
            baseline_eval_id=e1["eval_id"],
            new_eval_id=e2["eval_id"],
        )
        assert r["regression_found"] is False

    def test_get_eval_info(self):
        ev = self.eval.evaluate_model(
            model_id="m1"
        )
        r = self.eval.get_eval_info(
            eval_id=ev["eval_id"]
        )
        assert r["retrieved"] is True

    def test_get_summary(self):
        self.eval.evaluate_model(
            model_id="m1"
        )
        r = self.eval.get_summary()
        assert r["retrieved"] is True
        assert r["total_evaluations"] == 1


# ==========================================
# FTModelVersionManager Testleri
# ==========================================


class TestFTModelVersionManager:
    """FTModelVersionManager testleri."""

    def setup_method(self):
        self.vm = FTModelVersionManager()

    def test_init(self):
        assert self.vm.model_count == 0

    def test_register_model(self):
        r = self.vm.register_model(
            name="my_model",
            base_model="gpt-4",
        )
        assert r["registered"] is True
        assert self.vm.model_count == 1

    def test_create_version(self):
        m = self.vm.register_model(
            name="m1"
        )
        r = self.vm.create_version(
            model_id=m["model_id"],
            job_id="j1",
        )
        assert r["created"] is True
        assert r["version"] == 1

    def test_create_multiple_versions(self):
        m = self.vm.register_model(
            name="m1"
        )
        self.vm.create_version(
            model_id=m["model_id"]
        )
        r = self.vm.create_version(
            model_id=m["model_id"]
        )
        assert r["version"] == 2

    def test_promote_version(self):
        m = self.vm.register_model(
            name="m1"
        )
        v = self.vm.create_version(
            model_id=m["model_id"]
        )
        r = self.vm.promote_version(
            version_id=v["version_id"],
            target_stage="staging",
        )
        assert r["promoted"] is True
        assert r["new_stage"] == "staging"

    def test_promote_invalid_stage(self):
        m = self.vm.register_model(
            name="m1"
        )
        v = self.vm.create_version(
            model_id=m["model_id"]
        )
        r = self.vm.promote_version(
            version_id=v["version_id"],
            target_stage="invalid",
        )
        assert r["promoted"] is False

    def test_archive_version(self):
        m = self.vm.register_model(
            name="m1"
        )
        v = self.vm.create_version(
            model_id=m["model_id"]
        )
        r = self.vm.archive_version(
            version_id=v["version_id"],
            reason="old",
        )
        assert r["archived"] is True

    def test_get_lineage(self):
        m = self.vm.register_model(
            name="m1"
        )
        self.vm.create_version(
            model_id=m["model_id"],
            job_id="j1",
        )
        r = self.vm.get_lineage(
            model_id=m["model_id"]
        )
        assert r["retrieved"] is True
        assert len(r["lineage"]) == 1

    def test_version_retention(self):
        vm = FTModelVersionManager(
            version_retention=2
        )
        m = vm.register_model(name="m1")
        for _ in range(5):
            vm.create_version(
                model_id=m["model_id"]
            )
        assert vm.model_count == 1

    def test_get_version_info(self):
        m = self.vm.register_model(
            name="m1"
        )
        v = self.vm.create_version(
            model_id=m["model_id"]
        )
        r = self.vm.get_version_info(
            version_id=v["version_id"]
        )
        assert r["retrieved"] is True

    def test_get_summary(self):
        m = self.vm.register_model(
            name="m1"
        )
        self.vm.create_version(
            model_id=m["model_id"]
        )
        r = self.vm.get_summary()
        assert r["retrieved"] is True
        assert r["total_models"] == 1
        assert r["total_versions"] == 1


# ==========================================
# DatasetCurator Testleri
# ==========================================


class TestDatasetCurator:
    """DatasetCurator testleri."""

    def setup_method(self):
        self.cur = DatasetCurator()

    def test_init(self):
        assert self.cur.dataset_count == 0

    def test_create_dataset(self):
        r = self.cur.create_dataset(
            name="ds1",
            task_type="classification",
        )
        assert r["created"] is True

    def test_add_samples(self):
        ds = self.cur.create_dataset()
        r = self.cur.add_samples(
            dataset_id=ds["dataset_id"],
            samples=[
                {"input": "a", "output": "b"},
                {"input": "c", "output": "d"},
            ],
        )
        assert r["success"] is True
        assert r["added"] == 2

    def test_annotate_sample(self):
        ds = self.cur.create_dataset()
        self.cur.add_samples(
            dataset_id=ds["dataset_id"],
            samples=[
                {"input": "a", "output": "b"},
            ],
        )
        r = self.cur.annotate_sample(
            dataset_id=ds["dataset_id"],
            sample_index=0,
            label="positive",
            annotator="user1",
        )
        assert r["annotated"] is True

    def test_annotate_invalid_index(self):
        ds = self.cur.create_dataset()
        r = self.cur.annotate_sample(
            dataset_id=ds["dataset_id"],
            sample_index=99,
        )
        assert r["annotated"] is False

    def test_score_quality(self):
        ds = self.cur.create_dataset()
        self.cur.add_samples(
            dataset_id=ds["dataset_id"],
            samples=[
                {
                    "input": "long input text here",
                    "output": "long output text here",
                },
            ],
        )
        r = self.cur.score_quality(
            dataset_id=ds["dataset_id"]
        )
        assert r["scored"] is True
        assert r["avg_quality"] > 0

    def test_augment_dataset(self):
        ds = self.cur.create_dataset()
        self.cur.add_samples(
            dataset_id=ds["dataset_id"],
            samples=[
                {"input": "a", "output": "b"},
            ],
        )
        r = self.cur.augment_dataset(
            dataset_id=ds["dataset_id"],
            augmentation_type="paraphrase",
            count=3,
        )
        assert r["augmented"] is True
        assert r["added"] == 1

    def test_augment_invalid_type(self):
        ds = self.cur.create_dataset()
        r = self.cur.augment_dataset(
            dataset_id=ds["dataset_id"],
            augmentation_type="invalid",
        )
        assert r["augmented"] is False

    def test_sample_dataset_random(self):
        ds = self.cur.create_dataset()
        self.cur.add_samples(
            dataset_id=ds["dataset_id"],
            samples=[
                {"input": f"i{i}", "output": f"o{i}"}
                for i in range(10)
            ],
        )
        r = self.cur.sample_dataset(
            dataset_id=ds["dataset_id"],
            count=3,
            strategy="random",
        )
        assert r["sampled"] is True
        assert r["count"] == 3

    def test_sample_dataset_quality(self):
        ds = self.cur.create_dataset()
        self.cur.add_samples(
            dataset_id=ds["dataset_id"],
            samples=[
                {
                    "input": f"i{i}",
                    "output": f"o{i}",
                    "quality": float(i) / 10,
                }
                for i in range(10)
            ],
        )
        r = self.cur.sample_dataset(
            dataset_id=ds["dataset_id"],
            count=3,
            strategy="quality_weighted",
        )
        assert r["sampled"] is True

    def test_get_dataset_info(self):
        ds = self.cur.create_dataset(
            name="info_ds"
        )
        r = self.cur.get_dataset_info(
            dataset_id=ds["dataset_id"]
        )
        assert r["retrieved"] is True
        assert r["name"] == "info_ds"

    def test_get_summary(self):
        self.cur.create_dataset()
        r = self.cur.get_summary()
        assert r["retrieved"] is True
        assert r["total_datasets"] == 1


# ==========================================
# FTPerformanceBenchmarker Testleri
# ==========================================


class TestFTPerformanceBenchmarker:
    """FTPerformanceBenchmarker testleri."""

    def setup_method(self):
        self.bench = FTPerformanceBenchmarker()

    def test_init(self):
        assert self.bench.suite_count == 0

    def test_create_suite(self):
        r = self.bench.create_suite(
            name="basic_suite",
            metrics=["accuracy", "latency"],
        )
        assert r["created"] is True

    def test_run_benchmark(self):
        s = self.bench.create_suite(
            name="s1",
            metrics=["accuracy"],
        )
        r = self.bench.run_benchmark(
            suite_id=s["suite_id"],
            model_id="m1",
            results=[
                {"accuracy": 0.9},
                {"accuracy": 0.85},
            ],
        )
        assert r["completed"] is True
        assert r["metrics"]["accuracy"] > 0

    def test_set_baseline(self):
        s = self.bench.create_suite(
            name="s1"
        )
        run = self.bench.run_benchmark(
            suite_id=s["suite_id"],
            model_id="m1",
            results=[{"accuracy": 0.9}],
        )
        r = self.bench.set_baseline(
            suite_id=s["suite_id"],
            run_id=run["run_id"],
        )
        assert r["set"] is True

    def test_compare_to_baseline(self):
        s = self.bench.create_suite(
            name="s1",
            metrics=["accuracy"],
        )
        r1 = self.bench.run_benchmark(
            suite_id=s["suite_id"],
            model_id="m1",
            results=[{"accuracy": 0.8}],
        )
        self.bench.set_baseline(
            suite_id=s["suite_id"],
            run_id=r1["run_id"],
        )
        r2 = self.bench.run_benchmark(
            suite_id=s["suite_id"],
            model_id="m2",
            results=[{"accuracy": 0.9}],
        )
        r = self.bench.compare_to_baseline(
            suite_id=s["suite_id"],
            run_id=r2["run_id"],
        )
        assert r["compared"] is True
        assert r["improved_count"] >= 1

    def test_generate_report(self):
        s = self.bench.create_suite(
            name="s1",
            metrics=["accuracy"],
        )
        self.bench.run_benchmark(
            suite_id=s["suite_id"],
            model_id="m1",
            results=[{"accuracy": 0.8}],
        )
        self.bench.run_benchmark(
            suite_id=s["suite_id"],
            model_id="m1",
            results=[{"accuracy": 0.85}],
        )
        r = self.bench.generate_report(
            suite_id=s["suite_id"]
        )
        assert r["generated"] is True
        assert r["total_runs"] == 2

    def test_analyze_trends(self):
        s = self.bench.create_suite(
            name="s1",
            metrics=["accuracy"],
        )
        for i in range(3):
            self.bench.run_benchmark(
                suite_id=s["suite_id"],
                model_id="m1",
                results=[
                    {"accuracy": 0.8 + i * 0.05}
                ],
            )
        r = self.bench.analyze_trends(
            model_id="m1"
        )
        assert r["analyzed"] is True
        assert r["runs"] == 3

    def test_get_summary(self):
        self.bench.create_suite(name="s1")
        r = self.bench.get_summary()
        assert r["retrieved"] is True
        assert r["total_suites"] == 1


# ==========================================
# FTModelDeployer Testleri
# ==========================================


class TestFTModelDeployer:
    """FTModelDeployer testleri."""

    def setup_method(self):
        self.dep = FTModelDeployer()

    def test_init(self):
        assert self.dep.deployment_count == 0

    def test_create_endpoint(self):
        r = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        assert r["created"] is True

    def test_deploy_model_immediate(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        r = self.dep.deploy_model(
            endpoint_id=ep["endpoint_id"],
            model_id="m2",
            version_id="v2",
            strategy="immediate",
        )
        assert r["deployed"] is True
        assert r["status"] == "completed"

    def test_deploy_model_canary(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        r = self.dep.deploy_model(
            endpoint_id=ep["endpoint_id"],
            model_id="m2",
            version_id="v2",
            strategy="canary",
        )
        assert r["deployed"] is True
        assert r["status"] == "canary"

    def test_deploy_model_blue_green(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        r = self.dep.deploy_model(
            endpoint_id=ep["endpoint_id"],
            model_id="m2",
            version_id="v2",
            strategy="blue_green",
        )
        assert r["status"] == "staged"

    def test_promote_deployment(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        dep = self.dep.deploy_model(
            endpoint_id=ep["endpoint_id"],
            model_id="m2",
            version_id="v2",
            strategy="canary",
        )
        r = self.dep.promote_deployment(
            deployment_id=dep[
                "deployment_id"
            ]
        )
        assert r["promoted"] is True
        assert r["traffic_pct"] == 1.0

    def test_rollback(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        dep = self.dep.deploy_model(
            endpoint_id=ep["endpoint_id"],
            model_id="m2",
            version_id="v2",
            strategy="immediate",
        )
        r = self.dep.rollback(
            deployment_id=dep[
                "deployment_id"
            ],
            reason="bad_perf",
        )
        assert r["rolled_back"] is True

    def test_check_health_healthy(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        r = self.dep.check_health(
            endpoint_id=ep["endpoint_id"]
        )
        assert r["checked"] is True
        assert r["health"] == "healthy"

    def test_check_health_unhealthy(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        self.dep.update_traffic(
            endpoint_id=ep["endpoint_id"],
            requests=100,
            errors=20,
        )
        r = self.dep.check_health(
            endpoint_id=ep["endpoint_id"]
        )
        assert r["health"] == "unhealthy"

    def test_update_traffic(self):
        ep = self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        r = self.dep.update_traffic(
            endpoint_id=ep["endpoint_id"],
            requests=10,
            latency_ms=50.0,
        )
        assert r["updated"] is True

    def test_get_summary(self):
        self.dep.create_endpoint(
            name="ep1",
            model_id="m1",
            version_id="v1",
        )
        r = self.dep.get_summary()
        assert r["retrieved"] is True
        assert r["active_endpoints"] == 1


# ==========================================
# FTDriftMonitor Testleri
# ==========================================


class TestFTDriftMonitor:
    """FTDriftMonitor testleri."""

    def setup_method(self):
        self.dm = FTDriftMonitor()

    def test_init(self):
        assert self.dm.monitor_count == 0

    def test_create_monitor(self):
        r = self.dm.create_monitor(
            model_id="m1",
            endpoint_id="ep1",
        )
        assert r["created"] is True
        assert r["status"] == "active"

    def test_set_baseline(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        r = self.dm.set_baseline(
            monitor_id=mon["monitor_id"],
            metrics={
                "accuracy": 0.9,
                "latency": 100,
            },
        )
        assert r["set"] is True

    def test_record_snapshot(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        r = self.dm.record_snapshot(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.85},
        )
        assert r["recorded"] is True

    def test_detect_drift(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        self.dm.set_baseline(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.9},
        )
        self.dm.record_snapshot(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.7},
        )
        r = self.dm.detect_drift(
            monitor_id=mon["monitor_id"]
        )
        assert r["detected"] is True
        assert r["drift_found"] is True
        assert r["total_drifts"] > 0

    def test_detect_no_drift(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        self.dm.set_baseline(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.9},
        )
        self.dm.record_snapshot(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.89},
        )
        r = self.dm.detect_drift(
            monitor_id=mon["monitor_id"]
        )
        assert r["drift_found"] is False

    def test_detect_drift_no_baseline(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        r = self.dm.detect_drift(
            monitor_id=mon["monitor_id"]
        )
        assert r["drift_found"] is False

    def test_generate_alert(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        r = self.dm.generate_alert(
            monitor_id=mon["monitor_id"],
            drift_info={
                "metric": "accuracy",
                "change_pct": 25.0,
                "severity": "critical",
            },
        )
        assert r["generated"] is True
        assert r["severity"] == "critical"

    def test_should_retrain_yes(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        self.dm.set_baseline(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.9},
        )
        self.dm.record_snapshot(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.6},
        )
        r = self.dm.should_retrain(
            monitor_id=mon["monitor_id"]
        )
        assert r["checked"] is True
        assert r["should_retrain"] is True

    def test_should_retrain_no(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        self.dm.set_baseline(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.9},
        )
        self.dm.record_snapshot(
            monitor_id=mon["monitor_id"],
            metrics={"accuracy": 0.88},
        )
        r = self.dm.should_retrain(
            monitor_id=mon["monitor_id"]
        )
        assert r["should_retrain"] is False

    def test_get_drift_history(self):
        mon = self.dm.create_monitor(
            model_id="m1"
        )
        r = self.dm.get_drift_history(
            monitor_id=mon["monitor_id"]
        )
        assert r["retrieved"] is True
        assert r["total_events"] == 0

    def test_get_summary(self):
        self.dm.create_monitor(
            model_id="m1"
        )
        r = self.dm.get_summary()
        assert r["retrieved"] is True
        assert r["active_monitors"] == 1


# ==========================================
# FineTuneManagerOrchestrator Testleri
# ==========================================


class TestFineTuneManagerOrchestrator:
    """FineTuneManagerOrchestrator testleri."""

    def setup_method(self):
        self.mgr = (
            FineTuneManagerOrchestrator()
        )

    def test_init(self):
        s = self.mgr.get_summary()
        assert s["retrieved"] is True
        assert s["datasets"] == 0

    def test_prepare_and_train(self):
        r = self.mgr.prepare_and_train(
            name="test_ft",
            base_model="gpt-4",
            samples=[
                {
                    "input": f"in_{i}",
                    "output": f"out_{i}",
                }
                for i in range(5)
            ],
        )
        assert r["success"] is True
        assert "job_id" in r
        assert "dataset_id" in r

    def test_prepare_and_train_empty(self):
        r = self.mgr.prepare_and_train(
            name="empty_ft",
            base_model="gpt-4",
        )
        assert r["success"] is True

    def test_evaluate_and_version(self):
        r = self.mgr.evaluate_and_version(
            job_id="j1",
            model_id="m1",
            model_name="test_model",
            test_data=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
            ],
            base_model="gpt-4",
        )
        assert r["success"] is True
        assert "model_id" in r
        assert "version_id" in r

    def test_deploy_and_monitor(self):
        ev = self.mgr.evaluate_and_version(
            job_id="j1",
            model_id="m1",
            model_name="test_model",
            base_model="gpt-4",
        )
        r = self.mgr.deploy_and_monitor(
            model_id=ev["model_id"],
            version_id=ev["version_id"],
            endpoint_name="ep_test",
        )
        assert r["success"] is True
        assert "endpoint_id" in r
        assert "deployment_id" in r

    def test_full_pipeline(self):
        r = self.mgr.full_pipeline(
            name="full_test",
            base_model="gpt-4",
            train_samples=[
                {
                    "input": f"train_{i}",
                    "output": f"out_{i}",
                }
                for i in range(5)
            ],
            test_samples=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
            ],
        )
        assert r["success"] is True
        assert "prepare_train" in r["steps"]
        assert (
            "evaluate_version" in r["steps"]
        )

    def test_full_pipeline_with_deploy(self):
        r = self.mgr.full_pipeline(
            name="deploy_test",
            base_model="gpt-4",
            train_samples=[
                {
                    "input": f"t_{i}",
                    "output": f"o_{i}",
                }
                for i in range(5)
            ],
            test_samples=[
                {
                    "predicted": "a",
                    "expected": "a",
                    "f1": 0.9,
                },
            ],
            deploy=True,
        )
        assert r["success"] is True

    def test_get_analytics(self):
        r = self.mgr.get_analytics()
        assert r["retrieved"] is True
        assert "data_preparer" in r
        assert "jobs" in r

    def test_get_summary(self):
        r = self.mgr.get_summary()
        assert r["retrieved"] is True
        assert "auto_evaluate" in r


# ==========================================
# Model Testleri
# ==========================================


class TestFineTuneModels:
    """Fine-tune model testleri."""

    def test_ft_provider_enum(self):
        assert FTProvider.OPENAI == "openai"
        assert len(FTProvider) == 5

    def test_ft_job_status_enum(self):
        assert (
            FTJobStatus.TRAINING
            == "training"
        )
        assert len(FTJobStatus) == 6

    def test_ft_model_stage_enum(self):
        assert (
            FTModelStage.PRODUCTION
            == "production"
        )
        assert len(FTModelStage) == 5

    def test_ft_deploy_strategy_enum(self):
        assert (
            FTDeployStrategy.CANARY
            == "canary"
        )
        assert len(FTDeployStrategy) == 4

    def test_ft_drift_type_enum(self):
        assert (
            FTDriftType.DATA_DRIFT
            == "data_drift"
        )
        assert len(FTDriftType) == 4

    def test_ft_alert_severity_enum(self):
        assert (
            FTAlertSeverity.CRITICAL
            == "critical"
        )
        assert len(FTAlertSeverity) == 3

    def test_ft_data_format_enum(self):
        assert FTDataFormat.CHAT == "chat"
        assert len(FTDataFormat) == 4

    def test_sampling_strategy_enum(self):
        assert (
            SamplingStrategy.RANDOM
            == "random"
        )
        assert len(SamplingStrategy) == 5

    def test_augmentation_type_enum(self):
        assert (
            AugmentationType.PARAPHRASE
            == "paraphrase"
        )
        assert len(AugmentationType) == 5

    def test_ft_metric_type_enum(self):
        assert (
            FTMetricType.ACCURACY
            == "accuracy"
        )
        assert len(FTMetricType) == 6

    def test_training_dataset_model(self):
        td = TrainingDataset(
            name="test",
            total_samples=100,
        )
        assert td.name == "test"
        assert td.format_type == "chat"

    def test_finetune_job_model(self):
        j = FineTuneJob(
            name="j1",
            base_model="gpt-4",
        )
        assert j.status == "created"
        assert j.progress == 0.0

    def test_hyperparameters_model(self):
        hp = FTHyperparameters()
        assert hp.epochs == 3
        assert hp.batch_size == 4

    def test_model_version_model(self):
        v = FTModelVersion(version=2)
        assert v.version == 2
        assert v.stage == "development"

    def test_evaluation_model(self):
        ev = FTEvaluation(
            passed=True,
            avg_quality=0.85,
        )
        assert ev.passed is True

    def test_benchmark_result_model(self):
        br = FTBenchmarkResult(
            avg_score=0.9
        )
        assert br.avg_score == 0.9

    def test_deployment_model(self):
        d = FTDeployment(
            strategy="canary"
        )
        assert d.strategy == "canary"

    def test_endpoint_model(self):
        ep = FTEndpoint(name="ep1")
        assert ep.status == "active"
        assert ep.health == "healthy"

    def test_drift_alert_model(self):
        da = FTDriftAlert(
            severity="critical"
        )
        assert da.severity == "critical"

    def test_summary_model(self):
        s = FTSummary(
            datasets=5, jobs=3
        )
        assert s.datasets == 5
        assert s.jobs == 3


# ==========================================
# Config Testleri
# ==========================================


class TestFineTuneConfig:
    """Fine-tune config testleri."""

    def test_config_defaults(self):
        from app.config import Settings

        s = Settings()
        assert s.finetune_enabled is True
        assert (
            s.finetune_default_provider
            == "openai"
        )
        assert (
            s.finetune_auto_evaluate is True
        )
        assert (
            s.finetune_drift_monitoring
            is True
        )
        assert (
            s.finetune_version_retention
            == 10
        )
