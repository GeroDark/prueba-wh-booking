from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline

from apps.core.admin import image_thumbnail

from .models import Amenity, City, Country, District, Property, PropertyImage, Tax


class TaxInline(TranslationTabularInline):
    model = Tax
    extra = 0


@admin.register(Country)
class CountryAdmin(TranslationAdmin):
    list_display = ("name", "code", "thumbnail", "order", "is_active")
    list_editable = ("order", "is_active")
    readonly_fields = ("thumbnail",)
    prepopulated_fields = {"slug": ("name_es",)}
    inlines = [TaxInline]

    @admin.display(description=_("image"))
    def thumbnail(self, obj):
        return image_thumbnail(obj.image)


class DistrictInline(TranslationTabularInline):
    model = District
    extra = 0
    prepopulated_fields = {"slug": ("name_es",)}


@admin.register(City)
class CityAdmin(TranslationAdmin):
    list_display = ("name", "country", "timezone", "is_active")
    list_filter = ("country",)
    list_select_related = ("country",)
    search_fields = ("name_es", "name_en")
    prepopulated_fields = {"slug": ("name_es",)}
    inlines = [DistrictInline]


@admin.register(District)
class DistrictAdmin(TranslationAdmin):
    """Registered for the property form autocomplete; districts are edited inside their city."""

    search_fields = ("name_es", "name_en", "city__name_es")
    list_display = ("name", "city")
    list_select_related = ("city",)

    def has_module_permission(self, request):
        return False


@admin.register(Amenity)
class AmenityAdmin(TranslationAdmin):
    list_display = ("name", "icon", "order")
    list_editable = ("order",)


class PropertyImageInline(TranslationTabularInline):
    model = PropertyImage
    extra = 1
    fields = ("image", "thumbnail", "alt_text", "order")
    readonly_fields = ("thumbnail",)

    @admin.display(description=_("preview"))
    def thumbnail(self, obj):
        return image_thumbnail(obj.image)


@admin.register(Property)
class PropertyAdmin(TranslationAdmin):
    list_display = (
        "title",
        "district",
        "max_guests",
        "price_per_night",
        "image_count",
        "is_featured",
        "is_active",
    )
    list_editable = ("is_featured", "is_active")
    list_filter = ("is_active", "is_featured", "district__city__country", "district__city")
    list_select_related = ("district__city",)
    search_fields = ("title_es", "title_en", "address", "district__name_es")
    prepopulated_fields = {"slug": ("title_es",)}
    autocomplete_fields = ("district",)
    filter_horizontal = ("amenities",)
    inlines = [PropertyImageInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "description")}),
        (_("Location"), {"fields": ("district", "address", ("latitude", "longitude"))}),
        (_("Capacity"), {"fields": (("max_guests", "bedrooms", "beds", "bathrooms"),)}),
        (_("Pricing"), {"fields": (("price_per_night", "cleaning_fee"),)}),
        (_("Amenities"), {"fields": ("amenities",)}),
        (_("Visibility"), {"fields": (("is_featured", "is_active"),)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_image_count=Count("images"))

    @admin.display(description=_("photos"), ordering="_image_count")
    def image_count(self, obj):
        return obj._image_count
