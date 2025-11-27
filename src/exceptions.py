from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class AppError(Exception):
    """
    Исключение базового уровня приложения.

    Должно использоваться для всех ожидаемых, контролируемых сценариев ошибок в
    приложении.
    """
    def __init__(self, message: str = "", *, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: Dict[str, Any] = context or {}

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message or self.__class__.__name__


class RepositoryError(AppError):
    """
    Базовая класс ошибок для persistence/repository слоя.
    """


class UnitOfWorkError(AppError):
    """
    Ошибка для UOW при которой падает транзакция
    """


class MessagingError(AppError):
    """
    Базовый класс ошибок для messaging / RabbitMQ операций.
    """


class TaskError(AppError):
    """
    Базовый класс ошибок для task-related оперций.
    """


@dataclass
class TaskNotFoundError(TaskError):
    """
    Возникает, когда задача с заданным UUID не существует.
    """

    task_id: Any
    message: str = "Task not found"

    def __post_init__(self) -> None:
        self.context = {"task_id": str(self.task_id)}


@dataclass
class TaskCancellationError(TaskError):

    task_id: Any
    status: Any
    message: str = "Task cannot be cancelled in the current status"

    def __post_init__(self) -> None:
        self.context = {
            "task_id": str(self.task_id),
            "status": str(self.status),
        }


class TaskCreationError(TaskError):
    """
    Вызывается, когда задача не может быть создана.
    """


@dataclass
class TaskPublishError(MessagingError):
    """
    Возникает, когда задача не может быть опубликована в очереди.
    """

    task_id: Any
    message: str = "Failed to publish task to the message queue"

    def __post_init__(self) -> None:
        self.context = {"task_id": str(self.task_id)}


@dataclass
class TaskConsumeError(MessagingError):
    """
    Вызывается, когда сообщение о задаче не может быть обработано.
    """

    raw_message: Any | None = None
    message: str = "Failed to consume task message from the queue"

    def __post_init__(self) -> None:
        if self.raw_message is not None:
            self.context = {"raw_message": str(self.raw_message)}


