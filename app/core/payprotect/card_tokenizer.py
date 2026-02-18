"""
Kart tokenizer modulu.

Kart tokenizasyonu, token uretimi,
detokenizasyon, token kasasi,
PAN maskeleme.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CardTokenizer:
    """Kart tokenizer.

    Attributes:
        _vault: Token kasasi.
        _masks: Maskeleme kayitlari.
        _stats: Istatistikler.
    """

    CARD_TYPES: list[str] = [
        "visa",
        "mastercard",
        "amex",
        "discover",
        "diners",
        "jcb",
        "unknown",
    ]

    def __init__(self) -> None:
        """Tokenizer baslatir."""
        self._vault: dict[
            str, dict
        ] = {}
        self._masks: dict[
            str, str
        ] = {}
        self._stats: dict[str, int] = {
            "tokens_created": 0,
            "detokenizations": 0,
            "masks_generated": 0,
            "tokens_revoked": 0,
            "lookups": 0,
        }
        logger.info(
            "CardTokenizer baslatildi"
        )

    @property
    def token_count(self) -> int:
        """Aktif token sayisi."""
        return sum(
            1
            for t in self._vault.values()
            if t["status"] == "active"
        )

    def tokenize(
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
            if len(card_number) < 13:
                return {
                    "tokenized": False,
                    "error": (
                        "Gecersiz kart no"
                    ),
                }

            tid = f"tok_{uuid4()!s:.8}"
            # Hash ile guvence
            card_hash = hashlib.sha256(
                card_number.encode()
            ).hexdigest()

            # PAN maskeleme
            masked = self._mask_pan(
                card_number
            )
            self._masks[tid] = masked

            last4 = card_number[-4:]

            self._vault[tid] = {
                "token_id": tid,
                "card_hash": card_hash,
                "card_type": card_type,
                "holder_name": holder_name,
                "last_four": last4,
                "masked_pan": masked,
                "expiry_month": expiry_month,
                "expiry_year": expiry_year,
                "merchant_id": merchant_id,
                "status": "active",
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "last_used": None,
                "usage_count": 0,
            }
            self._stats[
                "tokens_created"
            ] += 1

            return {
                "token_id": tid,
                "masked_pan": masked,
                "last_four": last4,
                "card_type": card_type,
                "tokenized": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tokenized": False,
                "error": str(e),
            }

    def _mask_pan(
        self, card_number: str
    ) -> str:
        """PAN maskeleme yapar."""
        self._stats[
            "masks_generated"
        ] += 1
        if len(card_number) < 8:
            return "****"
        first4 = card_number[:4]
        last4 = card_number[-4:]
        mid = "*" * (
            len(card_number) - 8
        )
        return f"{first4}{mid}{last4}"

    def detokenize(
        self,
        token_id: str = "",
    ) -> dict[str, Any]:
        """Detokenize eder.

        Args:
            token_id: Token ID.

        Returns:
            Kart bilgisi (maskelenmis).
        """
        try:
            self._stats[
                "detokenizations"
            ] += 1
            token = self._vault.get(
                token_id
            )
            if not token:
                return {
                    "found": False,
                    "error": (
                        "Token bulunamadi"
                    ),
                }

            if token["status"] != "active":
                return {
                    "found": False,
                    "error": (
                        "Token aktif degil"
                    ),
                }

            token["usage_count"] += 1
            token["last_used"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            return {
                "token_id": token_id,
                "masked_pan": token[
                    "masked_pan"
                ],
                "last_four": token[
                    "last_four"
                ],
                "card_type": token[
                    "card_type"
                ],
                "holder_name": token[
                    "holder_name"
                ],
                "expiry_month": token[
                    "expiry_month"
                ],
                "expiry_year": token[
                    "expiry_year"
                ],
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def revoke_token(
        self,
        token_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Token iptal eder.

        Args:
            token_id: Token ID.
            reason: Iptal nedeni.

        Returns:
            Iptal bilgisi.
        """
        try:
            token = self._vault.get(
                token_id
            )
            if not token:
                return {
                    "revoked": False,
                    "error": (
                        "Token bulunamadi"
                    ),
                }

            token["status"] = "revoked"
            self._stats[
                "tokens_revoked"
            ] += 1

            return {
                "token_id": token_id,
                "reason": reason,
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def get_token_info(
        self,
        token_id: str = "",
    ) -> dict[str, Any]:
        """Token bilgisi getirir.

        Args:
            token_id: Token ID.

        Returns:
            Token bilgisi.
        """
        try:
            self._stats["lookups"] += 1
            token = self._vault.get(
                token_id
            )
            if not token:
                return {
                    "found": False,
                    "error": (
                        "Token bulunamadi"
                    ),
                }

            return {
                "token_id": token_id,
                "masked_pan": token[
                    "masked_pan"
                ],
                "last_four": token[
                    "last_four"
                ],
                "card_type": token[
                    "card_type"
                ],
                "status": token["status"],
                "usage_count": token[
                    "usage_count"
                ],
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_type: dict[str, int] = {}
            for t in self._vault.values():
                ct = t["card_type"]
                by_type[ct] = (
                    by_type.get(ct, 0) + 1
                )

            return {
                "total_tokens": len(
                    self._vault
                ),
                "active_tokens": (
                    self.token_count
                ),
                "by_type": by_type,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
