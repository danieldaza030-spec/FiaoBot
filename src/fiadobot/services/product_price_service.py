"""Service for updating product prices deterministically."""

from __future__ import annotations

from decimal import Decimal

from fiadobot.models.product import Product
from fiadobot.repositories.product_repository import ProductRepository

from .exceptions import InvalidPriceError, ProductNotFoundError
from .money import normalize_money

# Product price updates are a focused orchestration service.
# pylint: disable=too-few-public-methods


class ProductPriceService:
    """Update a product price without affecting historical sales.

    Args:
        product_repository: Repository used to update product records.
    """

    def __init__(self, product_repository: ProductRepository) -> None:
        """Initialize the service with its repository dependency.

        Args:
            product_repository: Repository used to persist product prices.

        Returns:
            None.

        Raises:
            None.
        """

        self.product_repository = product_repository

    def update_product_price(self, product_id: int, new_price: Decimal) -> Product:
        """Update the current product price and return the updated product.

        Args:
            product_id: Identifier of the product to update.
            new_price: New current price to persist.

        Returns:
            The updated product record.

        Raises:
            InvalidPriceError: If the new price is zero or negative.
            ProductNotFoundError: If the product does not exist.
        """

        if new_price <= 0:
            raise InvalidPriceError("Product price must be greater than zero.")

        updated_product = self.product_repository.update_price(
            product_id,
            normalize_money(new_price),
        )
        if updated_product is None:
            raise ProductNotFoundError(f"Product {product_id} was not found.")

        return updated_product
