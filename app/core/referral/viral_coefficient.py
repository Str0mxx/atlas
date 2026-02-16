"""ATLAS Viral Katsayı Hesaplayıcı.

K-faktör hesaplama, büyüme modelleme,
döngü süresi, projeksiyon ve kıyaslama.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ViralCoefficientCalculator:
    """Viral katsayı hesaplayıcısı.

    Viral büyüme katsayılarını hesaplar,
    modeller ve kıyaslar.

    Attributes:
        _calculations: Hesaplama kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._calculations: dict[
            str, dict
        ] = {}
        self._stats = {
            "k_factors_calculated": 0,
            "projections_made": 0,
        }
        logger.info(
            "ViralCoefficientCalculator "
            "baslatildi",
        )

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats[
            "k_factors_calculated"
        ]

    @property
    def projection_count(self) -> int:
        """Projeksiyon sayısı."""
        return self._stats[
            "projections_made"
        ]

    def calculate_k_factor(
        self,
        invites_per_user: float = 0.0,
        conversion_rate: float = 0.0,
    ) -> dict[str, Any]:
        """K-faktör hesaplar.

        Args:
            invites_per_user: Kullanıcı başına
                davet.
            conversion_rate: Dönüşüm oranı.

        Returns:
            K-faktör bilgisi.
        """
        k = round(
            invites_per_user
            * conversion_rate,
            3,
        )
        viral = k >= 1.0

        if k >= 1.5:
            phase = "viral"
        elif k >= 1.0:
            phase = "growth"
        elif k >= 0.5:
            phase = "seed"
        else:
            phase = "plateau"

        cid = (
            f"kf_{len(self._calculations)}"
        )
        self._calculations[cid] = {
            "k_factor": k,
            "phase": phase,
        }
        self._stats[
            "k_factors_calculated"
        ] += 1

        return {
            "calc_id": cid,
            "k_factor": k,
            "is_viral": viral,
            "phase": phase,
            "calculated": True,
        }

    def model_growth(
        self,
        initial_users: int = 100,
        k_factor: float = 0.8,
        periods: int = 6,
    ) -> dict[str, Any]:
        """Büyüme modelleme yapar.

        Args:
            initial_users: Başlangıç kullanıcı.
            k_factor: K-faktör.
            periods: Dönem sayısı.

        Returns:
            Model bilgisi.
        """
        users = float(initial_users)
        timeline = [initial_users]

        for _ in range(periods):
            new = users * k_factor
            users += new
            timeline.append(round(users))

        return {
            "initial_users": initial_users,
            "k_factor": k_factor,
            "final_users": timeline[-1],
            "growth_multiple": round(
                timeline[-1] / initial_users,
                2,
            ),
            "timeline": timeline,
            "modeled": True,
        }

    def measure_cycle_time(
        self,
        invite_to_signup_hours: float = 0.0,
        signup_to_invite_hours: float = 0.0,
    ) -> dict[str, Any]:
        """Döngü süresi ölçer.

        Args:
            invite_to_signup_hours: Davetten
                kayıda süre.
            signup_to_invite_hours: Kayıttan
                davete süre.

        Returns:
            Döngü bilgisi.
        """
        total = (
            invite_to_signup_hours
            + signup_to_invite_hours
        )

        if total <= 24:
            speed = "fast"
        elif total <= 72:
            speed = "normal"
        else:
            speed = "slow"

        return {
            "invite_to_signup": (
                invite_to_signup_hours
            ),
            "signup_to_invite": (
                signup_to_invite_hours
            ),
            "total_cycle_hours": total,
            "speed": speed,
            "measured": True,
        }

    def project_growth(
        self,
        current_users: int = 0,
        k_factor: float = 0.0,
        cycle_days: int = 7,
        target_users: int = 10000,
    ) -> dict[str, Any]:
        """Büyüme projeksiyonu yapar.

        Args:
            current_users: Mevcut kullanıcı.
            k_factor: K-faktör.
            cycle_days: Döngü günü.
            target_users: Hedef kullanıcı.

        Returns:
            Projeksiyon bilgisi.
        """
        if k_factor <= 0 or current_users <= 0:
            return {
                "reachable": False,
                "projected": True,
            }

        users = float(current_users)
        cycles = 0
        while users < target_users:
            users += users * k_factor
            cycles += 1
            if cycles > 100:
                break

        days = cycles * cycle_days
        self._stats[
            "projections_made"
        ] += 1

        return {
            "current_users": current_users,
            "target_users": target_users,
            "cycles_needed": cycles,
            "days_needed": days,
            "reachable": cycles <= 100,
            "projected": True,
        }

    def benchmark(
        self,
        k_factor: float = 0.0,
        industry: str = "saas",
    ) -> dict[str, Any]:
        """Kıyaslama yapar.

        Args:
            k_factor: K-faktör.
            industry: Sektör.

        Returns:
            Kıyaslama bilgisi.
        """
        benchmarks = {
            "saas": 0.4,
            "ecommerce": 0.3,
            "social": 0.8,
            "gaming": 0.6,
            "fintech": 0.25,
        }
        industry_avg = benchmarks.get(
            industry, 0.3,
        )

        if k_factor >= industry_avg * 2:
            rating = "exceptional"
        elif k_factor >= industry_avg:
            rating = "above_average"
        elif k_factor >= industry_avg * 0.5:
            rating = "average"
        else:
            rating = "below_average"

        return {
            "k_factor": k_factor,
            "industry": industry,
            "industry_average": industry_avg,
            "rating": rating,
            "benchmarked": True,
        }
