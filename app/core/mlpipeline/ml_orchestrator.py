"""ATLAS ML Orkestratoru modulu.

Tam ML pipeline yonetimi,
is akisi, zamanlama,
izleme ve entegrasyon.
"""

import logging
import time
from typing import Any

from app.core.mlpipeline.data_preprocessor import (
    DataPreprocessor,
)
from app.core.mlpipeline.drift_detector import (
    DriftDetector,
)
from app.core.mlpipeline.experiment_tracker import (
    ExperimentTracker,
)
from app.core.mlpipeline.feature_engineer import (
    FeatureEngineer,
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
from app.core.mlpipeline.model_trainer import (
    ModelTrainer,
)

logger = logging.getLogger(__name__)


class MLOrchestrator:
    """ML orkestratoru.

    Tum ML pipeline bilesenlierini koordine eder.

    Attributes:
        preprocessor: Veri on isleyici.
        engineer: Ozellik muhendisi.
        trainer: Model egitici.
        evaluator: Model degerlendirici.
        registry: Model kayit defteri.
        server: Model sunucusu.
        tracker: Deney takipcisi.
        drift: Kayma tespitcisi.
    """

    def __init__(
        self,
        cache_size: int = 1000,
        drift_threshold: float = 0.05,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            cache_size: Model onbellek boyutu.
            drift_threshold: Kayma esigi.
        """
        self.preprocessor = DataPreprocessor()
        self.engineer = FeatureEngineer()
        self.trainer = ModelTrainer()
        self.evaluator = ModelEvaluator()
        self.registry = ModelRegistry()
        self.server = ModelServer(cache_size)
        self.tracker = ExperimentTracker()
        self.drift = DriftDetector(drift_threshold)

        self._pipelines: dict[
            str, dict[str, Any]
        ] = {}
        self._pipeline_runs: list[
            dict[str, Any]
        ] = []
        self._initialized = False

        logger.info(
            "MLOrchestrator baslatildi",
        )

    def initialize(
        self,
        config: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Sistemi baslatir.

        Args:
            config: Konfigurasyon.

        Returns:
            Baslangic bilgisi.
        """
        self._initialized = True
        return {
            "status": "initialized",
            "config": config or {},
            "components": 8,
        }

    def run_pipeline(
        self,
        name: str,
        data: dict[str, Any],
        config: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Tam pipeline calistirir.

        Args:
            name: Pipeline adi.
            data: Veri seti.
            config: Konfigurasyon.

        Returns:
            Pipeline sonucu.
        """
        cfg = config or {}
        start_time = time.time()
        stages_completed: list[str] = []

        # 1. On isleme
        features = data.get("features", {})
        for fname, fvalues in features.items():
            if isinstance(fvalues, list) and fvalues:
                if isinstance(fvalues[0], (int, float)):
                    self.preprocessor.fit_scaler(
                        fname, fvalues,
                    )
        stages_completed.append("preprocessing")

        # 2. Ozellik muhendisligi
        for fname, fvalues in features.items():
            if isinstance(fvalues, list) and fvalues:
                if isinstance(fvalues[0], (int, float)):
                    self.engineer.extract_statistical(
                        fname, fvalues,
                    )
        stages_completed.append(
            "feature_engineering",
        )

        # 3. Egitim
        model_id = cfg.get("model_id", name)
        train_result = self.trainer.train(
            model_id, data,
            cfg.get("hyperparams"),
        )
        stages_completed.append("training")

        # 4. Degerlendirme
        y_true = data.get("y_true", [])
        y_pred = data.get("y_pred", [])
        eval_result = {}
        if y_true and y_pred:
            eval_result = self.evaluator.evaluate(
                model_id, y_true, y_pred,
            )
        stages_completed.append("evaluation")

        # 5. Kayit
        self.registry.register(
            name,
            cfg.get("version", "1.0.0"),
            metrics=eval_result.get(
                "per_class", {},
            ),
        )
        stages_completed.append("registration")

        duration = time.time() - start_time

        result = {
            "pipeline": name,
            "model_id": model_id,
            "stages_completed": stages_completed,
            "training": train_result,
            "evaluation": eval_result,
            "duration": duration,
            "timestamp": time.time(),
        }

        self._pipeline_runs.append(result)
        self._pipelines[name] = {
            "name": name,
            "last_run": result,
            "run_count": len([
                r for r in self._pipeline_runs
                if r["pipeline"] == name
            ]),
        }

        return result

    def deploy_model(
        self,
        name: str,
        version: str,
    ) -> dict[str, Any]:
        """Modeli dagitir.

        Args:
            name: Model adi.
            version: Versiyon.

        Returns:
            Dagitim sonucu.
        """
        model = self.registry.get_model(
            name, version,
        )
        if not model:
            return {"error": "model_not_found"}

        self.registry.update_status(
            name, version, "deployed",
        )

        model_id = f"{name}:{version}"
        self.server.load_model(
            model_id, model,
        )

        return {
            "name": name,
            "version": version,
            "status": "deployed",
        }

    def check_drift(
        self,
        features: dict[str, list[float]],
    ) -> dict[str, Any]:
        """Kayma kontrolu yapar.

        Args:
            features: Ozellik verileri.

        Returns:
            Kayma sonucu.
        """
        return self.drift.detect_feature_drift(
            features,
        )

    def get_snapshot(self) -> dict[str, Any]:
        """Pipeline snapshot'i getirir.

        Returns:
            Snapshot bilgisi.
        """
        return {
            "scalers": (
                self.preprocessor.scaler_count
            ),
            "generated_features": (
                self.engineer.feature_count
            ),
            "trained_models": (
                self.trainer.model_count
            ),
            "evaluations": (
                self.evaluator.evaluation_count
            ),
            "registered_models": (
                self.registry.model_count
            ),
            "deployed_models": (
                self.registry.deployed_count
            ),
            "loaded_models": (
                self.server.loaded_count
            ),
            "experiments": (
                self.tracker.experiment_count
            ),
            "drift_alerts": (
                self.drift.alert_count
            ),
            "pipeline_runs": len(
                self._pipeline_runs,
            ),
            "initialized": self._initialized,
            "timestamp": time.time(),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu getirir.

        Returns:
            Analitik bilgisi.
        """
        return {
            "preprocessing": {
                "scalers": (
                    self.preprocessor.scaler_count
                ),
                "encoders": (
                    self.preprocessor.encoder_count
                ),
            },
            "features": {
                "generated": (
                    self.engineer.feature_count
                ),
                "transformations": (
                    self.engineer.transformation_count
                ),
            },
            "training": {
                "models": (
                    self.trainer.model_count
                ),
                "checkpoints": (
                    self.trainer.checkpoint_count
                ),
            },
            "evaluation": {
                "evaluations": (
                    self.evaluator.evaluation_count
                ),
                "comparisons": (
                    self.evaluator.comparison_count
                ),
            },
            "registry": {
                "total": (
                    self.registry.model_count
                ),
                "deployed": (
                    self.registry.deployed_count
                ),
            },
            "serving": {
                "loaded": (
                    self.server.loaded_count
                ),
                "predictions": (
                    self.server.prediction_count
                ),
            },
            "experiments": {
                "total": (
                    self.tracker.experiment_count
                ),
                "runs": (
                    self.tracker.total_runs
                ),
            },
            "drift": {
                "baselines": (
                    self.drift.baseline_count
                ),
                "alerts": (
                    self.drift.alert_count
                ),
                "drifts": (
                    self.drift.drift_count
                ),
            },
            "timestamp": time.time(),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayisi."""
        return len(self._pipelines)

    @property
    def run_count(self) -> int:
        """Toplam calistirma sayisi."""
        return len(self._pipeline_runs)

    @property
    def is_initialized(self) -> bool:
        """Baslatildi mi."""
        return self._initialized
