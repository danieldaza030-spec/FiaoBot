"""Business service for historical analytics reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from fiadobot.repositories.analytics_repository import (
    AnalyticsRepository,
    FrequentCustomerRow,
    ProductSalesRow,
)

# Analytics is a focused read-only service.
# pylint: disable=too-few-public-methods


@dataclass(frozen=True, slots=True)
class AnalyticsDateRange:
    """Inclusive date range used in analytics reports.

    Args:
        start_date: Inclusive lower bound of the report.
        end_date: Inclusive upper bound of the report.
    """

    start_date: datetime
    end_date: datetime


@dataclass(frozen=True, slots=True)
class SalesByProductReport:
    """Structured result for a sales-by-product analytics query.

    Args:
        date_range: Inclusive range covered by the report.
        rows: Aggregated product rows sorted by relevance.
    """

    date_range: AnalyticsDateRange
    rows: list[ProductSalesRow] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FrequentCustomersReport:
    """Structured result for a frequent-customers analytics query.

    Args:
        date_range: Inclusive range covered by the report.
        rows: Aggregated customer rows sorted by relevance.
    """

    date_range: AnalyticsDateRange
    rows: list[FrequentCustomerRow] = field(default_factory=list)


class AnalyticsService:
    """Generate deterministic historical analytics reports.

    Args:
        analytics_repository: Repository used to fetch aggregate historical data.
    """

    def __init__(self, analytics_repository: AnalyticsRepository) -> None:
        """Initialize the service with its analytics repository.

        Args:
            analytics_repository: Repository used to fetch aggregate data.

        Returns:
            None.

        Raises:
            None.
        """

        self.analytics_repository = analytics_repository

    def generate_sales_by_product_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> SalesByProductReport:
        """Return a report with product sales aggregated by date range.

        Args:
            start_date: Inclusive lower bound for the report.
            end_date: Inclusive upper bound for the report.

        Returns:
            The aggregated product sales report.

        Raises:
            ValueError: If the date range is invalid.
        """

        self._validate_date_range(start_date, end_date)
        rows = self.analytics_repository.list_sales_by_product(start_date, end_date)
        return SalesByProductReport(
            date_range=AnalyticsDateRange(start_date=start_date, end_date=end_date),
            rows=rows,
        )

    def generate_frequent_customers_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> FrequentCustomersReport:
        """Return a report with the most frequent customers by date range.

        Args:
            start_date: Inclusive lower bound for the report.
            end_date: Inclusive upper bound for the report.

        Returns:
            The aggregated customer frequency report.

        Raises:
            ValueError: If the date range is invalid.
        """

        self._validate_date_range(start_date, end_date)
        rows = self.analytics_repository.list_frequent_customers(start_date, end_date)
        return FrequentCustomersReport(
            date_range=AnalyticsDateRange(start_date=start_date, end_date=end_date),
            rows=rows,
        )

    @staticmethod
    def _validate_date_range(start_date: datetime, end_date: datetime) -> None:
        """Ensure the provided date range is valid.

        Args:
            start_date: Inclusive lower bound for the range.
            end_date: Inclusive upper bound for the range.

        Returns:
            None.

        Raises:
            ValueError: If the end date precedes the start date.
        """

        if end_date < start_date:
            raise ValueError("The analytics date range is invalid.")
