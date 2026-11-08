from django.urls import path
from . import views

app_name = "ocd_live"

urlpatterns = [
    # Vitrine principale OCD Live
    path("", views.index, name="index"),
    
    # Système officiel de Réservation Live Pitch & Vente
    path("reserver/", views.live_reservation, name="reservation"),
    path("suivi/<str:code>/", views.live_suivi, name="suivi"),
    path("fiche/<str:code>/pdf/", views.live_fiche_pdf, name="fiche_pdf"),
    path("admin/", views.live_admin_dashboard, name="admin_dashboard"),
    path("admin/action/<int:booking_id>/", views.live_admin_action, name="admin_action"),
    path("api/slots/", views.live_available_slots_api, name="available_slots_api"),
    
    # Opportunités & Directs (catalogue)
    path("opportunites/", views.opportunities_list, name="opportunities_list"),
    path("opportunites/<slug:slug>/", views.opportunity_detail, name="opportunity_detail"),
    path("directs/", views.live_list, name="live_list"),
    path("directs/<slug:slug>/", views.live_detail, name="live_detail"),
    
    # Réservations & Billetterie existante
    path("reserver/<slug:slug>/", views.book_session, name="book_session"),
    path("pass/<str:package_code>/", views.book_package, name="book_package"),
    path("billet/<str:ticket_code>/", views.booking_detail, name="booking_detail"),
    
    # Espace Membre
    path("mon-espace/", views.dashboard, name="dashboard"),
]

