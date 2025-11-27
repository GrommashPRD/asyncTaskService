from __future__ import annotations

import asyncio
from uuid import UUID

from src.entity.outbox import OutboxEvent
from src.exceptions import TaskPublishError
from src.infrastructure.persistence.db import Database
from src.infrastructure.persistence.repositories.outbox import OutboxRepository
from src.infrastructure.persistence.repositories.tasks import TaskRepository
from src.logger import logger
from src.messaging.priority_queue import PriorityTaskQueue


class OutboxDispatcher:
    """
    Постоянно публикует ожидающие отправки события в RabbitMQ.
    """

    def __init__(
        self,
        db: Database,
        publisher: PriorityTaskQueue,
        *,
        batch_size: int = 50,
        max_retries: int = 5,
        idle_sleep: float = 2.0,
    ) -> None:
        """
        Зависимости и конфигурация.
        """
        self._db = db
        self._publisher = publisher
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._idle_sleep = idle_sleep

    async def run_forever(self) -> None:
        """
        Цикл отправки сообщений
        """
        while True:
            processed_any = await self.dispatch_pending()
            if not processed_any:
                await asyncio.sleep(self._idle_sleep)

    async def dispatch_pending(self) -> bool:
        """
        Обрабатывает и сообщает что было отправлено.
        :return:
        """
        async with self._db.connection() as session:
            outbox_repo = OutboxRepository(session)
            task_repo = TaskRepository(session)

            events = await outbox_repo.fetch_pending(
                self._batch_size,
                max_retries=self._max_retries,
            )
            if not events:
                return False

            for event in events:
                await self._process_event(event, outbox_repo, task_repo)
            return True

    async def _process_event(
        self,
        event: OutboxEvent,
        outbox_repo: OutboxRepository,
        task_repo: TaskRepository,
    ) -> None:
        """
        Отправка событий в зависимости от типа
        """
        if event.event_type == "task.created":
            await self._handle_task_created(event, outbox_repo, task_repo)
        else:
            logger.warning("Unknown outbox event %s", event.event_type)
            await outbox_repo.mark_sent(event.id)

    async def _handle_task_created(
        self,
        event: OutboxEvent,
        outbox_repo: OutboxRepository,
        task_repo: TaskRepository,
    ) -> None:
        """
        Публикует задачу в очередь
        """
        payload = event.payload
        task_id_raw = payload.get("task_id")
        if task_id_raw is None:
            logger.error("Outbox event %s missing task_id", event.id)
            await outbox_repo.mark_failed(event.id, "missing task_id")
            return

        task_id = UUID(task_id_raw)
        task = await task_repo.get_task(task_id)
        if task is None:
            logger.warning("Task %s not found, marking outbox event sent", task_id)
            await outbox_repo.mark_sent(event.id)
            return

        try:
            await self._publisher.publish(task)
            await outbox_repo.mark_sent(event.id)
        except TaskPublishError as exc:
            logger.warning(
                "Failed to publish task %s from outbox event %s: %s",
                task_id,
                event.id,
                exc,
            )
            await outbox_repo.mark_failed(event.id, str(exc))


async def main(loop_sleep: float = 2.0) -> None:
    """
    Запуск диспетчера как отдельный автомоный процесс,
    при необходимости можно поменять реализацию.
    """
    from src.container import Container
    from src.settings import settings

    container = Container()
    container.config.from_pydantic(settings)

    dispatcher = OutboxDispatcher(
        db=container.infrastructure.db(),
        publisher=container.messaging.priority_task_queue(),
        idle_sleep=loop_sleep,
    )
    await dispatcher.run_forever()


if __name__ == "__main__":
    asyncio.run(main())

