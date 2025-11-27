"""
Контейнер для usecase слоя
"""

from dependency_injector import containers, providers

from src.infrastructure.persistence.repositories.tasks import TaskRepository
from src.infrastructure.persistence.uow import UnitOfWork
from src.usecase.tasks import TaskUseCase


class UsecaseContainer(containers.DeclarativeContainer):

    task_repository: providers.Dependency[TaskRepository] = providers.Dependency()
    uow: providers.Dependency[UnitOfWork] = providers.Dependency()

    task_usecase = providers.Factory(
        TaskUseCase,
        repository=task_repository,
        uow=uow,
    )
