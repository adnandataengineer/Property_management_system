from django.urls import path
from .views import PropertyListView, PropertyDetailView, booking_request_create

app_name = "properties"

urlpatterns = [
    path("", PropertyListView.as_view(), name="list"),
    path("<int:pk>/", PropertyDetailView.as_view(), name="detail"),
    path("<int:pk>/book/", booking_request_create, name="book"),
]
