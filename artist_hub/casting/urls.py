"""
artist_hub/casting/urls.py — Définition des routes du module casting et dashboard staff.
Namespace : 'artist_hub:casting'
"""
from django.urls import path
from . import views
from . import views_dashboard

app_name = "casting"

urlpatterns = [
    path("confirmation/", views.CandidateConfirmationView.as_view(), name="confirmation"),
    # Parcours public
    path("", views.CastingIndexView.as_view(), name="index"),
    path("inscription/", views.CandidateRegisterWizardView.as_view(), name="register"),
    path("suivi/", views.CandidateTrackView.as_view(), name="track"),
    path("fiche-pdf/<str:candidate_number>/", views.CandidateCardPdfView.as_view(), name="download_card"),

    # Dashboard staff (réservé aux administrateurs / jury is_staff)
    path("staff/dashboard/", views_dashboard.StaffDashboardListView.as_view(), name="dashboard"),
    path("staff/candidat/<str:candidate_number>/", views_dashboard.StaffCandidateDetailView.as_view(), name="staff_candidate_detail"),
    path("staff/actions-groupees/", views_dashboard.StaffBulkActionView.as_view(), name="staff_bulk_action"),
    path("staff/export-csv/", views_dashboard.StaffExportCsvView.as_view(), name="staff_export_csv"),
    path("staff/candidat/<str:candidate_number>/preuve/", views_dashboard.StaffPaymentProofView.as_view(), name="staff_payment_proof"),
    path("staff/paiement/<uuid:payment_id>/preuve/", views_dashboard.StaffPaymentProofView.as_view(), name="staff_payment_proof_by_payment"),
    path("staff/statistiques/", views_dashboard.StaffStatsView.as_view(), name="staff_stats"),
]
