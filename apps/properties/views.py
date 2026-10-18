from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import ngettext
from django.views.generic import DetailView, ListView

from apps.core.templatetags.formatting import money

from .forms import SearchForm
from .models import Property


def map_marker(prop):
    """Data for one map pin. Coordinates are the public, rounded ones (see D27)."""
    lat, lng = prop.public_coordinates
    cover = prop.cover_image
    return {
        "id": prop.pk,
        "title": prop.title,
        "lat": lat,
        "lng": lng,
        "price": money(prop.price_per_night),
        "location": f"{prop.district.name}, {prop.city.name}",
        "url": reverse("properties:detail", args=[prop.slug]),
        "image": cover.image.url if cover else "",
    }


class PropertySearchView(ListView):
    """Search results: filters from the search bar, a paginated list and a map of the same page."""

    template_name = "pages/search_results.html"
    context_object_name = "properties"
    paginate_by = 10

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.form = SearchForm(request.GET or None)
        self.filters = self.get_filters()

    def get_filters(self):
        """Valid filters only: an invalid field shows its error but does not block the others."""
        if not self.form.is_bound:
            return {}
        self.form.is_valid()
        return {name: value for name, value in self.form.cleaned_data.items() if value}

    def get_queryset(self):
        return Property.objects.active().search(**self.filters).with_card_data()

    def get_summary(self):
        """Readable active filters, e.g. ["Lima", "10 nov – 14 nov 2026", "2 huéspedes"]."""
        filters = self.filters
        parts = []
        place = filters.get("district") or filters.get("city") or filters.get("country")
        if filters.get("district"):
            parts.append(f"{filters['district'].name}, {filters['district'].city.name}")
        elif place:
            parts.append(place.name)
        if filters.get("check_in") and filters.get("check_out"):
            arrival = date_format(filters["check_in"], "j M")
            departure = date_format(filters["check_out"], "j M Y")
            parts.append(f"{arrival} – {departure}")
        if filters.get("guests"):
            guests = filters["guests"]
            parts.append(
                ngettext("%(count)d guest", "%(count)d guests", guests) % {"count": guests}
            )
        return parts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            search_form=self.form,
            filters=self.filters,
            summary=self.get_summary(),
            map_markers=[
                map_marker(prop) for prop in context["properties"] if prop.public_coordinates
            ],
        )
        return context


class PropertyDetailView(DetailView):
    """Property page.

    Phase 2 shows the essentials; gallery, booking form and map arrive in phase 5.
    """

    template_name = "pages/property_detail.html"
    context_object_name = "property"

    def get_queryset(self):
        return Property.objects.active().with_card_data().prefetch_related("amenities")
