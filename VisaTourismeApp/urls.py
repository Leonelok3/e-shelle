from django.urls import path
from . import views

app_name = 'visa_tourisme'

urlpatterns = [
    # Page d’accueil du module Visa Tourisme
    path('', views.visa_tourisme_home, name='home'),

    # Assistant (formulaire + analyse)
    path('assistant/', views.visa_tourisme_assistant, name='assistant'),

    # Coach IA (chat autour d’un plan de visa)
    path('coach/', views.visa_tourisme_coach, name='coach'),

    # Historique conseiller
    path('historique/', views.visa_tourisme_history, name='historique'),

    # Export PDF d’une analyse
    path('pdf/<int:pk>/', views.visa_tourisme_pdf, name='pdf'),
    path('result/<int:pk>/', views.visa_tourisme_result, name='result'),
]
