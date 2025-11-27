from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.entity.tasks import CreateTask, Task, TaskId, TaskStatus
from src.exceptions import TaskCancellationError, TaskNotFoundError
from src.main import create_app


class FakeTaskUseCase:
    """
    Пример использования заглушки для тестирования обработчиков API без реальной базы данных.
    """

    def __init__(self) -> None:
        self.created: list[CreateTask] = []
        self._tasks: dict[TaskId, Task] = {}

    async def create_task(self, payload: CreateTask) -> Task:
        self.created.append(payload)
        task_id = TaskId(uuid4())
        task = Task(
            id=task_id,
            name=payload.name,
            description=payload.description,
            priority=payload.priority,
            status=TaskStatus.NEW,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            finished_at=None,
            result=None,
            error=None,
        )
        self._tasks[task_id] = task
        return task

    async def list_tasks(self, *args: Any, **kwargs: Any) -> tuple[list[Task], int]:
        tasks = list(self._tasks.values())
        return tasks, len(tasks)

    async def get_task(self, task_id: TaskId) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id=task_id)
        return task

    async def cancel_task(self, task_id: TaskId) -> Task:
        task = await self.get_task(task_id)
        if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            raise TaskCancellationError(task_id=task_id, status=task.status)
        task.status = TaskStatus.CANCELLED
        self._tasks[task_id] = task
        return task


@pytest.fixture()
def fake_task_usecase() -> FakeTaskUseCase:
    return FakeTaskUseCase()


@pytest.fixture()
def api_client(fake_task_usecase: FakeTaskUseCase) -> TestClient:
    app = create_app()
    app.container.usecase.task_usecase.override(providers.Object(fake_task_usecase))

    with TestClient(app) as client:
        yield client

    app.container.usecase.task_usecase.reset_override()



