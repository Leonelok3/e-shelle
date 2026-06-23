from django.urls import path
from . import views

app_name = 'stories'

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/<int:pk>/', views.project_detail, name='detail'),
    path('projects/<int:pk>/status/', views.project_status, name='status'),
]
