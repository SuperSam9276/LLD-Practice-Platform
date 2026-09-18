from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.db.models import Base

DEFAULT_DB_URL = "sqlite:///./lld_platform.db"


def make_engine(db_url: str = DEFAULT_DB_URL):
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, connect_args=connect_args)


def make_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine) -> None:
    """Creates tables if they don't exist. Fine for a 2-day MVP; a real
    project would use Alembic migrations instead of create_all."""
    Base.metadata.create_all(engine)


def get_session(session_factory: sessionmaker) -> Session:
    return session_factory()
