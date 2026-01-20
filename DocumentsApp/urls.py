from django.urls import path
from . import views

app_name = "DocumentsApp"

urlpatterns = [
    path("", views.documents_home, name="home"),
    path("traduction/", views.translation, name="translation"),
    path("traduction/resultat/<int:pk>/", views.translation_result, name="translation_result"),
    path("compression/", views.compression, name="compression"),
    path("conversion/", views.conversion, name="conversion"),
]
