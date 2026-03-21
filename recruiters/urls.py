from django.urls import path
from . import views

app_name = "recruiters"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profil/", views.profile_edit, name="profile_edit"),
    path("entreprise/<int:pk>/", views.public_profile, name="public_profile"),
    path("invitations/", views.my_invites, name="my_invites"),
]
