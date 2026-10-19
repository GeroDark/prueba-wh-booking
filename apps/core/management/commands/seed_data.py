from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.safety import add_confirmation_argument, refuse_in_production
from apps.core.seeding import data
from apps.core.seeding.loader import FlushError, Seeder, flush_content
from apps.properties.models import Property


class Command(BaseCommand):
    help = (
        "Load demo content: site texts, destinations, properties with photos and a demo guest. "
        "Safe to run several times: existing records are updated, not duplicated."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help=(
                "Delete the seeded catalog, demo bookings and site content first (users are kept). "
                "Refuses to run if real bookings exist."
            ),
        )
        parser.add_argument(
            "--properties",
            type=int,
            metavar="N",
            help=f"Load only the first N of the {len(data.PROPERTIES)} demo properties.",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Do not attach photos (faster, e.g. for quick checks).",
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help=(
                "Do nothing if there are already properties. Used on every start in production, "
                "so the demo data is loaded once and later edits in the admin are kept."
            ),
        )
        add_confirmation_argument(parser)

    def handle(self, *args, flush, properties, skip_images, if_empty, **options):
        if properties is not None and not 1 <= properties <= len(data.PROPERTIES):
            raise CommandError(f"--properties must be between 1 and {len(data.PROPERTIES)}.")
        if if_empty and Property.objects.exists():
            self.stdout.write("Data already loaded: nothing to do.")
            return
        if flush:
            refuse_in_production(options, "seed_data --flush")

        with transaction.atomic():
            if flush:
                try:
                    flush_content()
                except FlushError as error:
                    raise CommandError(str(error)) from error
                self.stdout.write("Existing content deleted.")
            Seeder(
                with_images=not skip_images,
                property_limit=properties,
                log=self.stdout.write,
            ).run()

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
