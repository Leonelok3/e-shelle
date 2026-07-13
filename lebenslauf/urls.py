from django.urls import path
from . import views

app_name = "lebenslauf"

urlpatterns = [
    path("",                              views.dashboard,           name="dashboard"),
    path("profil/",                       views.edit_profile,        name="edit_profile"),
    path("experiences/",                  views.manage_experiences,  name="manage_experiences"),
    path("experiences/<int:pk>/supprimer/", views.delete_experience,  name="delete_experience"),
    path("formation/",                    views.manage_education,    name="manage_education"),
    path("langues/",                      views.manage_languages,    name="manage_languages"),
    path("generer/",                      views.generate_lebenslauf, name="generate"),
    path("generer/<int:offer_pk>/",       views.generate_lebenslauf, name="generate_for_offer"),
    path("voir/<int:pk>/",               views.view_lebenslauf,     name="view_lebenslauf"),
    path("telecharger/<int:pk>/",        views.download_lebenslauf, name="download"),
    path("telecharger/<int:pk>/docx/",   views.download_lebenslauf_docx, name="download_docx"),
    path("telecharger/<int:pk>/anschreiben/", views.download_anschreiben_docx, name="download_anschreiben_docx"),
]
