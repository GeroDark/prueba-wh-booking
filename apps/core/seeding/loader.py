"""Idempotent loader for the demo content in `data.py`.

Every record is matched by a natural key (slug, code, key...) with update_or_create, so running
the command twice updates the content instead of duplicating it. Images are only attached when
the record has none, and they go through the model's OptimizedImageField (WebP, max 1200px).
"""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File

from apps.core.models import (
    Banner,
    ContactChannel,
    FeatureItem,
    FeatureSection,
    HomePage,
    MenuGroup,
    MenuLink,
    SiteSettings,
    SocialLink,
)
from apps.properties.models import (
    Amenity,
    City,
    Country,
    District,
    Property,
    PropertyImage,
    Tax,
)

from . import data

SEED_IMAGES_DIR = Path(settings.BASE_DIR) / "seed" / "images"


def translated(field, values):
    """("hola", "hello") -> {"field_es": "hola", "field_en": "hello"}"""
    spanish, english = values
    return {f"{field}_es": spanish, f"{field}_en": english}


class Seeder:
    def __init__(self, *, with_images=True, property_limit=None, log=print):
        self.with_images = with_images
        self.property_limit = property_limit
        self.log = log

    def run(self):
        self.seed_site_content()
        countries = self.seed_countries()
        self.seed_taxes(countries)
        districts = self.seed_locations(countries)
        amenities = self.seed_amenities()
        self.seed_properties(districts, amenities)
        self.seed_demo_user()

    # Helpers

    def attach_image(self, instance, field_name, relative_path):
        """Assign a seed image to an empty image field; saving the model optimizes it."""
        if not self.with_images or getattr(instance, field_name):
            return False
        path = SEED_IMAGES_DIR / relative_path
        with path.open("rb") as handle:
            setattr(instance, field_name, File(handle, name=path.name))
            instance.save()
        return True

    # Site content

    def seed_site_content(self):
        site = SiteSettings.load()
        site.contact_email = data.SITE_SETTINGS["contact_email"]
        site.whatsapp_number = data.SITE_SETTINGS["whatsapp_number"]
        for key, value in translated(
            "whatsapp_message", data.SITE_SETTINGS["whatsapp_message"]
        ).items():
            setattr(site, key, value)
        site.save()

        home = HomePage.load()
        for field in (
            "hero_title",
            "hero_subtitle",
            "destinations_title",
            "featured_title",
            "featured_text",
        ):
            for key, value in translated(field, data.HOME_PAGE[field]).items():
                setattr(home, key, value)
        home.save()
        self.attach_image(home, "hero_image", data.HOME_PAGE["hero_image"])

        for section_data in data.FEATURE_SECTIONS:
            section, _ = FeatureSection.objects.update_or_create(
                key=section_data["key"],
                defaults={
                    **translated("title", section_data["title"]),
                    **translated("text", section_data["text"]),
                },
            )
            for order, item_data in enumerate(section_data["items"]):
                item, _ = FeatureItem.objects.update_or_create(
                    section=section,
                    order=order,
                    defaults={
                        **translated("title", item_data["title"]),
                        **translated("description", item_data.get("description", ("", ""))),
                    },
                )
                self.attach_image(item, "image", item_data["image"])

        for banner_data in data.BANNERS:
            banner, _ = Banner.objects.update_or_create(
                key=banner_data["key"],
                defaults={
                    **translated("title", banner_data["title"]),
                    **translated("text", banner_data["text"]),
                    **translated("cta_label", banner_data["cta_label"]),
                    "layout": banner_data["layout"],
                    "cta_target": banner_data["cta_target"],
                    "cta_url": banner_data["cta_url"],
                    "order": banner_data["order"],
                },
            )
            self.attach_image(banner, "image", banner_data["image"])

        for order, menu_data in enumerate(data.MENUS):
            group, _ = MenuGroup.objects.update_or_create(
                placement=menu_data["placement"],
                order=order,
                defaults=translated("title", menu_data["title"]),
            )
            for link_order, label in enumerate(menu_data["links"]):
                MenuLink.objects.update_or_create(
                    group=group,
                    order=link_order,
                    defaults={**translated("label", label), "url": data.WH_SITE},
                )

        for order, channel in enumerate(data.CONTACT_CHANNELS):
            ContactChannel.objects.update_or_create(
                kind=channel["kind"],
                value=channel["value"],
                defaults={
                    **translated("label", channel["label"]),
                    "country_code": channel["country_code"],
                    "order": order,
                },
            )

        for order, social in enumerate(data.SOCIAL_LINKS):
            SocialLink.objects.update_or_create(
                network=social["network"], defaults={"url": social["url"], "order": order}
            )
        self.log("Site content: settings, home page, sections, banners, menus and contacts.")

    # Locations and catalog

    def seed_countries(self):
        countries = {}
        for order, country_data in enumerate(data.COUNTRIES):
            country, _ = Country.objects.update_or_create(
                code=country_data["code"],
                defaults={
                    **translated("name", country_data["name"]),
                    "slug": country_data["slug"],
                    "order": order,
                },
            )
            self.attach_image(country, "image", country_data["image"])
            countries[country.code] = country
        self.log(f"Countries: {len(countries)}.")
        return countries

    def seed_taxes(self, countries):
        for order, tax_data in enumerate(data.TAXES):
            Tax.objects.update_or_create(
                country=countries[tax_data["country"]],
                name_es=tax_data["name"][0],
                defaults={
                    "name_en": tax_data["name"][1],
                    "rate": Decimal(tax_data["rate"]),
                    "order": order,
                },
            )
        self.log(f"Taxes: {len(data.TAXES)}.")

    def seed_locations(self, countries):
        districts = {}
        for city_data in data.CITIES:
            city, _ = City.objects.update_or_create(
                slug=city_data["slug"],
                defaults={
                    **translated("name", city_data["name"]),
                    "country": countries[city_data["country"]],
                    "timezone": city_data["timezone"],
                },
            )
            for slug, name in city_data["districts"]:
                district, _ = District.objects.update_or_create(
                    city=city, slug=slug, defaults={"name_es": name, "name_en": name}
                )
                districts[(city.slug, slug)] = district
        self.log(f"Cities: {len(data.CITIES)}, districts: {len(districts)}.")
        return districts

    def seed_amenities(self):
        amenities = {}
        for order, amenity_data in enumerate(data.AMENITIES):
            amenity, _ = Amenity.objects.update_or_create(
                icon=amenity_data["icon"],
                defaults={**translated("name", amenity_data["name"]), "order": order},
            )
            amenities[amenity.icon] = amenity
        self.log(f"Amenities: {len(amenities)}.")
        return amenities

    def seed_properties(self, districts, amenities):
        catalog = data.PROPERTIES[: self.property_limit] if self.property_limit else data.PROPERTIES
        for property_data in catalog:
            latitude, longitude = property_data["coordinates"]
            prop, _ = Property.objects.update_or_create(
                slug=property_data["slug"],
                defaults={
                    **translated("title", property_data["title"]),
                    **translated("description", property_data["description"]),
                    "district": districts[(property_data["city"], property_data["district"])],
                    "address": property_data["address"],
                    "latitude": Decimal(latitude),
                    "longitude": Decimal(longitude),
                    "max_guests": property_data["guests"],
                    "bedrooms": property_data["bedrooms"],
                    "beds": property_data["beds"],
                    "bathrooms": property_data["bathrooms"],
                    "price_per_night": Decimal(property_data["price"]),
                    "cleaning_fee": Decimal(property_data["cleaning"]),
                    "is_featured": property_data["featured"],
                    "is_active": True,
                },
            )
            prop.amenities.set(amenities[icon] for icon in property_data["amenities"])
            if self.with_images and not prop.images.exists():
                title_es, title_en = property_data["title"]
                for order, image_path in enumerate(property_data["images"], start=1):
                    image = PropertyImage(
                        property=prop,
                        order=order,
                        alt_text_es=f"{title_es}, foto {order}",
                        alt_text_en=f"{title_en}, photo {order}",
                    )
                    self.attach_image(image, "image", image_path)
        self.log(f"Properties: {len(catalog)}.")

    def seed_demo_user(self):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=data.DEMO_USER["email"], defaults={"full_name": data.DEMO_USER["full_name"]}
        )
        if created:
            user.set_password(data.DEMO_USER["password"])
            user.save(update_fields=["password"])
        self.log(f"Demo guest: {data.DEMO_USER['email']} / {data.DEMO_USER['password']}")


def flush_content():
    """Remove the seeded catalog and site content. Users are kept."""
    PropertyImage.objects.all().delete()
    Property.objects.all().delete()
    District.objects.all().delete()
    City.objects.all().delete()
    Tax.objects.all().delete()
    Country.objects.all().delete()
    Amenity.objects.all().delete()
    for model in (
        FeatureSection,
        Banner,
        MenuGroup,
        ContactChannel,
        SocialLink,
        HomePage,
        SiteSettings,
    ):
        model.objects.all().delete()
