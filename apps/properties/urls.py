from django.urls import path

from .views import PropertyDetailView, PropertySearchView

app_name = "properties"

urlpatterns = [
    path("search/", PropertySearchView.as_view(), name="search"),
    path("properties/<slug:slug>/", PropertyDetailView.as_view(), name="detail"),
]
