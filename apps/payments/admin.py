from django.contrib import admin

from .models import Payment


class PaymentInline(admin.TabularInline):
    """Payment attempts of a booking, shown on the booking page. A record, never editable."""

    model = Payment
    extra = 0
    can_delete = False
    fields = (
        "created_at",
        "status",
        "amount",
        "currency",
        "card_brand",
        "card_last4",
        "decline_code",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "status",
        "amount",
        "currency",
        "card_brand",
        "card_last4",
        "created_at",
    )
    list_filter = ("status", "card_brand")
    list_select_related = ("booking",)
    search_fields = ("booking__reference", "gateway_reference")
    readonly_fields = [field.name for field in Payment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
