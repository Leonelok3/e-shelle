from django.urls import path
from .views import (
    HomeView, GeneratorView, PdfDownloadView,
    LetterListView, LetterDetailView
)

app_name = 'motivation_letter'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('generator/', GeneratorView.as_view(), name='generator'),
    path('generator/pdf/', PdfDownloadView.as_view(), name='download_pdf'),
    path('letters/', LetterListView.as_view(), name='letter_list'),
    path('letters/<int:pk>/', LetterDetailView.as_view(), name='letter_detail'),
]
