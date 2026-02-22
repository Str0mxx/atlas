"""
Voice Call Manager - Sesli arama yasam dongusu yonetimi.

Aramalarin baslatilmasi, kabul edilmesi, sonlandirilmasi,
beklemeye alinmasi, transkript yonetimi, sira kilidi ve
bayat arama temizligi islemlerini yonetir.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.voicesys_models import (
    CallDirection,
    CallStatus,
    StaleCallConfig,
    VoiceCall,
)

logger = logging.getLogger(__name__)


class VoiceCallManager:
    """
    Sesli arama yasam dongusu yoneticisi.

    Attributes:
        max_concurrent: Esanli maksimum arama sayisi
        stale_config: Bayat arama yapilandirmasi
    """

    def __init__(self, max_concurrent: int = 5, stale_config: Optional[StaleCallConfig] = None) -> None:
        """VoiceCallManager baslatici."""
        self.max_concurrent = max_concurrent
        self.stale_config = stale_config or StaleCallConfig()
        self._calls: dict[str, VoiceCall] = {}
        self._history: list[dict] = []
        logger.info("VoiceCallManager baslatildi, max_concurrent=%d", max_concurrent)

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina olay ekler."""
        entry = {"action": action, "timestamp": time.time(), "details": details or {}}
        self._history.append(entry)

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Arama istatistiklerini dondurur."""
        total = len(self._calls)
        active = sum(1 for c in self._calls.values() if c.status == CallStatus.ACTIVE)
        ended = sum(1 for c in self._calls.values() if c.status == CallStatus.ENDED)
        failed = sum(1 for c in self._calls.values() if c.status == CallStatus.FAILED)
        durations = [c.duration for c in self._calls.values() if c.duration > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        return {"total_calls": total, "active_calls": active, "ended_calls": ended, "failed_calls": failed, "avg_duration": round(avg_duration, 2), "history_count": len(self._history)}

    def initiate_call(self, callee: str, caller: str = "atlas") -> VoiceCall:
        """Giden arama baslatir."""
        active_count = sum(1 for c in self._calls.values() if c.status in (CallStatus.ACTIVE, CallStatus.RINGING, CallStatus.INITIATING))
        if active_count >= self.max_concurrent:
            self._record_history("initiate_rejected", {"reason": "max_concurrent"})
            raise RuntimeError(f"Maksimum esanli arama limitine ulasildi: {self.max_concurrent}")
        now = time.time()
        call = VoiceCall(call_id=str(uuid.uuid4()), direction=CallDirection.OUTBOUND, status=CallStatus.RINGING, caller=caller, callee=callee, started_at=now, last_activity=now)
        self._calls[call.call_id] = call
        self._record_history("initiate_call", {"call_id": call.call_id, "callee": callee})
        return call

    def accept_call(self, call_id: str) -> VoiceCall:
        """Gelen aramayi kabul eder."""
        call = self._get_call_or_raise(call_id)
        if call.status not in (CallStatus.RINGING, CallStatus.INITIATING):
            raise ValueError(f"Arama kabul edilemez durumda: {call.status}")
        call.status = CallStatus.ACTIVE
        call.last_activity = time.time()
        self._record_history("accept_call", {"call_id": call_id})
        return call

    def end_call(self, call_id: str) -> VoiceCall:
        """Aktif aramayi sonlandirir."""
        call = self._get_call_or_raise(call_id)
        now = time.time()
        call.status = CallStatus.ENDED
        call.ended_at = now
        call.duration = now - call.started_at if call.started_at > 0 else 0.0
        call.turn_lock = False
        self._record_history("end_call", {"call_id": call_id, "duration": call.duration})
        return call

    def hold_call(self, call_id: str) -> bool:
        """Aramayi beklemeye alir."""
        call = self._get_call_or_raise(call_id)
        if call.status != CallStatus.ACTIVE:
            return False
        call.status = CallStatus.ON_HOLD
        call.last_activity = time.time()
        self._record_history("hold_call", {"call_id": call_id})
        return True

    def resume_call(self, call_id: str) -> bool:
        """Beklemedeki aramayi devam ettirir."""
        call = self._get_call_or_raise(call_id)
        if call.status != CallStatus.ON_HOLD:
            return False
        call.status = CallStatus.ACTIVE
        call.last_activity = time.time()
        self._record_history("resume_call", {"call_id": call_id})
        return True

    def get_call(self, call_id: str) -> Optional[VoiceCall]:
        """Arama bilgisini dondurur."""
        return self._calls.get(call_id)

    def list_active_calls(self) -> list[VoiceCall]:
        """Aktif aramalari listeler."""
        return [c for c in self._calls.values() if c.status in (CallStatus.ACTIVE, CallStatus.RINGING, CallStatus.ON_HOLD)]

    def add_transcript_entry(self, call_id: str, speaker: str, text: str) -> None:
        """Transkripte giris ekler."""
        call = self._get_call_or_raise(call_id)
        entry = {"speaker": speaker, "text": text, "timestamp": time.time()}
        call.transcript.append(entry)
        call.last_activity = time.time()
        self._record_history("add_transcript", {"call_id": call_id, "speaker": speaker})

    def get_transcript(self, call_id: str) -> list[dict]:
        """Arama transkriptini dondurur."""
        call = self._calls.get(call_id)
        if call is None:
            return []
        return list(call.transcript)

    def acquire_turn_lock(self, call_id: str) -> bool:
        """Arama icin sira kilidi alir."""
        call = self._get_call_or_raise(call_id)
        if call.turn_lock:
            return False
        call.turn_lock = True
        self._record_history("acquire_turn_lock", {"call_id": call_id})
        return True

    def release_turn_lock(self, call_id: str) -> bool:
        """Arama sira kilidini serbest birakir."""
        call = self._get_call_or_raise(call_id)
        if not call.turn_lock:
            return False
        call.turn_lock = False
        self._record_history("release_turn_lock", {"call_id": call_id})
        return True

    def reap_stale_calls(self) -> list[str]:
        """Bayat aramalari temizler."""
        if not self.stale_config.reaper_enabled:
            return []
        now = time.time()
        reaped: list[str] = []
        for call_id, call in list(self._calls.items()):
            if call.status in (CallStatus.ENDED, CallStatus.FAILED, CallStatus.STALE):
                continue
            if self._is_stale_internal(call, now):
                call.status = CallStatus.STALE
                call.ended_at = now
                call.duration = now - call.started_at if call.started_at > 0 else 0.0
                call.turn_lock = False
                reaped.append(call_id)
        if reaped:
            self._record_history("reap_stale_calls", {"reaped": reaped})
        return reaped

    def is_stale(self, call_id: str) -> bool:
        """Aramanin bayat olup olmadigini kontrol eder."""
        call = self._calls.get(call_id)
        if call is None:
            return False
        if call.status in (CallStatus.ENDED, CallStatus.FAILED, CallStatus.STALE):
            return call.status == CallStatus.STALE
        return self._is_stale_internal(call, time.time())

    def get_call_duration(self, call_id: str) -> float:
        """Arama suresini hesaplar."""
        call = self._calls.get(call_id)
        if call is None:
            return 0.0
        if call.duration > 0:
            return call.duration
        if call.started_at > 0:
            return time.time() - call.started_at
        return 0.0

    def _get_call_or_raise(self, call_id: str) -> VoiceCall:
        """Aramayi dondurur veya hata firlatir."""
        call = self._calls.get(call_id)
        if call is None:
            raise KeyError(f"Arama bulunamadi: {call_id}")
        return call

    def _is_stale_internal(self, call: VoiceCall, now: float) -> bool:
        """Dahili bayatlik kontrolu."""
        idle_time = now - call.last_activity if call.last_activity > 0 else 0.0
        total_time = now - call.started_at if call.started_at > 0 else 0.0
        return (idle_time > self.stale_config.max_idle_seconds or total_time > self.stale_config.stale_seconds)
