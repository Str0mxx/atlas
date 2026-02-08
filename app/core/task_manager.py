"""ATLAS merkezi gorev yasam dongusu yoneticisi.

Gorev olusturma, onceliklendirme, kuyruga alma, dagitim,
yeniden deneme, bagimlillik takibi ve uc katmanli hafiza
entegrasyonunu yonetir.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import ActionType, DecisionMatrix
from app.core.memory.long_term import LongTermMemory
from app.core.memory.short_term import ShortTermMemory
from app.core.memory.semantic import SemanticMemory
from app.models.task import TaskCreate, TaskResponse, TaskStatus

logger = logging.getLogger(__name__)


# === Pydantic Modeller ===


class TaskPriority(IntEnum):
    """Gorev oncelik tanimlari.

    Dusuk deger = yuksek oncelik (PriorityQueue uyumu icin).
    """

    CRITICAL = 1     # HIGH risk + HIGH urgency -> IMMEDIATE
    HIGH = 2         # AUTO_FIX aksiyonu
    MEDIUM = 3       # NOTIFY aksiyonu
    LOW = 4          # LOG aksiyonu
    BACKGROUND = 5   # Zamanlanmis / dusuk oncelikli


class TaskSubmission(BaseModel):
    """Gorev gonderim modeli.

    Dis kaynaklardan gelen ham gorev verisini yapilandirir.

    Attributes:
        description: Gorev aciklamasi.
        risk: Risk seviyesi (low/medium/high).
        urgency: Aciliyet seviyesi (low/medium/high).
        target_agent: Hedef agent adi (opsiyonel).
        source: Gorev kaynagi (telegram/webhook/api/monitor/scheduled).
        metadata: Ek veriler (callback_data, chat_id vb.).
        depends_on: Bagimli olunan gorev ID'leri.
        max_retries: Maksimum deneme sayisi (None ise config'den alinir).
    """

    description: str
    risk: str = "low"
    urgency: str = "low"
    target_agent: str | None = None
    source: str = "api"
    metadata: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    max_retries: int | None = None


class QueuedTask(BaseModel):
    """Oncelik kuyruktaki gorev.

    Attributes:
        id: Gorev UUID (PostgreSQL'deki TaskRecord.id ile ayni).
        priority: Hesaplanan oncelik degeri.
        submission: Orijinal gonderim verisi.
        retry_count: Mevcut deneme sayisi.
        created_at: Kuyruga ekleme zamani.
    """

    id: str
    priority: TaskPriority
    submission: TaskSubmission
    retry_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __lt__(self, other: "QueuedTask") -> bool:
        """PriorityQueue karsilastirmasi icin."""
        if self.priority != other.priority:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class TaskMetrics(BaseModel):
    """Gorev yoneticisi metrikleri.

    Attributes:
        total_submitted: Toplam gonderilen gorev sayisi.
        total_completed: Basarili tamamlanan sayisi.
        total_failed: Basarisiz sayisi.
        total_cancelled: Iptal edilen sayisi.
        queue_size: Kuyrukta bekleyen sayisi.
        active_count: Calisan gorev sayisi.
        success_rate: Basari orani (0.0 - 1.0).
        by_agent: Agent bazli tamamlanan gorev sayilari.
        by_status: Durum bazli gorev sayilari.
    """

    total_submitted: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    queue_size: int = 0
    active_count: int = 0
    success_rate: float = 0.0
    by_agent: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)


# === Oncelik hesaplama tablosu ===
_ACTION_PRIORITY_MAP: dict[ActionType, TaskPriority] = {
    ActionType.IMMEDIATE: TaskPriority.CRITICAL,
    ActionType.AUTO_FIX: TaskPriority.HIGH,
    ActionType.NOTIFY: TaskPriority.MEDIUM,
    ActionType.LOG: TaskPriority.LOW,
}


class TaskManager:
    """Merkezi gorev yasam dongusu yoneticisi.

    Gorev olusturma, kuyruga alma, dagitim, yeniden deneme,
    bagimliliklari izleme ve uc katmanli hafiza entegrasyonunu yonetir.

    Attributes:
        master_agent: Gorevleri calistiran ana koordinator.
        long_term: PostgreSQL uzun sureli hafiza.
        short_term: Redis kisa sureli hafiza (opsiyonel).
        semantic: Qdrant semantik hafiza (opsiyonel).
        telegram_bot: Bildirim gonderici (opsiyonel).
        max_retries: Maksimum yeniden deneme sayisi.
        max_concurrent: Esanli calistirilacak maks gorev sayisi.
    """

    def __init__(
        self,
        master_agent: BaseAgent,
        long_term: LongTermMemory,
        short_term: ShortTermMemory | None = None,
        semantic: SemanticMemory | None = None,
        telegram_bot: Any = None,
        max_retries: int | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        """TaskManager'i baslatir.

        Args:
            master_agent: Gorevleri calistiran MasterAgent.
            long_term: PostgreSQL hafiza (zorunlu, kalici kayit).
            short_term: Redis hafiza (opsiyonel, aktif gorev cache).
            semantic: Qdrant hafiza (opsiyonel, semantik arama).
            telegram_bot: TelegramBot nesnesi (opsiyonel, bildirimler).
            max_retries: Maks yeniden deneme. None ise config'den alinir.
            max_concurrent: Esanli gorev limiti. None ise config'den alinir.
        """
        self.master_agent = master_agent
        self.long_term = long_term
        self.short_term = short_term
        self.semantic = semantic
        self.telegram_bot = telegram_bot

        self.max_retries = max_retries or settings.master_agent_max_retries
        _max_concurrent = max_concurrent or settings.task_manager_max_concurrent

        # Karar matrisi (oncelik hesaplama icin)
        self._decision_matrix = DecisionMatrix()

        # Oncelik kuyrugu
        self._queue: asyncio.PriorityQueue[QueuedTask] = asyncio.PriorityQueue()

        # Calisan gorevler: task_id -> asyncio.Task
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

        # Bagimlillik takibi
        self._dependencies: dict[str, set[str]] = {}   # task_id -> bekledigi ID'ler
        self._dependents: dict[str, set[str]] = {}      # task_id -> onu bekleyen ID'ler

        # Zamanlanmis gorevler: schedule_id -> {submission, cron, next_run}
        self._scheduled_tasks: dict[str, dict[str, Any]] = {}

        # Esanlillik kontrolu
        self._semaphore = asyncio.Semaphore(_max_concurrent)
        self._lock = asyncio.Lock()

        # Arkaplan dongu referanslari
        self._worker_task: asyncio.Task[None] | None = None
        self._scheduler_task: asyncio.Task[None] | None = None
        self._running = False

        # In-memory metrik sayaclari
        self._counters = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }
        self._agent_counters: dict[str, int] = {}

        logger.info(
            "TaskManager olusturuldu (max_retries=%d, max_concurrent=%d)",
            self.max_retries,
            _max_concurrent,
        )

    # === Lifecycle ===

    async def start(self) -> None:
        """Gorev yoneticisini baslatir ve arkaplan isleyicisini calistirir.

        Veritabanindan tamamlanmamis gorevleri yukler (crash recovery),
        arkaplan isleyici ve zamanlayici dongularini baslatir.
        """
        self._running = True

        # Crash recovery: tamamlanmamis gorevleri kuyruga yukle
        await self._recover_tasks()

        # Arkaplan donguleri basalt
        self._worker_task = asyncio.create_task(
            self._worker_loop(), name="task_manager_worker"
        )
        self._scheduler_task = asyncio.create_task(
            self._scheduler_loop(), name="task_manager_scheduler"
        )

        logger.info("TaskManager baslatildi (kuyruk=%d)", self._queue.qsize())

    async def stop(self) -> None:
        """Gorev yoneticisini durdurur.

        Calisan gorevlerin tamamlanmasini bekler (graceful shutdown).
        Bekleyen gorevler veritabaninda PENDING olarak kalir.
        """
        logger.info("TaskManager durduruluyor...")
        self._running = False

        # Arkaplan donguleri iptal et
        for bg_task in (self._worker_task, self._scheduler_task):
            if bg_task and not bg_task.done():
                bg_task.cancel()
                try:
                    await bg_task
                except asyncio.CancelledError:
                    pass

        # Aktif gorevlerin tamamlanmasini bekle (maks 30 saniye)
        if self._active_tasks:
            logger.info(
                "%d aktif gorev tamamlanmasi bekleniyor...",
                len(self._active_tasks),
            )
            pending = list(self._active_tasks.values())
            await asyncio.wait(pending, timeout=30)

        logger.info("TaskManager durduruldu")

    # === CRUD ===

    async def submit_task(self, submission: TaskSubmission) -> TaskResponse:
        """Yeni gorev olusturur ve kuyruga ekler.

        PostgreSQL'e yazar, Redis'e cache'ler, oncelik hesaplar
        ve bagimliliklari kontrol edip kuyruga ekler.

        Args:
            submission: Gorev gonderim verisi.

        Returns:
            Olusturulan gorev yaniti (ID dahil).

        Raises:
            ValueError: Gecersiz submission verisi.
        """
        if not submission.description.strip():
            raise ValueError("Gorev aciklamasi bos olamaz")

        # PostgreSQL'e kalici kayit
        task_data = TaskCreate(
            description=submission.description,
            agent=submission.target_agent,
            risk=submission.risk,
            urgency=submission.urgency,
        )
        task_response = await self.long_term.create_task(task_data)

        # Oncelik hesapla
        priority = self._calculate_priority(submission.risk, submission.urgency)

        # Kuyruk gorevi olustur
        queued = QueuedTask(
            id=task_response.id,
            priority=priority,
            submission=submission,
        )

        # Redis cache (opsiyonel)
        await self._cache_task_status(task_response.id, {
            "id": task_response.id,
            "status": TaskStatus.PENDING.value,
            "description": submission.description,
            "priority": priority.name,
            "source": submission.source,
        })

        # Bagimlillik kontrolu
        async with self._lock:
            has_unmet = await self._register_dependencies(
                task_response.id, submission.depends_on
            )

        # Bagimlilik yoksa veya hepsi cozulmusse kuyruga ekle
        if not has_unmet:
            await self._queue.put(queued)
        else:
            # Kuyruga alinmayi bekleyen gorev — QueuedTask'i saklayalim
            await self._cache_task_status(task_response.id + ":queued", queued.model_dump(mode="json"))

        self._counters["submitted"] += 1

        logger.info(
            "Gorev olusturuldu: id=%s, oncelik=%s, kaynak=%s",
            task_response.id[:8],
            priority.name,
            submission.source,
        )
        return task_response

    async def get_task(self, task_id: str) -> TaskResponse | None:
        """Gorev bilgisini getirir.

        Once Redis'ten (hizli yol), bulunamazsa PostgreSQL'den okur.

        Args:
            task_id: Gorev kimlik numarasi.

        Returns:
            Gorev yaniti veya None.
        """
        # PostgreSQL'den kalici kayit
        return await self.long_term.get_task(task_id)

    async def list_tasks(
        self,
        status: str | None = None,
        agent: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskResponse]:
        """Gorevleri filtreli listeler.

        Args:
            status: Durum filtresi.
            agent: Agent adi filtresi.
            limit: Maksimum kayit sayisi.
            offset: Baslangic ofseti.

        Returns:
            Gorev yanitlari listesi.
        """
        return await self.long_term.list_tasks(
            status=status, agent=agent, limit=limit, offset=offset
        )

    async def cancel_task(self, task_id: str) -> TaskResponse | None:
        """Gorevi iptal eder.

        PENDING durumundaki gorevler kuyruktan cikarilir.
        RUNNING durumundaki gorevlere iptal sinyali gonderilir.

        Args:
            task_id: Iptal edilecek gorev ID'si.

        Returns:
            Guncellenmis gorev yaniti veya None (bulunamazsa).
        """
        task = await self.long_term.get_task(task_id)
        if task is None:
            return None

        # Zaten tamamlanmis/iptal edilmis gorev
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return task

        # RUNNING gorev icin asyncio.Task iptal et
        async with self._lock:
            if task_id in self._active_tasks:
                self._active_tasks[task_id].cancel()

        # DB guncelle
        updated = await self.long_term.update_task(task_id, {
            "status": TaskStatus.CANCELLED.value,
            "result_message": "Gorev kullanici tarafindan iptal edildi",
        })

        # Redis temizle
        await self._delete_task_cache(task_id)

        # Bagimli gorevleri de iptal et
        async with self._lock:
            await self._cascade_cancel(task_id)

        self._counters["cancelled"] += 1
        logger.info("Gorev iptal edildi: %s", task_id[:8])
        return updated

    async def retry_task(self, task_id: str) -> TaskResponse | None:
        """Basarisiz gorevi tekrar kuyruga ekler.

        Args:
            task_id: Tekrar denenecek gorev ID'si.

        Returns:
            Guncellenmis gorev yaniti veya None.
        """
        task = await self.long_term.get_task(task_id)
        if task is None:
            return None

        if task.status != TaskStatus.FAILED:
            logger.warning("Sadece FAILED gorevler tekrar denenebilir: %s", task_id[:8])
            return task

        # DB durumunu sifirla
        updated = await self.long_term.update_task(task_id, {
            "status": TaskStatus.PENDING.value,
            "result_message": None,
            "result_success": None,
            "completed_at": None,
        })

        # Tekrar kuyruga ekle
        priority = self._calculate_priority(task.risk or "low", task.urgency or "low")
        submission = TaskSubmission(
            description=task.description,
            risk=task.risk or "low",
            urgency=task.urgency or "low",
            target_agent=task.agent,
            source="retry",
        )
        queued = QueuedTask(id=task_id, priority=priority, submission=submission)
        await self._queue.put(queued)

        logger.info("Gorev tekrar kuyruga eklendi: %s", task_id[:8])
        return updated

    # === Scheduling ===

    async def schedule_task(
        self,
        submission: TaskSubmission,
        cron_expression: str,
        schedule_id: str | None = None,
    ) -> str:
        """Tekrarlayan gorev planlar.

        Args:
            submission: Gorev sablonu.
            cron_expression: Basit zamanlama ifadesi.
                Desteklenen formatlar:
                - "every_Xm" : Her X dakikada bir (orn: "every_30m")
                - "every_Xh" : Her X saatte bir (orn: "every_1h")
            schedule_id: Zamanlama ID'si (None ise otomatik UUID).

        Returns:
            Zamanlama ID'si.
        """
        sid = schedule_id or str(uuid.uuid4())
        self._scheduled_tasks[sid] = {
            "submission": submission,
            "cron": cron_expression,
            "last_run": None,
            "interval_seconds": self._parse_interval(cron_expression),
        }
        logger.info("Zamanlanmis gorev eklendi: %s (%s)", sid[:8], cron_expression)
        return sid

    async def unschedule_task(self, schedule_id: str) -> bool:
        """Zamanlanmis gorevi iptal eder.

        Args:
            schedule_id: Iptal edilecek zamanlama ID'si.

        Returns:
            True: Basarili, False: Bulunamadi.
        """
        if schedule_id in self._scheduled_tasks:
            del self._scheduled_tasks[schedule_id]
            logger.info("Zamanlanmis gorev iptal edildi: %s", schedule_id[:8])
            return True
        return False

    # === Query ===

    async def get_metrics(self) -> TaskMetrics:
        """Gorev yoneticisi metriklerini dondurur.

        In-memory sayaclar ve kuyruk bilgilerini birlestirerek
        canli metrikleri hesaplar.

        Returns:
            Gorev metrikleri.
        """
        completed = self._counters["completed"]
        failed = self._counters["failed"]
        total_finished = completed + failed

        return TaskMetrics(
            total_submitted=self._counters["submitted"],
            total_completed=completed,
            total_failed=failed,
            total_cancelled=self._counters["cancelled"],
            queue_size=self._queue.qsize(),
            active_count=len(self._active_tasks),
            success_rate=completed / total_finished if total_finished > 0 else 0.0,
            by_agent=dict(self._agent_counters),
            by_status={
                "pending": self._queue.qsize(),
                "running": len(self._active_tasks),
                "completed": completed,
                "failed": failed,
                "cancelled": self._counters["cancelled"],
            },
        )

    async def search_similar_tasks(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Semantik olarak benzer gecmis gorevleri arar.

        Args:
            query: Arama sorgusu.
            limit: Maks sonuc sayisi.
            score_threshold: Minimum benzerlik skoru.

        Returns:
            Benzer gorev sonuclari listesi.
        """
        if self.semantic is None:
            return []

        try:
            results = await self.semantic.search(
                collection="task_history",
                query=query,
                limit=limit,
                score_threshold=score_threshold,
            )
            return [
                {
                    "id": r.id,
                    "text": r.text,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in results
            ]
        except Exception as exc:
            logger.warning("Semantik arama hatasi: %s", exc)
            return []

    async def get_queue_snapshot(self) -> list[dict[str, Any]]:
        """Kuyruk durumunun anlik goruntusunu dondurur.

        Returns:
            Kuyrukta bekleyen gorev bilgileri.
        """
        # PriorityQueue dogrudan iterate edilemez,
        # internal _queue listesine eriselim
        items = list(self._queue._queue)  # type: ignore[attr-defined]
        return [
            {
                "id": item.id,
                "priority": item.priority.name,
                "description": item.submission.description[:100],
                "retry_count": item.retry_count,
                "created_at": item.created_at.isoformat(),
            }
            for item in sorted(items)
        ]

    # === Internal: Oncelik Hesaplama ===

    def _calculate_priority(self, risk: str, urgency: str) -> TaskPriority:
        """Risk ve aciliyetten oncelik hesaplar.

        Karar matrisi aksiyon tipine gore oncelik belirlenir:
        - IMMEDIATE -> CRITICAL
        - AUTO_FIX  -> HIGH
        - NOTIFY    -> MEDIUM
        - LOG       -> LOW

        Args:
            risk: Risk seviyesi (low/medium/high).
            urgency: Aciliyet seviyesi (low/medium/high).

        Returns:
            Hesaplanan gorev onceligi.
        """
        try:
            action = self._decision_matrix.get_action_for(risk, urgency)
            return _ACTION_PRIORITY_MAP.get(action, TaskPriority.MEDIUM)
        except (ValueError, KeyError):
            return TaskPriority.MEDIUM

    # === Internal: Worker Loop ===

    async def _worker_loop(self) -> None:
        """Arkaplan gorev isleyici dongusu.

        Kuyruktan gorev alir, semaphore ile esanliligi sinirlar,
        her gorevi ayri asyncio.Task olarak calistirir.
        """
        logger.info("Worker dongusu baslatildi")
        while self._running:
            try:
                # Kuyruktan gorev al (1 saniyelik timeout ile)
                try:
                    queued_task = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Semaphore ile esanliligi sinirla
                await self._semaphore.acquire()

                # Gorevi arkaplan task olarak baslat
                task = asyncio.create_task(
                    self._execute_task(queued_task),
                    name=f"task_{queued_task.id[:8]}",
                )
                async with self._lock:
                    self._active_tasks[queued_task.id] = task

                # Tamamlandiginda temizle
                task.add_done_callback(
                    lambda t, tid=queued_task.id: asyncio.create_task(
                        self._on_task_done(tid)
                    )
                )

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Worker dongusu hatasi: %s", exc)
                await asyncio.sleep(1)

        logger.info("Worker dongusu durduruldu")

    async def _execute_task(self, queued_task: QueuedTask) -> None:
        """Tek bir gorevi calistirir ve sonucunu isler.

        Args:
            queued_task: Calistirilacak kuyruk gorevi.
        """
        task_id = queued_task.id
        submission = queued_task.submission

        logger.info(
            "Gorev calistiriliyor: id=%s, agent=%s, deneme=%d",
            task_id[:8],
            submission.target_agent or "auto",
            queued_task.retry_count + 1,
        )

        # DB durumunu RUNNING'e guncelle
        await self.long_term.update_task(task_id, {
            "status": TaskStatus.RUNNING.value,
            "agent": submission.target_agent,
        })

        # Redis cache guncelle
        await self._cache_task_status(task_id, {
            "id": task_id,
            "status": TaskStatus.RUNNING.value,
            "agent": submission.target_agent,
        })

        # MasterAgent'a gonder
        task_dict: dict[str, Any] = {
            "description": submission.description,
            "risk": submission.risk,
            "urgency": submission.urgency,
            "target_agent": submission.target_agent,
            "source": submission.source,
            **submission.metadata,
        }

        try:
            result = await self.master_agent.run(task_dict)
        except asyncio.CancelledError:
            # Gorev iptal edildi
            logger.info("Gorev iptal edildi (CancelledError): %s", task_id[:8])
            return
        except Exception as exc:
            result = TaskResult(
                success=False,
                message=f"Beklenmeyen hata: {exc}",
                errors=[str(exc)],
            )

        # Sonucu isle
        if result.success:
            await self._on_task_success(queued_task, result)
        else:
            await self._on_task_failure(queued_task, result)

    async def _on_task_success(
        self, queued_task: QueuedTask, result: TaskResult
    ) -> None:
        """Basarili gorev sonrasi islemleri.

        DB, Redis ve Qdrant guncellenir; bagimli gorevler acilir.

        Args:
            queued_task: Tamamlanan kuyruk gorevi.
            result: Agent sonucu.
        """
        task_id = queued_task.id
        submission = queued_task.submission

        # PostgreSQL guncelle
        await self.long_term.update_task(task_id, {
            "status": TaskStatus.COMPLETED.value,
            "result_message": result.message,
            "result_success": True,
        })

        # Redis temizle (kisa TTL ile gecici tut)
        await self._cache_task_status(task_id, {
            "id": task_id,
            "status": TaskStatus.COMPLETED.value,
            "message": result.message,
        })

        # Qdrant'a semantik kayit
        await self._store_semantic(
            task_id=task_id,
            description=submission.description,
            result_message=result.message,
            metadata={
                "agent": submission.target_agent,
                "risk": submission.risk,
                "urgency": submission.urgency,
                "status": "completed",
                "source": submission.source,
            },
        )

        # Metrik sayaclari guncelle
        self._counters["completed"] += 1
        if submission.target_agent:
            self._agent_counters[submission.target_agent] = (
                self._agent_counters.get(submission.target_agent, 0) + 1
            )

        # Bagimli gorevleri ac
        async with self._lock:
            await self._unblock_dependents(task_id)

        logger.info("Gorev tamamlandi: %s", task_id[:8])

    async def _on_task_failure(
        self, queued_task: QueuedTask, result: TaskResult
    ) -> None:
        """Basarisiz gorev sonrasi islemleri.

        Retry limiti icindeyse exponential backoff ile tekrar kuyruga ekler,
        limit asildiysa final basarisizlik olarak kaydeder.

        Args:
            queued_task: Basarisiz kuyruk gorevi.
            result: Agent hata sonucu.
        """
        task_id = queued_task.id
        max_retries = queued_task.submission.max_retries or self.max_retries

        if queued_task.retry_count < max_retries:
            # Retry: exponential backoff
            queued_task.retry_count += 1
            backoff = min(
                settings.task_manager_retry_backoff_base * (2 ** queued_task.retry_count),
                settings.task_manager_retry_backoff_max,
            )

            logger.warning(
                "Gorev basarisiz, %d saniye sonra tekrar denenecek: id=%s, deneme=%d/%d",
                backoff,
                task_id[:8],
                queued_task.retry_count,
                max_retries,
            )

            # Backoff sonrasi tekrar kuyruga ekle
            await asyncio.sleep(backoff)
            if self._running:
                await self._queue.put(queued_task)
        else:
            # Final basarisizlik
            await self.long_term.update_task(task_id, {
                "status": TaskStatus.FAILED.value,
                "result_message": result.message,
                "result_success": False,
            })

            await self._cache_task_status(task_id, {
                "id": task_id,
                "status": TaskStatus.FAILED.value,
                "message": result.message,
            })

            # Qdrant'a basarisizlik kaydi
            await self._store_semantic(
                task_id=task_id,
                description=queued_task.submission.description,
                result_message=f"BASARISIZ: {result.message}",
                metadata={
                    "agent": queued_task.submission.target_agent,
                    "risk": queued_task.submission.risk,
                    "urgency": queued_task.submission.urgency,
                    "status": "failed",
                    "errors": result.errors,
                },
            )

            self._counters["failed"] += 1

            # Bagimli gorevleri iptal et
            async with self._lock:
                await self._cascade_cancel(task_id)

            # Telegram bildirim gonder
            await self._notify_telegram(
                task_id=task_id,
                description=queued_task.submission.description,
                status="failed",
                message=result.message,
                risk=queued_task.submission.risk,
            )

            logger.error(
                "Gorev basarisiz (max retry asildi): id=%s, hata=%s",
                task_id[:8],
                result.message,
            )

    async def _on_task_done(self, task_id: str) -> None:
        """asyncio.Task tamamlanma temizligi.

        Active tasks sozlugunden cikarir ve semaphore'u serbest birakir.

        Args:
            task_id: Tamamlanan gorev ID'si.
        """
        async with self._lock:
            self._active_tasks.pop(task_id, None)
        self._semaphore.release()

    # === Internal: Bagimlillik Yonetimi ===

    async def _register_dependencies(
        self, task_id: str, depends_on: list[str]
    ) -> bool:
        """Gorev bagimliklarini kaydeder.

        Tamamlanmis bagimliliklari filtreler, sadece karsilanmamis
        olanlari izlemeye alir.

        Args:
            task_id: Bagimli gorev ID'si.
            depends_on: Bagimli olunan gorev ID'leri.

        Returns:
            True: Karsilanmamis bagimlilik var (beklenmeli).
            False: Tum bagimliliklar cozulmus veya yok.
        """
        if not depends_on:
            return False

        # Tamamlanmis bagimliliklari filtrele
        unmet: set[str] = set()
        for dep_id in depends_on:
            dep_task = await self.long_term.get_task(dep_id)
            if dep_task is None or dep_task.status != TaskStatus.COMPLETED:
                unmet.add(dep_id)

        if not unmet:
            return False

        # Karsilanmamis bagimliliklari kaydet
        self._dependencies[task_id] = unmet
        for dep_id in unmet:
            if dep_id not in self._dependents:
                self._dependents[dep_id] = set()
            self._dependents[dep_id].add(task_id)

        logger.info(
            "Gorev %s, %d bagimlilik bekliyor: %s",
            task_id[:8],
            len(unmet),
            [d[:8] for d in unmet],
        )
        return True

    async def _unblock_dependents(self, completed_task_id: str) -> None:
        """Tamamlanan gorev sonrasi bagimli gorevleri kontrol eder.

        Eger bir bagimli gorevlin tum bagimliliklari cozulmusse,
        kuyruga eklenir.

        Args:
            completed_task_id: Tamamlanan gorev ID'si.
        """
        waiting_tasks = self._dependents.pop(completed_task_id, set())

        for waiting_id in waiting_tasks:
            deps = self._dependencies.get(waiting_id)
            if deps is None:
                continue

            deps.discard(completed_task_id)

            if not deps:
                # Tum bagimliliklar cozuldu, kuyruga ekle
                del self._dependencies[waiting_id]

                # Cached QueuedTask'i getir ve kuyruga ekle
                cached = None
                if self.short_term:
                    try:
                        cached = await self.short_term.get_task_status(
                            waiting_id + ":queued"
                        )
                    except Exception:
                        pass

                if cached:
                    queued = QueuedTask.model_validate(cached)
                    await self._queue.put(queued)
                    logger.info(
                        "Gorev bagimlilik cozuldu, kuyruga eklendi: %s",
                        waiting_id[:8],
                    )

    async def _cascade_cancel(self, failed_task_id: str) -> None:
        """Basarisiz/iptal edilen gorevun bagimli gorevlerini iptal eder.

        Args:
            failed_task_id: Basarisiz/iptal olan gorev ID'si.
        """
        waiting_tasks = self._dependents.pop(failed_task_id, set())

        for waiting_id in waiting_tasks:
            self._dependencies.pop(waiting_id, None)

            await self.long_term.update_task(waiting_id, {
                "status": TaskStatus.CANCELLED.value,
                "result_message": f"Bagimli gorev basarisiz: {failed_task_id[:8]}",
            })
            self._counters["cancelled"] += 1

            # Zincirleme iptal
            await self._cascade_cancel(waiting_id)

        logger.info(
            "Cascade iptal: %s -> %d gorev iptal edildi",
            failed_task_id[:8],
            len(waiting_tasks),
        )

    # === Internal: Crash Recovery ===

    async def _recover_tasks(self) -> None:
        """Veritabanindan tamamlanmamis gorevleri yukler (crash recovery).

        RUNNING gorevler PENDING'e dusurulur ve kuyruga eklenir.
        PENDING gorevler dogrudan kuyruga eklenir.
        """
        recovered = 0

        # RUNNING gorevleri PENDING'e dusur
        running_tasks = await self.long_term.list_tasks(
            status=TaskStatus.RUNNING.value, limit=1000
        )
        for task in running_tasks:
            await self.long_term.update_task(task.id, {
                "status": TaskStatus.PENDING.value,
            })

        # PENDING gorevleri kuyruga ekle
        pending_tasks = await self.long_term.list_tasks(
            status=TaskStatus.PENDING.value, limit=1000
        )
        for task in pending_tasks:
            priority = self._calculate_priority(
                task.risk or "low", task.urgency or "low"
            )
            submission = TaskSubmission(
                description=task.description,
                risk=task.risk or "low",
                urgency=task.urgency or "low",
                target_agent=task.agent,
                source="recovery",
            )
            queued = QueuedTask(
                id=task.id,
                priority=priority,
                submission=submission,
            )
            await self._queue.put(queued)
            recovered += 1

        if recovered > 0:
            logger.info("Crash recovery: %d gorev kuyruga yuklendi", recovered)

    # === Internal: Scheduler Loop ===

    async def _scheduler_loop(self) -> None:
        """Zamanlanmis gorev dongusu.

        Her 60 saniye kontrol eder ve zamani gelen gorevleri kuyruga ekler.
        """
        logger.info("Zamanlayici dongusu baslatildi")
        while self._running:
            try:
                await asyncio.sleep(60)

                now = datetime.now(timezone.utc)
                for sid, sched in list(self._scheduled_tasks.items()):
                    interval = sched["interval_seconds"]
                    last_run = sched.get("last_run")

                    if last_run is None or (now - last_run).total_seconds() >= interval:
                        submission: TaskSubmission = sched["submission"]
                        try:
                            await self.submit_task(submission)
                            sched["last_run"] = now
                            logger.debug("Zamanlanmis gorev tetiklendi: %s", sid[:8])
                        except Exception as exc:
                            logger.error(
                                "Zamanlanmis gorev hatasi (%s): %s", sid[:8], exc
                            )

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Zamanlayici dongusu hatasi: %s", exc)

        logger.info("Zamanlayici dongusu durduruldu")

    @staticmethod
    def _parse_interval(expression: str) -> int:
        """Basit zamanlama ifadesini saniyeye cevirir.

        Desteklenen formatlar:
        - "every_Xm" : Her X dakikada bir
        - "every_Xh" : Her X saatte bir

        Args:
            expression: Zamanlama ifadesi.

        Returns:
            Saniye cinsinden aralik.

        Raises:
            ValueError: Gecersiz ifade formati.
        """
        expr = expression.lower().strip()
        if expr.startswith("every_") and expr.endswith("m"):
            minutes = int(expr[6:-1])
            return minutes * 60
        elif expr.startswith("every_") and expr.endswith("h"):
            hours = int(expr[6:-1])
            return hours * 3600
        else:
            raise ValueError(
                f"Gecersiz zamanlama ifadesi: {expression}. "
                "Beklenen format: 'every_Xm' veya 'every_Xh'"
            )

    # === Internal: Helpers ===

    async def _cache_task_status(
        self, key: str, data: dict[str, Any]
    ) -> None:
        """Redis'e gorev durumu kaydeder (hata yutulur).

        Args:
            key: Cache anahtari (genellikle task_id).
            data: Cache verisi.
        """
        if self.short_term is None:
            return
        try:
            await self.short_term.store_task_status(key, data)
        except Exception as exc:
            logger.warning("Redis cache yazma hatasi: %s", exc)

    async def _delete_task_cache(self, task_id: str) -> None:
        """Redis'ten gorev durumunu siler (hata yutulur).

        Args:
            task_id: Silinecek gorev ID'si.
        """
        if self.short_term is None:
            return
        try:
            await self.short_term.delete_task_status(task_id)
            await self.short_term.delete_task_status(task_id + ":queued")
        except Exception as exc:
            logger.warning("Redis cache silme hatasi: %s", exc)

    async def _store_semantic(
        self,
        task_id: str,
        description: str,
        result_message: str,
        metadata: dict[str, Any],
    ) -> None:
        """Qdrant'a gorev sonucu kaydeder (hata yutulur).

        Args:
            task_id: Gorev ID'si.
            description: Gorev aciklamasi.
            result_message: Sonuc mesaji.
            metadata: Ek meta veriler.
        """
        if self.semantic is None:
            return
        try:
            text = f"{description} -> {result_message}"
            await self.semantic.store(
                collection="task_history",
                text=text,
                metadata=metadata,
                source="task_manager",
                point_id=task_id,
            )
        except Exception as exc:
            logger.warning("Qdrant semantik kayit hatasi: %s", exc)

    async def _notify_telegram(
        self,
        task_id: str,
        description: str,
        status: str,
        message: str,
        risk: str | None = None,
    ) -> None:
        """Gorev durumu hakkinda Telegram bildirimi gonderir.

        Sadece basarisiz veya yuksek riskli gorevler icin bildirim gonderir.

        Args:
            task_id: Gorev ID'si.
            description: Gorev aciklamasi.
            status: Mevcut durum (completed/failed).
            message: Sonuc mesaji.
            risk: Risk seviyesi.
        """
        if self.telegram_bot is None:
            return

        # Sadece fail ve yuksek risk tamamlanmalarda bildir
        should_notify = (
            status == "failed"
            or risk == "high"
        )
        if not should_notify:
            return

        status_label = "BASARISIZ" if status == "failed" else "TAMAMLANDI"
        text = (
            f"ATLAS Gorev Bildirimi\n"
            f"Durum: {status_label}\n"
            f"ID: {task_id[:8]}\n"
            f"Aciklama: {description[:200]}\n"
            f"Sonuc: {message[:300]}"
        )

        try:
            if status == "failed":
                await self.telegram_bot.send_buttons(
                    text=text,
                    buttons=[
                        {"text": "Tekrar Dene", "callback_data": f"retry_{task_id}"},
                        {"text": "Kapat", "callback_data": f"dismiss_{task_id}"},
                    ],
                )
            else:
                await self.telegram_bot.send_message(text)
        except Exception as exc:
            logger.warning("Telegram bildirim hatasi: %s", exc)
