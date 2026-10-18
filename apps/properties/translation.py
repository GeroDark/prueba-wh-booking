from modeltranslation.translator import TranslationOptions, register

from .models import Amenity, City, Country, District, Property, PropertyImage, Tax


@register(Country)
class CountryTranslation(TranslationOptions):
    fields = ("name",)
    required_languages = ("es",)


@register(City)
class CityTranslation(TranslationOptions):
    fields = ("name",)
    required_languages = ("es",)


@register(District)
class DistrictTranslation(TranslationOptions):
    fields = ("name",)
    required_languages = ("es",)


@register(Amenity)
class AmenityTranslation(TranslationOptions):
    fields = ("name",)
    required_languages = ("es",)


@register(Property)
class PropertyTranslation(TranslationOptions):
    fields = ("title", "description")
    required_languages = ("es",)


@register(PropertyImage)
class PropertyImageTranslation(TranslationOptions):
    fields = ("alt_text",)
    required_languages = ("es",)


@register(Tax)
class TaxTranslation(TranslationOptions):
    fields = ("name",)
    required_languages = ("es",)
