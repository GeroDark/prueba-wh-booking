import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait until the default database accepts connections (used by the Docker entrypoint)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout", type=int, default=60, help="Seconds to wait before failing."
        )

    def handle(self, *args, timeout, **options):
        deadline = time.monotonic() + timeout
        while True:
            try:
                connections["default"].ensure_connection()
            except OperationalError as exc:
                if time.monotonic() >= deadline:
                    raise CommandError(f"Database unavailable after {timeout}s.") from exc
                self.stdout.write("Database unavailable, retrying in 1s...")
                time.sleep(1)
            else:
                self.stdout.write(self.style.SUCCESS("Database available."))
                return
