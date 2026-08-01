"""Product repository with pricing and catalog access operations."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from fiadobot.models.product import Product

from .base_repository import BaseRepository


class ProductRepository(BaseRepository):
    """Repository for product catalog operations.

    The repository keeps catalog reads and updates isolated from services.
    """

    def create_product(
        self,
        name: str,
        current_price: Decimal,
        active: bool = True,
    ) -> Product:
        """Create a new product and persist it to the database.

        Args:
            name: Unique product name to store.
            current_price: Current price for the new product.
            active: Whether the product should start enabled.

        Returns:
            The persisted product record.

        Raises:
            SQLAlchemyError: If the insert or commit fails.
        """

        product = Product(name=name, current_price=current_price, active=active)
        self.session.add(product)
        self._commit()
        self.session.refresh(product)
        return product

    def get_by_id(self, product_id: int) -> Product | None:
        """Return a product by primary key, if it exists.

        Args:
            product_id: Primary key of the product to load.

        Returns:
            The matching product or ``None`` when no record exists.
        """

        return self.session.get(Product, product_id)

    def get_by_name(self, name: str) -> Product | None:
        """Return a product matching the exact stored name.

        Args:
            name: Exact product name to search for.

        Returns:
            The matching product or ``None`` when no record exists.
        """

        statement = select(Product).where(Product.name == name)
        return self.session.scalar(statement)

    def list_all(self) -> list[Product]:
        """Return all products ordered by name.

        Returns:
            All stored products sorted alphabetically.
        """

        statement = select(Product).order_by(Product.name.asc())
        return list(self.session.scalars(statement).all())

    def list_active(self) -> list[Product]:
        """Return only active products ordered by name.

        Returns:
            Active products sorted alphabetically.
        """

        statement = select(Product).where(
            Product.active.is_(True)
        ).order_by(Product.name.asc())
        return list(self.session.scalars(statement).all())

    def update_price(self, product_id: int, new_price: Decimal) -> Product | None:
        """Update the current price of a product without keeping history.

        Args:
            product_id: Primary key of the product to update.
            new_price: New current price to persist.

        Returns:
            The updated product or ``None`` when no record exists.

        Raises:
            SQLAlchemyError: If the update or commit fails.
        """

        product = self.get_by_id(product_id)
        if product is None:
            return None

        product.current_price = new_price
        self._commit()
        self.session.refresh(product)
        return product

    def set_active(self, product_id: int, active: bool) -> Product | None:
        """Enable or disable a product in the catalog.

        Args:
            product_id: Primary key of the product to update.
            active: ``True`` to enable the product, ``False`` to disable it.

        Returns:
            The updated product or ``None`` when no record exists.

        Raises:
            SQLAlchemyError: If the update or commit fails.
        """

        product = self.get_by_id(product_id)
        if product is None:
            return None

        product.active = active
        self._commit()
        self.session.refresh(product)
        return product
