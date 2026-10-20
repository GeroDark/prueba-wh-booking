from django.db import models
from django.db.models import Exists, OuterRef


class PropertyQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def featured(self):
        return self.filter(is_featured=True)

    def with_card_data(self):
        """Everything a property card renders, in a fixed number of queries."""
        from .models import PropertyImage

        return self.select_related("district__city__country").prefetch_related(
            models.Prefetch("images", queryset=PropertyImage.objects.order_by("order", "id"))
        )

    def for_guests(self, guests):
        return self.filter(max_guests__gte=guests)

    def available(self, check_in, check_out, now=None):
        """Properties with no blocking booking (confirmed or live hold) in [check_in, check_out)."""
        from apps.bookings.models import Booking

        taken = (
            Booking.objects.blocking(now)
            .overlapping(check_in, check_out)
            .filter(property=OuterRef("pk"))
        )
        return self.exclude(Exists(taken))

    def search(
        self,
        *,
        country=None,
        city=None,
        district=None,
        check_in=None,
        check_out=None,
        guests=None,
    ):
        """Apply the search bar filters; every argument is optional."""
        queryset = self
        if country:
            queryset = queryset.filter(district__city__country=country)
        if city:
            queryset = queryset.filter(district__city=city)
        if district:
            queryset = queryset.filter(district=district)
        if guests:
            queryset = queryset.for_guests(guests)
        if check_in and check_out:
            from .models import cities_where_arrival_is_open

            # Only where the arrival is not already past in the city's own date (D09), exactly
            # as the booking will check it.
            queryset = queryset.filter(
                district__city__in=cities_where_arrival_is_open(check_in)
            ).available(check_in, check_out)
        return queryset
