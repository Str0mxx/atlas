"""Beceri butunluk kontrol yoneticisi.

Beceri dogrulama, hash kontrolu,
imza dogrulama ve kurcalama tespiti.
"""

import hashlib
import hmac
import logging
import time
from typing import Any
from uuid import uuid4

from app.models.injectionprotect_models import (
    IntegrityRecord,
    IntegrityStatus,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 10000
_MAX_HISTORY = 10000


class SkillIntegrityChecker:
    """Beceri butunluk kontrol yoneticisi.

    Beceri dogrulama, hash kontrolu,
    imza dogrulama ve kurcalama tespiti.

    Attributes:
        _records: Butunluk kayit deposu.
    """

    def __init__(
        self,
        secret_key: str = "atlas-integrity",
        hash_algorithm: str = "sha256",
    ) -> None:
        """SkillIntegrityChecker baslatir.

        Args:
            secret_key: HMAC anahtar.
            hash_algorithm: Hash algoritmasi.
        """
        self._records: dict[
            str, IntegrityRecord
        ] = {}
        self._record_order: list[str] = []
        self._secret_key = secret_key.encode()
        self._hash_algorithm = hash_algorithm
        self._skill_hashes: dict[
            str, str
        ] = {}
        self._skill_signatures: dict[
            str, str
        ] = {}
        self._total_ops: int = 0
        self._total_verified: int = 0
        self._total_valid: int = 0
        self._total_invalid: int = 0
        self._total_tampered: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

        logger.info(
            "SkillIntegrityChecker baslatildi "
            "algorithm=%s",
            self._hash_algorithm,
        )

    # ---- Kayit ----

    def register_skill(
        self,
        skill_name: str,
        content: str,
    ) -> IntegrityRecord:
        """Beceri kaydeder.

        Args:
            skill_name: Beceri adi.
            content: Beceri icerigi.

        Returns:
            Butunluk kaydi.
        """
        if len(self._records) >= _MAX_RECORDS:
            self._rotate()

        record_id = str(uuid4())[:8]
        now = time.time()
        self._total_ops += 1

        content_hash = self._compute_hash(
            content,
        )
        signature = self._compute_signature(
            content,
        )

        self._skill_hashes[skill_name] = (
            content_hash
        )
        self._skill_signatures[skill_name] = (
            signature
        )

        record = IntegrityRecord(
            record_id=record_id,
            skill_name=skill_name,
            expected_hash=content_hash,
            actual_hash=content_hash,
            status=IntegrityStatus.VALID,
            signature=signature,
            verified_at=now,
            details="initial registration",
        )

        self._records[record_id] = record
        self._record_order.append(record_id)

        self._record_history(
            "register_skill",
            record_id,
            f"skill={skill_name} "
            f"hash={content_hash[:16]}",
        )

        return record

    # ---- Dogrulama ----

    def verify_skill(
        self,
        skill_name: str,
        content: str,
    ) -> IntegrityRecord:
        """Beceri dogrular.

        Args:
            skill_name: Beceri adi.
            content: Mevcut icerik.

        Returns:
            Dogrulama kaydi.
        """
        if len(self._records) >= _MAX_RECORDS:
            self._rotate()

        record_id = str(uuid4())[:8]
        now = time.time()
        self._total_verified += 1
        self._total_ops += 1

        actual_hash = self._compute_hash(
            content,
        )
        expected_hash = self._skill_hashes.get(
            skill_name, "",
        )

        if not expected_hash:
            status = IntegrityStatus.UNKNOWN
            details = "skill not registered"
        elif actual_hash == expected_hash:
            status = IntegrityStatus.VALID
            details = "hash match"
            self._total_valid += 1
        else:
            status = IntegrityStatus.TAMPERED
            details = (
                f"hash mismatch: "
                f"expected={expected_hash[:16]} "
                f"actual={actual_hash[:16]}"
            )
            self._total_tampered += 1

        # Imza kontrolu
        expected_sig = (
            self._skill_signatures.get(
                skill_name, "",
            )
        )
        actual_sig = self._compute_signature(
            content,
        )

        if (
            expected_sig
            and actual_sig != expected_sig
            and status == IntegrityStatus.VALID
        ):
            status = IntegrityStatus.TAMPERED
            details = "signature mismatch"
            self._total_tampered += 1
            self._total_valid -= 1

        record = IntegrityRecord(
            record_id=record_id,
            skill_name=skill_name,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            status=status,
            signature=actual_sig,
            verified_at=now,
            details=details,
        )

        self._records[record_id] = record
        self._record_order.append(record_id)

        self._record_history(
            "verify_skill",
            record_id,
            f"skill={skill_name} "
            f"status={status.value}",
        )

        return record

    def verify_signature(
        self,
        content: str,
        signature: str,
    ) -> bool:
        """Imza dogrular.

        Args:
            content: Icerik.
            signature: Beklenen imza.

        Returns:
            Gecerli ise True.
        """
        computed = self._compute_signature(
            content,
        )
        self._total_ops += 1
        return hmac.compare_digest(
            computed, signature,
        )

    def check_tampering(
        self,
        skill_name: str,
        content: str,
    ) -> dict[str, Any]:
        """Kurcalama kontrol eder.

        Args:
            skill_name: Beceri adi.
            content: Mevcut icerik.

        Returns:
            Kontrol sonucu.
        """
        expected_hash = self._skill_hashes.get(
            skill_name, "",
        )
        actual_hash = self._compute_hash(
            content,
        )

        expected_sig = (
            self._skill_signatures.get(
                skill_name, "",
            )
        )
        actual_sig = self._compute_signature(
            content,
        )

        hash_match = (
            expected_hash == actual_hash
            if expected_hash
            else None
        )
        sig_match = (
            expected_sig == actual_sig
            if expected_sig
            else None
        )

        tampered = False
        if hash_match is False:
            tampered = True
        if sig_match is False:
            tampered = True

        self._total_ops += 1

        return {
            "skill_name": skill_name,
            "tampered": tampered,
            "hash_match": hash_match,
            "signature_match": sig_match,
            "expected_hash": (
                expected_hash[:16]
                if expected_hash
                else ""
            ),
            "actual_hash": actual_hash[:16],
        }

    # ---- Beceri Yonetimi ----

    def update_skill(
        self,
        skill_name: str,
        content: str,
    ) -> IntegrityRecord:
        """Beceri hash gunceller.

        Args:
            skill_name: Beceri adi.
            content: Yeni icerik.

        Returns:
            Guncelleme kaydi.
        """
        return self.register_skill(
            skill_name, content,
        )

    def remove_skill(
        self,
        skill_name: str,
    ) -> bool:
        """Beceri kaydini siler.

        Args:
            skill_name: Beceri adi.

        Returns:
            Basarili ise True.
        """
        removed = False
        if skill_name in self._skill_hashes:
            del self._skill_hashes[skill_name]
            removed = True
        if skill_name in self._skill_signatures:
            del self._skill_signatures[
                skill_name
            ]
            removed = True
        if removed:
            self._total_ops += 1
        return removed

    def list_skills(
        self,
    ) -> list[dict[str, str]]:
        """Kayitli becerileri listeler.

        Returns:
            Beceri listesi.
        """
        result = []
        for name, h in (
            self._skill_hashes.items()
        ):
            sig = self._skill_signatures.get(
                name, "",
            )
            result.append({
                "skill_name": name,
                "hash": h[:16],
                "has_signature": bool(sig),
            })
        return result

    # ---- Sorgulama ----

    def get_record(
        self,
        record_id: str,
    ) -> IntegrityRecord | None:
        """Kayit dondurur.

        Args:
            record_id: Kayit ID.

        Returns:
            Kayit veya None.
        """
        return self._records.get(record_id)

    def list_records(
        self,
        skill_name: str = "",
        status: str = "",
        limit: int = 50,
    ) -> list[IntegrityRecord]:
        """Kayitlari listeler.

        Args:
            skill_name: Beceri filtresi.
            status: Durum filtresi.
            limit: Maks sayi.

        Returns:
            Kayit listesi.
        """
        ids = list(
            reversed(self._record_order),
        )
        result: list[IntegrityRecord] = []

        for rid in ids:
            r = self._records.get(rid)
            if not r:
                continue
            if (
                skill_name
                and r.skill_name != skill_name
            ):
                continue
            if (
                status
                and r.status.value != status
            ):
                continue
            result.append(r)
            if len(result) >= limit:
                break

        return result

    def list_tampered(
        self,
        limit: int = 50,
    ) -> list[IntegrityRecord]:
        """Kurcalanmis kayitlari listeler.

        Args:
            limit: Maks sayi.

        Returns:
            Kurcalanmis kayitlar.
        """
        return self.list_records(
            status="tampered", limit=limit,
        )

    # ---- Gosterim ----

    def format_record(
        self,
        record_id: str,
    ) -> str:
        """Kaydi formatlar.

        Args:
            record_id: Kayit ID.

        Returns:
            Formatlenmis metin.
        """
        r = self._records.get(record_id)
        if not r:
            return ""

        parts = [
            f"Record: {r.record_id}",
            f"Skill: {r.skill_name}",
            f"Status: {r.status.value}",
            f"Expected: {r.expected_hash[:16]}",
            f"Actual: {r.actual_hash[:16]}",
            f"Details: {r.details}",
        ]
        return "\n".join(parts)

    # ---- Temizlik ----

    def clear_records(self) -> int:
        """Kayitlari temizler.

        Returns:
            Silinen sayi.
        """
        count = len(self._records)
        self._records.clear()
        self._record_order.clear()
        self._total_ops += 1
        return count

    def clear_all(self) -> int:
        """Tum verileri temizler.

        Returns:
            Silinen sayi.
        """
        count = len(self._records)
        self._records.clear()
        self._record_order.clear()
        self._skill_hashes.clear()
        self._skill_signatures.clear()
        self._total_ops += 1
        return count

    # ---- Hash/Imza ----

    def _compute_hash(
        self,
        content: str,
    ) -> str:
        """Hash hesaplar."""
        h = hashlib.new(self._hash_algorithm)
        h.update(content.encode("utf-8"))
        return h.hexdigest()

    def _compute_signature(
        self,
        content: str,
    ) -> str:
        """HMAC imza hesaplar."""
        return hmac.new(
            self._secret_key,
            content.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # ---- Dahili ----

    def _rotate(self) -> int:
        """Eski kayitlari temizler."""
        keep = _MAX_RECORDS // 2
        if len(self._record_order) <= keep:
            return 0

        to_remove = self._record_order[:-keep]
        for rid in to_remove:
            self._records.pop(rid, None)

        self._record_order = (
            self._record_order[-keep:]
        )
        return len(to_remove)

    def _record_history(
        self,
        action: str,
        record_id: str,
        detail: str,
    ) -> None:
        """Aksiyonu kaydeder."""
        self._history.append({
            "action": action,
            "record_id": record_id,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self._history) > _MAX_HISTORY:
            self._history = (
                self._history[-5000:]
            )

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gecmisi dondurur."""
        return list(
            reversed(
                self._history[-limit:],
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur."""
        return {
            "total_records": len(
                self._records,
            ),
            "total_verified": (
                self._total_verified
            ),
            "total_valid": self._total_valid,
            "total_invalid": (
                self._total_invalid
            ),
            "total_tampered": (
                self._total_tampered
            ),
            "registered_skills": len(
                self._skill_hashes,
            ),
            "hash_algorithm": (
                self._hash_algorithm
            ),
            "total_ops": self._total_ops,
        }
