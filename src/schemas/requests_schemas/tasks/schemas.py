from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field

from src.entity.tasks import TaskPriority, TaskStatus


class TaskCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    priority: TaskPriority = Field(..., description="Приоритет задачи")


class TaskListFilterQuery(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20

    @classmethod
    def as_query(
        cls,
        status: Optional[TaskStatus] = Query(None, alias="status"),
        priority: Optional[TaskPriority] = Query(None, alias="priority"),
        search: Optional[str] = Query(None, min_length=1, max_length=255),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ) -> "TaskListFilterQuery":
        return cls(
            status=status,
            priority=priority,
            search=search,
            page=page,
            page_size=page_size,
        )
