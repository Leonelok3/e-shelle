from django.urls import path
from . import views

app_name = "canada_resume"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profil/", views.edit_profile, name="edit_profile"),
    path("experiences/", views.manage_experiences, name="manage_experiences"),
    path("experiences/<int:pk>/supprimer/", views.delete_experience, name="delete_experience"),
    path("formation/", views.manage_education, name="manage_education"),
    path("formation/<int:pk>/supprimer/", views.delete_education, name="delete_education"),
    path("langues/", views.manage_languages, name="manage_languages"),
    path("langues/<int:pk>/supprimer/", views.delete_language, name="delete_language"),
    path("generer/", views.generate_resume, name="generate"),
    path("generer/<int:offer_pk>/", views.generate_resume, name="generate_for_offer"),
    path("voir/<int:pk>/", views.view_resume, name="view_resume"),
    path("telecharger/<int:pk>/docx/", views.download_resume_docx, name="download_docx"),
    path("telecharger/<int:pk>/lettre/", views.download_cover_letter_docx, name="download_lettre_docx"),
    path("api/ameliorer-description/", views.improve_description_api, name="improve_description_api"),
    path("diagnostic/", views.immigration_diagnostic, name="diagnostic"),
]
