from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.ProfileListView.as_view(), name="list"),

    path("me/", views.my_space, name="my_space"),
    path("toggle-public/", views.toggle_public, name="toggle_public"),

    path("<int:pk>/", views.ProfileDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ProfileUpdateView.as_view(), name="edit"),
    path("<int:pk>/portfolio/add/", views.add_portfolio_item, name="add_portfolio"),

    path("avatar/", views.upload_avatar, name="upload_avatar"),

    path("me/invitations/", views.my_invitations, name="my_invitations"),
    path("me/invitations-sent/", views.recruiter_invites, name="recruiter_invites"),

    path("invite/<int:invite_id>/accept/", views.invite_accept, name="invite_accept"),
    path("invite/<int:invite_id>/decline/", views.invite_decline, name="invite_decline"),
    path("favorites/", views.favorites_list, name="favorites_list"),
    path("favorite/<int:pk>/toggle/", views.toggle_favorite, name="toggle_favorite"),

]
