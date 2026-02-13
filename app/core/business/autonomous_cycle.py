"""ATLAS Otonom Dongu modulu.

7/24 otonom dongu: Detect -> Plan -> Execute -> Measure -> Optimize -> Repeat.
Uyku/uyanma zamanlama, oncelik yonetimi, acil durum isleme
ve insan eskalasyonu islemleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.business import (
    CyclePhase,
    CycleRun,
    CycleStatus,
    EscalationLevel,
    EscalationRequest,
)

logger = logging.getLogger(__name__)

# Asama sirasi
_PHASE_ORDER: list[CyclePhase] = [
    CyclePhase.DETECT,
    CyclePhase.PLAN,
    CyclePhase.EXECUTE,
    CyclePhase.MEASURE,
    CyclePhase.OPTIMIZE,
]


class AutonomousCycle:
    """7/24 otonom is dongusu.

    Firsat tespitinden olcume ve optimizasyona kadar
    tum is dongusunu otonom olarak yonetir. Uyku/uyanma
    zamanlama, oncelik sirasi ve acil durum islemleri icerir.

    Attributes:
        _status: Dongu durumu.
        _current_phase: Mevcut asama.
        _cycle_count: Tamamlanan dongu sayisi.
        _runs: Dongu calistirma kayitlari.
        _current_run: Aktif dongu kaydı.
        _escalations: Eskalasyon istaleri.
        _cycle_interval_minutes: Dongu araligi (dakika).
        _max_parallel: Maksimum paralel girisim.
        _human_approval_threshold: Insan onay esigi (0.0-1.0).
        _priorities: Oncelik kuyruğu (oncelik -> istek).
        _last_sleep: Son uyku zamani.
        _emergency_mode: Acil durum modu aktif mi.
    """

    def __init__(
        self,
        cycle_interval_minutes: int = 60,
        max_parallel: int = 3,
        human_approval_threshold: float = 0.8,
    ) -> None:
        """Otonom donguyu baslatir.

        Args:
            cycle_interval_minutes: Dongu araligi (dakika).
            max_parallel: Maksimum paralel girisim.
            human_approval_threshold: Insan onay esigi (0.0-1.0).
        """
        self._status = CycleStatus.IDLE
        self._current_phase = CyclePhase.DETECT
        self._cycle_count: int = 0
        self._runs: list[CycleRun] = []
        self._current_run: CycleRun | None = None
        self._escalations: list[EscalationRequest] = []
        self._cycle_interval_minutes = cycle_interval_minutes
        self._max_parallel = max_parallel
        self._human_approval_threshold = max(0.0, min(1.0, human_approval_threshold))
        self._priorities: dict[int, list[dict[str, Any]]] = {}
        self._last_sleep: datetime | None = None
        self._emergency_mode: bool = False

        logger.info(
            "AutonomousCycle baslatildi (aralik=%d dk, paralel=%d, onay_esigi=%.2f)",
            cycle_interval_minutes,
            max_parallel,
            self._human_approval_threshold,
        )

    def start_cycle(self) -> CycleRun:
        """Yeni dongu baslatir.

        Returns:
            Olusturulan CycleRun nesnesi.
        """
        self._cycle_count += 1
        run = CycleRun(
            cycle_number=self._cycle_count,
            phase=CyclePhase.DETECT,
            status=CycleStatus.RUNNING,
        )
        self._current_run = run
        self._current_phase = CyclePhase.DETECT
        self._status = CycleStatus.RUNNING
        self._runs.append(run)
        logger.info("Dongu #%d baslatildi", self._cycle_count)
        return run

    def advance_phase(self) -> CyclePhase:
        """Bir sonraki asamaya ilerler.

        Mevcut asama son asama (OPTIMIZE) ise DETECT'e doner
        ve dongu tamamlanir.

        Returns:
            Yeni asama.
        """
        current_idx = _PHASE_ORDER.index(self._current_phase)

        if current_idx >= len(_PHASE_ORDER) - 1:
            # Dongu tamamlandi, basa don
            self._current_phase = CyclePhase.DETECT
            if self._current_run:
                self._current_run.status = CycleStatus.IDLE
                self._current_run.completed_at = datetime.now(timezone.utc)
            self._status = CycleStatus.IDLE
            logger.info("Dongu #%d tamamlandi", self._cycle_count)
        else:
            self._current_phase = _PHASE_ORDER[current_idx + 1]
            if self._current_run:
                self._current_run.phase = self._current_phase

        logger.info("Asama ilerledi: %s", self._current_phase.value)
        return self._current_phase

    def update_run_stats(
        self,
        opportunities_found: int = 0,
        strategies_created: int = 0,
        tasks_executed: int = 0,
        optimizations_applied: int = 0,
    ) -> None:
        """Dongu istatistiklerini gunceller.

        Args:
            opportunities_found: Bulunan firsat sayisi.
            strategies_created: Olusturulan strateji sayisi.
            tasks_executed: Yurutulen gorev sayisi.
            optimizations_applied: Uygulanan optimizasyon sayisi.
        """
        if not self._current_run:
            return

        self._current_run.opportunities_found += opportunities_found
        self._current_run.strategies_created += strategies_created
        self._current_run.tasks_executed += tasks_executed
        self._current_run.optimizations_applied += optimizations_applied

    def enter_sleep(self) -> None:
        """Uyku moduna gecer.

        Dongu duraklatlir ve sonraki uyanma beklenir.
        """
        self._status = CycleStatus.PAUSED
        self._current_phase = CyclePhase.SLEEP
        self._last_sleep = datetime.now(timezone.utc)
        if self._current_run:
            self._current_run.phase = CyclePhase.SLEEP
        logger.info("Uyku moduna gecildi")

    def wake_up(self) -> None:
        """Uyku modundan cikar.

        Dongu DETECT asamasindan yeniden baslar.
        """
        self._status = CycleStatus.RUNNING
        self._current_phase = CyclePhase.DETECT
        if self._current_run:
            self._current_run.phase = CyclePhase.DETECT
            self._current_run.status = CycleStatus.RUNNING
        logger.info("Uyku modundan cikildi")

    def add_priority_item(self, priority: int, item: dict[str, Any]) -> None:
        """Oncelik kuyruğuna oge ekler.

        Dusuk numara = yuksek oncelik.

        Args:
            priority: Oncelik seviyesi (1=en yuksek).
            item: Istek detaylari.
        """
        if priority not in self._priorities:
            self._priorities[priority] = []
        self._priorities[priority].append(item)

    def get_next_priority(self) -> dict[str, Any] | None:
        """En yuksek oncelikli ogeyi alir.

        Returns:
            Oncelik ogesi veya None.
        """
        for level in sorted(self._priorities.keys()):
            if self._priorities[level]:
                return self._priorities[level].pop(0)
        return None

    def handle_emergency(self, reason: str, context: dict[str, Any] | None = None) -> EscalationRequest:
        """Acil durum islemi baslatir.

        Dongu acil durum moduna gecer ve insan eskalasyonu
        olusturulur.

        Args:
            reason: Acil durum nedeni.
            context: Baglamsal bilgi.

        Returns:
            Olusturulan EscalationRequest nesnesi.
        """
        self._emergency_mode = True
        self._status = CycleStatus.EMERGENCY
        if self._current_run:
            self._current_run.status = CycleStatus.EMERGENCY
            self._current_run.escalations += 1

        escalation = EscalationRequest(
            level=EscalationLevel.EMERGENCY,
            reason=reason,
            context=context or {},
            requires_response=True,
        )
        self._escalations.append(escalation)
        logger.critical("ACIL DURUM: %s", reason)
        return escalation

    def escalate(
        self,
        reason: str,
        level: EscalationLevel = EscalationLevel.INFO,
        requires_response: bool = False,
        context: dict[str, Any] | None = None,
    ) -> EscalationRequest:
        """Insan eskalasyonu olusturur.

        Args:
            reason: Eskalasyon nedeni.
            level: Eskalasyon seviyesi.
            requires_response: Yanit gerektiriyor mu.
            context: Baglamsal bilgi.

        Returns:
            Olusturulan EscalationRequest nesnesi.
        """
        escalation = EscalationRequest(
            level=level,
            reason=reason,
            context=context or {},
            requires_response=requires_response,
        )
        self._escalations.append(escalation)
        if self._current_run:
            self._current_run.escalations += 1

        logger.info("Eskalasyon: %s (seviye=%s)", reason[:30], level.value)
        return escalation

    def respond_to_escalation(self, escalation_id: str, response: str) -> bool:
        """Eskalasyona yanit verir.

        Args:
            escalation_id: Eskalasyon ID.
            response: Yanit metni.

        Returns:
            Basarili mi.
        """
        esc = next((e for e in self._escalations if e.id == escalation_id), None)
        if not esc:
            return False

        esc.response = response
        esc.responded_at = datetime.now(timezone.utc)

        # Acil durum eskalasyonuna yanit gelirse moddan cik
        if esc.level == EscalationLevel.EMERGENCY:
            self._emergency_mode = False
            self._status = CycleStatus.RUNNING
            logger.info("Acil durum eskalasyonu yanitlandi, normal moda donuldu")

        return True

    def needs_approval(self, risk_score: float) -> bool:
        """Risk puanina gore insan onayi gerekip gerekmedigini belirler.

        Args:
            risk_score: Risk puani (0.0-1.0).

        Returns:
            Onay gerekiyor mu.
        """
        return risk_score >= self._human_approval_threshold

    def stop(self) -> None:
        """Donguyu durdurur."""
        self._status = CycleStatus.STOPPED
        if self._current_run:
            self._current_run.status = CycleStatus.STOPPED
            self._current_run.completed_at = datetime.now(timezone.utc)
        logger.info("Dongu durduruldu")

    def get_run_history(self, limit: int = 10) -> list[CycleRun]:
        """Dongu gecmisini getirir.

        Args:
            limit: Maksimum sonuc sayisi.

        Returns:
            Son calistirma kayitlari.
        """
        return self._runs[-limit:]

    def get_pending_escalations(self) -> list[EscalationRequest]:
        """Bekleyen eskalasyonlari getirir.

        Returns:
            Yanitlanmamis eskalasyonlar.
        """
        return [e for e in self._escalations if e.requires_response and e.response is None]

    @property
    def status(self) -> CycleStatus:
        """Dongu durumu."""
        return self._status

    @property
    def current_phase(self) -> CyclePhase:
        """Mevcut asama."""
        return self._current_phase

    @property
    def cycle_count(self) -> int:
        """Tamamlanan dongu sayisi."""
        return self._cycle_count

    @property
    def is_running(self) -> bool:
        """Dongu calisiyor mu."""
        return self._status == CycleStatus.RUNNING

    @property
    def is_emergency(self) -> bool:
        """Acil durum modu aktif mi."""
        return self._emergency_mode

    @property
    def escalation_count(self) -> int:
        """Toplam eskalasyon sayisi."""
        return len(self._escalations)
