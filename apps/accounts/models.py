from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """Guest account identified by email. Personal fields follow the checkout registration form."""

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=150, blank=True)
    nationality = models.CharField(
        _("nationality"),
        max_length=2,
        blank=True,
        help_text=_("ISO 3166-1 alpha-2 country code."),
    )
    phone_prefix = models.CharField(_("phone prefix"), max_length=5, blank=True)
    phone_number = models.CharField(_("phone number"), max_length=20, blank=True)
    birth_date = models.DateField(_("birth date"), null=True, blank=True)
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=7,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    marketing_opt_in = models.BooleanField(_("subscribed to the newsletter"), default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
                violation_error_message=_("An account with this email already exists."),
            ),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email
