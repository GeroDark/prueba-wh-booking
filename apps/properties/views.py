from django.views.generic import DetailView, ListView

from .forms import SearchForm
from .models import Property


class PropertySearchView(ListView):
    """Search results.

    Phase 2 lists every active property; filters and the map arrive in phase 4.
    """

    template_name = "pages/search_results.html"
    context_object_name = "properties"
    paginate_by = 12

    def get_queryset(self):
        return Property.objects.active().with_card_data()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = SearchForm(self.request.GET or None)
        return context


class PropertyDetailView(DetailView):
    """Property page.

    Phase 2 shows the essentials; gallery, booking form and map arrive in phase 5.
    """

    template_name = "pages/property_detail.html"
    context_object_name = "property"

    def get_queryset(self):
        return Property.objects.active().with_card_data().prefetch_related("amenities")
