"""Account key for the failed sign-in limit (django-axes, D41).

The login accepts the e-mail in any case ("Ana@Mail.com" signs in as "ana@mail.com"), so the
limit must count those as the same account. Otherwise an attacker gets 5 new attempts for each
spelling: "ANA@mail.com", "aNa@mail.com"... A test caught it.
"""

from django.conf import settings

from .managers import UserManager


def lockout_username(request, credentials=None):
    field = settings.AXES_USERNAME_FORM_FIELD
    raw = (credentials or {}).get(field) or request.POST.get(field, "")
    return UserManager.normalize_email(raw)
