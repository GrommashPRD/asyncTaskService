import fastapi

from src.api.handlers.tasks.task_handler import router
from src.container import Container
from src.settings import settings


def create_container() -> Container:
    container = Container()
    container.config.from_pydantic(settings)
    return container


def create_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.container = create_container()
    app.include_router(router)
    return app


app = create_app()