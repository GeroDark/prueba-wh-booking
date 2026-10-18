import pytest

from apps.core.models import Banner, ContactChannel, HomePage, SiteSettings

pytestmark = pytest.mark.django_db


def test_singleton_load_always_returns_the_same_row():
    first = HomePage.load()
    second = HomePage.load()

    assert first.pk == second.pk == HomePage.SINGLETON_PK
    assert HomePage.objects.count() == 1


def test_saving_a_new_singleton_instance_overwrites_the_existing_row():
    HomePage.load()

    HomePage(hero_title_es="Otro título").save()

    assert HomePage.objects.count() == 1
    assert HomePage.load().hero_title_es == "Otro título"


def test_whatsapp_url_uses_digits_and_encodes_the_message():
    settings = SiteSettings(
        whatsapp_number="+51 947 022 549", whatsapp_message_es="Hola, ¿qué tal?"
    )

    assert (
        settings.whatsapp_url == "https://wa.me/51947022549?text=Hola%2C%20%C2%BFqu%C3%A9%20tal%3F"
    )


def test_whatsapp_url_is_empty_without_a_number():
    assert SiteSettings().whatsapp_url == ""


@pytest.mark.parametrize(
    ("kind", "value", "href"),
    [
        ("whatsapp", "+57 323 811 0133", "https://wa.me/573238110133"),
        ("phone", "+1 (253) 642-3881", "tel:+12536423881"),
        ("email", "sales@wynwoodhouse.com", "mailto:sales@wynwoodhouse.com"),
    ],
)
def test_contact_channel_links(kind, value, href):
    assert ContactChannel(kind=kind, value=value).get_href() == href


def test_whatsapp_channel_opens_the_chat_with_a_message():
    channel = ContactChannel(kind="whatsapp", value="+57 323 811 0133")

    assert channel.get_href(whatsapp_message="Hola") == "https://wa.me/573238110133?text=Hola"


def test_message_only_applies_to_whatsapp_channels():
    channel = ContactChannel(kind="email", value="sales@wynwoodhouse.com")

    assert channel.get_href(whatsapp_message="Hola") == "mailto:sales@wynwoodhouse.com"


def test_contact_channel_flag_points_to_a_bundled_svg():
    channel = ContactChannel(kind="whatsapp", value="1", country_code="pe")

    assert channel.flag_static_path == "vendor/flag-icons-7.6.0/flags/4x3/pe.svg"


def test_banner_whatsapp_button_uses_site_settings():
    site = SiteSettings(whatsapp_number="+51 1")
    banner = Banner(cta_target=Banner.CtaTarget.WHATSAPP, cta_url="https://ignored.example")

    assert banner.get_cta_url(site) == "https://wa.me/511"


def test_banner_whatsapp_message_overrides_the_general_one():
    site = SiteSettings(whatsapp_number="+51 1", whatsapp_message_es="General")
    specific = Banner(cta_target=Banner.CtaTarget.WHATSAPP, cta_message_es="Estadía larga")
    generic = Banner(cta_target=Banner.CtaTarget.WHATSAPP)

    assert specific.get_cta_url(site) == "https://wa.me/511?text=Estad%C3%ADa%20larga"
    assert generic.get_cta_url(site) == "https://wa.me/511?text=General"


def test_banner_link_button_uses_its_own_url():
    banner = Banner(cta_target=Banner.CtaTarget.LINK, cta_url="https://wynwoodhouse.com/")

    assert banner.get_cta_url(SiteSettings()) == "https://wynwoodhouse.com/"
