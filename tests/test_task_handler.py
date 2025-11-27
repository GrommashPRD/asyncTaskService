from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.api.handlers.tasks.task_handler import (cancel_task, create_task,
                                                 get_task, get_task_status,
                                                 list_tasks)
from src.entity.tasks import CreateTask, TaskPriority, TaskStatus
from src.api.schemas.requests_schemas.tasks.schemas import (TaskCreateRequest,
                                                            TaskListFilterQuery)


@pytest.mark.asyncio()
async def test_create_task_uses_usecase_only(
    fake_task_usecase,
) -> None:
    body = TaskCreateRequest(
        name="Test task",
        description="Test description",
        priority=TaskPriority.HIGH,
    )

    response = await create_task(
        body=body,
        uc=fake_task_usecase,
    )

    assert len(fake_task_usecase.created) == 1
    payload = fake_task_usecase.created[0]
    assert payload.name == body.name
    assert payload.description == body.description
    assert payload.priority == TaskPriority.HIGH

@pytest.mark.asyncio()
async def test_list_tasks_returns_empty_list_when_no_tasks(
    fake_task_usecase,
) -> None:
    fake_task_usecase._tasks.clear()

    filters = TaskListFilterQuery(
        page=1,
        page_size=10,
        status=None,
        priority=None,
        search=None,
    )

    response = await list_tasks(
        uc=fake_task_usecase,
        filters=filters,
    )

    assert response.total == 0
    assert response.items == []


@pytest.mark.asyncio()
async def test_get_task_not_found_raises_404(fake_task_usecase) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_task(task_id="00000000-0000-0000-0000-000000000000", uc=fake_task_usecase)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio()
async def test_get_task_status_ok(fake_task_usecase) -> None:
    created = await fake_task_usecase.create_task(
        CreateTask(
            name="Status task",
            description="Check status",
            priority=TaskPriority.MEDIUM,
        )
    )

    response = await get_task_status(task_id=created.id, uc=fake_task_usecase)

    assert response.task_id == created.id
    assert response.status == created.status


@pytest.mark.asyncio()
async def test_cancel_task_changes_status_to_cancelled(fake_task_usecase) -> None:
    created = await fake_task_usecase.create_task(
        CreateTask(
            name="Cancel task",
            description="To be cancelled",
            priority=TaskPriority.LOW,
        )
    )

    response = await cancel_task(task_id=created.id, uc=fake_task_usecase)

    assert response.id == created.id
    assert response.status == TaskStatus.CANCELLED

