import re
from urllib.parse import quote

from django.db import models
from django.utils.translation import gettext_lazy as _

from .constants import FLAG_CHOICES, flag_path, icon_path
from .fields import OptimizedImageField


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True


class SingletonModel(models.Model):
    """Model with exactly one row, for site-wide content edited from the admin."""

    SINGLETON_PK = 1

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj


def whatsapp_url(number, message=""):
    digits = re.sub(r"\D", "", number)
    url = f"https://wa.me/{digits}"
    return f"{url}?text={quote(message)}" if message else url


class SiteSettings(SingletonModel):
    contact_email = models.EmailField(_("contact email"), blank=True)
    whatsapp_number = models.CharField(
        _("WhatsApp number"),
        max_length=20,
        blank=True,
        help_text=_(
            "International format, e.g. +51 947 022 549. Used by the 'Contact us' buttons."
        ),
    )
    whatsapp_message = models.CharField(
        _("WhatsApp message"),
        max_length=200,
        blank=True,
        help_text=_(
            "Text pre-filled in every WhatsApp chat opened from the site "
            "(footer numbers and buttons without their own message)."
        ),
    )
    app_store_url = models.URLField(_("App Store URL"), blank=True)
    play_store_url = models.URLField(_("Google Play URL"), blank=True)
    # Linked from the text the guest accepts before paying (Figma "Página de pago").
    terms_url = models.URLField(_("terms of service URL"), blank=True)
    privacy_url = models.URLField(_("privacy policy URL"), blank=True)
    cancellation_policy_url = models.URLField(_("cancellation policy URL"), blank=True)

    class Meta:
        verbose_name = _("site settings")
        verbose_name_plural = _("site settings")

    def __str__(self):
        return str(_("Site settings"))

    def get_whatsapp_url(self, message="", number=""):
        """Chat link to `number` (default: the site's number) with `message` or the general one."""
        number = number or self.whatsapp_number
        return whatsapp_url(number, message or self.whatsapp_message) if number else ""

    @property
    def whatsapp_url(self):
        return self.get_whatsapp_url()


class HomePage(SingletonModel):
    hero_title = models.CharField(_("hero title"), max_length=120, blank=True)
    hero_subtitle = models.CharField(_("hero subtitle"), max_length=120, blank=True)
    hero_image = OptimizedImageField(_("hero image"), upload_to="home/", blank=True)
    destinations_title = models.CharField(_("destinations title"), max_length=120, blank=True)
    featured_title = models.CharField(_("featured properties title"), max_length=120, blank=True)
    featured_text = models.TextField(_("featured properties text"), blank=True)

    class Meta:
        verbose_name = _("home page")
        verbose_name_plural = _("home page")

    def __str__(self):
        return str(_("Home page"))


class Banner(models.Model):
    class Layout(models.TextChoices):
        IMAGE_LEFT = "image_left", _("Image on the left")
        IMAGE_RIGHT = "image_right", _("Image on the right")
        BACKGROUND = "background", _("Full-width background image")

    class CtaTarget(models.TextChoices):
        LINK = "link", _("Link")
        WHATSAPP = "whatsapp", _("WhatsApp chat (site settings)")

    key = models.SlugField(
        _("key"), unique=True, help_text=_("Identifier used by the templates, e.g. long-stay.")
    )
    title = models.CharField(_("title"), max_length=120)
    text = models.TextField(_("text"), blank=True)
    image = OptimizedImageField(_("image"), upload_to="banners/", blank=True)
    layout = models.CharField(_("layout"), max_length=20, choices=Layout, default=Layout.IMAGE_LEFT)
    cta_label = models.CharField(_("button label"), max_length=60, blank=True)
    cta_target = models.CharField(
        _("button action"), max_length=20, choices=CtaTarget, default=CtaTarget.LINK
    )
    cta_url = models.CharField(
        _("button URL"), max_length=300, blank=True, help_text=_("Only for the 'Link' action.")
    )
    cta_message = models.CharField(
        _("WhatsApp message"),
        max_length=200,
        blank=True,
        help_text=_(
            "Only for the WhatsApp action: text pre-filled in the chat. "
            "Empty uses the general message from the site settings."
        ),
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("banner")
        verbose_name_plural = _("banners")
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def get_cta_url(self, site_settings):
        if self.cta_target == self.CtaTarget.WHATSAPP:
            return site_settings.get_whatsapp_url(self.cta_message)
        return self.cta_url


class FeatureSection(models.Model):
    """Title + text + grid of illustrated items (e.g. "Services", "Why travel to Spain")."""

    key = models.SlugField(_("key"), unique=True)
    title = models.CharField(_("title"), max_length=120)
    text = models.TextField(_("text"), blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("feature section")
        verbose_name_plural = _("feature sections")

    def __str__(self):
        return self.title


class FeatureItem(models.Model):
    section = models.ForeignKey(
        FeatureSection, on_delete=models.CASCADE, related_name="items", verbose_name=_("section")
    )
    title = models.CharField(_("title"), max_length=80)
    description = models.CharField(_("description"), max_length=300, blank=True)
    image = OptimizedImageField(_("image"), upload_to="features/", blank=True)
    order = models.PositiveSmallIntegerField(_("order"), default=0)

    class Meta:
        verbose_name = _("feature item")
        verbose_name_plural = _("feature items")
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class MenuGroup(models.Model):
    """Group of navigation links: the header menu or one footer column."""

    class Placement(models.TextChoices):
        HEADER = "header", _("Header")
        FOOTER = "footer", _("Footer")

    placement = models.CharField(_("placement"), max_length=10, choices=Placement)
    title = models.CharField(_("title"), max_length=80, blank=True)
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("menu")
        verbose_name_plural = _("menus")
        ordering = ["placement", "order", "id"]

    def __str__(self):
        return f"{self.get_placement_display()}: {self.title or '-'}"


class MenuLink(models.Model):
    group = models.ForeignKey(
        MenuGroup, on_delete=models.CASCADE, related_name="links", verbose_name=_("menu")
    )
    label = models.CharField(_("label"), max_length=80)
    url = models.CharField(_("URL"), max_length=300)
    opens_in_new_tab = models.BooleanField(_("open in a new tab"), default=False)
    order = models.PositiveSmallIntegerField(_("order"), default=0)

    class Meta:
        verbose_name = _("link")
        verbose_name_plural = _("links")
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class ContactChannel(models.Model):
    class Kind(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        PHONE = "phone", _("Phone")
        EMAIL = "email", _("Email")

    kind = models.CharField(_("type"), max_length=10, choices=Kind)
    label = models.CharField(_("label"), max_length=80, blank=True)
    value = models.CharField(_("value"), max_length=120)
    country_code = models.CharField(
        _("country flag"), max_length=2, choices=FLAG_CHOICES, blank=True
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("contact channel")
        verbose_name_plural = _("contact channels")
        ordering = ["kind", "order", "id"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.value}"

    def get_href(self, whatsapp_message=""):
        """Link for the channel; WhatsApp chats open with `whatsapp_message` pre-filled."""
        if self.kind == self.Kind.WHATSAPP:
            return whatsapp_url(self.value, whatsapp_message)
        if self.kind == self.Kind.PHONE:
            return "tel:+" + re.sub(r"\D", "", self.value)
        return f"mailto:{self.value}"

    @property
    def flag_static_path(self):
        return flag_path(self.country_code) if self.country_code else ""


class SocialLink(models.Model):
    class Network(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        LINKEDIN = "linkedin", "LinkedIn"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        X = "twitter-x", "X"

    network = models.CharField(_("network"), max_length=20, choices=Network, unique=True)
    url = models.URLField(_("URL"))
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("social network")
        verbose_name_plural = _("social networks")
        ordering = ["order", "id"]

    def __str__(self):
        return self.get_network_display()

    @property
    def icon_static_path(self):
        return icon_path(self.network)
