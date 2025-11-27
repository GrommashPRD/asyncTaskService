from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"


@dataclass(slots=True)
class OutboxEventPayload:
    data: Dict[str, Any]


@dataclass(slots=True)
class OutboxEvent:
    id: UUID
    event_type: str
    payload: Dict[str, Any]
    status: OutboxStatus
    retries: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class NewOutboxEvent:
    event_type: str
    payload: Dict[str, Any]

