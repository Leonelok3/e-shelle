from django.urls import path
from . import views

app_name = 'ads'

urlpatterns = [
    # Support both /ads/project/ and /ads/projects/ (project/ used in some links)
    path('project/', views.project_list, name='project_index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create-ad/', views.create_ad, name='create_ad'),
    path('projects/', views.project_list, name='project_list'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('project/<int:pk>/start/', views.start_render, name='start_render'),
]
