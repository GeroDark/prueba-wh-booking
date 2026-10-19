import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.db.utils import OperationalError

from apps.core.management.commands import wait_for_db
from apps.core.safety import refuse_in_production


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


# Destructive commands in production (D38)


@pytest.fixture
def production(settings, monkeypatch):
    settings.DEBUG = False
    monkeypatch.setattr("apps.core.safety.is_test_database", lambda alias="default": False)


@pytest.mark.django_db
@pytest.mark.parametrize("command", [["flush", "--noinput"], ["seed_data", "--flush"]])
def test_destructive_commands_stop_in_production(production, command):
    with pytest.raises(CommandError, match="--i-understand-this-deletes-production-data"):
        call_command(*command)


def test_the_confirmation_flag_lets_them_run(production):
    refuse_in_production({"confirm_production": True}, "flush")  # no error


def test_locally_they_run_as_usual(settings, monkeypatch):
    monkeypatch.setattr("apps.core.safety.is_test_database", lambda alias="default": False)
    settings.DEBUG = True

    refuse_in_production({}, "flush")  # no error
