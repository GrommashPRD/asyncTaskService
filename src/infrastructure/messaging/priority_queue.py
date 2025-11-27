from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import asdict
from typing import Final

import aio_pika
from aio_pika import DeliveryMode
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from aio_pika.exceptions import DeliveryError

from src.entity.tasks import Task, TaskPriority
from src.exceptions import TaskPublishError
from src.logger import logger
from src.settings import settings

PRIORITY_MAPPING: Final[dict[TaskPriority, int]] = {
    TaskPriority.LOW: 1,
    TaskPriority.MEDIUM: 5,
    TaskPriority.HIGH: 10,
}


class PriorityTaskQueue:

    def __init__(self) -> None:
        self._url = self._get_rabbitmq_url()
        self._queue_name = settings.TASK_QUEUE_NAME
        self._max_priority = settings.TASK_QUEUE_MAX_PRIORITY
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._queue_declared = False
        self._setup_lock = asyncio.Lock()

    async def publish(self, task: Task) -> None:
        message_body = json.dumps(asdict(task), default=str).encode()
        priority = PRIORITY_MAPPING.get(task.priority, 1)
        channel = await self._ensure_channel()
        await self._ensure_queue(channel)
        try:
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    priority=min(priority, self._max_priority),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    headers={"task_id": str(task.id)},
                ),
                routing_key=self._queue_name,
            )
        except (DeliveryError, aio_pika.AMQPError) as exc:
            logger.exception("Failed to publish task %s to RabbitMQ", task.id)
            await self._reset_connection()
            raise TaskPublishError(
                f"Failed to publish task {task.id} to RabbitMQ"
            ) from exc

    async def _ensure_channel(self) -> AbstractChannel:
        if self._channel and not self._channel.is_closed:
            return self._channel

        async with self._setup_lock:
            if self._connection is None or self._connection.is_closed:
                try:
                    self._connection = await aio_pika.connect_robust(self._url)
                except aio_pika.AMQPError as exc:
                    logger.error("Failed to connect to RabbitMQ: %s", exc)
                    raise TaskPublishError("Failed to connect to RabbitMQ") from exc

            if self._channel is None or self._channel.is_closed:
                self._channel = await self._connection.channel(publisher_confirms=True)
                self._queue_declared = False

            return self._channel

    async def _ensure_queue(self, channel: AbstractChannel) -> None:
        if self._queue_declared:
            return

        async with self._setup_lock:
            if self._queue_declared:
                return
            await channel.declare_queue(
                self._queue_name,
                durable=True,
                arguments={"x-max-priority": self._max_priority},
            )
            self._queue_declared = True

    async def _reset_connection(self) -> None:
        async with self._setup_lock:
            if self._channel is not None:
                with contextlib.suppress(Exception):
                    await self._channel.close()
            if self._connection is not None:
                with contextlib.suppress(Exception):
                    await self._connection.close()
            self._channel = None
            self._connection = None
            self._queue_declared = False

    @staticmethod
    def _get_rabbitmq_url() -> str:
        return (
            f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASS}"
            f"@{settings.RABBIT_HOST}:{settings.RABBIT_PORT}{settings.RABBIT_VHOST}"
        )