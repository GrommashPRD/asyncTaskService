from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from src.entity.tasks import (CreateTask, Pagination, Task, TaskFilter, TaskId,
                              TaskStatus)
from src.exceptions import RepositoryError
from src.infrastructure.persistence.db.schema import Task as TaskModel


class TaskRepository:
    """
    Инкапсуляция CRUD-операций для задач.
    """

    def __init__(self, session: AsyncSession, *, auto_commit: bool = True) -> None:
        self._session: AsyncSession = session
        self._auto_commit = auto_commit

    async def create_task(self, payload: CreateTask) -> Task:
        """
        Запись новой такски в БД
        """
        try:
            db_task = TaskModel(
                name=payload.name,
                description=payload.description,
                priority=payload.priority,
            )
            self._session.add(db_task)
            await self._commit()
            await self._session.refresh(db_task)
            return self._to_entity(db_task)
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to create task") from exc

    async def list_tasks(
        self,
        filters: TaskFilter,
        pagination: Pagination,
    ) -> Tuple[List[Task], int]:
        """
        Возвращает постраничный список таск.
        """
        try:
            stmt: Select[TaskModel] = select(TaskModel)
            stmt = self._apply_filters(stmt, filters)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)

            result = await self._session.execute(stmt)
            rows = result.scalars().all()

            count_stmt: Select[Any] = select(func.count(TaskModel.id))
            count_stmt = self._apply_filters(count_stmt, filters)
            total = await self._session.scalar(count_stmt)
            total_count = int(total or 0)

            return [self._to_entity(row) for row in rows], total_count
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to list tasks") from exc

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """
        Возвращает таску по UUID или не возвращает, если она отсутствует.
        """
        try:
            stmt: Select[TaskModel] = select(TaskModel).where(TaskModel.id == task_id)
            result = await self._session.execute(stmt)
            task = result.scalar_one_or_none()
            return self._to_entity(task) if task else None
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to get task") from exc

    async def set_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        error: Optional[str] = None,
        result: Optional[str] = None,
        finished_at: Optional[datetime] = None,
    ) -> Optional[Task]:
        """
        Обновление статуса таски.
        """
        try:
            stmt: Select[TaskModel] = select(TaskModel).where(TaskModel.id == task_id)
            db_task = (await self._session.execute(stmt)).scalar_one_or_none()
            if db_task is None:
                return None

            db_task.status = status
            db_task.error = error
            db_task.result = result
            if finished_at is not None:
                db_task.finished_at = finished_at

            await self._commit()
            await self._session.refresh(db_task)
            return self._to_entity(db_task)
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise RepositoryError("Failed to update task status") from exc

    async def cancel_task(self, task_id: UUID) -> Optional[Task]:
        """
        Отмена задачи
        """
        return await self.set_status(
            task_id,
            TaskStatus.CANCELLED,
            finished_at=datetime.utcnow(),
        )

    def _apply_filters(self, stmt: Select[Any], filters: TaskFilter) -> Select[Any]:
        """
        Применение условий TaskFilter к выборке.
        """
        if filters.status:
            stmt = stmt.where(TaskModel.status == filters.status)
        if filters.priority:
            stmt = stmt.where(TaskModel.priority == filters.priority)
        if filters.search:
            like_pattern = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(TaskModel.name).like(like_pattern),
                    func.lower(TaskModel.description).like(like_pattern),
                )
            )
        if filters.created_from:
            stmt = stmt.where(TaskModel.created_at >= filters.created_from)
        if filters.created_to:
            stmt = stmt.where(TaskModel.created_at <= filters.created_to)
        return stmt

    @staticmethod
    def _to_entity(task: TaskModel) -> Task:
        """
        Преобразование модели ORM в объект entity.
        """
        return Task(
            id=TaskId(task.id),
            name=task.name,
            description=task.description,
            priority=task.priority,
            status=task.status,
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            result=task.result,
            error=task.error,
        )

    async def _commit(self) -> None:
        if self._auto_commit:
            await self._session.commit()
        else:
            await self._session.flush()
