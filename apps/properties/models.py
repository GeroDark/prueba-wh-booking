import zoneinfo
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.constants import FLAG_CHOICES, flag_path, icon_path
from apps.core.fields import OptimizedImageField
from apps.core.models import TimeStampedModel

from .querysets import PropertyQuerySet


def validate_timezone(value):
    if value not in zoneinfo.available_timezones():
        raise ValidationError(_("“%(value)s” is not a valid time zone."), params={"value": value})


class Country(models.Model):
    code = models.CharField(_("ISO code"), max_length=2, unique=True, choices=FLAG_CHOICES)
    name = models.CharField(_("name"), max_length=80)
    slug = models.SlugField(_("slug"), unique=True)
    image = OptimizedImageField(_("image"), upload_to="destinations/", blank=True)
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("country")
        verbose_name_plural = _("countries")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def flag_static_path(self):
        return flag_path(self.code)


class City(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="cities", verbose_name=_("country")
    )
    name = models.CharField(_("name"), max_length=80)
    slug = models.SlugField(_("slug"), unique=True)
    timezone = models.CharField(
        _("time zone"),
        max_length=64,
        validators=[validate_timezone],
        help_text=_("IANA name, e.g. America/Bogota. Decides which dates are in the past."),
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("city")
        verbose_name_plural = _("cities")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def local_today(self):
        """Today's date where the city is, which can differ from the server's date."""
        return timezone.localdate(timezone=zoneinfo.ZoneInfo(self.timezone))


class District(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name="districts", verbose_name=_("city")
    )
    name = models.CharField(_("name"), max_length=80)
    slug = models.SlugField(_("slug"))

    class Meta:
        verbose_name = _("district")
        verbose_name_plural = _("districts")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["city", "slug"], name="properties_district_unique_slug"
            ),
        ]

    def __str__(self):
        return f"{self.name}, {self.city}"


class Amenity(models.Model):
    class Icon(models.TextChoices):
        WIFI = "wifi", "Wi-Fi"
        TV = "tv", "TV"
        AIR_CONDITIONING = "snow", _("Air conditioning")
        KITCHEN = "fork-knife", _("Kitchen")
        WORKSPACE = "laptop", _("Workspace")
        PARKING = "p-square", _("Parking")
        ELEVATOR = "arrow-down-up", _("Elevator")
        SECURITY = "shield-check", _("Security")
        TERRACE = "tree", _("Terrace")
        POOL = "water", _("Pool")
        GRILL = "fire", _("Grill")
        GYM = "heart-pulse", _("Gym")
        SELF_CHECK_IN = "key", _("Self check-in")

    name = models.CharField(_("name"), max_length=60)
    icon = models.CharField(_("icon"), max_length=30, choices=Icon)
    order = models.PositiveSmallIntegerField(_("order"), default=0)

    class Meta:
        verbose_name = _("amenity")
        verbose_name_plural = _("amenities")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def icon_static_path(self):
        return icon_path(self.icon)


class Property(TimeStampedModel):
    title = models.CharField(_("title"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, unique=True)
    description = models.TextField(_("description"))
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, related_name="properties", verbose_name=_("district")
    )
    address = models.CharField(_("address"), max_length=200, blank=True)
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    max_guests = models.PositiveSmallIntegerField(
        _("maximum guests"), validators=[MinValueValidator(1)]
    )
    bedrooms = models.PositiveSmallIntegerField(_("bedrooms"), default=1)
    beds = models.PositiveSmallIntegerField(_("beds"), default=1)
    bathrooms = models.PositiveSmallIntegerField(_("bathrooms"), default=1)
    price_per_night = models.DecimalField(
        _("price per night"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    cleaning_fee = models.DecimalField(
        _("cleaning fee"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    amenities = models.ManyToManyField(
        Amenity, related_name="properties", blank=True, verbose_name=_("amenities")
    )
    is_featured = models.BooleanField(_("featured"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    objects = PropertyQuerySet.as_manager()

    class Meta:
        verbose_name = _("property")
        verbose_name_plural = _("properties")
        ordering = ["-is_featured", "title"]
        indexes = [models.Index(fields=["is_active", "is_featured"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(price_per_night__gt=0), name="properties_property_price_positive"
            ),
            models.CheckConstraint(
                condition=Q(cleaning_fee__gte=0),
                name="properties_property_cleaning_fee_not_negative",
            ),
            models.CheckConstraint(
                condition=Q(max_guests__gte=1), name="properties_property_max_guests_at_least_one"
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def city(self):
        return self.district.city

    @property
    def cover_image(self):
        """First image by order. Uses the prefetched images when available."""
        images = list(self.images.all())
        return images[0] if images else None


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images", verbose_name=_("property")
    )
    image = OptimizedImageField(_("image"), upload_to="properties/")
    alt_text = models.CharField(
        _("alternative text"),
        max_length=150,
        help_text=_("Describes the photo for screen readers and when it cannot load."),
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)

    class Meta:
        verbose_name = _("property image")
        verbose_name_plural = _("property images")
        ordering = ["order", "id"]

    def __str__(self):
        return self.alt_text


class Tax(models.Model):
    """Percentage applied to a stay's subtotal (nights + cleaning) in a country."""

    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="taxes", verbose_name=_("country")
    )
    name = models.CharField(_("name"), max_length=80)
    rate = models.DecimalField(
        _("rate (%)"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("100"))],
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("tax")
        verbose_name_plural = _("taxes")
        ordering = ["country", "order", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rate__gt=0, rate__lte=100), name="properties_tax_rate_range"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.rate}%)"
