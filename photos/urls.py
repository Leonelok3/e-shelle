from django.urls import path
from . import views

app_name = "photos"

urlpatterns = [
    path("", views.index, name="index"),                 # /visa-photo/
    path("submit/", views.submit, name="submit"),        # /visa-photo/submit/
    path("result/<int:pk>/", views.result, name="result"),
    path("download/<int:pk>/", views.download, name="download"),
    path("pay/<int:pk>/", views.pay, name="pay"),
]

