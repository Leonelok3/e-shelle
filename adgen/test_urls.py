"""Unrelated navigation destinations are stubs; Studio routes are real."""
from django.urls import path, include
from django.http import HttpResponse

def stub(request):
    return HttpResponse("Navigation destination")

urlpatterns = [
    path("pub/", include("adgen.urls")),
    path("audio-studio/", include("audio_studio.urls")),
    path("accounts/", include(([path(f"{name}/", stub, name=name) for name in ("upgrade", "login", "logout")], "accounts"))),
    path("chat/", include(([path("", stub, name="home")], "chat"))),
    path("assistant/", include(([path("", stub, name="chat")], "eshelle_ai"))),
]
