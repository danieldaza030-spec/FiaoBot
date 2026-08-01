"""SQLAlchemy declarative base and metadata conventions."""

from __future__ import annotations

# Declarative ORM bases naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models in the application.

    This base centralizes naming conventions so Alembic and SQLAlchemy
    generate consistent constraint and index names across the schema.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
