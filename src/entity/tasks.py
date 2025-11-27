from __future__ import annotations

import typing
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

TaskId = typing.NewType("TaskID", uuid.UUID)


class TaskStatus(str, Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(slots=True)
class Task:
    id: TaskId
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    result: Optional[str]
    error: Optional[str]


@dataclass(slots=True)
class CreateTask:
    name: str
    description: str
    priority: TaskPriority


@dataclass(slots=True)
class TaskFilter:
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    search: Optional[str] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None


@dataclass(slots=True)
class Pagination:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

