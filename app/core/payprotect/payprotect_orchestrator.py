"""
PayProtect orkestratoru modulu.

Tam odeme korumasi,
Tokenize -> Validate -> Process -> Protect,
PCI-DSS uyumlu, analitik.
"""

import logging
from typing import Any

from .card_tokenizer import CardTokenizer
from .chargeback_protector import (
    ChargebackProtector,
)
from .dual_approval_gate import (
    DualApprovalGate,
)
from .financial_data_isolator import (
    FinancialDataIsolator,
)
from .payment_anomaly_detector import (
    PaymentAnomalyDetector,
)
from .pci_dss_enforcer import (
    PCIDSSEnforcer,
)
from .secure_payment_gateway import (
    SecurePaymentGateway,
)
from .transaction_limiter import (
    TransactionLimiter,
)

logger = logging.getLogger(__name__)


class PayProtectOrchestrator:
    """PayProtect orkestratoru.

    Attributes:
        tokenizer: Kart tokenizer.
        pci: PCI-DSS uygulayici.
        limiter: Islem sinırlayici.
        anomaly: Anomali tespitcisi.
        gate: Cift onay kapisi.
        isolator: Veri izolasyoncusu.
        gateway: Odeme gecidi.
        chargeback: Chargeback koruyucu.
    """

    def __init__(
        self,
        block_threshold: float = 0.8,
        dual_approval_threshold: (
            float
        ) = 10000.0,
        compliance_level: str = "level_1",
        max_retries: int = 3,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            block_threshold: Engel esigi.
            dual_approval_threshold: Onay.
            compliance_level: PCI seviye.
            max_retries: Maks deneme.
        """
        self.tokenizer = CardTokenizer()
        self.pci = PCIDSSEnforcer(
            compliance_level=(
                compliance_level
            ),
        )
        self.limiter = TransactionLimiter()
        self.anomaly = (
            PaymentAnomalyDetector(
                block_threshold=(
                    block_threshold
                ),
            )
        )
        self.gate = DualApprovalGate(
            threshold=(
                dual_approval_threshold
            ),
        )
        self.isolator = (
            FinancialDataIsolator()
        )
        self.gateway = (
            SecurePaymentGateway(
                max_retries=max_retries,
            )
        )
        self.chargeback = (
            ChargebackProtector()
        )
        logger.info(
            "PayProtectOrchestrator "
            "baslatildi"
        )

    def tokenize_card(
        self,
        card_number: str = "",
        card_type: str = "unknown",
        holder_name: str = "",
        expiry_month: int = 0,
        expiry_year: int = 0,
        merchant_id: str = "",
    ) -> dict[str, Any]:
        """Karti tokenize eder.

        Args:
            card_number: Kart numarasi.
            card_type: Kart tipi.
            holder_name: Kart sahibi.
            expiry_month: Son kullanim ay.
            expiry_year: Son kullanim yil.
            merchant_id: Isyeri ID.

        Returns:
            Token bilgisi.
        """
        try:
            # PCI kontrol
            self.pci.check_data_storage(
                data_type="pan",
                is_tokenized=True,
            )

            # Veri izolasyonu
            self.isolator.encrypt_data(
                data_id=(
                    f"card_{card_number[-4:]}"
                ),
                data_class="card_data",
                zone_name="pci_zone",
            )

            # Tokenize
            result = (
                self.tokenizer.tokenize(
                    card_number=card_number,
                    card_type=card_type,
                    holder_name=holder_name,
                    expiry_month=expiry_month,
                    expiry_year=expiry_year,
                    merchant_id=merchant_id,
                )
            )

            # Denetim kaydi
            if result.get("tokenized"):
                self.pci.log_audit(
                    action="tokenize_card",
                    user_id=merchant_id,
                    detail=(
                        f"Kart tokenize: "
                        f"{result.get('masked_pan', '')}"
                    ),
                    data_type="pan",
                )

            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tokenized": False,
                "error": str(e),
            }

    def process_payment(
        self,
        user_id: str = "",
        amount: float = 0.0,
        token_id: str = "",
        merchant_id: str = "",
        currency: str = "TRY",
        location: str = "",
        gateway_name: str = "",
    ) -> dict[str, Any]:
        """Odeme isler (tam pipeline).

        Args:
            user_id: Kullanici ID.
            amount: Tutar.
            token_id: Token ID.
            merchant_id: Isyeri.
            currency: Para birimi.
            location: Konum.
            gateway_name: Gecit adi.

        Returns:
            Islem sonucu.
        """
        try:
            # 1. Limit kontrolu
            limit_check = (
                self.limiter
                .check_transaction(
                    user_id=user_id,
                    amount=amount,
                    currency=currency,
                    merchant_id=merchant_id,
                )
            )
            if (
                limit_check.get("checked")
                and not limit_check.get(
                    "allowed", True
                )
            ):
                return {
                    "processed": False,
                    "reason": "limit_exceeded",
                    "violations": (
                        limit_check.get(
                            "violations", []
                        )
                    ),
                }

            # 2. Anomali kontrolu
            analysis = (
                self.anomaly
                .analyze_transaction(
                    user_id=user_id,
                    amount=amount,
                    merchant_id=merchant_id,
                    location=location,
                )
            )
            if analysis.get("blocked"):
                return {
                    "processed": False,
                    "reason": (
                        "anomaly_blocked"
                    ),
                    "risk_score": (
                        analysis.get(
                            "risk_score", 0
                        )
                    ),
                    "flags": analysis.get(
                        "flags", []
                    ),
                }

            # 3. Cift onay kontrolu
            needs_approval = (
                self.gate
                .requires_approval(
                    amount=amount,
                )
            )
            if needs_approval:
                req = (
                    self.gate
                    .create_request(
                        request_type=(
                            "payment"
                        ),
                        amount=amount,
                        requester_id=(
                            user_id
                        ),
                        description=(
                            f"Odeme: "
                            f"{amount} "
                            f"{currency}"
                        ),
                    )
                )
                return {
                    "processed": False,
                    "reason": (
                        "approval_required"
                    ),
                    "request_id": req.get(
                        "request_id"
                    ),
                }

            # 4. Odeme isle
            result = (
                self.gateway
                .process_payment(
                    amount=amount,
                    currency=currency,
                    token_id=token_id,
                    merchant_id=(
                        merchant_id
                    ),
                    gateway_name=(
                        gateway_name
                    ),
                )
            )

            # 5. PCI denetim
            if result.get("processed"):
                self.pci.log_audit(
                    action=(
                        "process_payment"
                    ),
                    user_id=user_id,
                    detail=(
                        f"Odeme: "
                        f"{amount} "
                        f"{currency}"
                    ),
                    data_type="transaction",
                )

            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "processed": False,
                "error": str(e),
            }

    def handle_chargeback(
        self,
        transaction_id: str = "",
        amount: float = 0.0,
        reason: str = "other",
        customer_id: str = "",
        merchant_id: str = "",
    ) -> dict[str, Any]:
        """Chargeback isler.

        Args:
            transaction_id: Islem ID.
            amount: Tutar.
            reason: Neden.
            customer_id: Musteri.
            merchant_id: Isyeri.

        Returns:
            Itiraz bilgisi.
        """
        try:
            result = (
                self.chargeback
                .open_dispute(
                    transaction_id=(
                        transaction_id
                    ),
                    amount=amount,
                    reason=reason,
                    customer_id=customer_id,
                    merchant_id=merchant_id,
                )
            )

            if result.get("opened"):
                self.pci.log_audit(
                    action="chargeback",
                    user_id=customer_id,
                    detail=(
                        f"Itiraz: "
                        f"{amount} - "
                        f"{reason}"
                    ),
                    data_type="dispute",
                )

            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "opened": False,
                "error": str(e),
            }

    def run_compliance_check(
        self,
    ) -> dict[str, Any]:
        """PCI-DSS uyumluluk taramas.

        Returns:
            Tarama sonucu.
        """
        try:
            return (
                self.pci
                .run_compliance_scan()
            )

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik verir."""
        try:
            return {
                "tokenizer": (
                    self.tokenizer
                    .get_summary()
                ),
                "pci": (
                    self.pci.get_summary()
                ),
                "limiter": (
                    self.limiter
                    .get_summary()
                ),
                "anomaly": (
                    self.anomaly
                    .get_summary()
                ),
                "gate": (
                    self.gate.get_summary()
                ),
                "isolator": (
                    self.isolator
                    .get_summary()
                ),
                "gateway": (
                    self.gateway
                    .get_summary()
                ),
                "chargeback": (
                    self.chargeback
                    .get_summary()
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
                "active_tokens": (
                    self.tokenizer
                    .token_count
                ),
                "pci_violations": (
                    self.pci
                    .violation_count
                ),
                "limiter_alerts": (
                    self.limiter
                    .alert_count
                ),
                "anomalies": (
                    self.anomaly
                    .anomaly_count
                ),
                "pending_approvals": (
                    self.gate.pending_count
                ),
                "transactions": (
                    self.gateway
                    .transaction_count
                ),
                "open_disputes": (
                    self.chargeback
                    .dispute_count
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
