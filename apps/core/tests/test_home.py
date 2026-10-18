from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.template import Context, Template
from django.test.utils import CaptureQueriesContext
from django.utils import translation

from apps.core.models import Banner, HomePage
from apps.properties.models import Property

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    call_command("seed_data", skip_images=True, stdout=StringIO())


def featured_section(html):
    return html.split('id="featured"')[1].split("</section>")[0]


def test_home_renders_the_content_from_the_models(client, seeded):
    html = client.get("/es/").text

    assert "Experiencia de hogar, calidad de hotel" in html
    assert "¿Por qué viajar a España?" in html
    assert "Alquileres a largo plazo" in html
    assert "Servicios en Wynwood House" in html


def test_home_is_bilingual(client, seeded):
    html = client.get("/en/").text

    assert "Home experience, hotel quality" in html
    assert "Why travel to Spain?" in html
    assert "Long-term rentals" in html


def test_editing_the_home_page_in_the_admin_changes_the_site(client, seeded):
    home = HomePage.load()
    home.hero_title_es = "Tu casa en Latinoamérica"
    home.save()

    assert "Tu casa en Latinoamérica" in client.get("/es/").text


def test_only_active_featured_properties_are_shown(client, seeded):
    featured = Property.objects.filter(is_featured=True).first()
    regular = Property.objects.filter(is_featured=False).first()
    Property.objects.filter(pk=featured.pk).update(is_active=False)

    section = featured_section(client.get("/es/").text)

    assert featured.title_es not in section
    assert regular.title_es not in section
    assert Property.objects.active().featured().first().title_es in section


def test_inactive_banners_are_hidden(client, seeded):
    Banner.objects.filter(key="events").update(is_active=False)

    html = client.get("/es/").text

    assert "¡Disfruta de nuestros eventos!" not in html
    assert "Alquileres a largo plazo" in html


def test_long_stay_button_opens_whatsapp_with_the_message(client, seeded):
    html = client.get("/es/").text

    assert "https://wa.me/51947022549?text=Hola%2C%20me%20gustar%C3%ADa" in html


def test_footer_shows_menus_contacts_and_flags(client, seeded):
    html = client.get("/es/").text

    assert "Política de privacidad" in html
    assert "tel:+12536423881" in html
    assert "flags/4x3/pe.svg" in html


def test_home_query_count_does_not_grow_with_the_catalog(client, seeded):
    def count_queries():
        with CaptureQueriesContext(connection) as queries:
            assert client.get("/es/").status_code == 200
        return len(queries)

    with_six_featured = count_queries()
    Property.objects.update(is_featured=True)
    with_all_featured = count_queries()

    assert with_all_featured == with_six_featured


@pytest.mark.parametrize(
    ("language", "value", "expected"),
    [
        ("es", "1250.00", "US$ 1\xa0250"),  # Spanish groups thousands with a non-breaking space
        ("en", "1250.00", "US$ 1,250"),
        ("es", "83.50", "US$ 83,50"),
        ("en", "83", "US$ 83"),
    ],
)
def test_money_filter_formats_by_language(language, value, expected):
    template = Template("{% load formatting %}{{ value|money }}")

    with translation.override(language):
        assert template.render(Context({"value": value})) == expected


def test_search_and_detail_pages_render(client, seeded):
    prop = Property.objects.first()

    assert client.get("/es/search/").status_code == 200
    assert client.get(f"/es/properties/{prop.slug}/").status_code == 200


def test_inactive_property_detail_is_not_found(client, seeded):
    prop = Property.objects.first()
    Property.objects.filter(pk=prop.pk).update(is_active=False)

    assert client.get(f"/es/properties/{prop.slug}/").status_code == 404


def test_pages_render_with_production_static_files(client, seeded, settings, tmp_path):
    """Manifest storage fails on any {% static %} path that is not a real file (e.g. a folder)."""
    settings.STATIC_ROOT = tmp_path / "static"
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    call_command("collectstatic", interactive=False, verbosity=0)

    for url in ("/es/", "/en/", "/es/search/"):
        assert client.get(url).status_code == 200, url
