from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):   # wspólna baza dla modeli ORM
    pass


def get_engine(dsn: str):
    return create_async_engine(dsn, echo=False, future=True)


def get_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)
