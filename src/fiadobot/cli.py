"""Operational command-line entry point for tasks outside the chat surface.

Some operational tasks, such as authorizing a new Telegram chat, must be
available before the bot can talk to anyone in that chat. This module
provides a small CLI so operators can run those tasks directly against a
deployed database (``python -m fiadobot.cli ...``) without writing ad hoc
SQL or Python scripts.
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .db.session import create_session_factory
from .logging_config import configure_logging
from .repositories import AuthorizedUserRepository

logger = logging.getLogger(__name__)


def add_authorized_user(chat_id: int, role: str) -> None:
    """Authorize a Telegram chat to use the bot.

    Args:
        chat_id: Telegram chat identifier to authorize.
        role: Role assigned to the chat, e.g. "vendedor" or "tester".

    Returns:
        None.

    Raises:
        SQLAlchemyError: If the insert or commit fails.
    """

    session_factory = create_session_factory()
    with session_factory() as session:
        repository = AuthorizedUserRepository(session)
        user = repository.add_user(chat_id, role)
        logger.info("Authorized chat_id=%s with role=%s", user.chat_id, user.role)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the fiadobot CLI.

    Returns:
        The configured argument parser.
    """

    parser = argparse.ArgumentParser(
        prog="python -m fiadobot.cli",
        description="Operational commands for fiadobot.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_user_parser = subparsers.add_parser(
        "add-authorized-user",
        help="Authorize a Telegram chat_id to use the bot.",
    )
    add_user_parser.add_argument(
        "chat_id", type=int, help="Telegram chat identifier to authorize."
    )
    add_user_parser.add_argument(
        "role", help='Role assigned to the chat, e.g. "vendedor" or "tester".'
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the fiadobot CLI.

    Args:
        argv: Optional argument list, mainly for testing. Defaults to
            ``sys.argv[1:]`` when omitted.

    Returns:
        Zero on success, non-zero when no known command was executed.
    """

    configure_logging(load_config())
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add-authorized-user":
        add_authorized_user(args.chat_id, args.role)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
