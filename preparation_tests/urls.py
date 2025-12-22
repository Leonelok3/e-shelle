from django.urls import path
from . import views

app_name = "preparation_tests"

urlpatterns = [

    # =========================
    # ACCUEIL / HUBS
    # =========================
    path("", views.home, name="home"),
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<slug:exam_code>/", views.exam_detail, name="exam_detail"),
    path("exams-fr/", views.french_exams, name="french_exams"),

    path("fr/tef/", views.tef_hub, name="tef_hub"),
    path("fr/tcf/", views.tcf_hub, name="tcf_hub"),
    path("fr/delf-dalf/", views.delf_hub, name="delf_hub"),

    # =========================
    # COURS / LEÇONS
    # =========================
    path(
        "fr/<str:exam_code>/<str:section>/",
        views.course_section,
        name="course_section",
    ),
    path(
        "<str:exam_code>/<str:section>/lesson/<int:lesson_id>/",
        views.lesson_session,
        name="lesson_session",
    ),

    # =========================
    # EXAMEN BLANC (NOUVEAU MOTEUR)
    # =========================
    path(
        "prep/<slug:exam_code>/<slug:section_code>/mock/start/",
        views.start_mock_exam,
        name="start_mock_exam",
    ),
    path(
        "prep/mock/<int:session_id>/",
        views.mock_exam_session,
        name="mock_exam_session",
    ),
    path(
        "prep/mock/<int:session_id>/results/",
        views.mock_exam_results,
        name="mock_exam_results",
    ),

    # =========================
    # ANCIEN MOTEUR (CONSERVÉ)
    # =========================
    path("session/start/<slug:exam_code>/", views.start_session, name="start_session"),
    path(
        "session/start/<slug:exam_code>/<slug:section>/",
        views.start_session_with_section,
        name="start_session_with_section",
    ),
    path("attempt/<int:attempt_id>/", views.take_section, name="take_section"),
    path(
        "answer/<int:attempt_id>/<int:question_id>/",
        views.submit_answer,
        name="submit_answer",
    ),

    # =========================
    # RÉSULTATS
    # =========================
    path(
        "session/<int:session_id>/result/",
        views.session_result,
        name="session_result",
    ),

    # =========================
    # CERTIFICAT
    # =========================
    path(
        "certificate/<str:exam_code>/<str:level>/",
        views.download_certificate,
        name="download_certificate",
    ),

    # =========================
    # DASHBOARD
    # =========================
    path("dashboard/tef/", views.tef_dashboard, name="tef_dashboard"),
    path(
        "certificates/<str:public_id>/",
        views.verify_certificate,
        name="verify_certificate",
    ),

    path("coach-ia/", views.coach_ai_history, name="coach_ai_history"),
    path("coach-ia/pdf/<int:report_id>/", views.coach_ai_pdf, name="coach_ai_pdf"),
    path("sessions/", views.session_review, name="session_review"),

    

    path(
    "prep/<slug:exam_code>/study-plan/",
    views.study_plan_view,
    name="study_plan",
),

    path(
    "prep/<slug:exam_code>/study-plan/complete/",
    views.complete_study_day,
    name="complete_study_day",
),

    path(
    "certificates/verify/<str:public_id>/",
    views.verify_certificate,
    name="verify_certificate",
),

    path(
    "dashboard/",
    views.dashboard_global,
    name="dashboard_global",
),

]
