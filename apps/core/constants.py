"""Static assets that content can reference by key.

Icons and flags are SVG files shipped with the code (MIT-licensed libraries in static/vendor).
Content editors pick them from a list instead of uploading SVGs, which could carry scripts.
"""

from django.utils.translation import gettext_lazy as _

BOOTSTRAP_ICONS_DIR = "vendor/bootstrap-icons-1.13.2/icons"
FLAG_ICONS_DIR = "vendor/flag-icons-7.6.0/flags/4x3"

FLAG_CHOICES = [
    ("co", _("Colombia")),
    ("es", _("Spain")),
    ("it", _("Italy")),
    ("mx", _("Mexico")),
    ("pa", _("Panama")),
    ("pe", _("Peru")),
    ("us", _("United States")),
]


def icon_path(name):
    return f"{BOOTSTRAP_ICONS_DIR}/{name}.svg"


def flag_path(country_code):
    return f"{FLAG_ICONS_DIR}/{country_code.lower()}.svg"
