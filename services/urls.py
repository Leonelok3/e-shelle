"""services/urls.py"""
from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "services"

urlpatterns = [
    path("",                views.index,         name="index"),
    path("portfolio/",      views.portfolio,     name="portfolio"),
    path("configurateur/",  views.configurateur, name="configurateur"),
    path("contact/",        views.contact,       name="contact"),
    path(
        "whatsapp-business/",
        TemplateView.as_view(template_name="services/whatsapp-business.html"),
        name="whatsapp-business",
    ),
    path("devis/",          views.devis,         name="devis"),
]
