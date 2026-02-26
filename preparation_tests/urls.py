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
    path("exam/<str:exam_code>/", views.exam_detail, name="exam_detail"),

    # =====================================================
    # 🇫🇷 HUBS EXAMENS FRANÇAIS
    # =====================================================
    path("fr/", views.french_exams, name="french_exams"),
    path("fr/tef/", views.tef_hub, name="tef_hub"),
    path("fr/tcf/", views.tcf_hub, name="tcf_hub"),
    path("fr/delf/", views.delf_hub, name="delf_hub"),
    path("fr/dalf/", views.delf_hub, name="dalf_hub"),

    # =====================================================
    # 🎧 HUB CO (Compréhension Orale) - CECR
    # =====================================================
    path("fr/co/", views.co_hub, name="co_hub"),
    path("fr/co/<str:level>/", views.co_by_level, name="co_by_level"),

    # =====================================================
    # 📖 HUB CE (Compréhension Écrite) - CECR
    # =====================================================
    path("fr/ce/", views.ce_hub, name="ce_hub"),
    path("fr/ce/<str:level>/", views.ce_by_level, name="ce_by_level"),

    # =====================================================
    # 📝 EXAMEN BLANC (MOCK)
    # =====================================================
    path(
        "mock/<str:exam_code>/<str:section_code>/start/",
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
    # 🕒 SESSIONS (ANCIEN MOTEUR)
    # =====================================================
    path(
        "start/<str:exam_code>/",
        views.start_session,
        name="start_session",
    ),
    path(
        "start/<str:exam_code>/<str:section>/",
        views.start_session_with_section,
        name="start_session_with_section",
    ),
    path(
        "section/<int:attempt_id>/",
        views.take_section,
        name="take_section",
    ),
    path(
        "section/<int:attempt_id>/submit/<int:question_id>/",
        views.submit_answer,
        name="submit_answer",
    ),

    # =====================================================
    # 📊 RÉSULTATS & CORRECTIONS
    # =====================================================
    path(
        "result/<int:session_id>/",
        views.session_result,
        name="session_result",
    ),
    path(
        "correction/<int:session_id>/",
        views.session_correction,
        name="session_correction",
    ),
    path(
        "retry/<int:session_id>/",
        views.retry_session_errors,
        name="retry_session_errors",
    ),

    # =====================================================
    # 📜 CERTIFICATS
    # =====================================================
    path(
        "certificate/<str:exam_code>/<str:level>/download/",
        views.download_certificate,
        name="download_certificate",
    ),
    path(
        "certificate/verify/<str:public_id>/",
        views.verify_certificate,
        name="verify_certificate",
    ),

    # =====================================================
    # 📊 DASHBOARD & COACH IA
    # =====================================================
    path("dashboard/", views.dashboard_global, name="dashboard_global"),
    path("coach/history/", views.coach_ai_history, name="coach_ai_history"),
    path("coach/pdf/<int:report_id>/", views.coach_ai_pdf, name="coach_ai_pdf"),
    path("review/", views.session_review, name="session_review"),

    # =====================================================
    # 📅 PLAN D'ÉTUDE
    # =====================================================
    path(
        "study-plan/<str:exam_code>/",
        views.study_plan_view,
        name="study_plan",
    ),
    path(
        "study-plan/<str:exam_code>/complete/",
        views.complete_study_day,
        name="complete_study_day",
    ),

    # =====================================================
    # 🔄 API PROGRESSION EXERCICES
    # =====================================================
    path(
        "api/exercise-progress/",
        views.exercise_progress,
        name="exercise_progress",
    ),
    # Alias sans préfixe api/ pour compatibilité JS (fetch /prep/exercise-progress/)
    path(
        "exercise-progress/",
        views.exercise_progress,
    ),

    # =====================================================
    # 📘 SECTIONS DE COURS PAR EXAMEN — ROUTES GÉNÉRIQUES
    # ⚠️ OBLIGATOIREMENT EN DERNIER : <str:...> capture tout.
    # Toute route fixe placée après serait inaccessible.
    # =====================================================
    path(
        "<str:exam_code>/<str:section>/lesson/<int:lesson_id>/",
        views.lesson_session,
        name="lesson_session",
    ),
    path(
        "<str:exam_code>/<str:section>/",
        views.course_section,
        name="course_section",
    ),
]