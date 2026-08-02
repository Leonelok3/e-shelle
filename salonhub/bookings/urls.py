from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("<slug:slug>/creneaux/", views.available_slots, name="available_slots"),
    path("<slug:slug>/reserver/", views.create_appointment, name="create_appointment"),
]
