"""ATLAS ML Pipeline testleri."""

import unittest

from app.models.mlpipeline import (
    DriftRecord,
    DriftType,
    ExperimentRecord,
    ExperimentStatus,
    MetricType,
    MLPipelineSnapshot,
    ModelRecord,
    ModelStatus,
    PipelineStage,
    ScalingMethod,
)
from app.core.mlpipeline.data_preprocessor import (
    DataPreprocessor,
)
from app.core.mlpipeline.feature_engineer import (
    FeatureEngineer,
)
from app.core.mlpipeline.model_trainer import (
    ModelTrainer,
)
from app.core.mlpipeline.model_evaluator import (
    ModelEvaluator,
)
from app.core.mlpipeline.model_registry import (
    ModelRegistry,
)
from app.core.mlpipeline.model_server import (
    ModelServer,
)
from app.core.mlpipeline.experiment_tracker import (
    ExperimentTracker,
)
from app.core.mlpipeline.drift_detector import (
    DriftDetector,
)
from app.core.mlpipeline.ml_orchestrator import (
    MLOrchestrator,
)


# ── Models ──────────────────────────────────────


class TestModels(unittest.TestCase):
    def test_scaling_method_values(self):
        assert ScalingMethod.STANDARD == "standard"
        assert ScalingMethod.MINMAX == "minmax"
        assert ScalingMethod.ROBUST == "robust"
        assert ScalingMethod.LOG == "log"

    def test_model_status_values(self):
        assert ModelStatus.DRAFT == "draft"
        assert ModelStatus.TRAINING == "training"
        assert ModelStatus.DEPLOYED == "deployed"
        assert ModelStatus.RETIRED == "retired"

    def test_drift_type_values(self):
        assert DriftType.DATA == "data"
        assert DriftType.CONCEPT == "concept"
        assert DriftType.FEATURE == "feature"
        assert DriftType.COVARIATE == "covariate"

    def test_metric_type_values(self):
        assert MetricType.ACCURACY == "accuracy"
        assert MetricType.AUC == "auc"
        assert MetricType.MSE == "mse"

    def test_experiment_status_values(self):
        assert ExperimentStatus.PENDING == "pending"
        assert ExperimentStatus.RUNNING == "running"
        assert ExperimentStatus.COMPLETED == "completed"

    def test_pipeline_stage_values(self):
        assert PipelineStage.PREPROCESSING == "preprocessing"
        assert PipelineStage.TRAINING == "training"
        assert PipelineStage.DEPLOYMENT == "deployment"

    def test_model_record(self):
        r = ModelRecord(name="test_model", version="1.0")
        assert r.name == "test_model"
        assert r.version == "1.0"
        assert r.status == ModelStatus.DRAFT
        assert len(r.model_id) == 8

    def test_experiment_record(self):
        r = ExperimentRecord(name="exp1")
        assert r.name == "exp1"
        assert r.status == ExperimentStatus.PENDING
        assert r.runs == 0

    def test_drift_record(self):
        r = DriftRecord(feature="age", score=0.1, detected=True)
        assert r.feature == "age"
        assert r.score == 0.1
        assert r.detected is True
        assert r.drift_type == DriftType.DATA

    def test_mlpipeline_snapshot(self):
        s = MLPipelineSnapshot(total_models=5, deployed_models=2)
        assert s.total_models == 5
        assert s.deployed_models == 2
        assert s.pipeline_stage == PipelineStage.PREPROCESSING


# ── DataPreprocessor ────────────────────────────


class TestDataPreprocessor(unittest.TestCase):
    def test_init(self):
        dp = DataPreprocessor()
        assert dp.scaler_count == 0
        assert dp.encoder_count == 0

    def test_fit_scaler_standard(self):
        dp = DataPreprocessor()
        r = dp.fit_scaler("age", [10, 20, 30, 40, 50], "standard")
        assert r["feature"] == "age"
        assert r["method"] == "standard"
        assert dp.scaler_count == 1

    def test_fit_scaler_minmax(self):
        dp = DataPreprocessor()
        dp.fit_scaler("price", [100, 200, 300], "minmax")
        result = dp.transform("price", [100, 200, 300])
        assert result[0] == 0.0
        assert result[-1] == 1.0

    def test_fit_scaler_robust(self):
        dp = DataPreprocessor()
        dp.fit_scaler("val", [1, 2, 3, 4, 5, 6, 7, 8], "robust")
        result = dp.transform("val", [3])
        assert isinstance(result[0], float)

    def test_fit_scaler_maxabs(self):
        dp = DataPreprocessor()
        dp.fit_scaler("x", [-5, 0, 5, 10], "maxabs")
        result = dp.transform("x", [10])
        assert result[0] == 1.0

    def test_fit_scaler_log(self):
        dp = DataPreprocessor()
        dp.fit_scaler("y", [1, 2, 3], "log")
        result = dp.transform("y", [1, 2, 3])
        assert len(result) == 3

    def test_fit_scaler_empty(self):
        dp = DataPreprocessor()
        r = dp.fit_scaler("x", [])
        assert r.get("error") == "empty"

    def test_transform_no_scaler(self):
        dp = DataPreprocessor()
        result = dp.transform("unknown", [1, 2, 3])
        assert result == [1, 2, 3]

    def test_transform_standard(self):
        dp = DataPreprocessor()
        dp.fit_scaler("f", [0, 10], "standard")
        result = dp.transform("f", [5])
        assert isinstance(result[0], float)

    def test_handle_missing_mean(self):
        dp = DataPreprocessor()
        r = dp.handle_missing("f", [1.0, None, 3.0], "mean")
        assert len(r) == 3
        assert r[1] == 2.0

    def test_handle_missing_median(self):
        dp = DataPreprocessor()
        r = dp.handle_missing("f", [1.0, None, 3.0, 5.0], "median")
        assert r[1] == 3.0

    def test_handle_missing_zero(self):
        dp = DataPreprocessor()
        r = dp.handle_missing("f", [1.0, None], "zero")
        assert r[1] == 0.0

    def test_handle_missing_drop(self):
        dp = DataPreprocessor()
        r = dp.handle_missing("f", [1.0, None, 3.0], "drop")
        assert len(r) == 2

    def test_handle_missing_all_none(self):
        dp = DataPreprocessor()
        r = dp.handle_missing("f", [None, None])
        assert r == [0.0, 0.0]

    def test_encode_label(self):
        dp = DataPreprocessor()
        r = dp.encode_categorical("color", ["red", "blue", "red"], "label")
        assert len(r) == 3
        assert dp.encoder_count == 1

    def test_encode_onehot(self):
        dp = DataPreprocessor()
        r = dp.encode_categorical("color", ["red", "blue"], "onehot")
        assert len(r) == 2
        assert isinstance(r[0], list)

    def test_select_features(self):
        dp = DataPreprocessor()
        features = {
            "a": [1, 2, 3, 4],
            "b": [4, 3, 2, 1],
            "c": [1, 1, 1, 1],
        }
        target = [1, 2, 3, 4]
        r = dp.select_features(features, target, top_k=2)
        assert len(r) <= 2
        assert dp.history_count >= 1

    def test_get_stats(self):
        dp = DataPreprocessor()
        dp.fit_scaler("x", [1, 2, 3])
        s = dp.get_stats("x")
        assert s is not None
        assert "mean" in s

    def test_get_stats_not_found(self):
        dp = DataPreprocessor()
        assert dp.get_stats("nope") is None

    def test_selected_features_property(self):
        dp = DataPreprocessor()
        assert dp.selected_features == []


# ── FeatureEngineer ─────────────────────────────


class TestFeatureEngineer(unittest.TestCase):
    def test_init(self):
        fe = FeatureEngineer()
        assert fe.feature_count == 0
        assert fe.transformation_count == 0

    def test_extract_statistical(self):
        fe = FeatureEngineer()
        r = fe.extract_statistical("price", [10, 20, 30, 40, 50])
        assert "price_mean" in r
        assert "price_std" in r
        assert "price_min" in r
        assert "price_max" in r
        assert fe.feature_count >= 6

    def test_extract_statistical_empty(self):
        fe = FeatureEngineer()
        r = fe.extract_statistical("x", [])
        assert r == {}

    def test_polynomial_features(self):
        fe = FeatureEngineer()
        r = fe.polynomial_features("x", [1, 2, 3], degree=3)
        assert "x_pow2" in r
        assert "x_pow3" in r
        assert r["x_pow2"] == [1, 4, 9]

    def test_interaction_features(self):
        fe = FeatureEngineer()
        r = fe.interaction_features("a", [1, 2, 3], "b", [4, 5, 6])
        assert "a_x_b" in r
        assert "a_plus_b" in r
        assert "a_div_b" in r
        assert r["a_x_b"] == [4, 10, 18]

    def test_interaction_division_by_zero(self):
        fe = FeatureEngineer()
        r = fe.interaction_features("a", [1], "b", [0])
        assert r["a_div_b"] == [0.0]

    def test_time_features(self):
        fe = FeatureEngineer()
        r = fe.time_features("ts", [100, 200, 350])
        assert "ts_delta" in r
        assert "ts_ma" in r
        assert "ts_cumsum" in r
        assert r["ts_delta"][0] == 0.0

    def test_time_features_empty(self):
        fe = FeatureEngineer()
        r = fe.time_features("ts", [])
        assert r == {}

    def test_apply_transform_log(self):
        fe = FeatureEngineer()
        r = fe.apply_transform("x", [1, 2, 3], "log")
        assert len(r) == 3
        assert fe.transformation_count == 1

    def test_apply_transform_sqrt(self):
        fe = FeatureEngineer()
        r = fe.apply_transform("x", [4, 9, 16], "sqrt")
        assert r[0] == 2.0
        assert r[1] == 3.0

    def test_apply_transform_square(self):
        fe = FeatureEngineer()
        r = fe.apply_transform("x", [2, 3], "square")
        assert r == [4, 9]

    def test_apply_transform_reciprocal(self):
        fe = FeatureEngineer()
        r = fe.apply_transform("x", [2, 0], "reciprocal")
        assert r[0] == 0.5
        assert r[1] == 0.0

    def test_apply_transform_abs(self):
        fe = FeatureEngineer()
        r = fe.apply_transform("x", [-1, 2, -3], "abs")
        assert r == [1, 2, 3]

    def test_get_generated(self):
        fe = FeatureEngineer()
        fe.apply_transform("x", [1, 2], "square")
        gen = fe.get_generated()
        assert "x_square" in gen

    def test_get_feature(self):
        fe = FeatureEngineer()
        fe.apply_transform("x", [1, 2], "abs")
        assert fe.get_feature("x_abs") == [1, 2]
        assert fe.get_feature("nope") is None

    def test_history_count(self):
        fe = FeatureEngineer()
        fe.extract_statistical("x", [1, 2])
        fe.polynomial_features("y", [1], degree=2)
        assert fe.history_count == 2


# ── ModelTrainer ────────────────────────────────


class TestModelTrainer(unittest.TestCase):
    def test_init(self):
        mt = ModelTrainer()
        assert mt.model_count == 0
        assert mt.learning_rate == 0.01

    def test_init_custom(self):
        mt = ModelTrainer(
            learning_rate=0.001, epochs=50, batch_size=64,
        )
        assert mt.learning_rate == 0.001

    def test_train(self):
        mt = ModelTrainer(epochs=5)
        r = mt.train("m1", {"samples": 100})
        assert r["model_id"] == "m1"
        assert r["status"] == "trained"
        assert r["epochs_completed"] == 5
        assert mt.model_count == 1

    def test_train_early_stopping(self):
        mt = ModelTrainer(epochs=100)
        r = mt.train(
            "m1", {"samples": 10},
            hyperparams={"patience": 3, "epochs": 100},
        )
        assert r["early_stopped"] is True

    def test_train_hyperparams(self):
        mt = ModelTrainer()
        r = mt.train(
            "m1", {},
            hyperparams={"learning_rate": 0.1, "epochs": 3},
        )
        assert r["hyperparams"]["learning_rate"] == 0.1

    def test_validate(self):
        mt = ModelTrainer(epochs=3)
        mt.train("m1", {})
        r = mt.validate("m1", {"samples": 50})
        assert "val_accuracy" in r
        assert r["model_id"] == "m1"

    def test_validate_not_found(self):
        mt = ModelTrainer()
        r = mt.validate("nope", {})
        assert r.get("error") == "model_not_found"

    def test_checkpoints(self):
        mt = ModelTrainer(epochs=5)
        mt.train("m1", {})
        cp = mt.get_checkpoints("m1")
        assert len(cp) > 0

    def test_training_history(self):
        mt = ModelTrainer(epochs=5)
        mt.train("m1", {})
        h = mt.get_training_history("m1")
        assert len(h) == 5

    def test_get_model(self):
        mt = ModelTrainer(epochs=3)
        mt.train("m1", {})
        m = mt.get_model("m1")
        assert m is not None
        assert m["model_id"] == "m1"

    def test_get_model_not_found(self):
        mt = ModelTrainer()
        assert mt.get_model("nope") is None

    def test_set_hyperparams(self):
        mt = ModelTrainer()
        r = mt.set_hyperparams("m1", {"lr": 0.01})
        assert r["params"]["lr"] == 0.01

    def test_checkpoint_count(self):
        mt = ModelTrainer(epochs=5)
        mt.train("m1", {})
        assert mt.checkpoint_count > 0


# ── ModelEvaluator ──────────────────────────────


class TestModelEvaluator(unittest.TestCase):
    def test_init(self):
        me = ModelEvaluator()
        assert me.evaluation_count == 0

    def test_evaluate(self):
        me = ModelEvaluator()
        y_true = [0, 0, 1, 1, 1]
        y_pred = [0, 1, 1, 1, 0]
        r = me.evaluate("m1", y_true, y_pred)
        assert r["accuracy"] == 0.6
        assert "precision" in r
        assert "recall" in r
        assert "f1" in r
        assert me.evaluation_count == 1

    def test_evaluate_perfect(self):
        me = ModelEvaluator()
        y = [0, 1, 0, 1]
        r = me.evaluate("m1", y, y)
        assert r["accuracy"] == 1.0

    def test_evaluate_empty(self):
        me = ModelEvaluator()
        r = me.evaluate("m1", [], [])
        assert r.get("error") == "invalid_data"

    def test_evaluate_mismatch(self):
        me = ModelEvaluator()
        r = me.evaluate("m1", [0, 1], [0])
        assert r.get("error") == "invalid_data"

    def test_confusion_matrix(self):
        me = ModelEvaluator()
        y_true = [0, 0, 1, 1]
        y_pred = [0, 1, 1, 0]
        r = me.confusion_matrix(y_true, y_pred)
        assert r["size"] == 2
        assert len(r["matrix"]) == 2

    def test_roc_auc(self):
        me = ModelEvaluator()
        y_true = [0, 0, 1, 1]
        y_scores = [0.1, 0.4, 0.6, 0.9]
        r = me.roc_auc(y_true, y_scores)
        assert r["auc"] > 0.5

    def test_roc_auc_perfect(self):
        me = ModelEvaluator()
        y_true = [0, 0, 1, 1]
        y_scores = [0.0, 0.0, 1.0, 1.0]
        r = me.roc_auc(y_true, y_scores)
        assert r["auc"] == 1.0

    def test_roc_auc_empty(self):
        me = ModelEvaluator()
        r = me.roc_auc([], [])
        assert r["auc"] == 0.0

    def test_roc_auc_all_same(self):
        me = ModelEvaluator()
        r = me.roc_auc([1, 1, 1], [0.5, 0.6, 0.7])
        assert r["auc"] == 0.5

    def test_cross_validate(self):
        me = ModelEvaluator()
        data = [{"x": i} for i in range(20)]
        r = me.cross_validate("m1", data, k_folds=5)
        assert len(r["fold_scores"]) == 5
        assert "mean_score" in r
        assert me.cv_count == 1

    def test_cross_validate_empty(self):
        me = ModelEvaluator()
        r = me.cross_validate("m1", [], k_folds=5)
        assert r.get("error") == "invalid_params"

    def test_compare_models(self):
        me = ModelEvaluator()
        me.evaluate("a", [0, 1, 1], [0, 1, 1])
        me.evaluate("b", [0, 1, 1], [0, 1, 0])
        r = me.compare_models("a", "b")
        assert r["winner"] == "a"
        assert me.comparison_count == 1

    def test_compare_models_missing(self):
        me = ModelEvaluator()
        r = me.compare_models("a", "b")
        assert r.get("error") == "missing_evaluation"

    def test_get_evaluation(self):
        me = ModelEvaluator()
        me.evaluate("m1", [0, 1], [0, 1])
        assert me.get_evaluation("m1") is not None
        assert me.get_evaluation("nope") is None


# ── ModelRegistry ───────────────────────────────


class TestModelRegistry(unittest.TestCase):
    def test_init(self):
        mr = ModelRegistry()
        assert mr.model_count == 0

    def test_register(self):
        mr = ModelRegistry()
        r = mr.register("clf", "1.0", {"accuracy": 0.9})
        assert r["name"] == "clf"
        assert r["version"] == "1.0"
        assert mr.model_count == 1

    def test_get_model(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        m = mr.get_model("clf", "1.0")
        assert m is not None
        assert m["name"] == "clf"

    def test_get_model_latest(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        mr.register("clf", "2.0")
        m = mr.get_model("clf")
        assert m["version"] == "2.0"

    def test_get_model_not_found(self):
        mr = ModelRegistry()
        assert mr.get_model("nope") is None

    def test_update_status(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        r = mr.update_status("clf", "1.0", "deployed")
        assert r["status"] == "deployed"
        assert mr.deployed_count == 1

    def test_update_status_not_found(self):
        mr = ModelRegistry()
        r = mr.update_status("nope", "1.0", "deployed")
        assert r.get("error") == "not_found"

    def test_update_metrics(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        r = mr.update_metrics("clf", "1.0", {"f1": 0.85})
        assert r["metrics"]["f1"] == 0.85

    def test_update_metrics_not_found(self):
        mr = ModelRegistry()
        r = mr.update_metrics("nope", "1.0", {})
        assert r.get("error") == "not_found"

    def test_compare(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0", {"accuracy": 0.8})
        mr.register("clf", "2.0", {"accuracy": 0.9})
        r = mr.compare("clf", "1.0", "2.0")
        assert r["comparison"]["accuracy"]["improved"] is True

    def test_compare_not_found(self):
        mr = ModelRegistry()
        r = mr.compare("clf", "1.0", "2.0")
        assert r.get("error") == "not_found"

    def test_lineage(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        mr.update_status("clf", "1.0", "deployed")
        lin = mr.get_lineage("clf")
        assert len(lin) == 2

    def test_versions(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        mr.register("clf", "2.0")
        v = mr.get_versions("clf")
        assert len(v) == 2

    def test_tag_model(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        r = mr.tag_model("clf", "1.0", "production")
        assert r["tag"] == "production"

    def test_get_by_tag(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        mr.tag_model("clf", "1.0", "latest")
        m = mr.get_by_tag("clf", "latest")
        assert m is not None
        assert m["version"] == "1.0"

    def test_get_by_tag_not_found(self):
        mr = ModelRegistry()
        assert mr.get_by_tag("clf", "nope") is None

    def test_list_models(self):
        mr = ModelRegistry()
        mr.register("a", "1.0")
        mr.register("b", "1.0")
        assert len(mr.list_models()) == 2

    def test_list_models_filtered(self):
        mr = ModelRegistry()
        mr.register("a", "1.0")
        mr.register("b", "1.0")
        mr.update_status("a", "1.0", "deployed")
        assert len(mr.list_models("deployed")) == 1

    def test_delete_model(self):
        mr = ModelRegistry()
        mr.register("clf", "1.0")
        assert mr.delete_model("clf", "1.0") is True
        assert mr.model_count == 0

    def test_delete_model_not_found(self):
        mr = ModelRegistry()
        assert mr.delete_model("nope", "1.0") is False

    def test_version_count(self):
        mr = ModelRegistry()
        mr.register("a", "1.0")
        mr.register("a", "2.0")
        assert mr.version_count == 2


# ── ModelServer ─────────────────────────────────


class TestModelServer(unittest.TestCase):
    def test_init(self):
        ms = ModelServer()
        assert ms.loaded_count == 0
        assert ms.cache_count == 0

    def test_load_model(self):
        ms = ModelServer()
        r = ms.load_model("m1")
        assert r["status"] == "loaded"
        assert ms.loaded_count == 1

    def test_unload_model(self):
        ms = ModelServer()
        ms.load_model("m1")
        assert ms.unload_model("m1") is True
        assert ms.loaded_count == 0

    def test_unload_not_found(self):
        ms = ModelServer()
        assert ms.unload_model("nope") is False

    def test_predict(self):
        ms = ModelServer()
        ms.load_model("m1")
        r = ms.predict("m1", {"features": [0.5, 0.5]})
        assert "prediction" in r
        assert "confidence" in r
        assert ms.prediction_count == 1

    def test_predict_not_loaded(self):
        ms = ModelServer()
        r = ms.predict("nope", {})
        assert r.get("error") == "model_not_loaded"

    def test_predict_cache_hit(self):
        ms = ModelServer()
        ms.load_model("m1")
        inp = {"features": [0.5]}
        ms.predict("m1", inp)
        ms.predict("m1", inp)
        stats = ms.get_stats()
        assert stats["cache_hits"] >= 1

    def test_batch_predict(self):
        ms = ModelServer()
        ms.load_model("m1")
        batch = [
            {"features": [0.1]},
            {"features": [0.5]},
            {"features": [0.9]},
        ]
        r = ms.batch_predict("m1", batch)
        assert r["batch_size"] == 3
        assert len(r["predictions"]) == 3

    def test_batch_predict_not_loaded(self):
        ms = ModelServer()
        r = ms.batch_predict("nope", [{}])
        assert r.get("error") == "model_not_loaded"

    def test_clear_cache(self):
        ms = ModelServer()
        ms.load_model("m1")
        ms.predict("m1", {"features": [1]})
        cleared = ms.clear_cache()
        assert cleared >= 1
        assert ms.cache_count == 0

    def test_clear_cache_model(self):
        ms = ModelServer()
        ms.load_model("m1")
        ms.load_model("m2")
        ms.predict("m1", {"features": [1]})
        ms.predict("m2", {"features": [2]})
        cleared = ms.clear_cache("m1")
        assert cleared >= 1

    def test_cache_eviction(self):
        ms = ModelServer(cache_size=2)
        ms.load_model("m1")
        ms.predict("m1", {"features": [1]})
        ms.predict("m1", {"features": [2]})
        ms.predict("m1", {"features": [3]})
        assert ms.cache_count <= 2

    def test_get_model_info(self):
        ms = ModelServer()
        ms.load_model("m1")
        info = ms.get_model_info("m1")
        assert info is not None
        assert info["status"] == "ready"

    def test_get_model_info_not_found(self):
        ms = ModelServer()
        assert ms.get_model_info("nope") is None

    def test_get_stats(self):
        ms = ModelServer()
        stats = ms.get_stats()
        assert "total_predictions" in stats
        assert "loaded_models" in stats

    def test_request_count(self):
        ms = ModelServer()
        ms.load_model("m1")
        ms.predict("m1", {"features": [1]})
        assert ms.request_count >= 1


# ── ExperimentTracker ───────────────────────────


class TestExperimentTracker(unittest.TestCase):
    def test_init(self):
        et = ExperimentTracker()
        assert et.experiment_count == 0
        assert et.total_runs == 0

    def test_create_experiment(self):
        et = ExperimentTracker()
        r = et.create_experiment("exp1", "test experiment")
        assert r["name"] == "exp1"
        assert r["status"] == "active"
        assert et.experiment_count == 1

    def test_start_run(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        r = et.start_run("exp1", params={"lr": 0.01})
        assert r["status"] == "running"
        assert et.total_runs == 1

    def test_start_run_not_found(self):
        et = ExperimentTracker()
        r = et.start_run("nope")
        assert r.get("error") == "experiment_not_found"

    def test_log_params(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        r = et.log_params("exp1", "run_1", {"lr": 0.01})
        assert r["params_logged"] == 1

    def test_log_params_not_found(self):
        et = ExperimentTracker()
        r = et.log_params("exp1", "nope", {})
        assert r.get("error") == "run_not_found"

    def test_log_metrics(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        r = et.log_metrics(
            "exp1", "run_1", {"accuracy": 0.8}, step=1,
        )
        assert r["metrics_logged"] == 1

    def test_log_metrics_not_found(self):
        et = ExperimentTracker()
        r = et.log_metrics("exp1", "nope", {})
        assert r.get("error") == "run_not_found"

    def test_end_run(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        et.log_metrics("exp1", "run_1", {"accuracy": 0.9})
        r = et.end_run("exp1", "run_1")
        assert r["status"] == "completed"
        assert "duration" in r

    def test_end_run_not_found(self):
        et = ExperimentTracker()
        r = et.end_run("exp1", "nope")
        assert r.get("error") == "run_not_found"

    def test_log_artifact(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        r = et.log_artifact("exp1", "run_1", "model.pkl", "model")
        assert r["name"] == "model.pkl"
        assert et.artifact_count == 1

    def test_get_artifacts(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        et.log_artifact("exp1", "run_1", "f1")
        et.log_artifact("exp1", "run_1", "f2")
        arts = et.get_artifacts("exp1", "run_1")
        assert len(arts) == 2

    def test_compare_runs(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        et.log_metrics("exp1", "run_1", {"acc": 0.8})
        et.start_run("exp1")
        et.log_metrics("exp1", "run_2", {"acc": 0.9})
        r = et.compare_runs("exp1")
        assert r["runs_compared"] == 2
        assert "acc" in r["metrics"]

    def test_compare_runs_filtered(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        et.log_metrics("exp1", "run_1", {"acc": 0.8})
        et.start_run("exp1")
        et.log_metrics("exp1", "run_2", {"acc": 0.9})
        r = et.compare_runs("exp1", run_ids=["run_1"])
        assert r["runs_compared"] == 1

    def test_compare_runs_empty(self):
        et = ExperimentTracker()
        r = et.compare_runs("nope")
        assert r.get("error") == "no_runs"

    def test_get_experiment(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        exp = et.get_experiment("exp1")
        assert exp is not None
        assert exp["name"] == "exp1"

    def test_get_experiment_not_found(self):
        et = ExperimentTracker()
        assert et.get_experiment("nope") is None

    def test_get_runs(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        et.start_run("exp1")
        runs = et.get_runs("exp1")
        assert len(runs) == 2

    def test_get_runs_filtered(self):
        et = ExperimentTracker()
        et.create_experiment("exp1")
        et.start_run("exp1")
        et.end_run("exp1", "run_1")
        et.start_run("exp1")
        runs = et.get_runs("exp1", status="running")
        assert len(runs) == 1


# ── DriftDetector ───────────────────────────────


class TestDriftDetector(unittest.TestCase):
    def test_init(self):
        dd = DriftDetector()
        assert dd.baseline_count == 0
        assert dd.alert_count == 0

    def test_set_baseline(self):
        dd = DriftDetector()
        r = dd.set_baseline("age", [20, 30, 40, 50, 60])
        assert r["feature"] == "age"
        assert "mean" in r
        assert dd.baseline_count == 1

    def test_set_baseline_empty(self):
        dd = DriftDetector()
        r = dd.set_baseline("age", [])
        assert r.get("error") == "empty_values"

    def test_detect_data_drift_no_drift(self):
        dd = DriftDetector(threshold=10.0)
        dd.set_baseline("age", [20, 30, 40, 50, 60])
        r = dd.detect_data_drift("age", [22, 32, 42, 52, 62])
        assert r["drift_detected"] is False

    def test_detect_data_drift_detected(self):
        dd = DriftDetector(threshold=0.01)
        dd.set_baseline("age", [20, 30, 40, 50, 60])
        r = dd.detect_data_drift("age", [200, 300, 400, 500, 600])
        assert r["drift_detected"] is True
        assert dd.alert_count >= 1

    def test_detect_data_drift_no_baseline(self):
        dd = DriftDetector()
        r = dd.detect_data_drift("x", [1, 2, 3])
        assert r["drift_detected"] is False
        assert r["reason"] == "no_baseline"

    def test_detect_concept_drift(self):
        dd = DriftDetector(threshold=0.01)
        accs = [0.9, 0.9, 0.88, 0.87, 0.85, 0.5, 0.4, 0.3, 0.2, 0.1]
        r = dd.detect_concept_drift("m1", accs)
        assert r["drift_detected"] is True
        assert dd.should_retrain("m1") is True

    def test_detect_concept_drift_no_drift(self):
        dd = DriftDetector(threshold=10.0)
        accs = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
        r = dd.detect_concept_drift("m1", accs)
        assert r["drift_detected"] is False

    def test_detect_concept_drift_insufficient(self):
        dd = DriftDetector()
        r = dd.detect_concept_drift("m1", [0.9, 0.8])
        assert r["drift_detected"] is False
        assert r["reason"] == "insufficient_data"

    def test_detect_feature_drift(self):
        dd = DriftDetector(threshold=0.01)
        dd.set_baseline("a", [1, 2, 3, 4, 5])
        dd.set_baseline("b", [10, 20, 30, 40, 50])
        r = dd.detect_feature_drift({
            "a": [100, 200, 300, 400, 500],
            "b": [10, 20, 30, 40, 50],
        })
        assert r["features_checked"] == 2
        assert r["features_drifted"] >= 1

    def test_get_alerts(self):
        dd = DriftDetector(threshold=0.01)
        dd.set_baseline("x", [1, 2, 3])
        dd.detect_data_drift("x", [100, 200, 300])
        alerts = dd.get_alerts()
        assert len(alerts) >= 1

    def test_get_alerts_filtered(self):
        dd = DriftDetector(threshold=0.01)
        dd.set_baseline("x", [1, 2, 3])
        dd.detect_data_drift("x", [100, 200, 300])
        alerts = dd.get_alerts(drift_type="data")
        assert len(alerts) >= 1
        alerts2 = dd.get_alerts(drift_type="concept")
        assert len(alerts2) == 0

    def test_retrain_triggers(self):
        dd = DriftDetector(threshold=0.01)
        accs = [0.9, 0.9, 0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1]
        dd.detect_concept_drift("m1", accs)
        triggers = dd.get_retrain_triggers()
        assert "m1" in triggers

    def test_acknowledge_retrain(self):
        dd = DriftDetector(threshold=0.01)
        accs = [0.9, 0.9, 0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1]
        dd.detect_concept_drift("m1", accs)
        assert dd.acknowledge_retrain("m1") is True
        assert dd.should_retrain("m1") is False

    def test_acknowledge_retrain_not_found(self):
        dd = DriftDetector()
        assert dd.acknowledge_retrain("nope") is False

    def test_should_retrain_no_trigger(self):
        dd = DriftDetector()
        assert dd.should_retrain("nope") is False

    def test_drift_count(self):
        dd = DriftDetector(threshold=0.01)
        dd.set_baseline("x", [1, 2, 3])
        dd.detect_data_drift("x", [100, 200, 300])
        assert dd.drift_count >= 1

    def test_history_count(self):
        dd = DriftDetector()
        dd.set_baseline("x", [1, 2, 3])
        dd.detect_data_drift("x", [1, 2, 3])
        assert dd.history_count >= 1


# ── MLOrchestrator ──────────────────────────────


class TestMLOrchestrator(unittest.TestCase):
    def test_init(self):
        ml = MLOrchestrator()
        assert ml.is_initialized is False
        assert ml.pipeline_count == 0

    def test_initialize(self):
        ml = MLOrchestrator()
        r = ml.initialize()
        assert r["status"] == "initialized"
        assert ml.is_initialized is True

    def test_run_pipeline(self):
        ml = MLOrchestrator()
        data = {
            "features": {"x": [1.0, 2.0, 3.0]},
            "y_true": [0, 1, 1],
            "y_pred": [0, 1, 0],
            "samples": 3,
        }
        r = ml.run_pipeline("test_pipe", data)
        assert r["pipeline"] == "test_pipe"
        assert "training" in r
        assert len(r["stages_completed"]) == 5
        assert ml.pipeline_count == 1
        assert ml.run_count == 1

    def test_run_pipeline_custom(self):
        ml = MLOrchestrator()
        data = {"features": {}, "samples": 10}
        r = ml.run_pipeline(
            "pipe2", data,
            config={"model_id": "custom", "version": "2.0"},
        )
        assert r["model_id"] == "custom"

    def test_deploy_model(self):
        ml = MLOrchestrator()
        ml.registry.register("clf", "1.0")
        r = ml.deploy_model("clf", "1.0")
        assert r["status"] == "deployed"

    def test_deploy_model_not_found(self):
        ml = MLOrchestrator()
        r = ml.deploy_model("nope", "1.0")
        assert r.get("error") == "model_not_found"

    def test_check_drift(self):
        ml = MLOrchestrator()
        ml.drift.set_baseline("x", [1, 2, 3])
        r = ml.check_drift({"x": [1, 2, 3]})
        assert "features_checked" in r

    def test_get_snapshot(self):
        ml = MLOrchestrator()
        snap = ml.get_snapshot()
        assert "scalers" in snap
        assert "trained_models" in snap
        assert "pipeline_runs" in snap
        assert "initialized" in snap

    def test_get_analytics(self):
        ml = MLOrchestrator()
        a = ml.get_analytics()
        assert "preprocessing" in a
        assert "features" in a
        assert "training" in a
        assert "evaluation" in a
        assert "registry" in a
        assert "serving" in a
        assert "experiments" in a
        assert "drift" in a

    def test_full_workflow(self):
        ml = MLOrchestrator()
        ml.initialize()

        # Pipeline
        data = {
            "features": {"x": [1.0, 2.0, 3.0]},
            "y_true": [0, 1, 1],
            "y_pred": [0, 1, 1],
        }
        ml.run_pipeline("clf", data, {"version": "1.0"})

        # Deploy
        ml.deploy_model("clf", "1.0")

        snap = ml.get_snapshot()
        assert snap["deployed_models"] >= 1


# ── Config ──────────────────────────────────────


class TestConfigSettings(unittest.TestCase):
    def test_mlpipeline_settings(self):
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "mlpipeline_enabled")
        assert hasattr(s, "model_cache_size")
        assert hasattr(s, "experiment_retention_days")
        assert hasattr(s, "drift_check_interval")
        assert hasattr(s, "auto_retrain")

    def test_mlpipeline_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.mlpipeline_enabled is True
        assert s.model_cache_size == 1000
        assert s.experiment_retention_days == 90
        assert s.drift_check_interval == 3600
        assert s.auto_retrain is False


if __name__ == "__main__":
    unittest.main()
