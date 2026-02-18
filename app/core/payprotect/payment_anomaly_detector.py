"""
Odeme anomali tespitcisi modulu.

Olagan disi kalipler, dolandiricilik
gostergeleri, davranissal analiz,
gercek zamanli puanlama, engelleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PaymentAnomalyDetector:
    """Odeme anomali tespitcisi.

    Attributes:
        _profiles: Kullanici profilleri.
        _anomalies: Anomali kayitlari.
        _rules: Tespit kurallari.
        _blocks: Engelleme kayitlari.
        _stats: Istatistikler.
    """

    ANOMALY_TYPES: list[str] = [
        "unusual_amount",
        "unusual_location",
        "unusual_time",
        "rapid_transactions",
        "new_merchant",
        "card_testing",
        "velocity_spike",
    ]

    RISK_LEVELS: list[str] = [
        "low",
        "medium",
        "high",
        "critical",
    ]

    def __init__(
        self,
        block_threshold: float = 0.8,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            block_threshold: Engel esigi.
        """
        self._block_threshold = (
            block_threshold
        )
        self._profiles: dict[
            str, dict
        ] = {}
        self._anomalies: list[dict] = []
        self._rules: dict[
            str, dict
        ] = {}
        self._blocks: list[dict] = []
        self._stats: dict[str, int] = {
            "profiles_created": 0,
            "analyses_run": 0,
            "anomalies_detected": 0,
            "blocks_triggered": 0,
            "false_positives": 0,
        }
        self._init_default_rules()
        logger.info(
            "PaymentAnomalyDetector "
            "baslatildi"
        )

    def _init_default_rules(
        self,
    ) -> None:
        """Varsayilan kurallari yukler."""
        defaults = {
            "high_amount": {
                "type": "unusual_amount",
                "threshold": 5000.0,
                "weight": 0.3,
            },
            "rapid_txn": {
                "type": (
                    "rapid_transactions"
                ),
                "threshold": 5,
                "weight": 0.25,
            },
            "card_test": {
                "type": "card_testing",
                "threshold": 3,
                "weight": 0.35,
            },
            "velocity": {
                "type": "velocity_spike",
                "threshold": 10,
                "weight": 0.2,
            },
        }
        self._rules = defaults

    @property
    def anomaly_count(self) -> int:
        """Anomali sayisi."""
        return len(self._anomalies)

    def create_profile(
        self,
        user_id: str = "",
        avg_amount: float = 0.0,
        avg_daily_count: int = 0,
        common_merchants: (
            list[str] | None
        ) = None,
        common_locations: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Kullanici profili olusturur.

        Args:
            user_id: Kullanici ID.
            avg_amount: Ort tutar.
            avg_daily_count: Ort gunluk.
            common_merchants: Bilinen isyeri.
            common_locations: Bilinen konum.

        Returns:
            Profil bilgisi.
        """
        try:
            self._profiles[user_id] = {
                "user_id": user_id,
                "avg_amount": avg_amount,
                "avg_daily_count": (
                    avg_daily_count
                ),
                "common_merchants": (
                    common_merchants or []
                ),
                "common_locations": (
                    common_locations or []
                ),
                "transaction_count": 0,
            }
            self._stats[
                "profiles_created"
            ] += 1

            return {
                "user_id": user_id,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def analyze_transaction(
        self,
        user_id: str = "",
        amount: float = 0.0,
        merchant_id: str = "",
        location: str = "",
        card_present: bool = True,
        recent_count: int = 0,
    ) -> dict[str, Any]:
        """Islemi analiz eder.

        Args:
            user_id: Kullanici ID.
            amount: Tutar.
            merchant_id: Isyeri.
            location: Konum.
            card_present: Kart mevcut.
            recent_count: Son islem sayisi.

        Returns:
            Analiz sonucu.
        """
        try:
            self._stats[
                "analyses_run"
            ] += 1
            risk_score = 0.0
            flags: list[dict] = []
            profile = self._profiles.get(
                user_id
            )

            # Yuksek tutar
            rule = self._rules.get(
                "high_amount", {}
            )
            threshold = rule.get(
                "threshold", 5000
            )
            if amount > threshold:
                risk_score += rule.get(
                    "weight", 0.3
                )
                flags.append({
                    "type": "unusual_amount",
                    "detail": (
                        f"Yuksek: "
                        f"{amount}"
                    ),
                })

            # Profil varsa karsilastir
            if profile:
                avg = profile["avg_amount"]
                if (
                    avg > 0
                    and amount > avg * 3
                ):
                    risk_score += 0.2
                    flags.append({
                        "type": (
                            "unusual_amount"
                        ),
                        "detail": (
                            f"Ort {avg} "
                            f"ustu: {amount}"
                        ),
                    })

                merchants = profile[
                    "common_merchants"
                ]
                if (
                    merchants
                    and merchant_id
                    not in merchants
                ):
                    risk_score += 0.1
                    flags.append({
                        "type": (
                            "new_merchant"
                        ),
                        "detail": (
                            f"Yeni isyeri: "
                            f"{merchant_id}"
                        ),
                    })

                locs = profile[
                    "common_locations"
                ]
                if (
                    locs
                    and location
                    and location not in locs
                ):
                    risk_score += 0.15
                    flags.append({
                        "type": (
                            "unusual_location"
                        ),
                        "detail": (
                            f"Yeni konum: "
                            f"{location}"
                        ),
                    })

            # Hizli islem
            vrule = self._rules.get(
                "rapid_txn", {}
            )
            vthresh = vrule.get(
                "threshold", 5
            )
            if recent_count > vthresh:
                risk_score += vrule.get(
                    "weight", 0.25
                )
                flags.append({
                    "type": (
                        "rapid_transactions"
                    ),
                    "detail": (
                        f"{recent_count} "
                        f"hizli islem"
                    ),
                })

            # Kart testi
            if (
                amount < 1.0
                and recent_count > 2
            ):
                risk_score += 0.35
                flags.append({
                    "type": "card_testing",
                    "detail": (
                        "Kart test kalıbı"
                    ),
                })

            risk_score = min(
                risk_score, 1.0
            )

            # Risk seviyesi
            if risk_score >= 0.8:
                risk_level = "critical"
            elif risk_score >= 0.5:
                risk_level = "high"
            elif risk_score >= 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"

            # Anomali kaydi
            if flags:
                aid = f"an_{uuid4()!s:.8}"
                anomaly = {
                    "anomaly_id": aid,
                    "user_id": user_id,
                    "amount": amount,
                    "risk_score": round(
                        risk_score, 2
                    ),
                    "risk_level": risk_level,
                    "flags": flags,
                    "detected_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                }
                self._anomalies.append(
                    anomaly
                )
                self._stats[
                    "anomalies_detected"
                ] += 1

            # Engelleme
            blocked = (
                risk_score
                >= self._block_threshold
            )
            if blocked:
                bid = f"bl_{uuid4()!s:.8}"
                self._blocks.append({
                    "block_id": bid,
                    "user_id": user_id,
                    "amount": amount,
                    "risk_score": round(
                        risk_score, 2
                    ),
                    "blocked_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                })
                self._stats[
                    "blocks_triggered"
                ] += 1

            return {
                "user_id": user_id,
                "amount": amount,
                "risk_score": round(
                    risk_score, 2
                ),
                "risk_level": risk_level,
                "flags": flags,
                "blocked": blocked,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def mark_false_positive(
        self,
        anomaly_id: str = "",
    ) -> dict[str, Any]:
        """Yanlis pozitif isaretle.

        Args:
            anomaly_id: Anomali ID.

        Returns:
            Isaret bilgisi.
        """
        try:
            for a in self._anomalies:
                if (
                    a["anomaly_id"]
                    == anomaly_id
                ):
                    a["false_positive"] = (
                        True
                    )
                    self._stats[
                        "false_positives"
                    ] += 1
                    return {
                        "anomaly_id": (
                            anomaly_id
                        ),
                        "marked": True,
                    }

            return {
                "marked": False,
                "error": (
                    "Anomali bulunamadi"
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "marked": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_profiles": len(
                    self._profiles
                ),
                "total_anomalies": len(
                    self._anomalies
                ),
                "total_blocks": len(
                    self._blocks
                ),
                "block_threshold": (
                    self._block_threshold
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
