"""Unit tests for the operational CLI entry point."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

from fiadobot import cli


def test_main_add_authorized_user_invokes_repository(monkeypatch) -> None:
    """It should parse the subcommand and delegate to the repository."""

    mock_session = MagicMock()
    mock_repository = MagicMock()
    mock_user = MagicMock(chat_id=555, role="vendedor")
    mock_repository.add_user.return_value = mock_user

    @contextmanager
    def fake_session_scope():
        yield mock_session

    monkeypatch.setattr(cli, "configure_logging", lambda config: None)
    monkeypatch.setattr(cli, "create_session_factory", lambda: fake_session_scope)
    monkeypatch.setattr(
        cli, "AuthorizedUserRepository", lambda session: mock_repository
    )

    exit_code = cli.main(["add-authorized-user", "555", "vendedor"])

    assert exit_code == 0
    mock_repository.add_user.assert_called_once_with(555, "vendedor")
