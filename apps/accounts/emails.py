"""E-mails about the account itself (D43)."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.translation import gettext as _

from apps.core.models import SiteSettings

logger = logging.getLogger(__name__)


def email_frame_context():
    """Absolute addresses for e-mails, which have no request (same frame as D37)."""
    return {
        "site_url": settings.SITE_URL,
        "logo_url": f"{settings.SITE_URL}{static('img/email/logo.png')}",
    }


def send_password_changed_notice(user):
    """Tell the owner that the account's password changed, so a reset they did not ask for
    does not go unnoticed (OWASP Forgot Password Cheat Sheet). No password and no token in it:
    only how to get the account back. Sent in the active language, the one of the page where
    the password was changed. A failure is logged; it never undoes or blocks the change."""
    context = {
        **email_frame_context(),
        "user": user,
        "contact_email": SiteSettings.load().contact_email,
    }
    message = EmailMultiAlternatives(
        _("Your Wynwood House password was changed"),
        render_to_string("emails/password_changed.txt", context),
        to=[user.email],
    )
    html = render_to_string("emails/password_changed.html", context)
    message.attach_alternative(html, "text/html")
    try:
        message.send()
    except Exception:
        logger.exception("Password change notice for user %s could not be sent", user.pk)
