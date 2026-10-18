from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "property", "guest", "check_in", "check_out", "nights", "status")
    list_filter = ("status", "property__district__city")
    list_select_related = ("property", "guest")
    search_fields = ("reference", "guest__email", "property__title_es")
    date_hierarchy = "check_in"
    readonly_fields = ("reference", "created_at", "updated_at", "confirmed_at")
    autocomplete_fields = ("guest",)
    raw_id_fields = ("property",)

    @admin.display(description=_("nights"))
    def nights(self, obj):
        return obj.nights
