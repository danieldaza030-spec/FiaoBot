"""Customer repository with exact and approximate search capabilities."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import desc, func, select

from fiadobot.models.client import Client

from .base_repository import BaseRepository


@dataclass(frozen=True, slots=True)
class ClientMatch:
    """Approximate client match returned by fuzzy search."""

    client: Client
    similarity: float


class ClientRepository(BaseRepository):
    """Repository for customer data access operations."""

    def create_client(
        self,
        name: str,
        alias: str | None = None,
        phone_number: str | None = None,
    ) -> Client:
        """Create a new customer and persist it to the database."""

        client = Client(name=name, alias=alias, phone_number=phone_number)
        self.session.add(client)
        self._commit()
        self.session.refresh(client)
        return client

    def get_by_id(self, client_id: int) -> Client | None:
        """Return a customer by primary key, if it exists."""

        return self.session.get(Client, client_id)

    def get_by_name(self, name: str) -> Client | None:
        """Return a customer matching the exact stored name."""

        statement = select(Client).where(Client.name == name)
        return self.session.scalar(statement)

    def list_all(self) -> list[Client]:
        """Return all customers ordered by name."""

        statement = select(Client).order_by(Client.name.asc())
        return list(self.session.scalars(statement).all())

    def search_similar(
        self,
        text: str,
        *,
        limit: int = 5,
        threshold: float = 0.3,
    ) -> list[ClientMatch]:
        """Return the closest customer matches using pg_trgm similarity."""

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
