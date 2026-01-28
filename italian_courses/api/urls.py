from django.urls import path

from . import views

app_name = "italian_courses_api"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("categories/", views.categories, name="categories"),
    path("lessons/", views.lessons, name="lessons"),
]
