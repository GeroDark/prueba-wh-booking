from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core.images import optimize_image
from apps.properties.tests.factories import PropertyImageFactory, image_upload


def stored_image(field_file):
    field_file.open("rb")
    image = Image.open(field_file)
    image.load()
    field_file.close()
    return image


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((4000, 3000), (1200, 900)),  # landscape: width capped
        ((1500, 3000), (600, 1200)),  # portrait: height capped
        ((800, 600), (800, 600)),  # already small: never upscaled
    ],
)
def test_optimizer_fits_the_image_inside_1200px_keeping_aspect_ratio(size, expected):
    name, content = optimize_image(
        image_upload(size=size), "photo.jpg", max_dimension=1200, quality=80
    )

    image = Image.open(content)
    assert name == "photo.webp"
    assert image.format == "WEBP"
    assert image.size == expected


def test_optimizer_applies_exif_orientation():
    exif = Image.Exif()
    exif[0x0112] = 6  # "rotate 90° clockwise", as phones store portrait photos
    upload = image_upload(size=(400, 200), exif=exif)

    _, content = optimize_image(upload, "phone.jpg", max_dimension=1200, quality=80)

    assert Image.open(content).size == (200, 400)


def test_optimizer_keeps_transparency():
    upload = image_upload(name="logo.png", size=(300, 300), image_format="PNG", mode="RGBA")

    _, content = optimize_image(upload, "logo.png", max_dimension=1200, quality=80)

    assert Image.open(content).mode == "RGBA"


@pytest.mark.django_db
def test_uploaded_property_image_is_stored_as_optimized_webp():
    property_image = PropertyImageFactory(image=image_upload("living room.jpg", size=(3000, 2000)))

    assert property_image.image.name.startswith("properties/")
    assert property_image.image.name.endswith(".webp")
    image = stored_image(property_image.image)
    assert image.format == "WEBP"
    assert image.size == (1200, 800)


@pytest.mark.django_db
def test_direct_save_on_the_field_is_optimized_too():
    property_image = PropertyImageFactory()
    buffer = BytesIO()
    Image.new("RGB", (2400, 2400)).save(buffer, format="PNG")

    property_image.image.save("square.png", SimpleUploadedFile("square.png", buffer.getvalue()))

    assert property_image.image.name.endswith(".webp")
    assert stored_image(property_image.image).size == (1200, 1200)


@pytest.mark.django_db
def test_limits_come_from_settings(settings):
    settings.IMAGE_MAX_DIMENSION = 500

    property_image = PropertyImageFactory(image=image_upload(size=(1000, 800)))

    assert stored_image(property_image.image).size == (500, 400)
