"""Application entry point for bootstrapping the application."""

from __future__ import annotations

from fastapi import FastAPI

from .api import health_router, telegram_router
from .config import load_config
from .logging_config import configure_logging


def create_app() -> FastAPI:
    """Build the FastAPI application with all routers registered.

    Returns:
        A configured FastAPI application instance ready to be served, e.g.
        via ``uvicorn fiadobot.main:app``.
    """

    config = load_config()
    configure_logging(config)
    application = FastAPI(title=config.app_name)
    application.include_router(health_router)
    application.include_router(telegram_router)
    return application


app = create_app()


def main() -> int:
    """Run the application bootstrap sequence.

    Returns:
        Zero when the bootstrap completes successfully.

    Raises:
        SystemExit: Raised only when the module is executed as a script.
    """

    config = load_config()
    print(f"{config.app_name} ready in {config.environment} mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
