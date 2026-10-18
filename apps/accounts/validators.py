"""Password rules shown in the design's checklist, on top of Django's validators (see D05).

Django already checks the length (8+), common passwords, numeric-only passwords and similarity
to the user's data. These two add the remaining items of the Figma checklist.
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class NumberOrSymbolValidator:
    """At least one digit or one character that is not a letter."""

    def validate(self, password, user=None):
        if not re.search(r"[\d\W_]", password):
            raise ValidationError(
                _("The password must contain at least one number or symbol."),
                code="password_no_number_or_symbol",
            )

    def get_help_text(self):
        return _("Contains a number or symbol.")


class PersonalInfoValidator:
    """The password cannot contain the e-mail's name part or any word of the full name.

    Django's UserAttributeSimilarityValidator compares the whole password with each attribute;
    this one also catches passwords that merely include them (e.g. "ana.torres2026" for
    ana.torres@mail.com).
    """

    min_length = 3

    def validate(self, password, user=None):
        if user is None:
            return
        email = (getattr(user, "email", "") or "").lower()
        full_name = (getattr(user, "full_name", "") or "").lower()
        pieces = [email.split("@")[0], *re.split(r"[\s.\-_]+", full_name)]
        lowered = password.lower()
        if any(len(piece) >= self.min_length and piece in lowered for piece in pieces):
            raise ValidationError(
                _("The password cannot contain your name or e-mail address."),
                code="password_contains_personal_info",
            )

    def get_help_text(self):
        return _("Does not contain your name or e-mail address.")
