from django.urls import path
from . import views

app_name = "preparation_tests"

urlpatterns = [
    # =========================================================
    # Accueil
    # =========================================================
    path("", views.home, name="home"),

    # =========================================================
    # Examens disponibles
    # =========================================================
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<slug:exam_code>/", views.exam_detail, name="exam_detail"),

    # =========================================================
    # Sessions génériques (banque de questions)
    # =========================================================
    path("session/start/<slug:exam_code>/", views.start_session, name="start_session"),
    path(
        "session/start/<slug:exam_code>/<slug:section_code>/",
        views.start_session_with_section,
        name="start_session_with_section",
    ),

    # Tentatives
    path("attempt/<int:attempt_id>/", views.take_section, name="take_section"),
    path("answer/<int:attempt_id>/<int:question_id>/", views.submit_answer, name="submit_answer"),
    path("session/<int:session_id>/result/", views.session_result, name="session_result"),

    # =========================================================
    # Pages hubs
    # =========================================================
    path("exams-fr/", views.french_exams, name="french_exams"),
    path("exams-en/", views.english_exams, name="english_exams"),
    path("exams-de/", views.german_exams, name="german_exams"),

    # =========================================================
    # Hubs FR par examen
    # =========================================================
    path("fr/tef/", views.tef_hub, name="tef_hub"),
    path("fr/tcf/", views.tcf_hub, name="tcf_hub"),
    path("fr/delf-dalf/", views.delf_hub, name="delf_hub"),

    # =========================================================
    # TEF — Cours (sections)
    # =========================================================
    path("fr/tef/co/", views.tef_co, name="tef_co"),
    path("fr/tef/ce/", views.tef_ce, name="tef_ce"),
    path("fr/tef/ee/", views.tef_ee, name="tef_ee"),
    path("fr/tef/eo/", views.tef_eo, name="tef_eo"),

    # =========================================================
    # Session TEF CO (par leçon)
    # =========================================================
    path(
        "tef/co/lesson/<int:lesson_id>/session/",
        views.lesson_session_co,
        name="lesson_session_co",
    ),

    # =========================================================
    # Mode Examen CO (NOUVEAU)
    # =========================================================
    path(
        "tef/co/mock/",
        views.start_mock_tef_co,
        name="start_mock_tef_co",
    ),

    ###### partie CE 

        # Session TEF CE (par leçon)
    path(
        "tef/ce/lesson/<int:lesson_id>/session/",
        views.lesson_session_ce,
        name="lesson_session_ce",
    ),

   

]
