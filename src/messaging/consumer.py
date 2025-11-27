from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

import aio_pika

from src.container import Container
from src.entity.tasks import TaskStatus
from src.exceptions import TaskConsumeError
from src.logger import logger
from src.settings import settings
from src.usecase.tasks import TaskUseCase


@dataclass
class TaskMessage:
    """DTO для сообщения задачи из очереди."""

    raw: dict[str, Any]


class TaskConsumer:

    def __init__(self, *, usecase: Optional[TaskUseCase] = None) -> None:
        self._url: str = self._get_rabbitmq_url()
        self._queue_name: str = settings.TASK_QUEUE_NAME
        self._max_priority: int = settings.TASK_QUEUE_MAX_PRIORITY
        self._usecase: TaskUseCase = usecase or self._build_usecase()

    async def start(self) -> None:
        try:
            connection: aio_pika.abc.AbstractRobustConnection = await aio_pika.connect_robust(
                self._url
            )
        except aio_pika.AMQPError as exc:
            logger.error("Failed to connect to RabbitMQ as consumer: %s", exc)
            raise TaskConsumeError("Failed to connect to RabbitMQ") from exc

        logger.info("Connected to RabbitMQ as consumer")

        async with connection:
            try:
                channel: aio_pika.abc.AbstractChannel = await connection.channel()
                await channel.declare_queue(
                    self._queue_name,
                    durable=True,
                    arguments={"x-max-priority": self._max_priority},
                )

                queue: aio_pika.abc.AbstractQueue = await channel.declare_queue(
                    self._queue_name, durable=True
                )

                await queue.consume(self._on_message, no_ack=False)
                logger.info("Started consuming from queue %s", self._queue_name)
                await asyncio.Future()
            except aio_pika.AMQPError as exc:
                logger.error("RabbitMQ error in consumer: %s", exc)
                raise TaskConsumeError("RabbitMQ consumer error") from exc

    async def _on_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                payload: dict[str, Any] = json.loads(message.body.decode())
                task_msg = TaskMessage(raw=payload)
                await self._process_task(task_msg)
                logger.info("Processed task message: %s", payload.get("id"))
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning("Invalid task message received: %s", exc)
                raise TaskConsumeError("Invalid task message payload") from exc

    async def _process_task(self, task: TaskMessage) -> None:
        task_id = self._extract_task_id(task)
        try:
            await self._usecase.set_status(task_id, TaskStatus.IN_PROGRESS)
            # Здесь могла быть бизнес-логика обработки задачи.
            await self._usecase.set_status(
                task_id,
                TaskStatus.COMPLETED,
                result="Processed by TaskConsumer",
            )
        except Exception as exc:
            logger.exception("Failed to process task %s: %s", task_id, exc)
            await self._usecase.set_status(
                task_id,
                TaskStatus.FAILED,
                error=str(exc),
            )
            raise TaskConsumeError("Task processing failed") from exc

    @staticmethod
    def _extract_task_id(task: TaskMessage) -> UUID:
        task_id_raw = task.raw.get("id") or task.raw.get("task_id")
        if task_id_raw is None:
            raise TaskConsumeError("Task message missing 'id' field")
        return UUID(task_id_raw)

    @staticmethod
    def _get_rabbitmq_url() -> str:
        return (
            f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASS}"
            f"@{settings.RABBIT_HOST}:{settings.RABBIT_PORT}{settings.RABBIT_VHOST}"
        )

    @staticmethod
    def _build_usecase() -> TaskUseCase:
        container = Container()
        container.config.from_pydantic(settings)
        return container.usecase.task_usecase()



