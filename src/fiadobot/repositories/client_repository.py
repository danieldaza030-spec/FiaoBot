"""Customer repository with exact and approximate search capabilities."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import desc, func, select

from fiadobot.models.client import Client

from .base_repository import BaseRepository


@dataclass(frozen=True, slots=True)
class ClientMatch:
    """Approximate client match returned by fuzzy search.

    Args:
        client: Matched client record.
        similarity: Similarity score returned by PostgreSQL.
    """

    client: Client
    similarity: float


class ClientRepository(BaseRepository):
    """Repository for customer data access operations.

    The repository centralizes exact lookup, listing and fuzzy search logic for
    customer records.
    """

    def create_client(
        self,
        name: str,
        alias: str | None = None,
        phone_number: str | None = None,
    ) -> Client:
        """Create a new customer and persist it to the database.

        Args:
            name: Unique customer name to store.
            alias: Optional short name or nickname.
            phone_number: Optional phone number for the customer.

        Returns:
            The persisted customer record.

        Raises:
            SQLAlchemyError: If the insert or commit fails.
        """

        client = Client(name=name, alias=alias, phone_number=phone_number)
        self.session.add(client)
        self._commit()
        self.session.refresh(client)
        return client

    def get_by_id(self, client_id: int) -> Client | None:
        """Return a customer by primary key, if it exists.

        Args:
            client_id: Primary key of the customer to load.

        Returns:
            The matching customer or ``None`` when no record exists.
        """

        return self.session.get(Client, client_id)

    def get_by_name(self, name: str) -> Client | None:
        """Return a customer matching the exact stored name.

        Args:
            name: Exact customer name to search for.

        Returns:
            The matching customer or ``None`` when no record exists.
        """

        statement = select(Client).where(Client.name == name)
        return self.session.scalar(statement)

    def list_all(self) -> list[Client]:
        """Return all customers ordered by name.

        Returns:
            All stored customers sorted alphabetically.
        """

        statement = select(Client).order_by(Client.name.asc())
        return list(self.session.scalars(statement).all())

    def search_similar(
        self,
        text: str,
        *,
        limit: int = 5,
        threshold: float = 0.3,
    ) -> list[ClientMatch]:
        """Return the closest customer matches using pg_trgm similarity.

        Args:
            text: Free-form text entered by the vendor.
            limit: Maximum number of matches to return.
            threshold: Minimum similarity score required for a match.

        Returns:
            The list of matches ordered by similarity.

        Raises:
            SQLAlchemyError: If the similarity query fails.
        """

        search_text = text.lower().strip()
        searchable_name = func.lower(Client.name)
        searchable_alias = func.lower(func.coalesce(Client.alias, ""))
        combined_text = func.lower(Client.name + " " + func.coalesce(Client.alias, ""))

        similarity = func.greatest(
            func.similarity(searchable_name, search_text),
            func.similarity(searchable_alias, search_text),
            func.similarity(combined_text, search_text),
        ).label("similarity")

        statement = (
            select(Client, similarity)
            .where(similarity >= threshold)
            .order_by(desc(similarity), Client.name.asc())
            .limit(limit)
        )

        results = self.session.execute(statement).all()
        return [ClientMatch(client=row[0], similarity=float(row[1])) for row in results]
