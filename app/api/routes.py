"""ATLAS API endpoint'leri.

Gorev yonetimi, agent bilgileri, metrikler ve semantik
hafiza aramasi icin RESTful API endpointleri.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.task_manager import TaskMetrics, TaskSubmission
from app.models.task import TaskResponse, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# === Response modelleri ===


class TaskListResponse(BaseModel):
    """Gorev listesi yanit modeli.

    Attributes:
        tasks: Gorev listesi.
        total: Toplam sonuc sayisi.
        limit: Sayfa basi kayit siniri.
        offset: Baslangic ofseti.
    """

    tasks: list[TaskResponse]
    total: int
    limit: int
    offset: int


class TaskDetailResponse(BaseModel):
    """Tek gorev detay yanit modeli.

    Attributes:
        task: Gorev bilgisi.
    """

    task: TaskResponse


class AgentInfoResponse(BaseModel):
    """Agent listesi yanit modeli.

    Attributes:
        agents: Kayitli agent bilgileri listesi.
        count: Toplam agent sayisi.
    """

    agents: list[dict[str, Any]]
    count: int


class MetricsResponse(BaseModel):
    """Metrik yanit modeli.

    Attributes:
        metrics: Gorev yoneticisi metrikleri.
    """

    metrics: TaskMetrics


class MemorySearchRequest(BaseModel):
    """Semantik hafiza arama istek modeli.

    Attributes:
        query: Arama sorgusu.
        limit: Maksimum sonuc sayisi.
        score_threshold: Minimum benzerlik skoru.
    """

    query: str
    limit: int = Field(default=5, ge=1, le=50)
    score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class MemorySearchResponse(BaseModel):
    """Semantik hafiza arama yanit modeli.

    Attributes:
        results: Arama sonuclari.
        query: Kullanilan sorgu.
        count: Sonuc sayisi.
    """

    results: list[dict[str, Any]]
    query: str
    count: int


# === Yardimci fonksiyonlar ===


def _get_task_manager(request: Request) -> Any:
    """App state'ten TaskManager'i alir.

    Args:
        request: FastAPI istek nesnesi.

    Returns:
        TaskManager nesnesi.

    Raises:
        HTTPException: TaskManager hazir degilse (503).
    """
    task_manager = getattr(request.app.state, "task_manager", None)
    if not task_manager:
        raise HTTPException(
            status_code=503,
            detail="TaskManager hazir degil",
        )
    return task_manager


# === Gorev endpoint'leri ===


@router.post("/tasks", status_code=202)
async def create_task(
    request: Request,
    payload: dict[str, Any],
) -> dict[str, str]:
    """Yeni gorev olusturur ve TaskManager'a iletir.

    Gorev arkaplanda islenecek sekilde kuyruga eklenir.
    Yanit olarak gorev ID'si ve durumu dondurulur (202 Accepted).

    Args:
        request: FastAPI istek nesnesi.
        payload: Gorev detaylarini iceren sozluk.

    Returns:
        Gorev kabul bilgisi.
    """
    task_manager = _get_task_manager(request)

    logger.info("Yeni gorev alindi: %s", payload.get("description", "tanimsiz"))

    submission = TaskSubmission(
        description=str(payload.get("description", "tanimsiz gorev")),
        risk=str(payload.get("risk", "low")),
        urgency=str(payload.get("urgency", "low")),
        target_agent=(
            str(payload["target_agent"]) if payload.get("target_agent") else None
        ),
        source="api",
        metadata={
            k: v
            for k, v in payload.items()
            if k not in ("description", "risk", "urgency", "target_agent")
        },
    )

    task_response = await task_manager.submit_task(submission)

    return {
        "status": "accepted",
        "message": "Gorev kuyruga eklendi",
        "task_id": task_response.id,
        "task_status": task_response.status.value,
    }


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    request: Request,
    status: str | None = Query(default=None, description="Durum filtresi"),
    agent: str | None = Query(default=None, description="Agent adi filtresi"),
    limit: int = Query(default=50, ge=1, le=200, description="Sayfa basi kayit"),
    offset: int = Query(default=0, ge=0, description="Baslangic ofseti"),
) -> TaskListResponse:
    """Gorevleri filtreli listeler.

    Args:
        request: FastAPI istek nesnesi.
        status: Durum filtresi (pending, running, completed, failed, cancelled).
        agent: Agent adi filtresi.
        limit: Sayfa basi kayit siniri.
        offset: Baslangic ofseti.

    Returns:
        Gorev listesi yaniti.
    """
    task_manager = _get_task_manager(request)

    # Gecerli durum kontrolu
    if status is not None:
        valid_statuses = {s.value for s in TaskStatus}
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Gecersiz durum: {status}. Gecerli: {', '.join(valid_statuses)}",
            )

    tasks = await task_manager.list_tasks(
        status=status, agent=agent, limit=limit, offset=offset,
    )

    return TaskListResponse(
        tasks=tasks,
        total=len(tasks),
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    request: Request,
    task_id: str,
) -> TaskDetailResponse:
    """Belirli bir gorevin detayini getirir.

    Args:
        request: FastAPI istek nesnesi.
        task_id: Gorev kimlik numarasi.

    Returns:
        Gorev detay yaniti.

    Raises:
        HTTPException: Gorev bulunamazsa (404).
    """
    task_manager = _get_task_manager(request)

    task = await task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Gorev bulunamadi")

    return TaskDetailResponse(task=task)


@router.post("/tasks/{task_id}/cancel", response_model=TaskDetailResponse)
async def cancel_task(
    request: Request,
    task_id: str,
) -> TaskDetailResponse:
    """Gorevi iptal eder.

    PENDING durumundaki gorevler kuyruktan cikarilir.
    RUNNING durumundaki gorevlere iptal sinyali gonderilir.

    Args:
        request: FastAPI istek nesnesi.
        task_id: Iptal edilecek gorev ID'si.

    Returns:
        Guncellenmis gorev bilgisi.

    Raises:
        HTTPException: Gorev bulunamazsa (404).
    """
    task_manager = _get_task_manager(request)

    task = await task_manager.cancel_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Gorev bulunamadi")

    logger.info("API ile gorev iptal edildi: %s", task_id[:8])
    return TaskDetailResponse(task=task)


@router.post("/tasks/{task_id}/retry", response_model=TaskDetailResponse)
async def retry_task(
    request: Request,
    task_id: str,
) -> TaskDetailResponse:
    """Basarisiz gorevi tekrar kuyruga ekler.

    Sadece FAILED durumundaki gorevler icin gecerlidir.

    Args:
        request: FastAPI istek nesnesi.
        task_id: Tekrar denenecek gorev ID'si.

    Returns:
        Guncellenmis gorev bilgisi.

    Raises:
        HTTPException: Gorev bulunamazsa (404).
    """
    task_manager = _get_task_manager(request)

    task = await task_manager.retry_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Gorev bulunamadi")

    logger.info("API ile gorev tekrar kuyruga eklendi: %s", task_id[:8])
    return TaskDetailResponse(task=task)


# === Agent endpoint'leri ===


@router.get("/agents", response_model=AgentInfoResponse)
async def list_agents(request: Request) -> AgentInfoResponse:
    """Kayitli agent listesini dondurur.

    Args:
        request: FastAPI istek nesnesi.

    Returns:
        Agent bilgileri yaniti.
    """
    master_agent = getattr(request.app.state, "master_agent", None)
    if not master_agent:
        return AgentInfoResponse(agents=[], count=0)

    agents = master_agent.get_registered_agents()
    return AgentInfoResponse(agents=agents, count=len(agents))


# === Metrik endpoint'leri ===


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(request: Request) -> MetricsResponse:
    """TaskManager metriklerini dondurur.

    Kuyruk boyutu, aktif gorev sayisi, basari orani
    ve agent bazli istatistikleri icerir.

    Args:
        request: FastAPI istek nesnesi.

    Returns:
        Metrik yaniti.
    """
    task_manager = _get_task_manager(request)

    metrics = await task_manager.get_metrics()
    return MetricsResponse(metrics=metrics)


# === Hafiza endpoint'leri ===


@router.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(
    request: Request,
    body: MemorySearchRequest,
) -> MemorySearchResponse:
    """Semantik hafizada benzer gorevleri arar.

    Qdrant vektor veritabanini kullanarak gecmis gorevler
    arasinda benzerlik aramasi yapar.

    Args:
        request: FastAPI istek nesnesi.
        body: Arama parametreleri.

    Returns:
        Arama sonuclari yaniti.

    Raises:
        HTTPException: Semantik hafiza kullanilamazsa (503).
    """
    task_manager = _get_task_manager(request)

    try:
        results = await task_manager.search_similar_tasks(
            query=body.query,
            limit=body.limit,
            score_threshold=body.score_threshold,
        )
    except Exception as exc:
        logger.error("Semantik arama hatasi: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Semantik hafiza kullanilamiyor",
        )

    return MemorySearchResponse(
        results=results,
        query=body.query,
        count=len(results),
    )
