"""ATLAS Hiz Sinir Orkestrator modulu.

Tam hiz sinirlama, coklu algoritma,
dagitik sinirlama, izleme, yapilandirma.
"""

import logging
import time
from typing import Any

from app.core.ratelimit.leaky_bucket import (
    LeakyBucket,
)
from app.core.ratelimit.quota_manager import (
    QuotaManager,
)
from app.core.ratelimit.rate_analytics import (
    RateAnalytics,
)
from app.core.ratelimit.rate_policy import (
    RatePolicy,
)
from app.core.ratelimit.sliding_window import (
    SlidingWindow,
)
from app.core.ratelimit.throttle_controller import (
    ThrottleController,
)
from app.core.ratelimit.token_bucket import (
    TokenBucket,
)
from app.core.ratelimit.violation_handler import (
    ViolationHandler,
)

logger = logging.getLogger(__name__)


class RateLimitOrchestrator:
    """Hiz sinir orkestrator.

    Tum hiz sinirlama bilesenleri koordine eder.

    Attributes:
        token_bucket: Token kovasi.
        sliding_window: Kayan pencere.
        leaky_bucket: Sizdiran kova.
        quotas: Kota yoneticisi.
        throttle: Kisma kontrolcusu.
        policies: Hiz politikasi.
        violations: Ihlal yoneticisi.
        analytics: Hiz analitigi.
    """

    def __init__(
        self,
        default_rpm: int = 60,
        burst_multiplier: float = 1.5,
        penalty_minutes: int = 15,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_rpm: Varsayilan dakika basina istek.
            burst_multiplier: Patlama carpani.
            penalty_minutes: Ceza suresi (dk).
        """
        self.token_bucket = TokenBucket(
            default_capacity=default_rpm,
            default_refill_rate=default_rpm / 60.0,
            burst_multiplier=burst_multiplier,
        )
        self.sliding_window = SlidingWindow(
            default_window_size=60,
            default_max_requests=default_rpm,
        )
        self.leaky_bucket = LeakyBucket(
            default_capacity=default_rpm * 2,
            default_leak_rate=default_rpm / 60.0,
        )
        self.quotas = QuotaManager()
        self.throttle = ThrottleController()
        self.policies = RatePolicy()
        self.violations = ViolationHandler(
            penalty_minutes=penalty_minutes,
        )
        self.analytics = RateAnalytics()

        self._default_rpm = default_rpm
        self._default_algorithm = "token_bucket"
        self._stats = {
            "total_checks": 0,
            "allowed": 0,
            "rejected": 0,
        }

        logger.info(
            "RateLimitOrchestrator baslatildi",
        )

    def check_rate_limit(
        self,
        subject_id: str,
        endpoint: str = "",
        tokens: int = 1,
        algorithm: str | None = None,
    ) -> dict[str, Any]:
        """Hiz siniri kontrolu yapar (tam pipeline).

        Args:
            subject_id: Konu ID.
            endpoint: Endpoint.
            tokens: Token sayisi.
            algorithm: Algoritma (opsiyonel).

        Returns:
            Kontrol sonucu.
        """
        self._stats["total_checks"] += 1
        algo = algorithm or self._default_algorithm

        # Ban kontrolu
        ban_check = self.violations.check_banned(
            subject_id,
        )
        if ban_check.get("banned"):
            self.analytics.record_request(
                subject_id, endpoint, allowed=False,
            )
            self._stats["rejected"] += 1
            return {
                "allowed": False,
                "reason": "banned",
                "retry_after": ban_check[
                    "retry_after"
                ],
            }

        # Kisma kontrolu
        throttle_result = self.throttle.check(
            target=endpoint,
        )
        if not throttle_result["allowed"]:
            self.analytics.record_request(
                subject_id, endpoint, allowed=False,
            )
            self._stats["rejected"] += 1
            return {
                "allowed": False,
                "reason": "throttled",
                "delay_ms": throttle_result.get(
                    "delay_ms", 0,
                ),
            }

        # Politika al
        policy = self.policies.evaluate(
            subject_id, endpoint,
        )

        # Algoritma kontrolu
        key = f"{subject_id}:{endpoint or 'default'}"

        if algo == "token_bucket":
            result = self._check_token_bucket(
                key, tokens, policy,
            )
        elif algo == "sliding_window":
            result = self._check_sliding_window(
                key, tokens, policy,
            )
        elif algo == "leaky_bucket":
            result = self._check_leaky_bucket(
                key, tokens, policy,
            )
        else:
            result = self._check_token_bucket(
                key, tokens, policy,
            )

        allowed = result.get("allowed", False)

        # Analitik kaydi
        self.analytics.record_request(
            subject_id, endpoint, allowed=allowed,
        )

        if allowed:
            self._stats["allowed"] += 1
        else:
            self._stats["rejected"] += 1
            # Ihlal kaydi
            self.violations.record_violation(
                subject_id,
                violation_type="rate_exceeded",
                details={
                    "endpoint": endpoint,
                    "algorithm": algo,
                },
            )

        result["subject_id"] = subject_id
        result["endpoint"] = endpoint
        return result

    def check_quota(
        self,
        subject_id: str,
        quota_id: str,
        amount: int = 1,
    ) -> dict[str, Any]:
        """Kota kontrolu yapar.

        Args:
            subject_id: Konu ID.
            quota_id: Kota ID.
            amount: Miktar.

        Returns:
            Kontrol sonucu.
        """
        result = self.quotas.consume(
            quota_id, amount,
        )

        if not result.get("allowed", False):
            self.violations.record_violation(
                subject_id,
                violation_type="quota_exceeded",
                details={"quota_id": quota_id},
            )

        return result

    def setup_rate_limit(
        self,
        subject_id: str,
        endpoint: str = "",
        rpm: int | None = None,
        algorithm: str = "token_bucket",
    ) -> dict[str, Any]:
        """Hiz siniri kurar.

        Args:
            subject_id: Konu ID.
            endpoint: Endpoint.
            rpm: Dakika basina istek.
            algorithm: Algoritma.

        Returns:
            Kurulum sonucu.
        """
        key = f"{subject_id}:{endpoint or 'default'}"
        rate = rpm or self._default_rpm

        if algorithm == "token_bucket":
            self.token_bucket.create_bucket(
                key,
                capacity=rate,
                refill_rate=rate / 60.0,
            )
        elif algorithm == "sliding_window":
            self.sliding_window.create_window(
                key,
                window_size=60,
                max_requests=rate,
            )
        elif algorithm == "leaky_bucket":
            self.leaky_bucket.create_bucket(
                key,
                capacity=rate * 2,
                leak_rate=rate / 60.0,
            )

        return {
            "key": key,
            "algorithm": algorithm,
            "rpm": rate,
            "status": "configured",
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "total_checks": (
                self._stats["total_checks"]
            ),
            "allowed": self._stats["allowed"],
            "rejected": self._stats["rejected"],
            "token_buckets": (
                self.token_bucket.bucket_count
            ),
            "sliding_windows": (
                self.sliding_window.window_count
            ),
            "leaky_buckets": (
                self.leaky_bucket.bucket_count
            ),
            "quotas": self.quotas.quota_count,
            "throttle_rules": (
                self.throttle.rule_count
            ),
            "policies": (
                self.policies.policy_count
            ),
            "violations": (
                self.violations.violation_count
            ),
            "bans": self.violations.ban_count,
        }

    def get_analytics_report(
        self,
    ) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "overview": self.analytics.get_report(),
            "capacity": (
                self.analytics.capacity_report()
            ),
            "trends": (
                self.analytics.analyze_trends()
            ),
            "top_subjects": (
                self.analytics.get_top_subjects()
            ),
            "top_endpoints": (
                self.analytics.get_top_endpoints()
            ),
        }

    def _check_token_bucket(
        self,
        key: str,
        tokens: int,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Token bucket kontrolu.

        Args:
            key: Anahtar.
            tokens: Token sayisi.
            policy: Politika.

        Returns:
            Kontrol sonucu.
        """
        if not self.token_bucket.get_bucket(key):
            rpm = policy.get(
                "rpm", self._default_rpm,
            )
            self.token_bucket.create_bucket(
                key,
                capacity=rpm,
                refill_rate=rpm / 60.0,
            )

        return self.token_bucket.consume(
            key, tokens,
        )

    def _check_sliding_window(
        self,
        key: str,
        tokens: int,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Sliding window kontrolu.

        Args:
            key: Anahtar.
            tokens: Token sayisi.
            policy: Politika.

        Returns:
            Kontrol sonucu.
        """
        if not self.sliding_window.get_window(key):
            rpm = policy.get(
                "rpm", self._default_rpm,
            )
            self.sliding_window.create_window(
                key,
                window_size=60,
                max_requests=rpm,
            )

        return self.sliding_window.record(
            key, tokens,
        )

    def _check_leaky_bucket(
        self,
        key: str,
        tokens: int,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        """Leaky bucket kontrolu.

        Args:
            key: Anahtar.
            tokens: Token sayisi.
            policy: Politika.

        Returns:
            Kontrol sonucu.
        """
        if not self.leaky_bucket.get_bucket(key):
            rpm = policy.get(
                "rpm", self._default_rpm,
            )
            self.leaky_bucket.create_bucket(
                key,
                capacity=rpm * 2,
                leak_rate=rpm / 60.0,
            )

        return self.leaky_bucket.add(
            key, tokens,
        )

    @property
    def total_checks(self) -> int:
        """Toplam kontrol sayisi."""
        return self._stats["total_checks"]

    @property
    def allowed_total(self) -> int:
        """Toplam izin verilen."""
        return self._stats["allowed"]

    @property
    def rejected_total(self) -> int:
        """Toplam reddedilen."""
        return self._stats["rejected"]
