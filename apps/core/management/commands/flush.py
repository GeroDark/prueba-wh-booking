from django.core.management.commands import flush

from apps.core.safety import add_confirmation_argument, refuse_in_production


class Command(flush.Command):
    """Django's `flush` (empties every table), guarded in production (D38)."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_confirmation_argument(parser)

    def handle(self, **options):
        refuse_in_production(options, "flush", options["database"])
        return super().handle(**options)
