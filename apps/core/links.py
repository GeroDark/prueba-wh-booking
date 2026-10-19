"""Links edited in the admin (menus, banner buttons) can only be safe kinds of URL (D40).

An `href` is not protected by HTML escaping: `javascript:alert(1)` contains nothing to escape and
runs when clicked. So the value is checked against an allowlist instead of a blocklist (browsers
also accept tricks such as "java\tscript:" or leading spaces):

- full links:     https://… or http://… with a host
- site pages:     /es/search/ (one leading slash; "//host" would point to another site)
- page anchors:   #section
- contact links:  mailto:… and tel:…
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

SAFE_LINK = re.compile(
    r"""
    ^(?:
        https?://[^\s/?#\\]+[^\s\\]*   # absolute link with a host
      | /(?![/\\])[^\s]*                # path on this site, not protocol-relative
      | \#[^\s]*                        # anchor
      | mailto:[^\s]+
      | tel:\+?[\d\s().-]+
    )$
    """,
    re.VERBOSE | re.IGNORECASE,
)
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def is_safe_link(value):
    value = str(value or "")
    return not CONTROL_CHARS.search(value) and bool(SAFE_LINK.match(value))


def validate_safe_link(value):
    if not is_safe_link(value):
        raise ValidationError(
            _(
                "Use a full link (https://…), a page of this site (/es/…), an anchor (#…), "
                "mailto: or tel:."
            ),
            code="unsafe_link",
        )
