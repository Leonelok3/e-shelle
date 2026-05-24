from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_view, name="home"),
    path("send/", views.send_message, name="send_message"),
    path("clear/", views.clear_session, name="clear_session"),
]
