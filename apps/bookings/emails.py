"""Booking confirmation e-mail (requirement 7 of the PDF, D37).

Sent after the payment is committed, in the language the guest booked in. Each booking goes
through three states:

- pending:  confirmation_claimed_at and confirmation_sent_at empty
- sending:  confirmation_claimed_at set; one process owns the delivery
- sent:     confirmation_sent_at set, only after the provider accepted the message

If sending fails, the claim is released and the booking is pending again. If the process dies
while sending, the claim goes stale and `send_booking_confirmations` takes it over. Delivery is
therefore "at least once": a crash right after the provider accepted the message can cause a
second copy, which is better than a guest with no confirmation. The payment is never affected.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.core.images import email_jpeg
from apps.core.models import SiteSettings, SocialLink
from apps.properties.models import Country

from .models import Booking

logger = logging.getLogger(__name__)

OTHER_DESTINATIONS = 4


def absolute(url):
    """E-mails have no request: '/media/a.webp' -> 'https://site/media/a.webp'. Storage URLs
    that are already absolute (a CDN in production) stay as they are."""
    return url if url.startswith(("http://", "https://")) else f"{settings.SITE_URL}{url}"


def email_context(booking):
    site = SiteSettings.load()
    prop = booking.property
    cover = prop.cover_image
    destinations = (
        Country.objects.filter(is_active=True)
        .exclude(image="")
        .exclude(pk=prop.city.country_id)[:OTHER_DESTINATIONS]
    )
    search_url = reverse("properties:search")
    return {
        "booking": booking,
        "prop": prop,
        "guest": booking.guest,
        "site_settings": site,
        "logo_url": absolute(static("img/email/logo.png")),
        # JPEG copies: WebP is not shown by every e-mail client (D37).
        "cover_url": absolute(email_jpeg(cover.image, 1200)) if cover else "",
        "booking_url": absolute(reverse("bookings:confirmation", args=[booking.reference])),
        "chat_url": site.get_whatsapp_url(
            _("Hi, I have a question about my booking %(reference)s.")
            % {"reference": booking.reference}
        ),
        "support_url": site.whatsapp_url,
        "destinations": [
            {
                "name": country.name,
                "image_url": absolute(email_jpeg(country.image, 300, 400)),
                "url": absolute(f"{search_url}?country={country.slug}"),
            }
            for country in destinations
        ],
        "social_links": [
            {
                "name": link.get_network_display(),
                "url": link.url,
                "icon_url": absolute(static(f"img/email/{link.network}.png")),
            }
            for link in SocialLink.objects.all()
        ],
    }


def build_confirmation_email(booking):
    """The message in the booking's language: HTML (Figma "Correo confirmación") + plain text."""
    with translation.override(booking.language):
        context = email_context(booking)
        subject = _("Your booking %(reference)s is confirmed") % {"reference": booking.reference}
        text = render_to_string("emails/booking_confirmation.txt", context)
        html = render_to_string("emails/booking_confirmation.html", context)
    message = EmailMultiAlternatives(subject, text, to=[booking.guest.email])
    message.attach_alternative(html, "text/html")
    return message


# A claim older than this belongs to a process that died while sending.
STALE_CLAIM = timedelta(minutes=10)


def pending_confirmations(now=None):
    """Confirmed bookings whose e-mail is pending, or stuck in "sending" (stale claim)."""
    now = now or timezone.now()
    return Booking.objects.filter(
        status=Booking.Status.CONFIRMED,
        guest__isnull=False,
        confirmation_sent_at__isnull=True,
    ).filter(
        Q(confirmation_claimed_at__isnull=True) | Q(confirmation_claimed_at__lt=now - STALE_CLAIM)
    )


def load_booking(booking_id):
    return (
        Booking.objects.select_related("guest", "property__district__city__country")
        .prefetch_related("lines", "property__images")
        .get(pk=booking_id)
    )


def send_booking_confirmation(booking_id, now=None):
    """Send the confirmation of one booking. Returns True if it was sent now.

    The claim is a conditional UPDATE, so two processes cannot both own the delivery. Everything
    after the claim (reading the booking, rendering, the provider call) is inside the error
    handling: whatever fails releases the claim, and "sent" is written only after the provider
    accepted the message.
    """
    claimed_at = now or timezone.now()
    claimed = (
        pending_confirmations(claimed_at)
        .filter(pk=booking_id)
        .update(confirmation_claimed_at=claimed_at)
    )
    if not claimed:
        return False

    try:
        booking = load_booking(booking_id)
        build_confirmation_email(booking).send()
    except Exception:
        # Only our own claim is released (another process may have taken over a stale one).
        Booking.objects.filter(pk=booking_id, confirmation_claimed_at=claimed_at).update(
            confirmation_claimed_at=None
        )
        logger.exception("Confirmation e-mail of booking %s could not be sent", booking_id)
        return False

    Booking.objects.filter(pk=booking_id).update(
        confirmation_sent_at=timezone.now(), confirmation_claimed_at=None
    )
    logger.info("Confirmation e-mail of %s sent", booking.reference)
    return True


def send_confirmation_on_commit(booking):
    """Only after the payment is saved: a rolled-back payment never sends an e-mail."""
    transaction.on_commit(lambda: send_booking_confirmation(booking.pk))
