"""ATLAS Kurtarma Yoneticisi modulu.

Yedek restorasyon, durum kurtarma,
geri alma yurutme, veri butunluk
kontrolu ve servis restorasyon.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import RecoveryRecord

logger = logging.getLogger(__name__)


class RecoveryManager:
    """Kurtarma yoneticisi.

    Sistem kurtarma islemlerini yonetir,
    yedeklerden restorasyon yapar ve
    veri butunlugunu dogrular.

    Attributes:
        _recoveries: Kurtarma kayitlari.
        _backups: Yedek bilgileri.
        _checkpoints: Kontrol noktalari.
        _rollback_stack: Geri alma yigini.
    """

    def __init__(self) -> None:
        """Kurtarma yoneticisini baslatir."""
        self._recoveries: list[RecoveryRecord] = []
        self._backups: dict[str, dict[str, Any]] = {}
        self._checkpoints: list[dict[str, Any]] = []
        self._rollback_stack: list[dict[str, Any]] = []

        logger.info("RecoveryManager baslatildi")

    def create_backup(
        self,
        name: str,
        target: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Yedek olusturur.

        Args:
            name: Yedek adi.
            target: Hedef bilesen.
            data: Yedeklenen veri.

        Returns:
            Yedek bilgisi.
        """
        backup = {
            "name": name,
            "target": target,
            "data": data or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "size_keys": len(data) if data else 0,
        }
        self._backups[name] = backup

        logger.info("Yedek olusturuldu: %s (%s)", name, target)
        return backup

    def restore_backup(
        self,
        name: str,
    ) -> RecoveryRecord:
        """Yedekten restorasyon yapar.

        Args:
            name: Yedek adi.

        Returns:
            RecoveryRecord nesnesi.
        """
        backup = self._backups.get(name)
        success = backup is not None

        record = RecoveryRecord(
            action="backup_restore",
            target=name,
            success=success,
            data_integrity=1.0 if success else 0.0,
            duration_seconds=0.5 if success else 0.0,
        )
        self._recoveries.append(record)

        if success:
            logger.info("Yedek restore edildi: %s", name)
        else:
            logger.warning("Yedek bulunamadi: %s", name)

        return record

    def create_checkpoint(
        self,
        label: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Kontrol noktasi olusturur.

        Args:
            label: Etiket.
            state: Durum verisi.

        Returns:
            Checkpoint bilgisi.
        """
        checkpoint = {
            "label": label,
            "state": dict(state),
            "index": len(self._checkpoints),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._checkpoints.append(checkpoint)

        return checkpoint

    def recover_state(
        self,
        label: str,
    ) -> RecoveryRecord:
        """Durumu kurtarir.

        Args:
            label: Checkpoint etiketi.

        Returns:
            RecoveryRecord nesnesi.
        """
        target_cp = None
        for cp in reversed(self._checkpoints):
            if cp["label"] == label:
                target_cp = cp
                break

        success = target_cp is not None

        record = RecoveryRecord(
            action="state_recovery",
            target=label,
            success=success,
            data_integrity=1.0 if success else 0.0,
            duration_seconds=0.3 if success else 0.0,
        )
        self._recoveries.append(record)

        return record

    def push_rollback(
        self,
        action: str,
        undo_data: dict[str, Any],
    ) -> None:
        """Geri alma bilgisi yigina ekler.

        Args:
            action: Aksiyon adi.
            undo_data: Geri alma verisi.
        """
        self._rollback_stack.append({
            "action": action,
            "undo_data": undo_data,
            "pushed_at": datetime.now(timezone.utc).isoformat(),
        })

    def execute_rollback(self) -> RecoveryRecord:
        """Son islemi geri alir.

        Returns:
            RecoveryRecord nesnesi.
        """
        if not self._rollback_stack:
            return RecoveryRecord(
                action="rollback",
                target="empty_stack",
                success=False,
            )

        rollback = self._rollback_stack.pop()

        record = RecoveryRecord(
            action="rollback",
            target=rollback["action"],
            success=True,
            data_integrity=1.0,
            duration_seconds=0.2,
        )
        self._recoveries.append(record)

        logger.info("Geri alma yurutuldu: %s", rollback["action"])
        return record

    def rollback_all(self) -> list[RecoveryRecord]:
        """Tum islemleri geri alir.

        Returns:
            Kurtarma kayit listesi.
        """
        records: list[RecoveryRecord] = []
        while self._rollback_stack:
            record = self.execute_rollback()
            records.append(record)
        return records

    def check_data_integrity(
        self,
        target: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
    ) -> dict[str, Any]:
        """Veri butunlugunu kontrol eder.

        Args:
            target: Hedef.
            expected: Beklenen veri.
            actual: Gercek veri.

        Returns:
            Kontrol sonucu.
        """
        missing_keys = set(expected.keys()) - set(actual.keys())
        extra_keys = set(actual.keys()) - set(expected.keys())
        mismatched: list[str] = []

        for key in set(expected.keys()) & set(actual.keys()):
            if expected[key] != actual[key]:
                mismatched.append(key)

        total_checks = len(expected)
        passed = total_checks - len(missing_keys) - len(mismatched)
        integrity = round(passed / total_checks, 3) if total_checks > 0 else 1.0

        return {
            "target": target,
            "integrity": integrity,
            "total_checks": total_checks,
            "passed": passed,
            "missing_keys": list(missing_keys),
            "extra_keys": list(extra_keys),
            "mismatched": mismatched,
            "healthy": integrity >= 0.95,
        }

    def restore_service(
        self,
        service: str,
        config: dict[str, Any] | None = None,
    ) -> RecoveryRecord:
        """Servis restore eder.

        Args:
            service: Servis adi.
            config: Yapilandirma.

        Returns:
            RecoveryRecord nesnesi.
        """
        record = RecoveryRecord(
            action="service_restore",
            target=service,
            success=True,
            data_integrity=1.0,
            duration_seconds=1.0,
        )
        self._recoveries.append(record)

        logger.info("Servis restore edildi: %s", service)
        return record

    def get_recovery_history(
        self,
        limit: int = 10,
    ) -> list[RecoveryRecord]:
        """Kurtarma gecmisini getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Kurtarma kayit listesi.
        """
        return self._recoveries[-limit:]

    def get_available_backups(self) -> list[str]:
        """Mevcut yedekleri getirir.

        Returns:
            Yedek adi listesi.
        """
        return list(self._backups.keys())

    @property
    def recovery_count(self) -> int:
        """Kurtarma sayisi."""
        return len(self._recoveries)

    @property
    def backup_count(self) -> int:
        """Yedek sayisi."""
        return len(self._backups)

    @property
    def checkpoint_count(self) -> int:
        """Checkpoint sayisi."""
        return len(self._checkpoints)

    @property
    def rollback_depth(self) -> int:
        """Geri alma yigin derinligi."""
        return len(self._rollback_stack)

    @property
    def success_rate(self) -> float:
        """Basari orani."""
        if not self._recoveries:
            return 0.0
        ok = sum(1 for r in self._recoveries if r.success)
        return round(ok / len(self._recoveries), 3)
