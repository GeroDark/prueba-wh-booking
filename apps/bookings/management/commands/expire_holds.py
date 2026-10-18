from django.core.management.base import BaseCommand

from apps.bookings.services import expire_holds


class Command(BaseCommand):
    help = (
        "Mark holds past their expiry as EXPIRED. Optional housekeeping (e.g. a cron every few "
        "minutes): availability is already correct without it, because expired holds stop "
        "blocking their dates on their own."
    )

    def handle(self, *args, **options):
        count = expire_holds()
        self.stdout.write(self.style.SUCCESS(f"Expired holds: {count}."))
