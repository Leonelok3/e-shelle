# preparation_tests/urls.py
from django.urls import path
from . import views

app_name = "preparation_tests"

urlpatterns = [
    # Accueil du module (déjà présent — conservé)
    path("", views.home, name="home"),

    # Nouvelles routes (MVP)
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<slug:exam_code>/", views.exam_detail, name="exam_detail"),

    path("session/start/<slug:exam_code>/", views.start_session, name="start_session"),
    path("attempt/<int:attempt_id>/", views.take_section, name="take_section"),
    path("answer/<int:attempt_id>/<int:question_id>/", views.submit_answer, name="submit_answer"),

    path("session/<int:session_id>/result/", views.session_result, name="session_result"),
  
    path("exams-fr/", views.french_exams, name="french_exams"),   # page dédiée aux examens FR

    # Hubs d'examens Français
    path("fr/tef/", views.tef_hub, name="tef_hub"),
    path("fr/tcf/", views.tcf_hub, name="tcf_hub"),
    path("fr/delf-dalf/", views.delf_hub, name="delf_hub"),

    path("exams-en/", views.english_exams, name="english_exams"), # page dediée aux examens ANG
    path("exams-de/", views.german_exams, name="german_exams"), # page dediee aux examens allemand DE



]
