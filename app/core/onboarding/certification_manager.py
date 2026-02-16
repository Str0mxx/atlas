"""ATLAS Sertifika Yöneticisi modülü.

Sertifika kriterleri, sınav yönetimi,
sertifika üretimi, süre takibi,
yenileme hatırlatması.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CertificationManager:
    """Sertifika yöneticisi.

    Sertifikaları yönetir.

    Attributes:
        _certifications: Sertifika
            tanımları.
        _issued: Verilen sertifikalar.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._certifications: dict[
            str, dict[str, Any]
        ] = {}
        self._issued: dict[
            str, dict[str, Any]
        ] = {}
        self._exams: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "certs_defined": 0,
            "certs_issued": 0,
            "exams_taken": 0,
        }

        logger.info(
            "CertificationManager "
            "baslatildi",
        )

    def define_criteria(
        self,
        cert_name: str,
        required_score: float = 70.0,
        required_modules: list[str]
        | None = None,
        validity_days: int = 365,
    ) -> dict[str, Any]:
        """Sertifika kriteri tanımlar.

        Args:
            cert_name: Sertifika adı.
            required_score: Gerekli puan.
            required_modules: Gerekli
                modüller.
            validity_days: Geçerlilik
                süresi (gün).

        Returns:
            Kriter bilgisi.
        """
        required_modules = (
            required_modules or []
        )

        self._certifications[cert_name] = {
            "name": cert_name,
            "required_score": (
                required_score
            ),
            "required_modules": (
                required_modules
            ),
            "validity_days": validity_days,
            "created": time.time(),
        }

        self._stats["certs_defined"] += 1

        return {
            "cert_name": cert_name,
            "required_score": (
                required_score
            ),
            "module_count": len(
                required_modules,
            ),
            "validity_days": validity_days,
            "defined": True,
        }

    def manage_exam(
        self,
        cert_name: str,
        user_id: str,
        score: float = 0.0,
    ) -> dict[str, Any]:
        """Sınav yönetimi yapar.

        Args:
            cert_name: Sertifika adı.
            user_id: Kullanıcı kimliği.
            score: Puan.

        Returns:
            Sınav bilgisi.
        """
        cert = self._certifications.get(
            cert_name,
        )
        if not cert:
            return {
                "cert_name": cert_name,
                "found": False,
            }

        self._counter += 1
        eid = f"exam_{self._counter}"

        required = cert["required_score"]
        passed = score >= required

        self._exams[eid] = {
            "exam_id": eid,
            "cert_name": cert_name,
            "user_id": user_id,
            "score": score,
            "passed": passed,
            "timestamp": time.time(),
        }

        self._stats["exams_taken"] += 1

        return {
            "exam_id": eid,
            "cert_name": cert_name,
            "user_id": user_id,
            "score": score,
            "passed": passed,
            "managed": True,
        }

    def generate_certificate(
        self,
        cert_name: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Sertifika üretir.

        Args:
            cert_name: Sertifika adı.
            user_id: Kullanıcı kimliği.

        Returns:
            Sertifika bilgisi.
        """
        cert = self._certifications.get(
            cert_name,
        )
        if not cert:
            return {
                "cert_name": cert_name,
                "found": False,
            }

        passed_exam = any(
            e["passed"]
            for e in self._exams.values()
            if (
                e["cert_name"] == cert_name
                and e["user_id"] == user_id
            )
        )

        if not passed_exam:
            return {
                "cert_name": cert_name,
                "user_id": user_id,
                "eligible": False,
            }

        self._counter += 1
        cid = f"cert_{self._counter}"

        validity = cert["validity_days"]
        issued_at = time.time()
        expires_at = (
            issued_at
            + validity * 86400
        )

        self._issued[cid] = {
            "cert_id": cid,
            "cert_name": cert_name,
            "user_id": user_id,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "status": "active",
        }

        self._stats["certs_issued"] += 1

        return {
            "cert_id": cid,
            "cert_name": cert_name,
            "user_id": user_id,
            "status": "active",
            "validity_days": validity,
            "generated": True,
        }

    def check_expiration(
        self,
        cert_id: str,
    ) -> dict[str, Any]:
        """Süre kontrolü yapar.

        Args:
            cert_id: Sertifika kimliği.

        Returns:
            Süre bilgisi.
        """
        issued = self._issued.get(cert_id)
        if not issued:
            return {
                "cert_id": cert_id,
                "found": False,
            }

        now = time.time()
        expires = issued["expires_at"]
        days_left = (
            (expires - now) / 86400
        )
        expired = days_left <= 0

        if expired:
            issued["status"] = "expired"

        return {
            "cert_id": cert_id,
            "expired": expired,
            "days_remaining": max(
                0, round(days_left, 1),
            ),
            "status": issued["status"],
            "checked": True,
        }

    def send_renewal_reminder(
        self,
        cert_id: str,
        threshold_days: int = 30,
    ) -> dict[str, Any]:
        """Yenileme hatırlatması gönderir.

        Args:
            cert_id: Sertifika kimliği.
            threshold_days: Eşik (gün).

        Returns:
            Hatırlatma bilgisi.
        """
        issued = self._issued.get(cert_id)
        if not issued:
            return {
                "cert_id": cert_id,
                "found": False,
            }

        now = time.time()
        expires = issued["expires_at"]
        days_left = (
            (expires - now) / 86400
        )

        needs_renewal = (
            days_left <= threshold_days
        )

        return {
            "cert_id": cert_id,
            "needs_renewal": needs_renewal,
            "days_remaining": round(
                max(0, days_left), 1,
            ),
            "threshold": threshold_days,
            "reminded": needs_renewal,
        }

    @property
    def defined_count(self) -> int:
        """Tanım sayısı."""
        return self._stats[
            "certs_defined"
        ]

    @property
    def issued_count(self) -> int:
        """Verilen sertifika sayısı."""
        return self._stats[
            "certs_issued"
        ]

    @property
    def exam_count(self) -> int:
        """Sınav sayısı."""
        return self._stats["exams_taken"]
