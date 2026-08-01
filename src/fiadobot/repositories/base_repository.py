"""Shared repository helpers built on top of SQLAlchemy sessions."""

from __future__ import annotations

# Repository base classes expose behavior through subclasses, not methods.
# pylint: disable=too-few-public-methods

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class BaseRepository:
    """Base class for repositories that operate on a SQLAlchemy session.

    Args:
        session: Active SQLAlchemy session used by repository methods.
    """

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session used for persistence.

        Returns:
            None.

        Raises:
            None.
        """

        self.session = session

    def _commit(self) -> None:
        """Commit the current transaction and roll back on database errors.

        Returns:
            None.

        Raises:
            SQLAlchemyError: If the commit fails and the transaction is rolled back.
        """

        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
