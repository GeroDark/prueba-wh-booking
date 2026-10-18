from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from .managers import UserManager
from .validators import validate_full_name


class User(AbstractUser):
    """Guest account identified by email. Personal fields follow the checkout registration form."""

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(
        _("full name"), max_length=150, blank=True, validators=[validate_full_name]
    )
    # ISO 3166-1 alpha-2 code; django-countries provides the translated names (D36).
    nationality = CountryField(_("nationality"), blank=True)
    phone_prefix = models.CharField(
        _("phone prefix"), max_length=5, blank=True, help_text=_("Country calling code, e.g. +51.")
    )
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        blank=True,
        help_text=_("National number without the prefix, digits only."),
    )
    birth_date = models.DateField(_("birth date"), null=True, blank=True)
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=7,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    marketing_opt_in = models.BooleanField(_("subscribed to the newsletter"), default=False)
    marketing_consent_at = models.DateTimeField(
        _("newsletter consent given at"),
        null=True,
        blank=True,
        help_text=_("When the guest ticked the newsletter box (proof of consent)."),
    )

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

    def set_marketing_consent(self, accepted, now=None):
        """Record the newsletter choice; the moment of a new consent is kept as proof."""
        if accepted and not self.marketing_opt_in:
            self.marketing_consent_at = now or timezone.now()
        elif not accepted:
            self.marketing_consent_at = None
        self.marketing_opt_in = accepted

    @property
    def has_guest_details(self):
        """The personal details the checkout asks for before paying (D12)."""
        return all(
            (
                self.full_name,
                self.nationality,
                self.phone_prefix,
                self.phone_number,
                self.birth_date,
            )
        )

    @property
    def phone(self):
        return f"{self.phone_prefix} {self.phone_number}" if self.phone_number else ""

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email
