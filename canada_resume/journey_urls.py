from django.urls import path
from . import views_journey as views

app_name = 'immigration97'
urlpatterns = [
    path('parcours/', views.dashboard, name='dashboard'),
    path('bienvenue/', views.onboarding, name='onboarding'),
    path('bilan/', views.assessment, name='assessment'),
    path('bilan/appliquer/', views.apply_assessment, name='apply_assessment'),
    path('dossier/', views.dossier, name='dossier'),
    path('dossier/avancement/', views.checklist_update, name='checklist_update'),
    path('brouillon/<int:exercise_id>/', views.draft, name='draft'),
]
