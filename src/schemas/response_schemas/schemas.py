from dataclasses import asdict
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.entity.tasks import Task, TaskPriority, TaskStatus


class TaskResponse(BaseModel):
    id: UUID
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    result: Optional[str]
    error: Optional[str]

    @staticmethod
    def from_entity(task: Task) -> "TaskResponse":
        return TaskResponse(**asdict(task))


class TaskListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TaskResponse]


class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: TaskStatus