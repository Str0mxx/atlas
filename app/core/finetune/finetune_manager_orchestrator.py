"""
Fine-tune yonetici orkestratoru modulu.

Tam fine-tuning yasam dongusu,
Prepare -> Train -> Evaluate -> Deploy -> Monitor,
ozel model yonetimi, analitik.
"""

import logging
from typing import Any

from .dataset_curator import DatasetCurator
from .finetune_orchestrator import (
    FineTuneJobOrchestrator,
)
from .ft_drift_monitor import FTDriftMonitor
from .ft_model_deployer import (
    FTModelDeployer,
)
from .ft_model_evaluator import (
    FTModelEvaluator,
)
from .ft_model_version_manager import (
    FTModelVersionManager,
)
from .ft_performance_benchmarker import (
    FTPerformanceBenchmarker,
)
from .training_data_preparer import (
    TrainingDataPreparer,
)

logger = logging.getLogger(__name__)


class FineTuneManagerOrchestrator:
    """Fine-tune yonetici orkestratoru.

    Attributes:
        _data_preparer: Veri hazirlayici.
        _job_orchestrator: Is orkestratoru.
        _evaluator: Degerlendirici.
        _version_manager: Versiyon yonetici.
        _curator: Kurator.
        _benchmarker: Benchmark.
        _deployer: Dagitimci.
        _drift_monitor: Drift izleyici.
    """

    def __init__(
        self,
        default_provider: str = "openai",
        auto_evaluate: bool = True,
        drift_monitoring: bool = True,
        version_retention: int = 10,
        pass_threshold: float = 0.7,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_provider: Varsayilan saglayici.
            auto_evaluate: Otomatik degerlendirme.
            drift_monitoring: Drift izleme.
            version_retention: Versiyon tutma.
            pass_threshold: Gecme esigi.
        """
        self._auto_evaluate = auto_evaluate
        self._drift_monitoring = (
            drift_monitoring
        )

        self._data_preparer = (
            TrainingDataPreparer()
        )
        self._job_orchestrator = (
            FineTuneJobOrchestrator(
                default_provider=(
                    default_provider
                ),
            )
        )
        self._evaluator = FTModelEvaluator(
            pass_threshold=pass_threshold,
        )
        self._version_manager = (
            FTModelVersionManager(
                version_retention=(
                    version_retention
                ),
            )
        )
        self._curator = DatasetCurator()
        self._benchmarker = (
            FTPerformanceBenchmarker()
        )
        self._deployer = FTModelDeployer()
        self._drift_monitor = (
            FTDriftMonitor()
        )

        logger.info(
            "FineTuneManagerOrchestrator "
            "baslatildi"
        )

    def prepare_and_train(
        self,
        name: str = "",
        base_model: str = "",
        samples: list[dict] | None = None,
        format_type: str = "chat",
        provider: str = "",
        hyperparameters: dict
        | None = None,
    ) -> dict[str, Any]:
        """Hazirla ve egit pipeline.

        Args:
            name: Is adi.
            base_model: Temel model.
            samples: Egitim verileri.
            format_type: Format tipi.
            provider: Saglayici.
            hyperparameters: Hiperparametreler.

        Returns:
            Pipeline bilgisi.
        """
        try:
            # 1. Veri seti olustur
            ds = (
                self._data_preparer
                .create_dataset(
                    name=f"{name}_data",
                    format_type=format_type,
                )
            )
            if not ds.get("created"):
                return {
                    "success": False,
                    "step": "create_dataset",
                    "error": ds.get("error"),
                }

            dataset_id = ds["dataset_id"]

            # 2. Ornekleri ekle
            if samples:
                bulk = (
                    self._data_preparer
                    .add_samples_bulk(
                        dataset_id=(
                            dataset_id
                        ),
                        samples=samples,
                    )
                )
                if not bulk.get(
                    "processed"
                ):
                    return {
                        "success": False,
                        "step": (
                            "add_samples"
                        ),
                        "error": bulk.get(
                            "error"
                        ),
                    }

            # 3. Dogrula
            val = (
                self._data_preparer
                .validate_dataset(
                    dataset_id=dataset_id,
                )
            )

            # 4. Is olustur
            job = (
                self._job_orchestrator
                .create_job(
                    name=name,
                    base_model=base_model,
                    dataset_id=dataset_id,
                    provider=provider,
                    hyperparameters=(
                        hyperparameters
                    ),
                )
            )
            if not job.get("created"):
                return {
                    "success": False,
                    "step": "create_job",
                    "error": job.get(
                        "error"
                    ),
                }

            # 5. Isi baslat
            start = (
                self._job_orchestrator
                .start_job(
                    job_id=job["job_id"],
                )
            )

            return {
                "dataset_id": dataset_id,
                "job_id": job["job_id"],
                "validation": val,
                "status": start.get(
                    "status", "created"
                ),
                "cost_estimate": start.get(
                    "cost_estimate", 0
                ),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def evaluate_and_version(
        self,
        job_id: str = "",
        model_id: str = "",
        model_name: str = "",
        test_data: list[dict]
        | None = None,
        base_model: str = "",
        provider: str = "",
    ) -> dict[str, Any]:
        """Degerlendir ve versiyonla.

        Args:
            job_id: Is ID.
            model_id: Model ID.
            model_name: Model adi.
            test_data: Test verisi.
            base_model: Temel model.
            provider: Saglayici.

        Returns:
            Pipeline bilgisi.
        """
        try:
            # 1. Model degerlendir
            ev = (
                self._evaluator
                .evaluate_model(
                    model_id=model_id,
                    test_dataset=(
                        test_data
                    ),
                )
            )

            # 2. Model kaydet
            reg = (
                self._version_manager
                .register_model(
                    name=model_name,
                    base_model=base_model,
                    provider=provider,
                )
            )
            if not reg.get("registered"):
                return {
                    "success": False,
                    "step": (
                        "register_model"
                    ),
                    "error": reg.get(
                        "error"
                    ),
                }

            # 3. Versiyon olustur
            ver = (
                self._version_manager
                .create_version(
                    model_id=reg[
                        "model_id"
                    ],
                    job_id=job_id,
                    metrics=ev.get(
                        "metrics", {}
                    ),
                )
            )

            return {
                "eval_id": ev.get(
                    "eval_id"
                ),
                "passed": ev.get(
                    "passed", False
                ),
                "avg_quality": ev.get(
                    "avg_quality", 0
                ),
                "model_id": reg[
                    "model_id"
                ],
                "version_id": ver.get(
                    "version_id"
                ),
                "version": ver.get(
                    "version"
                ),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def deploy_and_monitor(
        self,
        model_id: str = "",
        version_id: str = "",
        endpoint_name: str = "",
        strategy: str = "blue_green",
        enable_drift: bool = True,
    ) -> dict[str, Any]:
        """Dagit ve izle.

        Args:
            model_id: Model ID.
            version_id: Versiyon ID.
            endpoint_name: Endpoint adi.
            strategy: Dagitim stratejisi.
            enable_drift: Drift izleme.

        Returns:
            Pipeline bilgisi.
        """
        try:
            # 1. Endpoint olustur
            ep = (
                self._deployer
                .create_endpoint(
                    name=endpoint_name,
                    model_id=model_id,
                    version_id=version_id,
                )
            )
            if not ep.get("created"):
                return {
                    "success": False,
                    "step": (
                        "create_endpoint"
                    ),
                    "error": ep.get(
                        "error"
                    ),
                }

            # 2. Dagitim yap
            dep = self._deployer.deploy_model(
                endpoint_id=ep[
                    "endpoint_id"
                ],
                model_id=model_id,
                version_id=version_id,
                strategy=strategy,
            )

            # 3. Drift izleyici ekle
            drift_id = None
            if (
                enable_drift
                and self._drift_monitoring
            ):
                dm = (
                    self._drift_monitor
                    .create_monitor(
                        model_id=model_id,
                        endpoint_id=ep[
                            "endpoint_id"
                        ],
                    )
                )
                drift_id = dm.get(
                    "monitor_id"
                )

            return {
                "endpoint_id": ep[
                    "endpoint_id"
                ],
                "deployment_id": dep.get(
                    "deployment_id"
                ),
                "strategy": strategy,
                "drift_monitor_id": (
                    drift_id
                ),
                "status": dep.get(
                    "status"
                ),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def full_pipeline(
        self,
        name: str = "",
        base_model: str = "",
        train_samples: list[dict]
        | None = None,
        test_samples: list[dict]
        | None = None,
        format_type: str = "chat",
        provider: str = "",
        hyperparameters: dict
        | None = None,
        deploy: bool = False,
        deploy_strategy: str = (
            "blue_green"
        ),
    ) -> dict[str, Any]:
        """Tam pipeline calistirir.

        Args:
            name: Is adi.
            base_model: Temel model.
            train_samples: Egitim verileri.
            test_samples: Test verileri.
            format_type: Format tipi.
            provider: Saglayici.
            hyperparameters: Hiperparametreler.
            deploy: Dagitim yapilsin mi.
            deploy_strategy: Dagitim stratejisi.

        Returns:
            Tam pipeline bilgisi.
        """
        try:
            result: dict[str, Any] = {
                "pipeline": name,
                "steps": {},
            }

            # Step 1: Prepare & Train
            pt = self.prepare_and_train(
                name=name,
                base_model=base_model,
                samples=train_samples,
                format_type=format_type,
                provider=provider,
                hyperparameters=(
                    hyperparameters
                ),
            )
            result["steps"][
                "prepare_train"
            ] = pt

            if not pt.get("success"):
                result["success"] = False
                return result

            # Step 2: Evaluate & Version
            ev = self.evaluate_and_version(
                job_id=pt["job_id"],
                model_id=(
                    f"model_{name}"
                ),
                model_name=name,
                test_data=test_samples,
                base_model=base_model,
                provider=provider,
            )
            result["steps"][
                "evaluate_version"
            ] = ev

            if not ev.get("success"):
                result["success"] = False
                return result

            # Step 3: Deploy (opsiyonel)
            if deploy and ev.get("passed"):
                dm = (
                    self.deploy_and_monitor(
                        model_id=ev[
                            "model_id"
                        ],
                        version_id=ev[
                            "version_id"
                        ],
                        endpoint_name=(
                            f"ep_{name}"
                        ),
                        strategy=(
                            deploy_strategy
                        ),
                    )
                )
                result["steps"][
                    "deploy_monitor"
                ] = dm

            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir."""
        try:
            return {
                "data_preparer": (
                    self._data_preparer
                    .get_summary()
                ),
                "jobs": (
                    self._job_orchestrator
                    .get_summary()
                ),
                "evaluator": (
                    self._evaluator
                    .get_summary()
                ),
                "versions": (
                    self._version_manager
                    .get_summary()
                ),
                "curator": (
                    self._curator
                    .get_summary()
                ),
                "benchmarks": (
                    self._benchmarker
                    .get_summary()
                ),
                "deployments": (
                    self._deployer
                    .get_summary()
                ),
                "drift": (
                    self._drift_monitor
                    .get_summary()
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "datasets": (
                    self._data_preparer
                    .dataset_count
                ),
                "jobs": (
                    self._job_orchestrator
                    .job_count
                ),
                "evaluations": (
                    self._evaluator
                    .evaluation_count
                ),
                "models": (
                    self._version_manager
                    .model_count
                ),
                "curated_datasets": (
                    self._curator
                    .dataset_count
                ),
                "benchmark_suites": (
                    self._benchmarker
                    .suite_count
                ),
                "deployments": (
                    self._deployer
                    .deployment_count
                ),
                "drift_monitors": (
                    self._drift_monitor
                    .monitor_count
                ),
                "auto_evaluate": (
                    self._auto_evaluate
                ),
                "drift_monitoring": (
                    self._drift_monitoring
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
