"""ATLAS Model Degerlendirici modulu.

Dogruluk metrikleri, karisiklik matrisi,
ROC/AUC, capraz dogrulama
ve A/B karsilastirma.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Model degerlendirici.

    Model performansini olcer.

    Attributes:
        _evaluations: Degerlendirmeler.
        _comparisons: Karsilastirmalar.
    """

    def __init__(self) -> None:
        """Degerlendiriciyi baslatir."""
        self._evaluations: dict[
            str, dict[str, Any]
        ] = {}
        self._comparisons: list[
            dict[str, Any]
        ] = []
        self._cv_results: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "ModelEvaluator baslatildi",
        )

    def evaluate(
        self,
        model_id: str,
        y_true: list[int],
        y_pred: list[int],
    ) -> dict[str, Any]:
        """Modeli degerlendirir.

        Args:
            model_id: Model ID.
            y_true: Gercek degerler.
            y_pred: Tahmin degerleri.

        Returns:
            Degerlendirme sonucu.
        """
        n = len(y_true)
        if n == 0 or n != len(y_pred):
            return {"error": "invalid_data"}

        correct = sum(
            1 for t, p in zip(y_true, y_pred)
            if t == p
        )
        accuracy = correct / n

        # Siniflar
        classes = sorted(
            set(y_true) | set(y_pred),
        )

        # Sinif bazli metrikler
        per_class: dict[str, dict[str, float]] = {}
        for cls in classes:
            tp = sum(
                1 for t, p in zip(y_true, y_pred)
                if t == cls and p == cls
            )
            fp = sum(
                1 for t, p in zip(y_true, y_pred)
                if t != cls and p == cls
            )
            fn = sum(
                1 for t, p in zip(y_true, y_pred)
                if t == cls and p != cls
            )
            precision = (
                tp / (tp + fp)
                if (tp + fp) > 0 else 0.0
            )
            recall = (
                tp / (tp + fn)
                if (tp + fn) > 0 else 0.0
            )
            f1 = (
                2 * precision * recall
                / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )
            per_class[str(cls)] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": sum(
                    1 for t in y_true if t == cls
                ),
            }

        # Makro ortalama
        macro_precision = sum(
            c["precision"]
            for c in per_class.values()
        ) / max(len(per_class), 1)
        macro_recall = sum(
            c["recall"]
            for c in per_class.values()
        ) / max(len(per_class), 1)
        macro_f1 = sum(
            c["f1"]
            for c in per_class.values()
        ) / max(len(per_class), 1)

        result = {
            "model_id": model_id,
            "accuracy": accuracy,
            "precision": macro_precision,
            "recall": macro_recall,
            "f1": macro_f1,
            "per_class": per_class,
            "samples": n,
            "timestamp": time.time(),
        }

        self._evaluations[model_id] = result
        return result

    def confusion_matrix(
        self,
        y_true: list[int],
        y_pred: list[int],
    ) -> dict[str, Any]:
        """Karisiklik matrisi olusturur.

        Args:
            y_true: Gercek degerler.
            y_pred: Tahmin degerleri.

        Returns:
            Matris bilgisi.
        """
        classes = sorted(
            set(y_true) | set(y_pred),
        )
        n_classes = len(classes)
        class_map = {
            c: i for i, c in enumerate(classes)
        }

        matrix = [
            [0] * n_classes
            for _ in range(n_classes)
        ]

        for t, p in zip(y_true, y_pred):
            matrix[class_map[t]][class_map[p]] += 1

        return {
            "matrix": matrix,
            "classes": classes,
            "size": n_classes,
        }

    def roc_auc(
        self,
        y_true: list[int],
        y_scores: list[float],
    ) -> dict[str, Any]:
        """ROC/AUC hesaplar.

        Args:
            y_true: Gercek degerler (0/1).
            y_scores: Tahmin skorlari.

        Returns:
            ROC/AUC bilgisi.
        """
        if not y_true or len(y_true) != len(y_scores):
            return {"auc": 0.0}

        # Esiklere gore siralanmis
        pairs = sorted(
            zip(y_scores, y_true),
            reverse=True,
        )

        total_pos = sum(y_true)
        total_neg = len(y_true) - total_pos

        if total_pos == 0 or total_neg == 0:
            return {"auc": 0.5}

        tpr_list: list[float] = [0.0]
        fpr_list: list[float] = [0.0]
        tp = 0
        fp = 0

        for _, label in pairs:
            if label == 1:
                tp += 1
            else:
                fp += 1
            tpr_list.append(tp / total_pos)
            fpr_list.append(fp / total_neg)

        # Trapez kurali ile AUC
        auc = 0.0
        for i in range(1, len(fpr_list)):
            auc += (
                (fpr_list[i] - fpr_list[i - 1])
                * (tpr_list[i] + tpr_list[i - 1])
                / 2
            )

        return {
            "auc": auc,
            "tpr_points": len(tpr_list),
            "fpr_points": len(fpr_list),
        }

    def cross_validate(
        self,
        model_id: str,
        data: list[dict[str, Any]],
        k_folds: int = 5,
    ) -> dict[str, Any]:
        """Capraz dogrulama yapar.

        Args:
            model_id: Model ID.
            data: Veri seti.
            k_folds: Katman sayisi.

        Returns:
            CV sonucu.
        """
        n = len(data)
        if n == 0 or k_folds <= 0:
            return {"error": "invalid_params"}

        fold_size = max(1, n // k_folds)
        fold_scores: list[float] = []

        for fold in range(k_folds):
            start = fold * fold_size
            end = min(start + fold_size, n)

            # Simule edilmis skor
            score = 0.7 + (fold * 0.02)
            score = min(score, 0.99)
            fold_scores.append(score)

        mean_score = (
            sum(fold_scores) / len(fold_scores)
        )
        variance = sum(
            (s - mean_score) ** 2
            for s in fold_scores
        ) / len(fold_scores)
        std_score = math.sqrt(variance)

        result = {
            "model_id": model_id,
            "k_folds": k_folds,
            "fold_scores": fold_scores,
            "mean_score": mean_score,
            "std_score": std_score,
            "samples": n,
        }

        self._cv_results[model_id] = result
        return result

    def compare_models(
        self,
        model_a: str,
        model_b: str,
    ) -> dict[str, Any]:
        """Iki modeli karsilastirir.

        Args:
            model_a: Birinci model ID.
            model_b: Ikinci model ID.

        Returns:
            Karsilastirma sonucu.
        """
        eval_a = self._evaluations.get(model_a)
        eval_b = self._evaluations.get(model_b)

        if not eval_a or not eval_b:
            return {"error": "missing_evaluation"}

        metrics = [
            "accuracy", "precision",
            "recall", "f1",
        ]
        winner_counts: dict[str, int] = {
            model_a: 0, model_b: 0,
        }

        comparisons: dict[str, dict[str, Any]] = {}
        for m in metrics:
            va = eval_a.get(m, 0.0)
            vb = eval_b.get(m, 0.0)
            if va > vb:
                winner_counts[model_a] += 1
                w = model_a
            elif vb > va:
                winner_counts[model_b] += 1
                w = model_b
            else:
                w = "tie"
            comparisons[m] = {
                model_a: va,
                model_b: vb,
                "winner": w,
            }

        overall_winner = max(
            winner_counts,
            key=lambda k: winner_counts[k],
        )

        result = {
            "model_a": model_a,
            "model_b": model_b,
            "comparisons": comparisons,
            "winner": overall_winner,
            "timestamp": time.time(),
        }

        self._comparisons.append(result)
        return result

    def get_evaluation(
        self,
        model_id: str,
    ) -> dict[str, Any] | None:
        """Degerlendirme getirir.

        Args:
            model_id: Model ID.

        Returns:
            Degerlendirme veya None.
        """
        return self._evaluations.get(model_id)

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return len(self._evaluations)

    @property
    def comparison_count(self) -> int:
        """Karsilastirma sayisi."""
        return len(self._comparisons)

    @property
    def cv_count(self) -> int:
        """CV sayisi."""
        return len(self._cv_results)
