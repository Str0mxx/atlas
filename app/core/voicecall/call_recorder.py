"""ATLAS Arama Kaydedici modülü.

Arama kaydı, onay yönetimi, depolama yönetimi,
transkripsiyon bağlama, saklama politikaları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CallRecorder:
    """Arama kaydedici.

    Arama kayıtlarını yönetir.

    Attributes:
        _recordings: Kayıt kayıtları.
        _consents: Onay kayıtları.
    """

    def __init__(
        self,
        recording_enabled: bool = True,
        retention_days: int = 90,
        max_storage_mb: int = 10000,
    ) -> None:
        """Kaydediciyi başlatır.

        Args:
            recording_enabled: Kayıt etkin mi.
            retention_days: Saklama süresi (gün).
            max_storage_mb: Maks depolama (MB).
        """
        self._recordings: list[
            dict[str, Any]
        ] = []
        self._consents: dict[
            str, dict[str, Any]
        ] = {}
        self._recording_enabled = recording_enabled
        self._retention_days = retention_days
        self._max_storage_mb = max_storage_mb
        self._used_storage_mb = 0.0
        self._counter = 0
        self._stats = {
            "recordings": 0,
            "consents_granted": 0,
            "consents_denied": 0,
            "recordings_deleted": 0,
        }

        logger.info(
            "CallRecorder baslatildi",
        )

    def start_recording(
        self,
        call_id: str,
        consent_status: str = "pending",
    ) -> dict[str, Any]:
        """Kaydı başlatır.

        Args:
            call_id: Arama ID.
            consent_status: Onay durumu.

        Returns:
            Kayıt bilgisi.
        """
        if not self._recording_enabled:
            return {
                "error": "recording_disabled",
            }

        # Onay kontrolü
        if consent_status == "denied":
            return {
                "error": "consent_denied",
                "call_id": call_id,
            }

        self._counter += 1
        rid = f"rec_{self._counter}"

        recording = {
            "recording_id": rid,
            "call_id": call_id,
            "status": "recording",
            "consent": consent_status,
            "duration_seconds": 0,
            "size_mb": 0.0,
            "transcription_id": None,
            "started_at": time.time(),
            "ended_at": None,
        }
        self._recordings.append(recording)
        self._stats["recordings"] += 1

        return recording

    def stop_recording(
        self,
        recording_id: str,
        duration_seconds: int = 0,
    ) -> dict[str, Any]:
        """Kaydı durdurur.

        Args:
            recording_id: Kayıt ID.
            duration_seconds: Süre (saniye).

        Returns:
            Durdurma bilgisi.
        """
        rec = self._find_recording(recording_id)
        if not rec:
            return {
                "error": "recording_not_found",
            }

        rec["status"] = "completed"
        rec["duration_seconds"] = duration_seconds
        rec["size_mb"] = round(
            duration_seconds * 0.1, 2,
        )
        rec["ended_at"] = time.time()
        self._used_storage_mb += rec["size_mb"]

        return {
            "recording_id": recording_id,
            "status": "completed",
            "duration": duration_seconds,
            "size_mb": rec["size_mb"],
        }

    def request_consent(
        self,
        call_id: str,
        caller: str,
    ) -> dict[str, Any]:
        """Kayıt onayı ister.

        Args:
            call_id: Arama ID.
            caller: Arayan.

        Returns:
            Onay istemi bilgisi.
        """
        consent = {
            "call_id": call_id,
            "caller": caller,
            "status": "pending",
            "requested_at": time.time(),
        }
        self._consents[call_id] = consent

        return {
            "call_id": call_id,
            "consent_requested": True,
        }

    def grant_consent(
        self,
        call_id: str,
    ) -> dict[str, Any]:
        """Onay verir.

        Args:
            call_id: Arama ID.

        Returns:
            Onay bilgisi.
        """
        consent = self._consents.get(call_id)
        if not consent:
            self._consents[call_id] = {}
            consent = self._consents[call_id]

        consent["status"] = "granted"
        consent["granted_at"] = time.time()
        self._stats["consents_granted"] += 1

        return {
            "call_id": call_id,
            "consent": "granted",
        }

    def deny_consent(
        self,
        call_id: str,
    ) -> dict[str, Any]:
        """Onay reddeder.

        Args:
            call_id: Arama ID.

        Returns:
            Red bilgisi.
        """
        consent = self._consents.get(call_id)
        if not consent:
            self._consents[call_id] = {}
            consent = self._consents[call_id]

        consent["status"] = "denied"
        consent["denied_at"] = time.time()
        self._stats["consents_denied"] += 1

        return {
            "call_id": call_id,
            "consent": "denied",
        }

    def link_transcription(
        self,
        recording_id: str,
        transcription_id: str,
    ) -> dict[str, Any]:
        """Transkripsiyon bağlar.

        Args:
            recording_id: Kayıt ID.
            transcription_id: Transkripsiyon ID.

        Returns:
            Bağlama bilgisi.
        """
        rec = self._find_recording(recording_id)
        if not rec:
            return {
                "error": "recording_not_found",
            }

        rec["transcription_id"] = transcription_id

        return {
            "recording_id": recording_id,
            "transcription_id": transcription_id,
            "linked": True,
        }

    def apply_retention(self) -> dict[str, Any]:
        """Saklama politikası uygular.

        Returns:
            Uygulama bilgisi.
        """
        now = time.time()
        cutoff = now - self._retention_days * 86400
        deleted = 0

        to_keep = []
        for rec in self._recordings:
            if rec.get("started_at", 0) < cutoff:
                self._used_storage_mb -= rec.get(
                    "size_mb", 0,
                )
                deleted += 1
                self._stats[
                    "recordings_deleted"
                ] += 1
            else:
                to_keep.append(rec)

        self._recordings = to_keep
        self._used_storage_mb = max(
            0, self._used_storage_mb,
        )

        return {
            "deleted": deleted,
            "remaining": len(self._recordings),
            "storage_mb": round(
                self._used_storage_mb, 2,
            ),
        }

    def get_storage_status(self) -> dict[str, Any]:
        """Depolama durumunu getirir.

        Returns:
            Depolama bilgisi.
        """
        usage_pct = (
            self._used_storage_mb
            / self._max_storage_mb
            * 100
        ) if self._max_storage_mb > 0 else 0

        return {
            "used_mb": round(
                self._used_storage_mb, 2,
            ),
            "max_mb": self._max_storage_mb,
            "usage_percent": round(usage_pct, 1),
            "recordings": len(self._recordings),
        }

    def delete_recording(
        self,
        recording_id: str,
    ) -> dict[str, Any]:
        """Kayıt siler.

        Args:
            recording_id: Kayıt ID.

        Returns:
            Silme bilgisi.
        """
        rec = self._find_recording(recording_id)
        if not rec:
            return {
                "error": "recording_not_found",
            }

        self._used_storage_mb -= rec.get(
            "size_mb", 0,
        )
        self._recordings.remove(rec)
        self._stats["recordings_deleted"] += 1

        return {
            "recording_id": recording_id,
            "deleted": True,
        }

    def _find_recording(
        self,
        recording_id: str,
    ) -> dict[str, Any] | None:
        """Kayıt bulur."""
        for r in self._recordings:
            if r["recording_id"] == recording_id:
                return r
        return None

    def get_recordings(
        self,
        call_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kayıtları getirir.

        Args:
            call_id: Arama filtresi.
            limit: Maks kayıt.

        Returns:
            Kayıt listesi.
        """
        results = self._recordings
        if call_id:
            results = [
                r for r in results
                if r.get("call_id") == call_id
            ]
        return list(results[-limit:])

    @property
    def recording_count(self) -> int:
        """Kayıt sayısı."""
        return self._stats["recordings"]

    @property
    def active_recording_count(self) -> int:
        """Aktif kayıt sayısı."""
        return sum(
            1 for r in self._recordings
            if r["status"] == "recording"
        )
