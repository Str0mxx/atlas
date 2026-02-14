"""ATLAS Yuk Testi modulu.

Esanli kullanicilar, verimlilik testi,
stres testi, ani yuk testi
ve dayaniklilik testi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LoadTester:
    """Yuk test edici.

    Sistem yuk testlerini yonetir
    ve sonuclari analiz eder.

    Attributes:
        _scenarios: Test senaryolari.
        _results: Test sonuclari.
    """

    def __init__(
        self,
        default_users: int = 10,
        default_duration: int = 60,
    ) -> None:
        """Yuk test edicisini baslatir.

        Args:
            default_users: Varsayilan kullanici.
            default_duration: Varsayilan sure (sn).
        """
        self._default_users = default_users
        self._default_duration = default_duration
        self._scenarios: dict[
            str, dict[str, Any]
        ] = {}
        self._results: list[
            dict[str, Any]
        ] = []

        logger.info(
            "LoadTester baslatildi",
        )

    def create_scenario(
        self,
        name: str,
        endpoint: str,
        method: str = "GET",
        users: int | None = None,
        duration: int | None = None,
        ramp_up: int = 0,
    ) -> dict[str, Any]:
        """Senaryo olusturur.

        Args:
            name: Senaryo adi.
            endpoint: Hedef endpoint.
            method: HTTP metodu.
            users: Kullanici sayisi.
            duration: Sure (sn).
            ramp_up: Rampa suresi (sn).

        Returns:
            Senaryo bilgisi.
        """
        scenario = {
            "name": name,
            "endpoint": endpoint,
            "method": method,
            "users": users or self._default_users,
            "duration": (
                duration or self._default_duration
            ),
            "ramp_up": ramp_up,
            "created_at": time.time(),
        }
        self._scenarios[name] = scenario
        return scenario

    def run_throughput_test(
        self,
        name: str,
        requests_per_second: int = 100,
        duration: int = 10,
    ) -> dict[str, Any]:
        """Verimlilik testi calistirir.

        Args:
            name: Test adi.
            requests_per_second: Saniyedeki istek.
            duration: Sure (sn).

        Returns:
            Test sonucu.
        """
        total_requests = (
            requests_per_second * duration
        )
        # Simulasyon sonuclari
        avg_response = 50.0 + (
            requests_per_second * 0.1
        )
        error_rate = min(
            0.05,
            requests_per_second / 10000,
        )
        throughput = requests_per_second * (
            1 - error_rate
        )

        result = {
            "name": name,
            "type": "throughput",
            "total_requests": total_requests,
            "requests_per_second": (
                requests_per_second
            ),
            "duration": duration,
            "avg_response_ms": round(
                avg_response, 2,
            ),
            "error_rate": round(error_rate, 4),
            "throughput": round(throughput, 2),
            "timestamp": time.time(),
        }
        self._results.append(result)
        return result

    def run_stress_test(
        self,
        name: str,
        start_users: int = 10,
        max_users: int = 1000,
        step: int = 50,
    ) -> dict[str, Any]:
        """Stres testi calistirir.

        Args:
            name: Test adi.
            start_users: Baslangic kullanici.
            max_users: Maks kullanici.
            step: Adim buyuklugu.

        Returns:
            Test sonucu.
        """
        steps = []
        breaking_point = 0

        for users in range(
            start_users, max_users + 1, step,
        ):
            response_time = 20 + (users * 0.5)
            error_rate = max(
                0, (users - 500) / 5000,
            )

            step_result = {
                "users": users,
                "avg_response_ms": round(
                    response_time, 2,
                ),
                "error_rate": round(
                    error_rate, 4,
                ),
            }
            steps.append(step_result)

            if error_rate > 0.05 and not breaking_point:
                breaking_point = users

        result = {
            "name": name,
            "type": "stress",
            "start_users": start_users,
            "max_users": max_users,
            "breaking_point": breaking_point,
            "steps": steps,
            "timestamp": time.time(),
        }
        self._results.append(result)
        return result

    def run_spike_test(
        self,
        name: str,
        base_users: int = 10,
        spike_users: int = 500,
        spike_duration: int = 30,
    ) -> dict[str, Any]:
        """Ani yuk testi calistirir.

        Args:
            name: Test adi.
            base_users: Temel kullanici.
            spike_users: Ani yuk kullanici.
            spike_duration: Ani yuk suresi (sn).

        Returns:
            Test sonucu.
        """
        base_response = 20 + base_users * 0.1
        spike_response = 20 + spike_users * 0.5
        recovery_time = spike_users * 0.02

        result = {
            "name": name,
            "type": "spike",
            "base_users": base_users,
            "spike_users": spike_users,
            "spike_duration": spike_duration,
            "base_response_ms": round(
                base_response, 2,
            ),
            "spike_response_ms": round(
                spike_response, 2,
            ),
            "recovery_time_s": round(
                recovery_time, 2,
            ),
            "timestamp": time.time(),
        }
        self._results.append(result)
        return result

    def run_endurance_test(
        self,
        name: str,
        users: int = 50,
        duration_hours: float = 1.0,
    ) -> dict[str, Any]:
        """Dayaniklilik testi calistirir.

        Args:
            name: Test adi.
            users: Kullanici sayisi.
            duration_hours: Sure (saat).

        Returns:
            Test sonucu.
        """
        total_requests = int(
            users * duration_hours * 3600 * 0.5
        )
        memory_start_mb = 256
        memory_end_mb = 256 + int(
            duration_hours * 10,
        )
        memory_leak = memory_end_mb > (
            memory_start_mb * 1.2
        )

        result = {
            "name": name,
            "type": "endurance",
            "users": users,
            "duration_hours": duration_hours,
            "total_requests": total_requests,
            "memory_start_mb": memory_start_mb,
            "memory_end_mb": memory_end_mb,
            "memory_leak_detected": memory_leak,
            "avg_response_ms": round(
                20 + users * 0.2, 2,
            ),
            "timestamp": time.time(),
        }
        self._results.append(result)
        return result

    def get_results(
        self,
        test_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Sonuclari getirir.

        Args:
            test_type: Test tipi filtresi.

        Returns:
            Sonuc listesi.
        """
        if test_type:
            return [
                r for r in self._results
                if r.get("type") == test_type
            ]
        return list(self._results)

    def get_scenario(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Senaryo getirir.

        Args:
            name: Senaryo adi.

        Returns:
            Senaryo veya None.
        """
        return self._scenarios.get(name)

    @property
    def scenario_count(self) -> int:
        """Senaryo sayisi."""
        return len(self._scenarios)

    @property
    def result_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._results)
