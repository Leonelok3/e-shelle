from django.http import HttpResponse
from django.urls import include, path

def stub(request):
    return HttpResponse("Navigation")

urlpatterns = [
    path("njangi/", include("njangi.urls")),
    path("accounts/", include(([path(f"{name}/", stub, name=name) for name in ("login", "logout", "profile", "upgrade")], "accounts"))),
    path("", stub, name="home"),
]
