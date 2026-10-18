from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from PIL import Image

from apps.core.models import Banner, FeatureSection, HomePage, MenuLink
from apps.core.seeding import data
from apps.properties.models import City, Country, Property, PropertyImage

pytestmark = pytest.mark.django_db


def counts():
    return {
        model.__name__: model.objects.count()
        for model in (Country, City, Property, PropertyImage, FeatureSection, Banner, MenuLink)
    }


def test_seed_loads_the_whole_catalog_without_images():
    call_command("seed_data", skip_images=True)

    assert Property.objects.count() == len(data.PROPERTIES)
    assert Country.objects.count() == len(data.COUNTRIES)
    assert FeatureSection.objects.filter(key="why-spain").exists()
    assert Banner.objects.get(key="long-stay").cta_target == Banner.CtaTarget.WHATSAPP
    assert get_user_model().objects.filter(email=data.DEMO_USER["email"]).exists()


def test_seed_is_idempotent():
    call_command("seed_data", skip_images=True)
    first = counts()

    call_command("seed_data", skip_images=True)

    assert counts() == first


def test_seed_content_is_bilingual():
    call_command("seed_data", skip_images=True)

    prop = Property.objects.get(slug="modern-duplex-parque-virrey")
    assert prop.title_es == "Dúplex moderno en Parque Virrey"
    assert prop.title_en == "Modern duplex in Parque Virrey"


def test_seed_can_limit_the_number_of_properties():
    call_command("seed_data", skip_images=True, properties=3)

    assert Property.objects.count() == 3


def test_seed_rejects_an_invalid_property_limit():
    with pytest.raises(CommandError):
        call_command("seed_data", skip_images=True, properties=0)


def test_flush_removes_content_but_keeps_users():
    call_command("seed_data", skip_images=True)
    Property.objects.filter(slug="modern-duplex-parque-virrey").update(title_es="Editado")

    call_command("seed_data", skip_images=True, flush=True, properties=1)

    assert Property.objects.count() == 1
    assert Property.objects.get().title_es == "Dúplex moderno en Parque Virrey"
    assert get_user_model().objects.filter(email=data.DEMO_USER["email"]).exists()


def test_seed_images_go_through_the_optimizer():
    call_command("seed_data", properties=1)

    hero = HomePage.load().hero_image
    assert hero.name.endswith(".webp")
    for property_image in PropertyImage.objects.all():
        with Image.open(property_image.image.path) as image:
            assert image.format == "WEBP"
            assert max(image.size) <= 1200


def test_seed_creates_demo_bookings_relative_to_today():
    from django.utils import timezone

    from apps.bookings.models import Booking

    call_command("seed_data", skip_images=True)

    demo = Booking.objects.filter(reference__startswith=data.DEMO_BOOKING_PREFIX)
    assert demo.count() == len(data.DEMO_BOOKINGS)
    assert all(booking.check_in > timezone.localdate() for booking in demo)
    assert all(booking.status == Booking.Status.CONFIRMED for booking in demo)


def test_flush_refuses_to_delete_real_bookings():
    from apps.bookings.models import Booking

    call_command("seed_data", skip_images=True)
    demo = Booking.objects.first()
    # A real booking on free dates (overlapping ones are rejected by the database).
    Booking.objects.create(
        property=demo.property,
        check_in=demo.check_out + timedelta(days=100),
        check_out=demo.check_out + timedelta(days=103),
        guests=1,
    )

    with pytest.raises(CommandError, match="real bookings"):
        call_command("seed_data", skip_images=True, flush=True)

    assert Property.objects.count() == len(data.PROPERTIES)
