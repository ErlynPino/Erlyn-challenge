from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

_pool_kwargs = (
    {}
    if _is_sqlite
    else {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}
)

engine = create_engine(settings.database_url, echo=False, **_pool_kwargs)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session per request."""
    with Session(engine) as session:
        yield session
