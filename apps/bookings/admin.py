from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from modeltranslation.admin import TranslationTabularInline

from apps.payments.admin import PaymentInline

from .emails import send_booking_confirmation
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
    readonly_fields = (
        "reference",
        "total",
        "created_at",
        "updated_at",
        "confirmed_at",
        "confirmation_sent_at",
    )
    actions = ["resend_confirmation"]
    autocomplete_fields = ("guest",)
    raw_id_fields = ("property",)
    inlines = [BookingLineInline, PaymentInline]

    @admin.display(description=_("nights"))
    def nights(self, obj):
        return obj.nights

    @admin.action(description=_("Resend the confirmation e-mail"))
    def resend_confirmation(self, request, queryset):
        """For a guest who did not receive it or deleted it. Only confirmed bookings."""
        confirmed = queryset.filter(status=Booking.Status.CONFIRMED, guest__isnull=False)
        sent = 0
        for booking in confirmed:
            Booking.objects.filter(pk=booking.pk).update(confirmation_sent_at=None)
            sent += send_booking_confirmation(booking.pk)
        self.message_user(
            request,
            ngettext("%(count)d e-mail sent.", "%(count)d e-mails sent.", sent) % {"count": sent},
            messages.SUCCESS if sent else messages.WARNING,
        )
