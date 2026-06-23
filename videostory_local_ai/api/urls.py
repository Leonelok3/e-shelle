from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('projects/', views.project_list_create, name='project-list-create'),
    path('projects/<int:pk>/', views.project_detail, name='project-detail'),
    path('projects/<int:pk>/status/', views.project_status, name='project-status'),
]