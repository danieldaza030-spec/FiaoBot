"""Product repository with pricing and catalog access operations."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from fiadobot.models.product import Product

from .base_repository import BaseRepository


class ProductRepository(BaseRepository):
    """Repository for product catalog operations."""

    def create_product(
        self,
        name: str,
        current_price: Decimal,
        active: bool = True,
    ) -> Product:
        """Create a new product and persist it to the database."""

        product = Product(name=name, current_price=current_price, active=active)
        self.session.add(product)
        self._commit()
        self.session.refresh(product)
        return product

    def get_by_id(self, product_id: int) -> Product | None:
        """Return a product by primary key, if it exists."""

        return self.session.get(Product, product_id)

    def get_by_name(self, name: str) -> Product | None:
        """Return a product matching the exact stored name."""

        statement = select(Product).where(Product.name == name)
        return self.session.scalar(statement)

    def list_all(self) -> list[Product]:
        """Return all products ordered by name."""

        statement = select(Product).order_by(Product.name.asc())
        return list(self.session.scalars(statement).all())

    def list_active(self) -> list[Product]:
        """Return only active products ordered by name."""

        statement = select(Product).where(
            Product.active.is_(True)
        ).order_by(Product.name.asc())
        return list(self.session.scalars(statement).all())

    def update_price(self, product_id: int, new_price: Decimal) -> Product | None:
        """Update the current price of a product without keeping history."""

        product = self.get_by_id(product_id)
        if product is None:
            return None

        product.current_price = new_price
        self._commit()
        self.session.refresh(product)
        return product

    def set_active(self, product_id: int, active: bool) -> Product | None:
        """Enable or disable a product in the catalog."""

        product = self.get_by_id(product_id)
        if product is None:
            return None

        product.active = active
        self._commit()
        self.session.refresh(product)
        return product
