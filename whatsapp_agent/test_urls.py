from django.urls import include, path

urlpatterns = [path("whatsapp/", include("whatsapp_agent.urls"))]

