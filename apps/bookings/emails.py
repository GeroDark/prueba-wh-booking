"""Booking confirmation e-mail (requirement 7 of the PDF, D37).

Sent once, after the payment is committed, in the language the guest booked in. If sending fails
the payment is not affected: the booking stays marked as "not sent" and the
`send_booking_confirmations` command (or the admin action) retries it.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
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


def send_booking_confirmation(booking_id):
    """Send the confirmation once. Returns True if it was sent now.

    The booking is claimed first with a conditional UPDATE, so two calls at the same time cannot
    both send it; if sending fails, the claim is undone and the error logged.
    """
    claimed = Booking.objects.filter(
        pk=booking_id,
        status=Booking.Status.CONFIRMED,
        guest__isnull=False,
        confirmation_sent_at__isnull=True,
    ).update(confirmation_sent_at=timezone.now())
    if not claimed:
        return False

    booking = (
        Booking.objects.select_related("guest", "property__district__city__country")
        .prefetch_related("lines", "property__images")
        .get(pk=booking_id)
    )
    try:
        build_confirmation_email(booking).send()
    except Exception:
        Booking.objects.filter(pk=booking_id).update(confirmation_sent_at=None)
        logger.exception("Confirmation e-mail of %s could not be sent", booking.reference)
        return False
    logger.info("Confirmation e-mail of %s sent", booking.reference)
    return True


def send_confirmation_on_commit(booking):
    """Only after the payment is saved: a rolled-back payment never sends an e-mail."""
    transaction.on_commit(lambda: send_booking_confirmation(booking.pk))
