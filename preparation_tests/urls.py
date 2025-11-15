from django.urls import path
from . import views

# Nom de l'application (pour les namespaces dans les templates)
app_name = "preparation_tests"

urlpatterns = [
    # =========================================================
    # 🚀 Accueil module : page d'accueil
    # =========================================================
    path("", views.home, name="home"),

    # =========================================================
    # 📝 Examens disponibles : liste des examens et détails
    # =========================================================
    path("exams/", views.exam_list, name="exam_list"),  # Liste de tous les examens
    path("exams/<slug:exam_code>/", views.exam_detail, name="exam_detail"),  # Détail d'un examen particulier

    # =========================================================
    # 🚀 Sessions : démarrage d'une session d'entraînement
    # =========================================================
    path("session/start/<slug:exam_code>/", views.start_session, name="start_session"),  # Démarrage d'une session sans section spécifique
    # Variante RESTful pour inclure la section dans l'URL (plus propre que d'utiliser ?section=)
    path(
        "session/start/<slug:exam_code>/<slug:section_code>/",
        views.start_session_with_section,
        name="start_session_with_section",
    ),

    # =========================================================
    # 🧩 Tentatives et soumissions de réponses
    # =========================================================
    path("attempt/<int:attempt_id>/", views.take_section, name="take_section"),  # Affiche la question suivante ou le résultat
    path("answer/<int:attempt_id>/<int:question_id>/", views.submit_answer, name="submit_answer"),  # Soumettre la réponse
    path("session/<int:session_id>/result/", views.session_result, name="session_result"),  # Affiche les résultats de la session

    # =========================================================
    # 🌍 Pages "tableaux de bord" par langue
    # =========================================================
    path("exams-fr/", views.french_exams, name="french_exams"),  # Tableau de bord pour les examens en français
    path("exams-en/", views.english_exams, name="english_exams"),  # Tableau de bord pour les examens en anglais
    path("exams-de/", views.german_exams, name="german_exams"),  # Tableau de bord pour les examens en allemand

    # =========================================================
    # 📝 Hubs FR (pages spécifiques pour chaque examen)
    # =========================================================
    path("fr/tef/", views.tef_hub, name="tef_hub"),  # Hub pour l'examen TEF
    path("fr/tcf/", views.tcf_hub, name="tcf_hub"),  # Hub pour l'examen TCF
    path("fr/delf-dalf/", views.delf_hub, name="delf_hub"),  # Hub pour les examens DELF/DALF

    # =========================================================
    # 📚 TEF — Pages des cours (par section)
    # =========================================================
    path("fr/tef/co/", views.tef_co, name="tef_co"),  # Cours pour la section Compréhension orale (CO)
    path("fr/tef/ce/", views.tef_ce, name="tef_ce"),  # Cours pour la section Compréhension écrite (CE)
    path("fr/tef/ee/", views.tef_ee, name="tef_ee"),  # Cours pour la section Expression écrite (EE)
    path("fr/tef/eo/", views.tef_eo, name="tef_eo"),  # Cours pour la section Expression orale (EO)
    path("prep/<str:exam_code>/session/", views.start_session, name="start_session"), # SESSION TEF COkle

    path("tef/co/", views.tef_co, name="tef_co"),
    # nouvelle url pour la session liée à une leçon
    path(
        "tef/co/lesson/<int:lesson_id>/session/",
        views.lesson_session_co,
        name="lesson_session_co",
    ),

    # ton ancien start_session peut rester (si d'autres pages l’utilisent encore)
    path(
        "prep/prep_test/session/",
        views.start_session,
        name="start_session",
    ),
]
