from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("simplo.marketplace.urls", namespace="simplo_marketplace")),
    path("accounts/", include("simplo.accounts.urls", namespace="simplo_accounts")),
    path("transport/", include("simplo.transport.urls", namespace="simplo_transport")),
    path("livraison/", include("simplo.livraison.urls", namespace="simplo_livraison")),
    path("courses/", include("simplo.courses.urls", namespace="simplo_courses")),
]
