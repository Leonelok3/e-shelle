from django.urls import path
from . import views

app_name = "germany_opportunities"

urlpatterns = [
    path("",                       views.catalogue,       name="catalogue"),
    path("offre/<int:pk>/",        views.offer_detail,    name="offer_detail"),
    path("offre/<int:pk>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("offre/<int:pk>/applied/",  views.mark_applied,    name="mark_applied"),
    path("mes-favoris/",           views.my_bookmarks,    name="my_bookmarks"),
]
