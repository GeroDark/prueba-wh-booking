from django.core.management.base import BaseCommand

from apps.bookings.emails import pending_confirmations, send_booking_confirmation


class Command(BaseCommand):
    help = (
        "Send the confirmation e-mail of confirmed bookings that do not have it yet: pending ones "
        "(e.g. the provider was down when they were paid) and ones stuck in 'sending' because "
        "the process died. Safe to run any time, e.g. from a scheduled job."
    )

    def handle(self, *args, **options):
        pending = list(pending_confirmations().values_list("pk", flat=True))
        sent = sum(send_booking_confirmation(pk) for pk in pending)
        failed = len(pending) - sent
        style = self.style.SUCCESS if not failed else self.style.WARNING
        self.stdout.write(style(f"Confirmation e-mails sent: {sent}. Failed: {failed}."))
