from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.entity.tasks import TaskPriority


def test_create_task_endpoint_returns_created_response(
    api_client: TestClient,
    fake_task_usecase,
) -> None:
    payload = {
        "name": "HTTP task",
        "description": "Created via API",
        "priority": TaskPriority.HIGH.value,
    }

    response = api_client.post(
        "/api/v1/tasks/",
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["priority"] == TaskPriority.HIGH.value
    assert fake_task_usecase.created, "Usecase should capture payload"


def test_get_task_status_returns_not_found_for_missing_task(
    api_client: TestClient,
) -> None:
    random_id = uuid4()

    response = api_client.get(f"/api/v1/tasks/{random_id}/status")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

