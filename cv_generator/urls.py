# cv_generator/urls.py
from django.urls import path
from . import views
from .views import translate_summary

app_name = "cv_generator"

urlpatterns = [

    # =========================
    # Pages générales
    # =========================
    path("", views.index, name="index"),
    path("cv-list/", views.cv_list, name="cv_list"),
    path("templates/", views.template_selection, name="template_selection"),
    path(
        "templates/choose/<int:template_id>/",
        views.choose_template,
        name="choose_template"
    ),

    # =========================
    # Création CV - Étapes
    # =========================
    path("cv/<int:cv_id>/", views.create_cv, name="create_cv"),          # Étape 1
    path("cv/<int:cv_id>/step2/", views.create_cv_step2, name="create_cv_step2"),  # Étape 2
    path("cv/<int:cv_id>/step3/", views.create_cv_step3, name="create_cv_step3"),  # Étape 3

    # =========================
    # Upload CV
    # =========================
    path("cv/<int:cv_id>/upload/", views.upload_cv, name="upload_cv"),

    # =========================
    # Résumé professionnel
    # =========================
    path(
        "cv/<int:cv_id>/summary/update/",
        views.update_summary,
        name="update_summary"
    ),
    path(
        "cv/<int:cv_id>/ai-summary/",
        views.generate_ai_summary,
        name="generate_ai_summary"
    ),
    path(
        "cv/<int:cv_id>/translate-summary/",
        translate_summary,
        name="translate_summary"
    ),

    # =========================
    # Expériences
    # =========================
    path(
        "cv/<int:cv_id>/experience/<int:exp_id>/delete/",
        views.delete_experience,
        name="delete_experience"
    ),
    path(
        "cv/<int:cv_id>/experience/<int:exp_id>/ai/",
        views.generate_experience_tasks,
        name="generate_experience_tasks"
    ),

    # =========================
    # Formations
    # =========================
    path(
        "cv/<int:cv_id>/education/add/",
        views.add_education,
        name="add_education"
    ),
    path(
        "cv/<int:cv_id>/education/<int:edu_id>/delete/",
        views.delete_education,
        name="delete_education"
    ),

    # =========================
    # Compétences
    # =========================
    path(
        "cv/<int:cv_id>/skill/add/",
        views.add_skill,
        name="add_skill"
    ),
    path(
        "cv/<int:cv_id>/skill/<int:skill_id>/delete/",
        views.delete_skill,
        name="delete_skill"
    ),

    # =========================
    # Langues
    # =========================
    path(
        "cv/<int:cv_id>/language/add/",
        views.add_language,
        name="add_language"
    ),
    path(
        "cv/<int:cv_id>/language/<int:lang_id>/delete/",
        views.delete_language,
        name="delete_language"
    ),

    # =========================
    # Certifications
    # =========================
    path(
        "cv/<int:cv_id>/certification/add/",
        views.add_certification,
        name="add_certification"
    ),
    path(
        "cv/<int:cv_id>/certification/<int:cert_id>/delete/",
        views.delete_certification,
        name="delete_certification"
    ),

    # =========================
    # Bénévolat
    # =========================
    path(
        "cv/<int:cv_id>/volunteer/add/",
        views.add_volunteer,
        name="add_volunteer"
    ),
    path(
        "cv/<int:cv_id>/volunteer/<int:vol_id>/delete/",
        views.delete_volunteer,
        name="delete_volunteer"
    ),

    # =========================
    # Projets
    # =========================
    path(
        "cv/<int:cv_id>/project/add/",
        views.add_project,
        name="add_project"
    ),
    path(
        "cv/<int:cv_id>/project/<int:proj_id>/delete/",
        views.delete_project,
        name="delete_project"
    ),

    # =========================
    # Loisirs
    # =========================
    path(
        "cv/<int:cv_id>/hobby/add/",
        views.add_hobby,
        name="add_hobby"
    ),
    path(
        "cv/<int:cv_id>/hobby/<int:hobby_id>/delete/",
        views.delete_hobby,
        name="delete_hobby"
    ),

    # =========================
    # ATS & Analyse
    # =========================
    path(
        "cv/<int:cv_id>/ats-score/",
        views.ats_score,
        name="ats_score"
    ),

    # =========================
    # Finalisation & Export
    # =========================
    path(
        "cv/<int:cv_id>/complete/",
        views.complete_cv,
        name="complete_cv"
    ),
    path(
        "cv/<int:cv_id>/export-pdf/",
        views.export_pdf,
        name="export_pdf"
    ),

]
