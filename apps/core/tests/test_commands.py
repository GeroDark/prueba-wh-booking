import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.db.utils import OperationalError

from apps.core.management.commands import wait_for_db


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(wait_for_db.time, "sleep", lambda seconds: None)


def test_wait_for_db_retries_until_the_database_answers(monkeypatch, no_sleep, capsys):
    attempts = iter([OperationalError("starting up"), OperationalError("starting up"), None])

    def ensure_connection():
        error = next(attempts)
        if error:
            raise error

    monkeypatch.setattr(connections["default"], "ensure_connection", ensure_connection)

    call_command("wait_for_db")

    output = capsys.readouterr().out
    assert output.count("retrying") == 2
    assert "Database available." in output


def test_wait_for_db_fails_after_the_timeout(monkeypatch, no_sleep):
    def ensure_connection():
        raise OperationalError("down")

    monkeypatch.setattr(connections["default"], "ensure_connection", ensure_connection)

    with pytest.raises(CommandError, match="unavailable after 0s"):
        call_command("wait_for_db", timeout=0)
