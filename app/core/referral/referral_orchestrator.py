"""ATLAS Referans Orkestratörü.

Tam referans yönetim pipeline,
Create → Track → Reward → Optimize,
viral büyüme motoru, analitik.
"""

import logging
from typing import Any

from app.core.referral.ambassador_manager import (
    AmbassadorManager,
)
from app.core.referral.incentive_optimizer import (
    IncentiveOptimizer,
)
from app.core.referral.referral_conversion_tracker import (
    ReferralConversionTracker,
)
from app.core.referral.referral_fraud_detector import (
    ReferralFraudDetector,
)
from app.core.referral.referral_program_builder import (
    ReferralProgramBuilder,
)
from app.core.referral.reward_calculator import (
    ReferralRewardCalculator,
)
from app.core.referral.tracking_link_generator import (
    TrackingLinkGenerator,
)
from app.core.referral.viral_coefficient import (
    ViralCoefficientCalculator,
)

logger = logging.getLogger(__name__)


class ReferralOrchestrator:
    """Referans orkestratörü.

    Tüm referans bileşenlerini koordine eder.

    Attributes:
        builder: Program oluşturucu.
        links: Takip linki üretici.
        rewards: Ödül hesaplayıcı.
        ambassadors: Elçi yöneticisi.
        conversions: Dönüşüm takipçisi.
        incentives: Teşvik optimizasyonu.
        viral: Viral katsayı hesaplayıcı.
        fraud: Dolandırıcılık tespitçisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.builder = (
            ReferralProgramBuilder()
        )
        self.links = TrackingLinkGenerator()
        self.rewards = (
            ReferralRewardCalculator()
        )
        self.ambassadors = AmbassadorManager()
        self.conversions = (
            ReferralConversionTracker()
        )
        self.incentives = IncentiveOptimizer()
        self.viral = (
            ViralCoefficientCalculator()
        )
        self.fraud = ReferralFraudDetector()
        self._stats = {
            "pipelines_run": 0,
            "referrals_processed": 0,
        }

        logger.info(
            "ReferralOrchestrator "
            "baslatildi",
        )

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats["pipelines_run"]

    @property
    def processed_count(self) -> int:
        """İşlenen referans sayısı."""
        return self._stats[
            "referrals_processed"
        ]

    def create_and_share(
        self,
        referrer_id: str,
        program_name: str = "default",
    ) -> dict[str, Any]:
        """Oluştur ve paylaş pipeline.

        Args:
            referrer_id: Referansçı kimliği.
            program_name: Program adı.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Program oluştur
        prog = self.builder.design_program(
            program_name,
        )

        # 2. Link üret
        link = self.links.generate_link(
            referrer_id, program_name,
        )

        self._stats["pipelines_run"] += 1

        return {
            "program_id": prog["program_id"],
            "link_url": link["url"],
            "referrer_id": referrer_id,
            "pipeline_complete": True,
        }

    def process_referral(
        self,
        referrer_id: str,
        referred_id: str,
        value: float = 0.0,
    ) -> dict[str, Any]:
        """Referans işle pipeline.

        Args:
            referrer_id: Referansçı kimliği.
            referred_id: Davet edilen kimliği.
            value: Dönüşüm değeri.

        Returns:
            İşleme bilgisi.
        """
        # 1. Dolandırıcılık kontrol
        fraud = (
            self.fraud.detect_self_referral(
                referrer_id, referred_id,
            )
        )

        if fraud["risk"] != "clean":
            return {
                "referrer_id": referrer_id,
                "referred_id": referred_id,
                "fraud_detected": True,
                "processed": False,
            }

        # 2. Dönüşüm takip
        conv = (
            self.conversions
            .track_conversion(
                f"ref_{referrer_id}",
                referrer_id,
                referred_id,
                value,
            )
        )

        # 3. Ödül hesapla
        reward = self.rewards.calculate_reward(
            referrer_id, 10.0,
        )

        self._stats[
            "referrals_processed"
        ] += 1
        self._stats["pipelines_run"] += 1

        return {
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "conversion_id": conv[
                "conversion_id"
            ],
            "reward_amount": reward["amount"],
            "fraud_detected": False,
            "processed": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "referrals_processed": (
                self._stats[
                    "referrals_processed"
                ]
            ),
            "programs_created": (
                self.builder.program_count
            ),
            "links_generated": (
                self.links.link_count
            ),
            "rewards_calculated": (
                self.rewards.reward_count
            ),
            "ambassadors_recruited": (
                self.ambassadors
                .ambassador_count
            ),
            "conversions_tracked": (
                self.conversions
                .conversion_count
            ),
            "tests_run": (
                self.incentives.test_count
            ),
            "k_factors_calculated": (
                self.viral.calculation_count
            ),
            "fraud_checks": (
                self.fraud.check_count
            ),
        }
