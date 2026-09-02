from django.urls import path

from . import views

app_name = "auto_ecole"

urlpatterns = [
    path("", views.home, name="home"),
    path("inscription/", views.register_school, name="register"),
    path("<slug:slug>/", views.school_detail, name="school_detail"),
    path("<slug:school_slug>/<slug:course_slug>/", views.course_detail, name="course_detail"),
]
