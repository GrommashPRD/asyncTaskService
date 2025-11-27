from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.outbox import NewOutboxEvent, OutboxEvent, OutboxStatus
from src.infrastructure.persistence.db.schema import Outbox as OutboxModel


class OutboxRepository:

    def __init__(self, session: AsyncSession, *, auto_commit: bool = True) -> None:
        self._session = session
        self._auto_commit = auto_commit

    async def add_event(self, event: NewOutboxEvent) -> OutboxEvent:
        """
        Новое сообщение для outbox.
        """
        model = OutboxModel(
            event_type=event.event_type,
            payload=json.dumps(event.payload),
            status=OutboxStatus.PENDING,
        )
        self._session.add(model)
        await self._commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def fetch_pending(self, limit: int, *, max_retries: int | None = None) -> List[OutboxEvent]:
        """
        Выборка ожидающих событий ограниченная количеством и необязательным ограничением на повторные попытки.
        """
        stmt: Select[OutboxModel] = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PENDING)
            .order_by(OutboxModel.created_at.asc())
            .limit(limit)
        )
        if max_retries is not None:
            stmt = stmt.where(OutboxModel.retries < max_retries)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(row) for row in rows]

    async def mark_sent(self, event_id: UUID) -> None:
        """
        Помечает событие как отправленное и удаляет его из БД.
        """
        await self.delete(event_id)

    async def delete(self, event_id: UUID) -> None:
        """
        Удаление события.
        """
        await self._session.execute(
            delete(OutboxModel).where(OutboxModel.id == event_id)
        )
        await self._commit()

    async def mark_failed(self, event_id: UUID, error: str) -> None:
        await self._session.execute(
            update(OutboxModel)
            .where(OutboxModel.id == event_id)
            .values(
                retries=OutboxModel.retries + 1,
                last_error=error,
                updated_at=datetime.utcnow(),
            )
        )
        await self._commit()

    async def _commit(self) -> None:
        if self._auto_commit:
            await self._session.commit()
        else:
            await self._session.flush()

    def _to_entity(self, model: OutboxModel) -> OutboxEvent:
        payload: Dict[str, Any] = json.loads(model.payload)
        return OutboxEvent(
            id=model.id,
            event_type=model.event_type,
            payload=payload,
            status=model.status,
            retries=model.retries,
            last_error=model.last_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

