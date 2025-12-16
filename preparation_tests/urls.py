from django.urls import path
from . import views

app_name = "preparation_tests"

urlpatterns = [

    # =========================================================
    # 🏠 ACCUEIL
    # =========================================================
    path("", views.home, name="home"),

    # =========================================================
    # 📚 EXAMENS – LISTE & DÉTAILS
    # =========================================================
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<slug:exam_code>/", views.exam_detail, name="exam_detail"),

    # =========================================================
    # 🌍 HUBS PAR LANGUE
    # =========================================================
    path("exams-fr/", views.french_exams, name="french_exams"),
    # path("exams-en/", views.english_exams, name="english_exams"),
    # path("exams-de/", views.german_exams, name="german_exams"),

    # =========================================================
    # 🇫🇷 HUBS FRANÇAIS PAR EXAMEN
    # =========================================================
    path("fr/tef/", views.tef_hub, name="tef_hub"),
    path("fr/tcf/", views.tcf_hub, name="tcf_hub"),
    path("fr/delf-dalf/", views.delf_hub, name="delf_hub"),

    # =========================================================
    # 📖 TEF – COURS THÉORIQUES
    # =========================================================
    path("fr/tef/co/", views.tef_co, name="tef_co"),
    path("fr/tef/ce/", views.tef_ce, name="tef_ce"),
    path("fr/tef/ee/", views.tef_ee, name="tef_ee"),
    path("fr/tef/eo/", views.tef_eo, name="tef_eo"),

    # =========================================================
    # 📝 TEF – SESSIONS PAR LEÇON
    # =========================================================
    path(
        "tef/co/lesson/<int:lesson_id>/session/",
        views.lesson_session_co,
        name="lesson_session_co",
    ),
    path(
        "tef/ce/lesson/<int:lesson_id>/session/",
        views.lesson_session_ce,
        name="lesson_session_ce",
    ),
    path(
        "tef/ee/lesson/<int:lesson_id>/session/",
        views.lesson_session_ee,
        name="lesson_session_ee",
    ),
    path(
        "tef/eo/lesson/<int:lesson_id>/session/",
        views.lesson_session_eo,
        name="lesson_session_eo",
    ),

    # =========================================================
    # 🕒 TEF – EXAMENS BLANCS
    # =========================================================
    path(
        "tef/co/mock/",
        views.start_mock_tef_co,
        name="start_mock_tef_co",
    ),
    path(
        "fr/tef/co/examen-blanc/",
        views.tef_co_mock,
        name="tef_co_mock",
    ),

    # =========================================================
    # ✅ TCF – ENTRAÎNEMENTS & EXAMEN TYPE
    # =========================================================
    path(
        "tcf/<slug:section_code>/entrainement/",
        views.start_tcf_training,
        name="start_tcf_training",
    ),
    path(
        "tcf/examen-type/",
        views.start_tcf_full_exam,
        name="start_tcf_full_exam",
    ),

    # =========================================================
    # 🔄 SESSIONS GÉNÉRIQUES (BANQUE DE QUESTIONS)
    # =========================================================
    path(
        "session/start/<slug:exam_code>/",
        views.start_session,
        name="start_session",
    ),
    path(
        "session/start/<slug:exam_code>/<slug:section_code>/",
        views.start_session_with_section,
        name="start_session_with_section",
    ),

    # =========================================================
    # 🎓 TENTATIVES & RÉPONSES
    # =========================================================
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

    # =========================================================
    # 📊 RÉSULTATS & ANALYSES
    # =========================================================
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
        "session/<int:session_id>/skills/",
        views.session_skill_analysis,
        name="session_skill_analysis",
    ),

    # =========================================================
    # 🔁 RÉVISION & REPRISE
    # =========================================================
    path("sessions/", views.session_review, name="session_review"),
    path(
        "retry/<int:session_id>/",
        views.retry_wrong_questions,
        name="retry_wrong",
    ),
    path(
        "retry/run/<int:session_id>/",
        views.run_retry_session,
        name="run_retry_session",
    ),
    path(
        "session/<int:session_id>/retry-errors/",
        views.retry_session_errors,
        name="retry_session_errors",
    ),

    # =========================================================
    # 📊 DASHBOARD TEF (doublon conservé volontairement)
    # =========================================================
    path("dashboard/tef/", views.tef_dashboard, name="tef_dashboard"),
    path(
    "tef/co/",
    views.tef_co,
    name="tef_co",
),

    
    
]
