from django.urls import path
from . import views

app_name = "english_tests"

urlpatterns = [
    path("", views.english_hub, name="english_hub"),
    path("ielts/", views.ielts_hub, name="ielts_hub"),
    path("toefl/", views.toefl_hub, name="toefl_hub"),
    path("toeic/", views.toeic_hub, name="toeic_hub"),
    path("", views.exam_list, name="exam_list"),  # /prep/en/

]
