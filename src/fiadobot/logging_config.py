"""Root logger configuration shared by the web app and CLI entry points."""

from __future__ import annotations

import logging

from .config import AppConfig


def configure_logging(config: AppConfig) -> None:
    """Configure the root logger for the current process.

    Args:
        config: Application configuration holding the desired log level.

    Returns:
        None.
    """

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
