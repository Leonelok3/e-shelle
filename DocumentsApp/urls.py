from django.urls import path
from . import views

app_name = "DocumentsApp"

urlpatterns = [
    path('', views.documents_home, name='home'),
    path('traduction/', views.translation_view, name='translation'),
    path('compression/', views.compression_view, name='compression'),
]
