"""ATLAS Deney Takipcisi modulu.

Deney calistirma, parametre loglama,
metrik loglama, artifakt depolama
ve karsilastirma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """Deney takipcisi.

    ML deneylerini izler ve karsilastirir.

    Attributes:
        _experiments: Deneyler.
        _runs: Calistirmalar.
    """

    def __init__(self) -> None:
        """Takipciyi baslatir."""
        self._experiments: dict[
            str, dict[str, Any]
        ] = {}
        self._runs: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._artifacts: dict[
            str, list[dict[str, Any]]
        ] = {}

        logger.info(
            "ExperimentTracker baslatildi",
        )

    def create_experiment(
        self,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Deney olusturur.

        Args:
            name: Deney adi.
            description: Aciklama.
            tags: Etiketler.

        Returns:
            Deney bilgisi.
        """
        self._experiments[name] = {
            "name": name,
            "description": description,
            "tags": tags or [],
            "status": "active",
            "run_count": 0,
            "best_run": None,
            "created_at": time.time(),
        }
        self._runs[name] = []

        return {
            "name": name,
            "status": "active",
        }

    def start_run(
        self,
        experiment: str,
        run_name: str = "",
        params: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Calistirma baslatir.

        Args:
            experiment: Deney adi.
            run_name: Calistirma adi.
            params: Parametreler.

        Returns:
            Calistirma bilgisi.
        """
        exp = self._experiments.get(experiment)
        if not exp:
            return {"error": "experiment_not_found"}

        run_id = f"run_{exp['run_count'] + 1}"
        exp["run_count"] += 1

        run = {
            "run_id": run_id,
            "name": run_name or run_id,
            "experiment": experiment,
            "params": params or {},
            "metrics": {},
            "status": "running",
            "started_at": time.time(),
            "ended_at": None,
        }

        self._runs[experiment].append(run)

        return {
            "run_id": run_id,
            "experiment": experiment,
            "status": "running",
        }

    def log_params(
        self,
        experiment: str,
        run_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Parametre loglar.

        Args:
            experiment: Deney adi.
            run_id: Calistirma ID.
            params: Parametreler.

        Returns:
            Log sonucu.
        """
        run = self._find_run(
            experiment, run_id,
        )
        if not run:
            return {"error": "run_not_found"}

        run["params"].update(params)
        return {
            "run_id": run_id,
            "params_logged": len(params),
        }

    def log_metrics(
        self,
        experiment: str,
        run_id: str,
        metrics: dict[str, float],
        step: int | None = None,
    ) -> dict[str, Any]:
        """Metrik loglar.

        Args:
            experiment: Deney adi.
            run_id: Calistirma ID.
            metrics: Metrikler.
            step: Adim numarasi.

        Returns:
            Log sonucu.
        """
        run = self._find_run(
            experiment, run_id,
        )
        if not run:
            return {"error": "run_not_found"}

        for key, value in metrics.items():
            if key not in run["metrics"]:
                run["metrics"][key] = []
            run["metrics"][key].append({
                "value": value,
                "step": step,
                "timestamp": time.time(),
            })

        return {
            "run_id": run_id,
            "metrics_logged": len(metrics),
        }

    def end_run(
        self,
        experiment: str,
        run_id: str,
        status: str = "completed",
    ) -> dict[str, Any]:
        """Calistirmayi bitirir.

        Args:
            experiment: Deney adi.
            run_id: Calistirma ID.
            status: Son durum.

        Returns:
            Bitis bilgisi.
        """
        run = self._find_run(
            experiment, run_id,
        )
        if not run:
            return {"error": "run_not_found"}

        run["status"] = status
        run["ended_at"] = time.time()
        duration = (
            run["ended_at"] - run["started_at"]
        )

        # En iyi calistirmayi guncelle
        self._update_best_run(experiment)

        return {
            "run_id": run_id,
            "status": status,
            "duration": duration,
        }

    def log_artifact(
        self,
        experiment: str,
        run_id: str,
        name: str,
        artifact_type: str = "file",
        data: Any = None,
    ) -> dict[str, Any]:
        """Artifakt loglar.

        Args:
            experiment: Deney adi.
            run_id: Calistirma ID.
            name: Artifakt adi.
            artifact_type: Tip.
            data: Veri.

        Returns:
            Log sonucu.
        """
        key = f"{experiment}:{run_id}"
        if key not in self._artifacts:
            self._artifacts[key] = []

        self._artifacts[key].append({
            "name": name,
            "type": artifact_type,
            "data": data,
            "timestamp": time.time(),
        })

        return {
            "name": name,
            "type": artifact_type,
        }

    def get_artifacts(
        self,
        experiment: str,
        run_id: str,
    ) -> list[dict[str, Any]]:
        """Artifaktlari getirir.

        Args:
            experiment: Deney adi.
            run_id: Calistirma ID.

        Returns:
            Artifakt listesi.
        """
        key = f"{experiment}:{run_id}"
        return list(
            self._artifacts.get(key, []),
        )

    def compare_runs(
        self,
        experiment: str,
        run_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Calistirmalari karsilastirir.

        Args:
            experiment: Deney adi.
            run_ids: Karsilastirilacak ID'ler.

        Returns:
            Karsilastirma sonucu.
        """
        runs = self._runs.get(experiment, [])
        if run_ids:
            runs = [
                r for r in runs
                if r["run_id"] in run_ids
            ]

        if not runs:
            return {"error": "no_runs"}

        # Tum metrikleri topla
        all_metrics: set[str] = set()
        for run in runs:
            all_metrics.update(run["metrics"].keys())

        comparison: dict[str, dict[str, Any]] = {}
        for metric in all_metrics:
            comparison[metric] = {}
            for run in runs:
                entries = run["metrics"].get(
                    metric, [],
                )
                if entries:
                    values = [
                        e["value"] for e in entries
                    ]
                    comparison[metric][
                        run["run_id"]
                    ] = {
                        "last": values[-1],
                        "best": max(values),
                        "count": len(values),
                    }

        return {
            "experiment": experiment,
            "runs_compared": len(runs),
            "metrics": comparison,
        }

    def get_experiment(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Deney bilgisini getirir.

        Args:
            name: Deney adi.

        Returns:
            Deney bilgisi veya None.
        """
        return self._experiments.get(name)

    def get_runs(
        self,
        experiment: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Calistirmalari getirir.

        Args:
            experiment: Deney adi.
            status: Durum filtresi.

        Returns:
            Calistirma listesi.
        """
        runs = self._runs.get(experiment, [])
        if status:
            runs = [
                r for r in runs
                if r["status"] == status
            ]
        return list(runs)

    def _find_run(
        self,
        experiment: str,
        run_id: str,
    ) -> dict[str, Any] | None:
        """Calistirma bulur.

        Args:
            experiment: Deney adi.
            run_id: Calistirma ID.

        Returns:
            Calistirma veya None.
        """
        runs = self._runs.get(experiment, [])
        for run in runs:
            if run["run_id"] == run_id:
                return run
        return None

    def _update_best_run(
        self,
        experiment: str,
    ) -> None:
        """En iyi calistirmayi gunceller.

        Args:
            experiment: Deney adi.
        """
        runs = self._runs.get(experiment, [])
        completed = [
            r for r in runs
            if r["status"] == "completed"
        ]
        if not completed:
            return

        # Ilk metrige gore en iyi
        best = None
        best_score = -1.0
        for run in completed:
            for entries in run["metrics"].values():
                if entries:
                    score = entries[-1]["value"]
                    if score > best_score:
                        best_score = score
                        best = run["run_id"]
                break

        if best:
            self._experiments[experiment][
                "best_run"
            ] = best

    @property
    def experiment_count(self) -> int:
        """Deney sayisi."""
        return len(self._experiments)

    @property
    def total_runs(self) -> int:
        """Toplam calistirma sayisi."""
        return sum(
            len(r) for r in self._runs.values()
        )

    @property
    def artifact_count(self) -> int:
        """Toplam artifakt sayisi."""
        return sum(
            len(a)
            for a in self._artifacts.values()
        )
