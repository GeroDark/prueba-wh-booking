from django.db import models
from django.db.models import Q
from django.utils import timezone


class BookingQuerySet(models.QuerySet):
    def blocking(self, now=None):
        """Bookings that occupy their dates: confirmed ones and holds that have not expired.

        Expiry is lazy: an expired hold stops blocking as soon as its `expires_at` passes,
        without waiting for any background job to change its status (see D08).
        """
        now = now or timezone.now()
        return self.filter(
            Q(status=self.model.Status.CONFIRMED)
            | Q(status=self.model.Status.PENDING, expires_at__gt=now)
        )

    def overlapping(self, check_in, check_out):
        """Bookings sharing at least one night with [check_in, check_out) (see D06).

        Stays are half-open intervals: the check-out day is free for the next guest,
        so a stay ending on the 15th does not collide with one starting on the 15th.
        """
        return self.filter(check_in__lt=check_out, check_out__gt=check_in)
