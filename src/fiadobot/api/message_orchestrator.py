"""Orchestrate the full message flow: pending state -> LLM -> service -> reply.

This module is intentionally framework-agnostic: it only depends on the
service layer, the prompt builder and the ``LLMProvider`` abstraction, never
on FastAPI or Telegram-specific types. Business decisions and calculations
always happen inside the service layer; this class only routes data between
the LLM's structured intent and the deterministic backend services.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from unicodedata import normalize as normalize_unicode

from fiadobot.llm.provider import LLMProvider
from fiadobot.llm.exceptions import LLMProviderError
from fiadobot.prompting.prompt_builder import PromptBuilder
from fiadobot.prompting.types import PromptContext
from fiadobot.services import (
    FrequentCustomersReport,
    CUSTOMER_DISAMBIGUATION_ACTION,
    CustomerNotFoundError,
    EmptySaleError,
    InvalidCancellationReasonError,
    InvalidPaymentAmountError,
    InvalidPriceError,
    InvalidSaleItemError,
    NoPendingStateError,
    PendingOption,
    PendingReplyNotResolvedError,
    ProductNotFoundError,
    SaleItemInput,
    SalesByProductReport,
    ServiceError,
    TransactionAlreadyCancelledError,
    TransactionNotFoundError,
)

from .dependencies import ServiceContext

# The orchestrator exposes a single entry point on purpose; the remaining
# methods are private dispatch helpers used internally.
# pylint: disable=too-few-public-methods

_FALLBACK_MESSAGE = (
    "No entendí tu mensaje. Contame si querés registrar una venta, un pago, "
    "consultar un saldo, un resumen de cobro, anular una transacción o "
    "actualizar un precio."
)
_INVALID_REPLY_MESSAGE = (
    'No entendí tu respuesta. Contestá con el número de la opción, por '
    'ejemplo "2".'
)
_INVALID_ARGUMENTS_MESSAGE = (
    "No entendí bien los datos del pedido. ¿Podés escribirlo de nuevo?"
)
_PROVIDER_ERROR_MESSAGE = (
    "No pude procesar tu mensaje en este momento. Probá de nuevo en unos "
    "minutos."
)

_ERROR_MESSAGES: dict[type, str] = {
    CustomerNotFoundError: "No encontré ese cliente.",
    ProductNotFoundError: "No encontré ese producto.",
    TransactionNotFoundError: "No encontré esa transacción.",
    EmptySaleError: "La venta debe tener al menos un producto.",
    InvalidSaleItemError: "La cantidad debe ser mayor que cero.",
    InvalidPaymentAmountError: "El monto del pago debe ser mayor que cero.",
    InvalidCancellationReasonError: "Necesito un motivo para anular la transacción.",
    InvalidPriceError: "El precio debe ser mayor que cero.",
    TransactionAlreadyCancelledError: "Esa transacción ya estaba anulada.",
}


@dataclass(frozen=True, slots=True)
class _CustomerLookupResult:
    """Outcome of resolving free-form customer text to a customer id.

    Args:
        customer_id: Resolved customer id, or ``None`` when a reply is needed.
        question: Message to send back to the vendor when resolution is not
            immediately possible (no match or several ambiguous matches).
    """

    customer_id: int | None
    question: str | None


class MessageOrchestrator:
    """Coordinate one inbound message from intent extraction to final reply.

    Args:
        service_context: Bundle of repositories and services for one request.
        prompt_builder: Builder used to assemble the provider-agnostic prompt.
        llm_provider: Provider used to translate free text into a tool call.
    """

    def __init__(
        self,
        service_context: ServiceContext,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
    ) -> None:
        """Initialize the orchestrator with its collaborators.

        Args:
            service_context: Bundle of repositories and services.
            prompt_builder: Builder used to assemble prompts.
            llm_provider: Provider used to interpret free text.

        Returns:
            None.

        Raises:
            None.
        """

        self.service_context = service_context
        self.prompt_builder = prompt_builder
        self.llm_provider = llm_provider

    def handle_message(self, chat_id: int, text: str) -> str | None:
        """Handle a single authorized message and return the reply text.

        Args:
            chat_id: Telegram chat identifier that sent the message.
            text: Raw message text sent by the vendor.

        Returns:
            The reply text to send back, or ``None`` when there is nothing to
            say (e.g. an empty message).
        """

        stripped_text = text.strip()
        if not stripped_text:
            return None

        conversation_state_service = self.service_context.conversation_state_service
        if conversation_state_service.has_pending_state(chat_id):
            return self._handle_pending_reply(chat_id, stripped_text)

        return self._handle_new_message(chat_id, stripped_text)

    def _handle_pending_reply(self, chat_id: int, text: str) -> str:
        """Resolve a reply to a previously stored disambiguation question.

        Args:
            chat_id: Telegram chat identifier replying to a pending question.
            text: Raw reply text sent by the vendor.

        Returns:
            The reply text to send back to the vendor.
        """

        conversation_state_service = self.service_context.conversation_state_service
        try:
            resolution = conversation_state_service.resolve_pending_reply(
                chat_id, text
            )
        except PendingReplyNotResolvedError:
            return _INVALID_REPLY_MESSAGE
        except NoPendingStateError:
            return self._handle_new_message(chat_id, text)

        if resolution.pending_action != CUSTOMER_DISAMBIGUATION_ACTION:
            return _FALLBACK_MESSAGE

        tool_name = resolution.pending_arguments.get("tool_name")
        arguments = dict(resolution.pending_arguments.get("arguments", {}))
        return self._execute_tool(
            chat_id,
            tool_name,
            arguments,
            resolved_customer_id=resolution.selected_option.option_id,
        )

    def _handle_new_message(self, chat_id: int, text: str) -> str:
        """Interpret a fresh message through the LLM and execute the result.

        Args:
            chat_id: Telegram chat identifier that sent the message.
            text: Raw message text sent by the vendor.

        Returns:
            The reply text to send back to the vendor.
        """

        prompt_bundle = self.prompt_builder.build(PromptContext(user_message=text))
        try:
            tool_call = self.llm_provider.interpret(prompt_bundle)
        except LLMProviderError:
            return _PROVIDER_ERROR_MESSAGE

        if tool_call.tool_name is None:
            return tool_call.assistant_message or _FALLBACK_MESSAGE

        arguments = dict(tool_call.arguments)
        return self._execute_tool(chat_id, tool_call.tool_name, arguments)

    def _resolve_customer(
        self, chat_id: int, tool_name: str, arguments: dict[str, Any]
    ) -> _CustomerLookupResult:
        """Resolve free-form customer text, asking the vendor if ambiguous.

        Args:
            chat_id: Telegram chat identifier that owns the flow.
            tool_name: Name of the tool waiting for a resolved customer id.
            arguments: Original tool arguments, including ``cliente_texto``.

        Returns:
            The resolved customer id, or a question to send back to the
            vendor when the customer could not be resolved immediately.
        """

        customer_text = str(arguments.get("cliente_texto", "")).strip()
        if not customer_text:
            return _CustomerLookupResult(None, "¿A qué cliente te referís?")

        matches = self.service_context.client_repository.search_similar(customer_text)
        if not matches:
            return _CustomerLookupResult(
                None, f'No encontré ningún cliente parecido a "{customer_text}".'
            )

        if len(matches) == 1:
            return _CustomerLookupResult(matches[0].client.id, None)

        options = [
            PendingOption(option_id=match.client.id, display_name=match.client.name)
            for match in matches
        ]
        self.service_context.conversation_state_service.start_customer_disambiguation(
            chat_id, options, {"tool_name": tool_name, "arguments": arguments}
        )
        listed_options = "\n".join(
            f"{index}. {option.display_name}"
            for index, option in enumerate(options, start=1)
        )
        question = (
            f'Tengo varios clientes parecidos a "{customer_text}":\n'
            f"{listed_options}\n¿Cuál de ellos? Respondé con el número."
        )
        return _CustomerLookupResult(None, question)

    def _execute_tool(
        self,
        chat_id: int,
        tool_name: str | None,
        arguments: dict[str, Any],
        *,
        resolved_customer_id: int | None = None,
    ) -> str:
        """Dispatch a resolved tool call to its business service.

        Args:
            chat_id: Telegram chat identifier handling this tool call.
            tool_name: Canonical tool name selected by the LLM.
            arguments: Tool arguments, as returned by the LLM or resumed from
                a pending disambiguation flow.
            resolved_customer_id: Customer id already resolved by a previous
                disambiguation step, if any.

        Returns:
            The reply text to send back to the vendor.
        """

        try:
            if tool_name in self._CUSTOMER_TOOL_HANDLERS:
                handler = self._CUSTOMER_TOOL_HANDLERS[tool_name]
                return handler(self, chat_id, arguments, resolved_customer_id)
            if tool_name in self._SIMPLE_TOOL_HANDLERS:
                simple_handler = self._SIMPLE_TOOL_HANDLERS[tool_name]
                return simple_handler(self, arguments)
        except ServiceError as error:
            return self._format_service_error(error)
        except (TypeError, ValueError, KeyError, AttributeError):
            return _INVALID_ARGUMENTS_MESSAGE

        return _FALLBACK_MESSAGE

    def _run_registrar_venta(
        self,
        chat_id: int,
        arguments: dict[str, Any],
        resolved_customer_id: int | None,
    ) -> str:
        """Resolve the customer and products, then register a sale (RF01)."""

        customer_id = resolved_customer_id
        if customer_id is None:
            lookup = self._resolve_customer(chat_id, "registrar_venta", arguments)
            if lookup.customer_id is None:
                return lookup.question
            customer_id = lookup.customer_id

        sale_items: list[SaleItemInput] = []
        for item in arguments.get("items", []):
            product_name = str(item.get("producto", "")).strip()
            product = self.service_context.product_repository.get_by_name(
                product_name
            )
            if product is None:
                return (
                    f'No encontré el producto "{product_name}". '
                    "Verificá el nombre exacto."
                )

            sale_items.append(
                SaleItemInput(
                    product_id=product.id,
                    quantity=self._to_decimal(item.get("cantidad")),
                )
            )

        result = self.service_context.sale_service.register_sale(
            customer_id, sale_items
        )
        item_lines = "\n".join(
            f"- {item.quantity} x {item.product_name} = ${item.subtotal}"
            for item in result.items
        )
        return (
            f"Venta registrada:\n{item_lines}\n"
            f"Total: ${result.total_amount}\n"
            f"Saldo pendiente: ${result.pending_balance}"
        )

    def _run_registrar_pago(
        self,
        chat_id: int,
        arguments: dict[str, Any],
        resolved_customer_id: int | None,
    ) -> str:
        """Resolve the customer and register a payment (RF03)."""

        customer_id = resolved_customer_id
        if customer_id is None:
            lookup = self._resolve_customer(chat_id, "registrar_pago", arguments)
            if lookup.customer_id is None:
                return lookup.question
            customer_id = lookup.customer_id

        amount = self._to_decimal(arguments.get("monto"))
        result = self.service_context.payment_service.register_payment(
            customer_id, amount
        )
        return (
            f"Pago registrado: ${result.payment.amount}.\n"
            f"Saldo pendiente: ${result.pending_balance}"
        )

    def _run_consultar_saldo(
        self,
        chat_id: int,
        arguments: dict[str, Any],
        resolved_customer_id: int | None,
    ) -> str:
        """Resolve the customer and report the pending balance (RF02)."""

        customer_id = resolved_customer_id
        if customer_id is None:
            lookup = self._resolve_customer(chat_id, "consultar_saldo", arguments)
            if lookup.customer_id is None:
                return lookup.question
            customer_id = lookup.customer_id

        balance = self.service_context.balance_service.calculate_pending_balance(
            customer_id
        )
        return f"Saldo pendiente: ${balance}"

    def _run_generar_resumen_cobro(
        self,
        chat_id: int,
        arguments: dict[str, Any],
        resolved_customer_id: int | None,
    ) -> str:
        """Resolve the customer and build a collection summary (RF04)."""

        customer_id = resolved_customer_id
        if customer_id is None:
            lookup = self._resolve_customer(
                chat_id, "generar_resumen_cobro", arguments
            )
            if lookup.customer_id is None:
                return lookup.question
            customer_id = lookup.customer_id

        summary = (
            self.service_context.collection_summary_service.generate_collection_summary(
                customer_id
            )
        )
        lines = [
            f"- {transaction.date:%Y-%m-%d}: "
            + ", ".join(
                f"{item.quantity} x {item.product_name}"
                for item in transaction.items
            )
            + f" = ${transaction.total_amount}"
            for transaction in summary.transactions
        ]
        transactions_text = "\n".join(lines) if lines else "Sin transacciones activas."
        return (
            f"Resumen de {summary.customer.name}:\n{transactions_text}\n"
            f"Total ventas: ${summary.total_sales}\n"
            f"Total pagos: ${summary.total_payments}\n"
            f"Saldo pendiente: ${summary.pending_balance}"
        )

    def _run_anular_transaccion(self, arguments: dict[str, Any]) -> str:
        """Cancel a previously registered transaction (RF06)."""

        transaction_id = int(arguments["transaccion_id"])
        reason = str(arguments.get("motivo", "")).strip()
        result = (
            self.service_context.transaction_cancellation_service.cancel_transaction(
                transaction_id, reason
            )
        )
        return (
            f"Transacción #{result.transaction.id} anulada.\n"
            f"Saldo pendiente: ${result.pending_balance}"
        )

    def _run_actualizar_precio(self, arguments: dict[str, Any]) -> str:
        """Update a product's current price (RF07)."""

        product_text = str(arguments.get("producto_texto", "")).strip()
        product = self.service_context.product_repository.get_by_name(product_text)
        if product is None:
            return (
                f'No encontré el producto "{product_text}". '
                "Verificá el nombre exacto."
            )

        new_price = self._to_decimal(arguments.get("nuevo_precio"))
        price_service = self.service_context.product_price_service
        updated_product = price_service.update_product_price(product.id, new_price)
        return (
            f"Precio actualizado: {updated_product.name} ahora cuesta "
            f"${updated_product.current_price}."
        )

    def _run_consultar_analitica(self, arguments: dict[str, Any]) -> str:
        """Run a historical analytics query (RF05)."""

        try:
            report_type = self._normalize_analytics_type(str(arguments["tipo"]))
            range_data = arguments["rango_fechas"]
            if not isinstance(range_data, dict):
                raise ValueError

            start_date = self._parse_datetime(str(range_data["desde"]))
            end_date = self._parse_datetime(str(range_data["hasta"]))
        except (KeyError, TypeError, ValueError):
            return _INVALID_ARGUMENTS_MESSAGE

        analytics_service = self.service_context.analytics_service
        if report_type in self._PRODUCT_ANALYTICS_TYPES:
            report = analytics_service.generate_sales_by_product_report(
                start_date, end_date
            )
            return self._format_sales_by_product_report(report)

        if report_type in self._CUSTOMER_ANALYTICS_TYPES:
            report = analytics_service.generate_frequent_customers_report(
                start_date, end_date
            )
            return self._format_frequent_customers_report(report)

        return (
            "Tipo de analítica no soportado. Probá con ventas por producto "
            "o clientes más frecuentes."
        )

    def _format_service_error(self, error: ServiceError) -> str:
        """Translate a business exception into a short Spanish reply.

        Args:
            error: Business exception raised by the service layer.

        Returns:
            A short, user-facing Spanish message describing the failure.
        """

        return _ERROR_MESSAGES.get(
            type(error), "No pude completar la operación solicitada."
        )

    @staticmethod
    def _normalize_analytics_type(value: str) -> str:
        """Normalize the analytics type into a stable ASCII token."""

        normalized = normalize_unicode("NFKD", value).encode(
            "ascii", "ignore"
        ).decode("ascii")
        normalized = normalized.strip().lower().replace("-", "_").replace(
            " ", "_"
        )
        while "__" in normalized:
            normalized = normalized.replace("__", "_")

        return normalized

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """Parse a JSON date-time string returned by the LLM."""

        parsed_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed_value.tzinfo is None:
            return parsed_value.astimezone()

        return parsed_value

    @staticmethod
    def _format_analytics_date(value: datetime) -> str:
        """Format a date-time for human-readable analytics output."""

        return value.isoformat(timespec="minutes")

    def _format_sales_by_product_report(
        self,
        report: SalesByProductReport,
    ) -> str:
        """Render a sales-by-product report as a short Spanish message."""

        lines = [
            "Analítica de "
            f"{self._format_analytics_date(report.date_range.start_date)} a "
            f"{self._format_analytics_date(report.date_range.end_date)}",
            "Ventas por producto:",
        ]
        if not report.rows:
            lines.append("No hay ventas registradas en ese rango.")
            return "\n".join(lines)

        for index, row in enumerate(report.rows, start=1):
            lines.append(
                f"{index}. {row.product_name}: {row.units_sold} unidades, "
                f"{row.transaction_count} ventas, ${row.total_amount}"
            )

        return "\n".join(lines)

    def _format_frequent_customers_report(
        self,
        report: FrequentCustomersReport,
    ) -> str:
        """Render a frequent-customers report as a short Spanish message."""

        lines = [
            "Analítica de "
            f"{self._format_analytics_date(report.date_range.start_date)} a "
            f"{self._format_analytics_date(report.date_range.end_date)}",
            "Clientes más frecuentes:",
        ]
        if not report.rows:
            lines.append("No hay ventas registradas en ese rango.")
            return "\n".join(lines)

        for index, row in enumerate(report.rows, start=1):
            lines.append(
                f"{index}. {row.customer_name}: {row.transaction_count} ventas, "
                f"${row.total_amount}"
            )

        return "\n".join(lines)

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """Convert a raw LLM argument into a ``Decimal`` for money handling.

        Args:
            value: Raw value returned by the LLM (typically a JSON number).

        Returns:
            The value converted to ``Decimal``.

        Raises:
            ValueError: If the value cannot be converted to ``Decimal``.
        """

        try:
            return Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError(f"Invalid numeric value: {value!r}") from error

    _CUSTOMER_TOOL_HANDLERS = {
        "registrar_venta": _run_registrar_venta,
        "registrar_pago": _run_registrar_pago,
        "consultar_saldo": _run_consultar_saldo,
        "generar_resumen_cobro": _run_generar_resumen_cobro,
    }
    _SIMPLE_TOOL_HANDLERS = {
        "anular_transaccion": _run_anular_transaccion,
        "actualizar_precio": _run_actualizar_precio,
        "consultar_analitica": _run_consultar_analitica,
    }
    _PRODUCT_ANALYTICS_TYPES = {"ventas_por_producto", "ventas_por_productos"}
    _CUSTOMER_ANALYTICS_TYPES = {
        "clientes_mas_frecuentes",
        "clientes_frecuentes",
        "clientes_mas_compradores",
    }
