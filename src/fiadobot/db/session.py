"""Database engine and session factory helpers."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fiadobot.config import load_config


def build_database_url(database_url: str | None = None) -> str:
    """Return the database URL to use for database connections."""

    if database_url is not None:
        return database_url

    return load_config().database_url


def create_engine_from_config(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the configured database URL."""

    return create_engine(build_database_url(database_url), pool_pre_ping=True)


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory bound to the configured engine."""

    engine = create_engine_from_config(database_url)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
