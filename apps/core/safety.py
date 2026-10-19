"""Commands that delete data ask for an explicit confirmation in production (D38).

Locally (DEBUG on) and against test databases they run as usual. In production they stop with an
explanation unless the flag below is given, so a command typed in the wrong terminal cannot wipe
real bookings by accident.
"""

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connections

CONFIRM_FLAG = "--i-understand-this-deletes-production-data"


def add_confirmation_argument(parser):
    parser.add_argument(
        CONFIRM_FLAG,
        action="store_true",
        dest="confirm_production",
        help="Required to run this command in production (DEBUG off). Make a backup first.",
    )


def is_test_database(alias="default"):
    """The database Django created for the tests: the configured TEST NAME, `test_<name>` on
    PostgreSQL by default, or an in-memory SQLite database."""
    connection = connections[alias]
    name = str(connection.settings_dict["NAME"])
    test_name = (connection.settings_dict.get("TEST") or {}).get("NAME")
    if test_name:
        return name == str(test_name)
    if connection.vendor == "sqlite":
        return connection.is_in_memory_db()
    return name.startswith("test_")


def refuse_in_production(options, action, database="default"):
    if settings.DEBUG or options.get("confirm_production") or is_test_database(database):
        return
    raise CommandError(
        f"{action} deletes data and this is production (DEBUG is off). Make a backup first "
        f"(see 'Production data' in the README) and run it again with {CONFIRM_FLAG}."
    )
