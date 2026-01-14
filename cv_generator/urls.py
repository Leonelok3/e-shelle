# cv_generator/urls.py
from django.urls import path
from . import views

app_name = "cv_generator"

urlpatterns = [
    # Pages
    path("", views.index, name="index"),
    path("cv/list/", views.cv_list, name="cv_list"),

    # Templates
    path("templates/", views.template_selection, name="template_selection"),
    path("templates/<int:template_id>/choose/", views.choose_template, name="choose_template"),
    path("cv/<int:cv_id>/template/change/", views.change_template, name="change_template"),

    # Wizard
    path("cv/<int:cv_id>/create/", views.create_cv, name="create_cv"),
    path("cv/<int:cv_id>/step2/", views.create_cv_step2, name="create_cv_step2"),
    path("cv/<int:cv_id>/step3/", views.create_cv_step3, name="create_cv_step3"),
    path("cv/<int:cv_id>/finalize/", views.finalize_cv, name="finalize_cv"),

    # Upload
    path("cv/<int:cv_id>/upload/", views.upload_cv, name="upload_cv"),

    # CRUD - Expériences
    path("cv/<int:cv_id>/experience/delete/<int:exp_id>/", views.delete_experience, name="delete_experience"),

    # ✅ CRUD Step 3 (match EXACT ton template)
    path("cv/<int:cv_id>/formation/delete/<int:formation_id>/", views.delete_formation, name="delete_formation"),
    path("cv/<int:cv_id>/competence/delete/<int:competence_id>/", views.delete_competence, name="delete_competence"),

    # ✅ ICI: ton template utilise delete_language (donc on le crée)
    path("cv/<int:cv_id>/language/delete/<int:lang_id>/", views.delete_language, name="delete_language"),

    # PDF
    path("cv/<int:cv_id>/export/pdf/", views.export_pdf, name="export_pdf"),

    # IA / API (si tes vues existent)
    path("cv/<int:cv_id>/ats-score/", views.ats_score, name="ats_score"),
    path("cv/<int:cv_id>/ai-summary/", views.generate_ai_summary, name="generate_ai_summary"),
    path("cv/<int:cv_id>/translate/", views.translate_summary, name="translate_summary"),
    path(
        "cv/<int:cv_id>/experience/<int:experience_id>/generate-tasks/",
        views.generate_experience_tasks,
        name="generate_experience_tasks",
    ),
    path("cv/list/", views.cv_list, name="cv_list"),
    path("cv/<int:cv_id>/edit/", views.edit_cv, name="edit_cv"),
]
