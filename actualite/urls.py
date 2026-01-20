from django.urls import path
from .views import (
    news_list,
    news_detail,
    news_by_country,
    newsletter_subscribe,
)

app_name = "actualite"

urlpatterns = [
    # Liste générale
    path("", news_list, name="list"),

    # ✅ Pages pays (URL courte SEO GEO) -> /actualite/usa/
    path("<slug:country_slug>/", news_by_country, name="by_country_short"),

    # ✅ Pages pays (URL legacy) -> /actualite/pays/usa/
    path("pays/<slug:country_slug>/", news_by_country, name="by_country"),

    # Détail article -> /actualite/article/mon-article/
    path("article/<slug:slug>/", news_detail, name="detail"),

    # Newsletter
    path("newsletter/subscribe/", newsletter_subscribe, name="newsletter_subscribe"),
]
