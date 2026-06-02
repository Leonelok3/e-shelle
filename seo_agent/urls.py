from django.urls import path

from . import views

app_name = "seo_agent"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("correction/", views.correction_plan, name="correction_plan"),
    path("articles/", views.article_index, name="article_index"),
    path("articles/marche-numerique-afrique-2025/", views.article_marche_numerique, name="article_marche_numerique"),
]
