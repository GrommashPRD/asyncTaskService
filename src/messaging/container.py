"""
Контейнер для очереди
"""

from dependency_injector import containers, providers

from src.messaging.priority_queue import PriorityTaskQueue


class MessagingContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    priority_task_queue = providers.Factory(PriorityTaskQueue)

