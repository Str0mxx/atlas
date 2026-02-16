"""ATLAS Kriz Simülasyon Çalıştırıcı modülü.

Tatbikat yürütme, senaryo testi,
yanıt zamanlama, boşluk tespiti,
eğitim desteği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CrisisSimulationRunner:
    """Kriz simülasyon çalıştırıcı.

    Kriz simülasyonlarını çalıştırır.

    Attributes:
        _simulations: Simülasyon kayıtları.
        _gaps: Tespit edilen boşluklar.
    """

    def __init__(self) -> None:
        """Çalıştırıcıyı başlatır."""
        self._simulations: dict[
            str, dict[str, Any]
        ] = {}
        self._gaps: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "drills_executed": 0,
            "gaps_identified": 0,
        }

        logger.info(
            "CrisisSimulationRunner "
            "baslatildi",
        )

    def execute_drill(
        self,
        drill_name: str,
        drill_type: str = "tabletop",
        participants: list[str]
        | None = None,
        scenario: str = "",
    ) -> dict[str, Any]:
        """Tatbikat yürütür.

        Args:
            drill_name: Tatbikat adı.
            drill_type: Tatbikat tipi.
            participants: Katılımcılar.
            scenario: Senaryo.

        Returns:
            Yürütme bilgisi.
        """
        participants = participants or []
        self._counter += 1
        sid = f"sim_{self._counter}"

        self._simulations[sid] = {
            "simulation_id": sid,
            "name": drill_name,
            "type": drill_type,
            "participants": participants,
            "scenario": scenario,
            "status": "completed",
            "start_time": time.time(),
            "end_time": time.time(),
            "response_times": {},
        }

        self._stats[
            "drills_executed"
        ] += 1

        return {
            "simulation_id": sid,
            "name": drill_name,
            "participant_count": len(
                participants,
            ),
            "executed": True,
        }

    def test_scenario(
        self,
        scenario_name: str,
        crisis_type: str = "outage",
        expected_response_min: int = 30,
    ) -> dict[str, Any]:
        """Senaryo testi yapar.

        Args:
            scenario_name: Senaryo adı.
            crisis_type: Kriz tipi.
            expected_response_min: Beklenen
                yanıt süresi (dk).

        Returns:
            Test bilgisi.
        """
        self._counter += 1
        sid = f"sim_{self._counter}"

        simulated_time = (
            expected_response_min * 0.8
        )

        passed = (
            simulated_time
            <= expected_response_min
        )

        self._simulations[sid] = {
            "simulation_id": sid,
            "name": scenario_name,
            "type": "scenario_test",
            "crisis_type": crisis_type,
            "expected_min": (
                expected_response_min
            ),
            "actual_min": simulated_time,
            "passed": passed,
            "status": "completed",
        }

        return {
            "simulation_id": sid,
            "scenario": scenario_name,
            "passed": passed,
            "actual_minutes": simulated_time,
            "tested": True,
        }

    def measure_response_time(
        self,
        simulation_id: str,
        responder: str,
        response_seconds: float = 0,
    ) -> dict[str, Any]:
        """Yanıt zamanlama ölçer.

        Args:
            simulation_id: Simülasyon kimliği.
            responder: Yanıtlayan.
            response_seconds: Yanıt süresi.

        Returns:
            Ölçüm bilgisi.
        """
        sim = self._simulations.get(
            simulation_id,
        )
        if not sim:
            return {
                "simulation_id": (
                    simulation_id
                ),
                "found": False,
            }

        if "response_times" not in sim:
            sim["response_times"] = {}
        sim["response_times"][
            responder
        ] = response_seconds

        within_target = (
            response_seconds <= 300
        )

        return {
            "simulation_id": (
                simulation_id
            ),
            "responder": responder,
            "seconds": response_seconds,
            "within_target": within_target,
            "measured": True,
        }

    def identify_gaps(
        self,
        simulation_id: str,
    ) -> dict[str, Any]:
        """Boşlukları tespit eder.

        Args:
            simulation_id: Simülasyon kimliği.

        Returns:
            Tespit bilgisi.
        """
        sim = self._simulations.get(
            simulation_id,
        )
        if not sim:
            return {
                "simulation_id": (
                    simulation_id
                ),
                "found": False,
            }

        gaps = []
        response_times = sim.get(
            "response_times", {},
        )

        for resp, secs in (
            response_times.items()
        ):
            if secs > 300:
                gaps.append({
                    "type": "slow_response",
                    "responder": resp,
                    "seconds": secs,
                })

        if not sim.get(
            "participants", [],
        ):
            gaps.append({
                "type": "no_participants",
                "detail": (
                    "No participants "
                    "in drill"
                ),
            })

        for gap in gaps:
            self._gaps.append(gap)
            self._stats[
                "gaps_identified"
            ] += 1

        return {
            "simulation_id": (
                simulation_id
            ),
            "gaps": gaps,
            "gap_count": len(gaps),
            "identified": True,
        }

    def generate_training(
        self,
        gap_type: str = "general",
    ) -> dict[str, Any]:
        """Eğitim desteği üretir.

        Args:
            gap_type: Boşluk tipi.

        Returns:
            Eğitim bilgisi.
        """
        training_map = {
            "slow_response": {
                "module": (
                    "Rapid Response Training"
                ),
                "duration_hours": 2,
            },
            "no_participants": {
                "module": (
                    "Crisis Awareness"
                ),
                "duration_hours": 1,
            },
            "general": {
                "module": (
                    "Crisis Management 101"
                ),
                "duration_hours": 4,
            },
        }

        training = training_map.get(
            gap_type,
            training_map["general"],
        )

        return {
            "gap_type": gap_type,
            "module": training["module"],
            "duration_hours": training[
                "duration_hours"
            ],
            "generated": True,
        }

    @property
    def drill_count(self) -> int:
        """Tatbikat sayısı."""
        return self._stats[
            "drills_executed"
        ]

    @property
    def gap_count(self) -> int:
        """Boşluk sayısı."""
        return self._stats[
            "gaps_identified"
        ]
