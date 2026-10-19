import os

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Create the admin account from DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD if it "
        "does not exist yet. Runs on every start (the free hosting plan has no shell); it never "
        "changes an existing account, and does nothing when the variables are not set."
    )

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not (email and password):
            self.stdout.write("No DJANGO_SUPERUSER_EMAIL/PASSWORD: admin account not created.")
            return

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write("Admin account already exists: nothing to do.")
            return

        user = User(email=email, full_name="Wynwood House Admin")
        try:
            password_validation.validate_password(password, user)
        except ValidationError as error:
            # Fail loudly: a weak admin password must not reach production unnoticed.
            raise CommandError("DJANGO_SUPERUSER_PASSWORD: " + " ".join(error.messages)) from error
        User.objects.create_superuser(email=email, password=password, full_name=user.full_name)
        self.stdout.write(self.style.SUCCESS(f"Admin account {email} created."))
