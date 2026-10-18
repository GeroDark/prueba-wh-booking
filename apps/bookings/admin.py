from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationTabularInline

from apps.payments.admin import PaymentInline

from .models import Booking, BookingLine


class BookingLineInline(TranslationTabularInline):
    """Price lines are a frozen snapshot: visible, never editable."""

    model = BookingLine
    extra = 0
    can_delete = False
    fields = ("kind", "label", "amount")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "property",
        "guest",
        "check_in",
        "check_out",
        "nights",
        "total",
        "status",
    )
    list_filter = ("status", "property__district__city")
    list_select_related = ("property", "guest")
    search_fields = ("reference", "guest__email", "property__title_es")
    date_hierarchy = "check_in"
    readonly_fields = ("reference", "total", "created_at", "updated_at", "confirmed_at")
    autocomplete_fields = ("guest",)
    raw_id_fields = ("property",)
    inlines = [BookingLineInline, PaymentInline]

    @admin.display(description=_("nights"))
    def nights(self, obj):
        return obj.nights
