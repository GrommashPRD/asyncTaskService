from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.entity.tasks import Task, TaskId, TaskPriority, TaskStatus
from src.exceptions import TaskCancellationError, TaskNotFoundError
from src.usecase.tasks import TaskUseCase


class FakeTaskRepository:
    def __init__(self, tasks: dict[TaskId, Task] | None = None) -> None:
        self.tasks = tasks or {}

    async def get_task(self, task_id):
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            return None
        cancelled = replace(task, status=TaskStatus.CANCELLED)
        self.tasks[task_id] = cancelled
        return cancelled


class NoopUnitOfWork:
    class _Context:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def init(self):
        return self._Context()


@pytest.mark.asyncio()
async def test_get_task_raises_not_found_when_absent():
    usecase = TaskUseCase(repository=FakeTaskRepository(), uow=NoopUnitOfWork())

    with pytest.raises(TaskNotFoundError):
        await usecase.get_task(uuid4())


@pytest.mark.asyncio()
async def test_cancel_task_rejects_completed_task():
    task_id = TaskId(uuid4())
    task = Task(
        id=task_id,
        name="Done",
        description="Already finished",
        priority=TaskPriority.HIGH,
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        started_at=None,
        finished_at=None,
        result=None,
        error=None,
    )
    usecase = TaskUseCase(
        repository=FakeTaskRepository({task_id: task}),
        uow=NoopUnitOfWork(),
    )

    with pytest.raises(TaskCancellationError):
        await usecase.cancel_task(task_id)

