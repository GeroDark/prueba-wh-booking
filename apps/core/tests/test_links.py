"""Regression tests for links edited in the admin (D40): no `javascript:` in an href."""

import pytest
from django.core.exceptions import ValidationError

from apps.core.links import is_safe_link, validate_safe_link
from apps.core.models import Banner, MenuGroup, MenuLink, SiteSettings

SAFE = [
    "https://wynwoodhouse.com/",
    "http://example.com/a?b=c#d",
    "/es/search/?city=bogota",
    "/",
    "#services",
    "mailto:sales@wynwoodhouse.com",
    "tel:+51 947 022 549",
]
UNSAFE = [
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    " javascript:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "//evil.example/",  # protocol-relative: another site
    "/\\evil.example/",  # browsers read "/\" as "//"
    "https://",  # no host
    "https:/evil.example",
    "wynwoodhouse.com",  # relative by accident
    "",
]


@pytest.mark.parametrize("url", SAFE)
def test_safe_links_are_accepted(url):
    assert is_safe_link(url)
    validate_safe_link(url)


@pytest.mark.parametrize("url", UNSAFE)
def test_unsafe_links_are_rejected(url):
    assert not is_safe_link(url)
    with pytest.raises(ValidationError):
        validate_safe_link(url)


@pytest.mark.django_db
def test_the_admin_forms_reject_javascript_links():
    group = MenuGroup.objects.create(placement="header", title="Menu")
    link = MenuLink(group=group, label="Ofertas", url="javascript:alert(document.cookie)")
    banner = Banner(key="promo", title="Promo", cta_label="Ver", cta_url="javascript:alert(1)")

    with pytest.raises(ValidationError) as link_error:
        link.full_clean()
    with pytest.raises(ValidationError) as banner_error:
        banner.full_clean()

    assert "url" in link_error.value.message_dict
    assert "cta_url" in banner_error.value.message_dict


@pytest.mark.django_db
def test_an_unsafe_link_saved_without_validation_never_reaches_the_page(client):
    """Second barrier: objects.create() skips validation (an import, old data)."""
    SiteSettings.load()
    for placement in ("header", "footer"):
        group = MenuGroup.objects.create(placement=placement, title=placement)
        MenuLink.objects.create(group=group, label=f"Trap {placement}", url="javascript:alert(1)")
    Banner.objects.create(
        key="trap", title="Trap", cta_label="Click", cta_url="javascript:alert(1)", is_active=True
    )

    html = client.get("/es/").text

    assert "javascript:" not in html
    assert 'href="#"' in html
