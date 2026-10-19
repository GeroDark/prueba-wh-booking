from django.core.management.base import BaseCommand

from apps.bookings.emails import send_booking_confirmation
from apps.bookings.models import Booking


class Command(BaseCommand):
    help = (
        "Send the confirmation e-mail of confirmed bookings that do not have it yet (for example "
        "because the e-mail provider was down when they were paid). Safe to run any time: a "
        "booking is never e-mailed twice."
    )

    def handle(self, *args, **options):
        pending = Booking.objects.filter(
            status=Booking.Status.CONFIRMED,
            guest__isnull=False,
            confirmation_sent_at__isnull=True,
        ).values_list("pk", flat=True)
        sent = sum(send_booking_confirmation(pk) for pk in list(pending))
        failed = len(pending) - sent
        style = self.style.SUCCESS if not failed else self.style.WARNING
        self.stdout.write(style(f"Confirmation e-mails sent: {sent}. Failed: {failed}."))
