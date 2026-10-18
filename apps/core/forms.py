from django import forms
from django.utils.translation import gettext_lazy as _

# Django's own Spanish messages use "usted" ("Introduzca una fecha válida") and some echo the
# value back. The site speaks "tú" and says what to fix (see D35).
FRIENDLY_MESSAGES = {
    # Only reachable by skipping the browser's maxlength, but answered in the site's tone too.
    forms.CharField: {
        "max_length": _("Use at most %(limit_value)d characters (it has %(show_value)d)."),
    },
    forms.UUIDField: {"invalid": _("The form expired. Reload the page and try again.")},
    forms.EmailField: {"invalid": _("Enter a valid email address, for example name@example.com.")},
    forms.DateField: {"invalid": _("Enter a valid date.")},
    forms.IntegerField: {
        "invalid": _("Enter a whole number."),
        "min_value": _("Enter a number greater than or equal to %(limit_value)s."),
        "max_value": _("Enter a number less than or equal to %(limit_value)s."),
    },
    forms.ModelChoiceField: {"invalid_choice": _("Select one of the available options.")},
}


def default_error_messages(field):
    """The messages a field gets from its classes, before any custom `error_messages`."""
    messages = {}
    for cls in reversed(type(field).__mro__):
        messages.update(getattr(cls, "default_error_messages", {}))
    return messages


class FriendlyErrorsMixin:
    """Replace Django's default error messages with the site's own, keeping custom ones."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            defaults = default_error_messages(field)
            for field_class, messages in FRIENDLY_MESSAGES.items():
                if not isinstance(field, field_class):
                    continue
                for code, message in messages.items():
                    if field.error_messages.get(code) == defaults.get(code):
                        field.error_messages[code] = message
