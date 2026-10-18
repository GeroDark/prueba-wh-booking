from decimal import Decimal
from io import BytesIO

import factory
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.properties.models import City, Country, District, Property, PropertyImage, Tax


def image_upload(
    name="photo.jpg", size=(1600, 1200), image_format="JPEG", mode="RGB", **save_kwargs
):
    buffer = BytesIO()
    Image.new(mode, size, color=(200, 120, 60, 128)[: len(mode)]).save(
        buffer, format=image_format, **save_kwargs
    )
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{image_format.lower()}")


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ("code",)

    code = "co"
    name_es = "Colombia"
    name_en = "Colombia"
    slug = factory.LazyAttribute(lambda country: f"country-{country.code}")


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    country = factory.SubFactory(CountryFactory)
    name_es = factory.Sequence(lambda n: f"Ciudad {n}")
    name_en = factory.Sequence(lambda n: f"City {n}")
    slug = factory.Sequence(lambda n: f"city-{n}")
    timezone = "America/Bogota"


class DistrictFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = District

    city = factory.SubFactory(CityFactory)
    name_es = factory.Sequence(lambda n: f"Barrio {n}")
    name_en = factory.SelfAttribute("name_es")
    slug = factory.Sequence(lambda n: f"district-{n}")


class PropertyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Property

    title_es = factory.Sequence(lambda n: f"Departamento {n}")
    title_en = factory.Sequence(lambda n: f"Apartment {n}")
    slug = factory.Sequence(lambda n: f"apartment-{n}")
    description_es = "Descripción de prueba."
    description_en = "Test description."
    district = factory.SubFactory(DistrictFactory)
    max_guests = 2
    price_per_night = Decimal("100.00")
    cleaning_fee = Decimal("20.00")


class PropertyImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PropertyImage

    property = factory.SubFactory(PropertyFactory)
    image = factory.LazyFunction(image_upload)
    alt_text_es = "Sala de estar"
    alt_text_en = "Living room"


class TaxFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tax

    country = factory.SubFactory(CountryFactory)
    name_es = "IVA"
    name_en = "VAT"
    rate = Decimal("19.00")
