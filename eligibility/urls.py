from django.urls import path
from . import views

urlpatterns = [
    path("sessions/create/", views.create_session, name="eligibility_create_session"),
    path("sessions/<int:session_id>/answers/", views.patch_answers, name="eligibility_patch_answers"),
    path("sessions/<int:session_id>/compute_score/", views.compute_score, name="eligibility_compute_score"),
    path("sessions/<int:session_id>/result/", views.get_result, name="eligibility_get_result"),
]
