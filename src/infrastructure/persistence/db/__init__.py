import contextlib
import logging
import typing

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class Database:
    def __init__(self, db_url: str) -> None:
        self.engine = create_async_engine(db_url, echo=True)
        self.session_factory: sessionmaker[AsyncSession] = sessionmaker(  # type: ignore
            bind=typing.cast(Engine, self.engine),
            autoflush=False,
            class_=AsyncSession,
        )

    async def create_database(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @contextlib.asynccontextmanager
    async def connection(self) -> typing.AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session