import contextlib
import dataclasses
from collections.abc import AsyncGenerator

from src.exceptions import AppError, UnitOfWorkError
from src.infrastructure.persistence.db import Database
from src.infrastructure.persistence.repositories.outbox import OutboxRepository
from src.infrastructure.persistence.repositories.tasks import TaskRepository


@dataclasses.dataclass
class Repository:
    """
    repo доступные для UOW
    """

    tasks: TaskRepository
    outbox: OutboxRepository


class UnitOfWork:
    """
    Обработка жизненного цикла для commit/rollback логики.
    """

    def __init__(self, db: Database) -> None:
        self.db: Database = db

    @contextlib.asynccontextmanager
    async def init(self) -> AsyncGenerator[Repository, None]:
        async with self.db.connection() as conn:
            try:
                yield Repository(
                    tasks=TaskRepository(conn, auto_commit=False),
                    outbox=OutboxRepository(conn, auto_commit=False),
                )
            except AppError:
                await conn.rollback()
                raise
            except Exception as exc:
                await conn.rollback()
                raise UnitOfWorkError("UnitOfWork transaction failed") from exc
            else:
                await conn.commit()
