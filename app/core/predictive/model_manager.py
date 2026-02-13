"""ATLAS Model Yonetimi modulu.

Model egitimi, degerlendirme, secim, hiperparametre
ayarlama ve model versiyonlama.
"""

import logging
import math
import time
from typing import Any

from app.models.predictive import (
    MetricType,
    ModelStatus,
    PredictionModel,
)

logger = logging.getLogger(__name__)


class ModelManager:
    """Model yonetim sistemi.

    Tahmin modellerinin yasam dongusunu yonetir:
    egitim, degerlendirme, secim, hiperparametre
    ayarlama ve versiyonlama.

    Attributes:
        _models: Kayitli modeller.
        _active_model_id: Aktif model ID.
        _training_history: Egitim gecmisi.
    """

    def __init__(self) -> None:
        """Model yonetim sistemini baslatir."""
        self._models: dict[str, PredictionModel] = {}
        self._active_model_id: str | None = None
        self._training_history: list[dict[str, Any]] = []

        logger.info("ModelManager baslatildi")

    def train_model(
        self,
        name: str,
        model_type: str,
        data: list[float],
        parameters: dict[str, Any] | None = None,
    ) -> PredictionModel:
        """Model egitir.

        Args:
            name: Model adi.
            model_type: Model tipi (linear, exponential, vb).
            data: Egitim verisi.
            parameters: Model parametreleri.

        Returns:
            Egitilmis PredictionModel nesnesi.
        """
        start_time = time.monotonic()

        model = PredictionModel(
            name=name,
            model_type=model_type,
            status=ModelStatus.TRAINING,
            parameters=parameters or {},
            training_data_size=len(data),
        )

        # Basit model egitimi (istatistik hesaplama)
        if data:
            mean = sum(data) / len(data)
            variance = sum((v - mean) ** 2 for v in data) / len(data) if len(data) > 1 else 0.0
            std_dev = math.sqrt(variance)

            model.parameters["mean"] = mean
            model.parameters["std_dev"] = std_dev
            model.parameters["min"] = min(data)
            model.parameters["max"] = max(data)

            if model_type == "linear" and len(data) >= 2:
                # Lineer regresyon
                n = len(data)
                x_mean = (n - 1) / 2
                y_mean = mean
                num = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
                den = sum((i - x_mean) ** 2 for i in range(n))
                slope = num / den if den != 0 else 0.0
                intercept = y_mean - slope * x_mean
                model.parameters["slope"] = slope
                model.parameters["intercept"] = intercept

            model.status = ModelStatus.TRAINED
        else:
            model.status = ModelStatus.FAILED

        train_time = (time.monotonic() - start_time) * 1000
        self._models[model.id] = model
        self._training_history.append({
            "model_id": model.id,
            "name": name,
            "type": model_type,
            "data_size": len(data),
            "train_time_ms": train_time,
        })

        logger.info("Model egitildi: %s (%s), sure=%.1fms", name, model_type, train_time)
        return model

    def evaluate_model(self, model_id: str, test_data: list[float]) -> dict[str, float]:
        """Modeli degerlendirir.

        Args:
            model_id: Model ID.
            test_data: Test verisi.

        Returns:
            Metrik adi -> deger eslesmesi.
        """
        model = self._models.get(model_id)
        if not model or not test_data:
            return {}

        model.status = ModelStatus.EVALUATING

        mean = model.parameters.get("mean", 0.0)
        slope = model.parameters.get("slope", 0.0)
        intercept = model.parameters.get("intercept", mean)

        # Tahminler
        predictions: list[float] = []
        for i in range(len(test_data)):
            if model.model_type == "linear":
                pred = intercept + slope * (model.training_data_size + i)
            else:
                pred = mean
            predictions.append(pred)

        # Metrikler
        n = len(test_data)
        errors = [abs(test_data[i] - predictions[i]) for i in range(n)]
        sq_errors = [(test_data[i] - predictions[i]) ** 2 for i in range(n)]

        mae = sum(errors) / n
        rmse = math.sqrt(sum(sq_errors) / n)

        # MAPE
        mape_vals = [abs(e) / max(abs(t), 1e-10) for e, t in zip(errors, test_data)]
        mape = sum(mape_vals) / n

        # R-squared
        ss_res = sum(sq_errors)
        y_mean = sum(test_data) / n
        ss_tot = sum((t - y_mean) ** 2 for t in test_data)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        metrics = {
            MetricType.MAE.value: mae,
            MetricType.RMSE.value: rmse,
            MetricType.MAPE.value: mape,
            MetricType.R_SQUARED.value: r_squared,
        }

        model.metrics = metrics
        model.status = ModelStatus.TRAINED

        logger.info("Model degerlendirmesi: %s, MAE=%.4f, R²=%.4f", model.name, mae, r_squared)
        return metrics

    def select_best_model(self, metric: MetricType = MetricType.MAE) -> PredictionModel | None:
        """En iyi modeli secer.

        Args:
            metric: Karsilastirma metrigi.

        Returns:
            En iyi PredictionModel veya None.
        """
        candidates = [m for m in self._models.values() if m.metrics and m.status != ModelStatus.FAILED]
        if not candidates:
            return None

        # MAE, RMSE, MAPE: dusuk iyi. R_SQUARED: yuksek iyi.
        if metric in (MetricType.MAE, MetricType.RMSE, MetricType.MAPE):
            best = min(candidates, key=lambda m: m.metrics.get(metric.value, float("inf")))
        else:
            best = max(candidates, key=lambda m: m.metrics.get(metric.value, float("-inf")))

        self._active_model_id = best.id
        best.status = ModelStatus.DEPLOYED
        logger.info("En iyi model secildi: %s (%s=%.4f)", best.name, metric.value, best.metrics.get(metric.value, 0))
        return best

    def tune_hyperparameters(
        self,
        name: str,
        model_type: str,
        data: list[float],
        param_grid: dict[str, list[Any]],
    ) -> PredictionModel:
        """Hiperparametre ayarlama yapar.

        Grid search ile en iyi parametreleri bulur.

        Args:
            name: Model adi.
            model_type: Model tipi.
            data: Egitim verisi.
            param_grid: Parametre izgarasi.

        Returns:
            En iyi parametreli PredictionModel.
        """
        if not data or not param_grid:
            return self.train_model(name, model_type, data)

        # Train/test split (80/20)
        split = max(1, int(len(data) * 0.8))
        train_data = data[:split]
        test_data = data[split:] if split < len(data) else data[-2:]

        best_model: PredictionModel | None = None
        best_score = float("inf")

        # Grid search
        param_keys = list(param_grid.keys())
        param_values = list(param_grid.values())

        # Basit grid (tek parametre veya ilk parametre icin)
        for vals in param_values[0] if param_values else [None]:
            params = {param_keys[0]: vals} if param_keys else {}
            model = self.train_model(f"{name}_tune", model_type, train_data, params)
            metrics = self.evaluate_model(model.id, test_data)
            score = metrics.get(MetricType.MAE.value, float("inf"))

            if score < best_score:
                best_score = score
                best_model = model

        if best_model:
            best_model.name = name
            logger.info("Hiperparametre ayarlama tamamlandi: %s, skor=%.4f", name, best_score)
            return best_model

        return self.train_model(name, model_type, data)

    def get_model_version(self, model_id: str) -> str:
        """Model versiyonunu getirir.

        Args:
            model_id: Model ID.

        Returns:
            Versiyon string'i.
        """
        model = self._models.get(model_id)
        return model.version if model else "unknown"

    def update_model_version(self, model_id: str, new_version: str) -> bool:
        """Model versiyonunu gunceller.

        Args:
            model_id: Model ID.
            new_version: Yeni versiyon.

        Returns:
            Basarili mi.
        """
        model = self._models.get(model_id)
        if not model:
            return False
        model.version = new_version
        return True

    def deprecate_model(self, model_id: str) -> bool:
        """Modeli kullanim disi birakirir.

        Args:
            model_id: Model ID.

        Returns:
            Basarili mi.
        """
        model = self._models.get(model_id)
        if not model:
            return False
        model.status = ModelStatus.DEPRECATED
        if self._active_model_id == model_id:
            self._active_model_id = None
        logger.info("Model kullanim disi birakildi: %s", model.name)
        return True

    def get_model(self, model_id: str) -> PredictionModel | None:
        """Model getirir.

        Args:
            model_id: Model ID.

        Returns:
            PredictionModel veya None.
        """
        return self._models.get(model_id)

    @property
    def active_model(self) -> PredictionModel | None:
        """Aktif model."""
        if self._active_model_id:
            return self._models.get(self._active_model_id)
        return None

    @property
    def model_count(self) -> int:
        """Toplam model sayisi."""
        return len(self._models)

    @property
    def training_history(self) -> list[dict[str, Any]]:
        """Egitim gecmisi."""
        return list(self._training_history)
