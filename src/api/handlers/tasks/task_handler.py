from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.container import Container
from src.entity.tasks import CreateTask, Pagination, TaskFilter
from src.exceptions import (AppError, MessagingError, RepositoryError,
                            TaskCancellationError, TaskNotFoundError)
from src.logger import logger
from src.api.schemas.requests_schemas.tasks.schemas import (TaskCreateRequest,
                                                            TaskListFilterQuery)
from src.api.schemas.response_schemas.schemas import (TaskListResponse,
                                                      TaskResponse,
                                                      TaskStatusResponse)
from src.usecase.tasks import TaskUseCase

router = APIRouter(
    prefix="/api/v1",
    tags=["Tasks"],
)


def _map_app_error_to_http(exc: AppError) -> tuple[int, str]:
    if isinstance(exc, TaskNotFoundError):
        return status.HTTP_404_NOT_FOUND, "Task not found"
    if isinstance(exc, TaskCancellationError):
        return status.HTTP_400_BAD_REQUEST, "Task cannot be cancelled"
    if isinstance(exc, MessagingError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR, "Messaging error"
    if isinstance(exc, RepositoryError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR, "Database error"
    return status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error"


def _raise_http_from_app_error(operation: str, exc: AppError) -> None:
    status_code, detail = _map_app_error_to_http(exc)

    log_extra = {
        "error_type": type(exc).__name__,
        **getattr(exc, "context", {}),
    }

    message = "Application error in %s: %s"

    if 400 <= status_code < 500:
        logger.warning(message, operation, str(exc), extra=log_extra)
    else:
        # 5xx и все остальные - ошибки сервера
        logger.error(message, operation, str(exc), extra=log_extra)

    raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post(
    "/tasks/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def create_task(
    body: TaskCreateRequest,
    uc: TaskUseCase = Depends(Provide[Container.usecase.task_usecase]),
) -> TaskResponse:
    """
    Endpoint создания задачи
    :param body: Тело запроса вместе с приоритетом.
    :param uc: usecase с бизнес-логикой
    :return: TaskResponse
    """

    payload = CreateTask(
        name=body.name,
        description=body.description,
        priority=body.priority,
    )
    try:
        task = await uc.create_task(payload)
        return TaskResponse.from_entity(task)
    except AppError as exc:
        _raise_http_from_app_error("create_task", exc)


@router.get(
    "/tasks/",
    response_model=TaskListResponse,
)
@inject
async def list_tasks(
    uc: TaskUseCase = Depends(Provide[Container.usecase.task_usecase]),
    filters: TaskListFilterQuery = Depends(TaskListFilterQuery.as_query),
) -> TaskListResponse:
    """
    Список задач с фильтрами и пагинацией.
    :param uc: Usecase с бизнес-логикой.
    :param filters: Параметры фильтрации и пагинации из query.
    :return: TaskListResponse со списком и метаданными.
    """

    task_filters = TaskFilter(
        status=filters.status,
        priority=filters.priority,
        search=filters.search.strip() if filters.search else None,
    )
    pagination = Pagination(page=filters.page, page_size=filters.page_size)
    try:
        tasks, total = await uc.list_tasks(task_filters, pagination)
    except AppError as exc:
        _raise_http_from_app_error("list_tasks", exc)

    return TaskListResponse(
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        items=[TaskResponse.from_entity(task) for task in tasks],
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
@inject
async def get_task(
    task_id: UUID,
    uc: TaskUseCase = Depends(Provide[Container.usecase.task_usecase]),
) -> TaskResponse:
    """
    Получить задачу по идентификатору.
    :param task_id: UUID задачи.
    :param uc: Usecase с бизнес-логикой.
    :return: TaskResponse по найденной задаче.
    """

    try:
        task = await uc.get_task(task_id)
    except AppError as exc:
        _raise_http_from_app_error("get_task", exc)

    return TaskResponse.from_entity(task)


@router.delete(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
@inject
async def cancel_task(
    task_id: UUID,
    uc: TaskUseCase = Depends(Provide[Container.usecase.task_usecase]),
) -> TaskResponse:
    """
    Отменить задачу, если это допустимо.
    :param task_id: UUID задачи.
    :param uc: Usecase с бизнес-логикой.
    :return: TaskResponse с обновлённым состоянием задачи.
    """

    try:
        cancelled = await uc.cancel_task(task_id)
    except AppError as exc:
        _raise_http_from_app_error("cancel_task", exc)

    return TaskResponse.from_entity(cancelled)


@router.get(
    "/tasks/{task_id}/status",
    response_model=TaskStatusResponse,
)
@inject
async def get_task_status(
    task_id: UUID,
    uc: TaskUseCase = Depends(Provide[Container.usecase.task_usecase]),
) -> TaskStatusResponse:
    """
    Получить только статус задачи.
    :param task_id: UUID задачи.
    :param uc: Usecase с бизнес-логикой.
    :return: TaskStatusResponse с текущим статусом.
    """
    try:
        task = await uc.get_task(task_id)
    except AppError as exc:
        _raise_http_from_app_error("get_task_status", exc)

    return TaskStatusResponse(task_id=task.id, status=task.status)