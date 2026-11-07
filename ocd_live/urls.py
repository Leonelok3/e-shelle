from django.urls import path
from . import views

app_name = "ocd_live"

urlpatterns = [
    # Vitrine
    path("", views.index, name="index"),
    
    # Opportunités
    path("opportunites/", views.opportunities_list, name="opportunities_list"),
    path("opportunites/<slug:slug>/", views.opportunity_detail, name="opportunity_detail"),
    
    # Sessions Live & Masterclasses
    path("directs/", views.live_list, name="live_list"),
    path("directs/<slug:slug>/", views.live_detail, name="live_detail"),
    
    # Réservations & Billetterie
    path("reserver/<slug:slug>/", views.book_session, name="book_session"),
    path("pass/<str:package_code>/", views.book_package, name="book_package"),
    path("billet/<str:ticket_code>/", views.booking_detail, name="booking_detail"),
    
    # Espace Membre
    path("mon-espace/", views.dashboard, name="dashboard"),
]

