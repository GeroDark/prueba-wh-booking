from django.db import models


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
