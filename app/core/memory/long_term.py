"""ATLAS uzun sureli hafiza modulu (PostgreSQL).

Gorev gecmisi, karar kayitlari ve agent loglarinin kalici saklanmasi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database as db
from app.models.agent_log import AgentLogCreate, AgentLogRecord, AgentLogResponse
from app.models.decision import DecisionCreate, DecisionRecord, DecisionResponse
from app.models.task import TaskCreate, TaskRecord, TaskResponse, TaskStatus

logger = logging.getLogger(__name__)


class LongTermMemory:
    """PostgreSQL tabanli uzun sureli hafiza sinifi.

    Gorev gecmisi, karar kayitlari ve agent log CRUD islemlerini yonetir.
    """

    def __init__(self) -> None:
        """LongTermMemory'yi baslatir."""
        logger.info("Uzun sureli hafiza modulu hazirlandi")

    async def _get_session(self) -> AsyncSession:
        """Yeni bir async session olusturur.

        Returns:
            Yeni AsyncSession.

        Raises:
            RuntimeError: Veritabani baslatilmamissa.
        """
        if db.async_session_factory is None:
            raise RuntimeError("Veritabani baslatilmamis. Once init_db() cagiriniz.")
        return db.async_session_factory()

    # === Gorev gecmisi CRUD ===

    async def create_task(self, task_data: TaskCreate) -> TaskResponse:
        """Yeni gorev kaydi olusturur.

        Args:
            task_data: Gorev olusturma verisi.

        Returns:
            Olusturulan gorev yaniti.
        """
        session = await self._get_session()
        async with session:
            record = TaskRecord(
                description=task_data.description,
                agent=task_data.agent,
                risk=task_data.risk,
                urgency=task_data.urgency,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("Gorev kaydedildi: id=%s", record.id)
            return TaskResponse.model_validate(record)

    async def get_task(self, task_id: str) -> TaskResponse | None:
        """Gorev kaydini ID ile getirir.

        Args:
            task_id: Gorev kimlik numarasi.

        Returns:
            Gorev yaniti veya None (bulunamazsa).
        """
        session = await self._get_session()
        async with session:
            record = await session.get(TaskRecord, task_id)
            if record is None:
                return None
            return TaskResponse.model_validate(record)

    async def update_task(
        self,
        task_id: str,
        updates: dict[str, Any],
    ) -> TaskResponse | None:
        """Gorev kaydini gunceller.

        Args:
            task_id: Gorev kimlik numarasi.
            updates: Guncellenecek alanlar.

        Returns:
            Guncellenmis gorev yaniti veya None (bulunamazsa).
        """
        session = await self._get_session()
        async with session:
            record = await session.get(TaskRecord, task_id)
            if record is None:
                return None

            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)

            # Tamamlanma zamani otomatik set edilir
            if updates.get("status") in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
                record.completed_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(record)
            logger.info("Gorev guncellendi: id=%s", task_id)
            return TaskResponse.model_validate(record)

    async def list_tasks(
        self,
        status: str | None = None,
        agent: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskResponse]:
        """Gorev kayitlarini filtreli listeler.

        Args:
            status: Durum filtresi (opsiyonel).
            agent: Agent adi filtresi (opsiyonel).
            limit: Maksimum kayit sayisi.
            offset: Baslangic ofseti.

        Returns:
            Gorev yanitlari listesi.
        """
        session = await self._get_session()
        async with session:
            stmt = select(TaskRecord).order_by(desc(TaskRecord.created_at))

            if status is not None:
                stmt = stmt.where(TaskRecord.status == status)
            if agent is not None:
                stmt = stmt.where(TaskRecord.agent == agent)

            stmt = stmt.limit(limit).offset(offset)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [TaskResponse.model_validate(r) for r in records]

    # === Karar gecmisi ===

    async def save_decision(self, decision_data: DecisionCreate) -> DecisionResponse:
        """Karar kaydini veritabanina kaydeder.

        Args:
            decision_data: Karar olusturma verisi.

        Returns:
            Kaydedilen karar yaniti.
        """
        session = await self._get_session()
        async with session:
            record = DecisionRecord(
                task_id=decision_data.task_id,
                risk=decision_data.risk,
                urgency=decision_data.urgency,
                action=decision_data.action,
                confidence=decision_data.confidence,
                reason=decision_data.reason,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.info("Karar kaydedildi: id=%s, aksiyon=%s", record.id, record.action)
            return DecisionResponse.model_validate(record)

    async def query_decisions(
        self,
        task_id: str | None = None,
        risk: str | None = None,
        limit: int = 50,
    ) -> list[DecisionResponse]:
        """Karar kayitlarini filtreli sorgular.

        Args:
            task_id: Gorev ID filtresi (opsiyonel).
            risk: Risk seviyesi filtresi (opsiyonel).
            limit: Maksimum kayit sayisi.

        Returns:
            Karar yanitlari listesi.
        """
        session = await self._get_session()
        async with session:
            stmt = select(DecisionRecord).order_by(desc(DecisionRecord.created_at))

            if task_id is not None:
                stmt = stmt.where(DecisionRecord.task_id == task_id)
            if risk is not None:
                stmt = stmt.where(DecisionRecord.risk == risk)

            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [DecisionResponse.model_validate(r) for r in records]

    # === Agent log ===

    async def save_agent_log(self, log_data: AgentLogCreate) -> AgentLogResponse:
        """Agent log kaydini veritabanina kaydeder.

        Args:
            log_data: Agent log olusturma verisi.

        Returns:
            Kaydedilen log yaniti.
        """
        session = await self._get_session()
        async with session:
            record = AgentLogRecord(
                agent_name=log_data.agent_name,
                action=log_data.action,
                details=log_data.details,
                status=log_data.status,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            logger.debug(
                "Agent log kaydedildi: agent=%s, aksiyon=%s",
                record.agent_name,
                record.action,
            )
            return AgentLogResponse.model_validate(record)

    async def query_agent_logs(
        self,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AgentLogResponse]:
        """Agent log kayitlarini filtreli sorgular.

        Args:
            agent_name: Agent adi filtresi (opsiyonel).
            status: Durum filtresi (opsiyonel).
            limit: Maksimum kayit sayisi.

        Returns:
            Agent log yanitlari listesi.
        """
        session = await self._get_session()
        async with session:
            stmt = select(AgentLogRecord).order_by(desc(AgentLogRecord.created_at))

            if agent_name is not None:
                stmt = stmt.where(AgentLogRecord.agent_name == agent_name)
            if status is not None:
                stmt = stmt.where(AgentLogRecord.status == status)

            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [AgentLogResponse.model_validate(r) for r in records]
