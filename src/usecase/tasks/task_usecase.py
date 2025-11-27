from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from src.entity.outbox import NewOutboxEvent
from src.entity.tasks import (CreateTask, Pagination, Task, TaskFilter,
                              TaskStatus)
from src.exceptions import TaskCancellationError, TaskNotFoundError
from src.infrastructure.persistence.repositories.tasks import TaskRepository
from src.infrastructure.persistence.uow import UnitOfWork


class TaskUseCase:
    """
    Координирует операции задач между репозиториями и уровнем обмена сообщениями.
    """

    def __init__(self, repository: TaskRepository, uow: UnitOfWork) -> None:
        """
        Хранит зависимости репозитория
        """
        self._repository = repository
        self._uow = uow

    async def create_task(self, payload: CreateTask) -> Task:
        """
        Создает задачу и отправляет задачу в очередь.
        """
        async with self._uow.init() as repositories:
            task = await repositories.tasks.create_task(payload)
            await repositories.outbox.add_event(
                NewOutboxEvent(
                    event_type="task.created",
                    payload={"task_id": str(task.id)},
                )
            )
            return task

    async def list_tasks(
            self,
            filters: TaskFilter,
            pagination: Pagination
    ) -> Tuple[List[Task], int]:
        """
        Возвращает отфильтрованный и постраничный список задач.
        """
        return await self._repository.list_tasks(filters, pagination)

    async def get_task(self, task_id: UUID) -> Task:
        """
        Получает задачу если она существует
        """
        task = await self._repository.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(task_id=task_id)
        return task

    async def cancel_task(self, task_id: UUID) -> Task:
        """
        Отменяет задачу
        """
        task = await self.get_task(task_id)

        if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            raise TaskCancellationError(task_id=task_id, status=task.status)

        cancelled = await self._repository.cancel_task(task_id)
        if cancelled is None:
            raise TaskNotFoundError(task_id=task_id)
        return cancelled

    async def set_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        error: Optional[str] = None,
        result: Optional[str] = None,
    ) -> Task:
        updated = await self._repository.set_status(
            task_id,
            status,
            error=error,
            result=result
        )
        if updated is None:
            raise TaskNotFoundError(task_id=task_id)
        return updated

