from django.urls import path
from . import views

app_name = 'visaetude'  # important

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),

    path('countries/', views.countries_list, name='countries_list'),
    path('country/<str:country_code>/', views.country_guide, name='country_guide'),

    path('checklist/<str:country_code>/', views.checklist, name='checklist'),

    # ✅ Correction ici : on renomme pour correspondre aux templates
    path(
        'checklist/item/<int:item_id>/update/',
        views.update_checklist_item,
        name='update_checklist_item'
    ),
]
