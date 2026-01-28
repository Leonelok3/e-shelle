from django.urls import path
from .views import protection_protocol_view

app_name = "legal"

urlpatterns = [
    path(
        "protocole-protection/",
        protection_protocol_view,
        name="protection_protocol"
    ),
]
