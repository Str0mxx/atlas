"""
Chargeback koruyucu modulu.

Chargeback onleme, kanit toplama,
itiraz yonetimi, risk puanlama,
analitik.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ChargebackProtector:
    """Chargeback koruyucu.

    Attributes:
        _disputes: Itiraz kayitlari.
        _evidence: Kanit kayitlari.
        _risk_profiles: Risk profilleri.
        _alerts: Uyari kayitlari.
        _stats: Istatistikler.
    """

    DISPUTE_REASONS: list[str] = [
        "fraud",
        "not_received",
        "not_as_described",
        "duplicate",
        "unauthorized",
        "cancelled",
        "credit_not_processed",
        "other",
    ]

    DISPUTE_STATUSES: list[str] = [
        "opened",
        "evidence_submitted",
        "under_review",
        "won",
        "lost",
        "expired",
    ]

    def __init__(
        self,
        risk_threshold: float = 0.7,
    ) -> None:
        """Koruyucuyu baslatir.

        Args:
            risk_threshold: Risk esigi.
        """
        self._risk_threshold = (
            risk_threshold
        )
        self._disputes: dict[
            str, dict
        ] = {}
        self._evidence: dict[
            str, list
        ] = {}
        self._risk_profiles: dict[
            str, dict
        ] = {}
        self._alerts: list[dict] = []
        self._stats: dict[str, int] = {
            "disputes_opened": 0,
            "evidence_collected": 0,
            "disputes_won": 0,
            "disputes_lost": 0,
            "alerts_generated": 0,
            "risk_assessments": 0,
        }
        logger.info(
            "ChargebackProtector "
            "baslatildi"
        )

    @property
    def dispute_count(self) -> int:
        """Acik itiraz sayisi."""
        return sum(
            1
            for d in self._disputes.values()
            if d["status"] in (
                "opened",
                "evidence_submitted",
                "under_review",
            )
        )

    def open_dispute(
        self,
        transaction_id: str = "",
        amount: float = 0.0,
        reason: str = "other",
        customer_id: str = "",
        merchant_id: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Itiraz acar.

        Args:
            transaction_id: Islem ID.
            amount: Tutar.
            reason: Neden.
            customer_id: Musteri.
            merchant_id: Isyeri.
            description: Aciklama.

        Returns:
            Itiraz bilgisi.
        """
        try:
            did = f"dp_{uuid4()!s:.8}"
            self._disputes[did] = {
                "dispute_id": did,
                "transaction_id": (
                    transaction_id
                ),
                "amount": amount,
                "reason": reason,
                "customer_id": customer_id,
                "merchant_id": merchant_id,
                "description": description,
                "status": "opened",
                "opened_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "resolved_at": None,
                "outcome": None,
            }
            self._evidence[did] = []
            self._stats[
                "disputes_opened"
            ] += 1

            # Uyari
            self._alerts.append({
                "alert_id": (
                    f"al_{uuid4()!s:.8}"
                ),
                "dispute_id": did,
                "type": "dispute_opened",
                "amount": amount,
                "reason": reason,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            })
            self._stats[
                "alerts_generated"
            ] += 1

            return {
                "dispute_id": did,
                "status": "opened",
                "opened": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "opened": False,
                "error": str(e),
            }

    def collect_evidence(
        self,
        dispute_id: str = "",
        evidence_type: str = "",
        content: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Kanit toplar.

        Args:
            dispute_id: Itiraz ID.
            evidence_type: Kanit tipi.
            content: Icerik.
            source: Kaynak.

        Returns:
            Kanit bilgisi.
        """
        try:
            if (
                dispute_id
                not in self._disputes
            ):
                return {
                    "collected": False,
                    "error": (
                        "Itiraz bulunamadi"
                    ),
                }

            eid = f"ev_{uuid4()!s:.8}"
            evidence = {
                "evidence_id": eid,
                "evidence_type": (
                    evidence_type
                ),
                "content": content,
                "source": source,
                "collected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._evidence[
                dispute_id
            ].append(evidence)
            self._stats[
                "evidence_collected"
            ] += 1

            return {
                "evidence_id": eid,
                "dispute_id": dispute_id,
                "collected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "collected": False,
                "error": str(e),
            }

    def submit_evidence(
        self,
        dispute_id: str = "",
    ) -> dict[str, Any]:
        """Kanit gonderir.

        Args:
            dispute_id: Itiraz ID.

        Returns:
            Gonderim bilgisi.
        """
        try:
            dispute = self._disputes.get(
                dispute_id
            )
            if not dispute:
                return {
                    "submitted": False,
                    "error": (
                        "Itiraz bulunamadi"
                    ),
                }

            evidence = self._evidence.get(
                dispute_id, []
            )
            if not evidence:
                return {
                    "submitted": False,
                    "error": (
                        "Kanit bulunamadi"
                    ),
                }

            dispute["status"] = (
                "evidence_submitted"
            )

            return {
                "dispute_id": dispute_id,
                "evidence_count": len(
                    evidence
                ),
                "submitted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "submitted": False,
                "error": str(e),
            }

    def resolve_dispute(
        self,
        dispute_id: str = "",
        outcome: str = "won",
    ) -> dict[str, Any]:
        """Itirazi cozumler.

        Args:
            dispute_id: Itiraz ID.
            outcome: Sonuc (won/lost).

        Returns:
            Cozum bilgisi.
        """
        try:
            dispute = self._disputes.get(
                dispute_id
            )
            if not dispute:
                return {
                    "resolved": False,
                    "error": (
                        "Itiraz bulunamadi"
                    ),
                }

            dispute["status"] = outcome
            dispute["outcome"] = outcome
            dispute["resolved_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            if outcome == "won":
                self._stats[
                    "disputes_won"
                ] += 1
            else:
                self._stats[
                    "disputes_lost"
                ] += 1

            return {
                "dispute_id": dispute_id,
                "outcome": outcome,
                "resolved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "resolved": False,
                "error": str(e),
            }

    def assess_risk(
        self,
        merchant_id: str = "",
        total_transactions: int = 0,
        total_disputes: int = 0,
        total_amount: float = 0.0,
        dispute_amount: float = 0.0,
    ) -> dict[str, Any]:
        """Risk degerlendirmesi.

        Args:
            merchant_id: Isyeri ID.
            total_transactions: Toplam islem.
            total_disputes: Toplam itiraz.
            total_amount: Toplam tutar.
            dispute_amount: Itiraz tutari.

        Returns:
            Risk bilgisi.
        """
        try:
            self._stats[
                "risk_assessments"
            ] += 1

            # Oran hesapla
            dispute_rate = 0.0
            if total_transactions > 0:
                dispute_rate = (
                    total_disputes
                    / total_transactions
                )

            amount_rate = 0.0
            if total_amount > 0:
                amount_rate = (
                    dispute_amount
                    / total_amount
                )

            risk_score = round(
                (
                    dispute_rate * 0.6
                    + amount_rate * 0.4
                ),
                4,
            )

            if risk_score >= 0.1:
                risk_level = "critical"
            elif risk_score >= 0.05:
                risk_level = "high"
            elif risk_score >= 0.02:
                risk_level = "medium"
            else:
                risk_level = "low"

            profile = {
                "merchant_id": merchant_id,
                "dispute_rate": round(
                    dispute_rate, 4
                ),
                "amount_rate": round(
                    amount_rate, 4
                ),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "assessed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._risk_profiles[
                merchant_id
            ] = profile

            high_risk = (
                risk_score
                >= self._risk_threshold
            )
            if high_risk:
                self._alerts.append({
                    "alert_id": (
                        f"al_{uuid4()!s:.8}"
                    ),
                    "type": (
                        "high_chargeback_risk"
                    ),
                    "merchant_id": (
                        merchant_id
                    ),
                    "risk_score": risk_score,
                    "created_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                })
                self._stats[
                    "alerts_generated"
                ] += 1

            return {
                "merchant_id": merchant_id,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "dispute_rate": round(
                    dispute_rate, 4
                ),
                "high_risk": high_risk,
                "assessed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assessed": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik verir."""
        try:
            total = len(self._disputes)
            won = self._stats[
                "disputes_won"
            ]
            lost = self._stats[
                "disputes_lost"
            ]
            win_rate = 0.0
            if won + lost > 0:
                win_rate = round(
                    won / (won + lost), 2
                )

            total_amount = sum(
                d["amount"]
                for d in (
                    self._disputes.values()
                )
            )

            return {
                "total_disputes": total,
                "open_disputes": (
                    self.dispute_count
                ),
                "won": won,
                "lost": lost,
                "win_rate": win_rate,
                "total_amount": round(
                    total_amount, 2
                ),
                "analytics": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analytics": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_disputes": len(
                    self._disputes
                ),
                "open_disputes": (
                    self.dispute_count
                ),
                "total_evidence": sum(
                    len(e)
                    for e in (
                        self._evidence
                        .values()
                    )
                ),
                "risk_profiles": len(
                    self._risk_profiles
                ),
                "total_alerts": len(
                    self._alerts
                ),
                "risk_threshold": (
                    self._risk_threshold
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
