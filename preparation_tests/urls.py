from django.urls import path
from . import views

app_name = "preparation_tests"

urlpatterns = [

    # =====================================================
    # 🏠 ACCUEIL GÉNÉRAL
    # =====================================================
    path("", views.home, name="home"),

    # =====================================================
    # 📚 LISTE DES EXAMENS
    # =====================================================
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<slug:exam_code>/", views.exam_detail, name="exam_detail"),
    path("exams-fr/", views.french_exams, name="french_exams"),

    # =====================================================
    # 🇫🇷 HUBS FR (POINTS D’ENTRÉE)
    # =====================================================
    path("fr/tef/", views.tef_hub, name="tef_hub"),
    path("fr/tcf/", views.tcf_hub, name="tcf_hub"),
    path("fr/delf/", views.delf_hub, name="delf_hub"),
    path("fr/dalf/", views.delf_hub, name="dalf_hub"),  # même hub (CECR universel)

    # =====================================================
    # 📘 SECTIONS DE COURS (MOTEUR UNIQUE)
    # EX : /prep/fr/tef/co/
    # EX : /prep/fr/tcf/co/
    # EX : /prep/fr/delf/co/
    # =====================================================
    path(
        "fr/<slug:exam_code>/<slug:section>/",
        views.course_section,
        name="course_section",
    ),

    # =====================================================
    # 📖 LEÇON + EXERCICES
    # EX : /prep/fr/tef/co/lesson/12/
    # =====================================================
    path(
        "fr/<slug:exam_code>/<slug:section>/lesson/<int:lesson_id>/",
        views.lesson_session,
        name="lesson_session",
    ),

    # =====================================================
    # 📝 EXAMEN BLANC (NOUVEAU MOTEUR)
    # =====================================================
    path(
        "mock/<slug:exam_code>/<slug:section_code>/start/",
        views.start_mock_exam,
        name="start_mock_exam",
    ),
    path(
        "mock/<int:session_id>/",
        views.mock_exam_session,
        name="mock_exam_session",
    ),
    path(
        "mock/<int:session_id>/results/",
        views.mock_exam_results,
        name="mock_exam_results",
    ),

    # =====================================================
    # 🕒 ANCIEN MOTEUR (SESSIONS)
    # =====================================================
    path(
        "session/start/<slug:exam_code>/",
        views.start_session,
        name="start_session",
    ),
    path(
        "session/start/<slug:exam_code>/<slug:section>/",
        views.start_session_with_section,
        name="start_session_with_section",
    ),
    path(
        "attempt/<int:attempt_id>/",
        views.take_section,
        name="take_section",
    ),
    path(
        "answer/<int:attempt_id>/<int:question_id>/",
        views.submit_answer,
        name="submit_answer",
    ),

    # =====================================================
    # 📊 RÉSULTATS & CORRECTIONS
    # =====================================================
    path(
        "session/<int:session_id>/result/",
        views.session_result,
        name="session_result",
    ),
    path(
        "session/<int:session_id>/correction/",
        views.session_correction,
        name="session_correction",
    ),
    path(
        "session/<int:session_id>/retry-errors/",
        views.retry_session_errors,
        name="retry_session_errors",
    ),

    # =====================================================
    # 📜 CERTIFICATS
    # =====================================================
    path(
        "certificate/<slug:exam_code>/<slug:level>/",
        views.download_certificate,
        name="download_certificate",
    ),
    path(
        "certificates/verify/<slug:public_id>/",
        views.verify_certificate,
        name="verify_certificate",
    ),

    # =====================================================
    # 📊 DASHBOARD & COACH IA
    # =====================================================
    path(
        "dashboard/",
        views.dashboard_global,
        name="dashboard_global",
    ),
    path(
        "coach-ia/",
        views.coach_ai_history,
        name="coach_ai_history",
    ),
    path(
        "coach-ia/pdf/<int:report_id>/",
        views.coach_ai_pdf,
        name="coach_ai_pdf",
    ),
    path(
        "sessions/",
        views.session_review,
        name="session_review",
    ),

    # =====================================================
    # 📅 PLAN D’ÉTUDE
    # =====================================================
    path(
        "<slug:exam_code>/study-plan/",
        views.study_plan_view,
        name="study_plan",
    ),
    path(
        "<slug:exam_code>/study-plan/complete/",
        views.complete_study_day,
        name="complete_study_day",
    ),
]
