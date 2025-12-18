from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('', views.ProfileListView.as_view(), name='list'),
    path('mon-espace/', views.my_space, name='my_space'),   # 👈 NOUVEAU
    path('create/', views.ProfileCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ProfileDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProfileUpdateView.as_view(), name='edit'),
    path('<int:pk>/portfolio/add/', views.add_portfolio_item, name='add_portfolio'),
    path("avatar/", views.upload_avatar, name="upload_avatar"),
    path("me/avatar/", views.upload_avatar, name="avatar"),
    path("me/", views.my_space, name="me"),
    path("avatar/", views.upload_avatar, name="avatar"),
    path("my-space/", views.my_space, name="my_space"),



]
