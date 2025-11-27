"""
Корневой контейнер, который подключает все подконтейнеры.
"""

from dependency_injector import containers, providers

from src.infrastructure.container import InfrastructureContainer
from src.usecase.container import UsecaseContainer


class Container(containers.DeclarativeContainer):

    config = providers.Configuration()
    wiring_config = containers.WiringConfiguration(
        modules=["src.api.handlers.tasks.task_handler"],
    )

    infrastructure = providers.Container(
        InfrastructureContainer,
        config=config,
    )

    usecase = providers.Container(
        UsecaseContainer,
        task_repository=infrastructure.task_repository,
        uow=infrastructure.uow,
    )
