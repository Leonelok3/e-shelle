from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('', views.ProfileListView.as_view(), name='list'),
    path('create/', views.ProfileCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ProfileDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProfileUpdateView.as_view(), name='edit'),
    path('<int:pk>/portfolio/add/', views.add_portfolio_item, name='add_portfolio'),
]