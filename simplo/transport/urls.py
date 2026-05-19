from django.urls import path

from simplo.marketplace.views import provider_list

app_name = "simplo_transport"

urlpatterns = [
    path("", provider_list, name="providers"),
]
