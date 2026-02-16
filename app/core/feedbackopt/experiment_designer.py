"""ATLAS Deney Tasarımcısı modülü.

Hipotez üretimi, test tasarımı,
değişken izolasyonu, örneklem boyutu,
süre planlaması.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FeedbackExperimentDesigner:
    """Deney tasarımcısı.

    Geri bildirim temelli deneyler tasarlar.

    Attributes:
        _experiments: Deney kayıtları.
        _hypotheses: Hipotez kayıtları.
    """

    def __init__(self) -> None:
        """Tasarımcıyı başlatır."""
        self._experiments: dict[
            str, dict[str, Any]
        ] = {}
        self._hypotheses: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "experiments_designed": 0,
            "hypotheses_generated": 0,
        }

        logger.info(
            "FeedbackExperimentDesigner "
            "baslatildi",
        )

    def generate_hypothesis(
        self,
        observation: str,
        variable: str = "",
        expected_impact: str = "positive",
    ) -> dict[str, Any]:
        """Hipotez üretir.

        Args:
            observation: Gözlem.
            variable: Değişken.
            expected_impact: Beklenen etki.

        Returns:
            Hipotez bilgisi.
        """
        self._counter += 1
        hid = f"hyp_{self._counter}"

        hypothesis = {
            "hypothesis_id": hid,
            "observation": observation,
            "variable": variable,
            "expected_impact": (
                expected_impact
            ),
            "status": "proposed",
            "timestamp": time.time(),
        }
        self._hypotheses.append(hypothesis)
        self._stats[
            "hypotheses_generated"
        ] += 1

        return {
            "hypothesis_id": hid,
            "observation": observation,
            "variable": variable,
            "generated": True,
        }

    def design_test(
        self,
        hypothesis_id: str,
        test_type: str = "ab_test",
        control_group: str = "current",
        treatment: str = "modified",
    ) -> dict[str, Any]:
        """Test tasarlar.

        Args:
            hypothesis_id: Hipotez ID.
            test_type: Test tipi.
            control_group: Kontrol grubu.
            treatment: Uygulama.

        Returns:
            Tasarım bilgisi.
        """
        self._counter += 1
        eid = f"exp_{self._counter}"

        experiment = {
            "experiment_id": eid,
            "hypothesis_id": hypothesis_id,
            "test_type": test_type,
            "control_group": control_group,
            "treatment": treatment,
            "status": "designed",
            "metrics": [],
            "timestamp": time.time(),
        }
        self._experiments[eid] = experiment
        self._stats[
            "experiments_designed"
        ] += 1

        return {
            "experiment_id": eid,
            "test_type": test_type,
            "designed": True,
        }

    def isolate_variable(
        self,
        experiment_id: str,
        target_variable: str,
        controlled: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Değişken izole eder.

        Args:
            experiment_id: Deney ID.
            target_variable: Hedef değişken.
            controlled: Kontrol değişkenleri.

        Returns:
            İzolasyon bilgisi.
        """
        exp = self._experiments.get(
            experiment_id,
        )
        if not exp:
            return {
                "experiment_id": (
                    experiment_id
                ),
                "isolated": False,
            }

        controlled = controlled or []
        exp["target_variable"] = (
            target_variable
        )
        exp["controlled_variables"] = (
            controlled
        )

        isolation_quality = (
            "high"
            if len(controlled) >= 3
            else "medium"
            if len(controlled) >= 1
            else "low"
        )

        return {
            "experiment_id": experiment_id,
            "target_variable": (
                target_variable
            ),
            "controlled_count": len(
                controlled,
            ),
            "quality": isolation_quality,
            "isolated": True,
        }

    def calculate_sample_size(
        self,
        effect_size: float = 0.5,
        confidence: float = 0.95,
        power: float = 0.8,
    ) -> dict[str, Any]:
        """Örneklem boyutu hesaplar.

        Args:
            effect_size: Etki büyüklüğü.
            confidence: Güven seviyesi.
            power: Güç.

        Returns:
            Boyut bilgisi.
        """
        # Basit örneklem hesabı
        z_alpha = (
            2.576 if confidence >= 0.99
            else 1.96 if confidence >= 0.95
            else 1.645
        )
        z_beta = (
            1.28 if power >= 0.9
            else 0.842 if power >= 0.8
            else 0.524
        )

        if effect_size <= 0:
            return {
                "sample_size": 0,
                "calculated": False,
            }

        n = round(
            ((z_alpha + z_beta) ** 2)
            / (effect_size ** 2),
        )

        return {
            "sample_size": max(n, 10),
            "effect_size": effect_size,
            "confidence": confidence,
            "power": power,
            "calculated": True,
        }

    def plan_duration(
        self,
        experiment_id: str,
        daily_data_rate: float = 100.0,
        required_samples: int = 1000,
    ) -> dict[str, Any]:
        """Süre planlar.

        Args:
            experiment_id: Deney ID.
            daily_data_rate: Günlük veri.
            required_samples: Gereken örnek.

        Returns:
            Süre bilgisi.
        """
        exp = self._experiments.get(
            experiment_id,
        )
        if not exp:
            return {
                "experiment_id": (
                    experiment_id
                ),
                "planned": False,
            }

        if daily_data_rate <= 0:
            return {
                "experiment_id": (
                    experiment_id
                ),
                "planned": False,
                "reason": "Invalid data rate",
            }

        days = round(
            required_samples
            / daily_data_rate,
            1,
        )
        # Buffer ekleme
        total_days = round(days * 1.2, 1)

        exp["duration_days"] = total_days
        exp["required_samples"] = (
            required_samples
        )

        return {
            "experiment_id": experiment_id,
            "base_days": days,
            "total_days": total_days,
            "required_samples": (
                required_samples
            ),
            "planned": True,
        }

    @property
    def experiment_count(self) -> int:
        """Deney sayısı."""
        return self._stats[
            "experiments_designed"
        ]

    @property
    def hypothesis_count(self) -> int:
        """Hipotez sayısı."""
        return self._stats[
            "hypotheses_generated"
        ]
