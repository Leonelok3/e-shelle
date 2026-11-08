from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Booking,
    LiveBooking,
    LivePackage,
    LiveSession,
    LiveSlot,
    OCDPackage,
    Opportunity,
    OpportunityCategory,
    Slot,
)
from .services.booking_service import create_booking_for_session, create_booking_for_slot, confirm_booking_payment


class OCDLiveModuleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="investisseur", password="password123", email="invest@e-shelle.com")
        self.staff_user = User.objects.create_user(username="admin_staff", password="password123", email="staff@e-shelle.com", is_staff=True)
        
        self.category = OpportunityCategory.objects.create(
            name="Agrobusiness",
            slug="agrobusiness",
            icon="🌿",
        )
        self.opportunity = Opportunity.objects.create(
            title="Projet Élevage Rentable",
            slug="projet-elevage-rentable",
            category=self.category,
            country="Cameroun",
            city="Douala",
            summary="Dossier d'élevage avicole à fort rendement.",
            full_description="Détails complets du projet avicole avec contrat grossiste.",
            min_capital_xaf=Decimal("1000000.00"),
            estimated_roi="30% / an",
            status=Opportunity.Status.VERIFIED,
            is_featured=True,
        )
        self.session = LiveSession.objects.create(
            title="Masterclass Agrobusiness 1M",
            slug="masterclass-agrobusiness-1m",
            subtitle="Comment rentabiliser son élevage en 90 jours",
            description="Programme complet de la session live.",
            speaker_name="Expert Terrain",
            speaker_title="Consultant Agro",
            scheduled_at=timezone.now() + timedelta(days=2),
            duration_minutes=90,
            access_tier=LiveSession.AccessTier.PASS_REQUIRED,
            ticket_price_xaf=Decimal("2500.00"),
        )
        self.package = OCDPackage.objects.create(
            name="Pass Membre Mensuel",
            slug="pass-membre-mensuel",
            code="ocd_monthly",
            price_xaf=Decimal("15000.00"),
            duration_days=30,
            description="Accès tous les lives\nReplays illimités",
        )

        # 4 Packages officiels Live Pitch & Vente
        self.live_pkg_decouverte = LivePackage.objects.create(
            nom="Pass Découverte",
            slug="pass-decouverte",
            duree_minutes=60,
            prix_xaf=Decimal("10000.00"),
            description="Présentation simple produit/service",
            ordre=1,
        )
        self.live_pkg_business = LivePackage.objects.create(
            nom="Pass Business",
            slug="pass-business",
            duree_minutes=120,
            prix_xaf=Decimal("20000.00"),
            description="Présentation + démo + questions live (RECOMMANDÉ)",
            est_recommande=True,
            ordre=2,
        )

        # Créneau disponible pour test
        self.test_date = timezone.localdate() + timedelta(days=3)
        self.live_slot = LiveSlot.objects.create(
            date=self.test_date,
            heure_debut=time(14, 0),
            heure_fin=time(16, 0),
            capacite=1,
            est_disponible=True,
            est_bloque_admin=False,
        )

    def test_ocd_live_index_view(self):
        url = reverse("ocd_live:index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passez en direct devant des milliers de clients.")
        self.assertContains(response, "Pass Business")
        self.assertContains(response, "20 000")

    def test_opportunity_detail_increments_views(self):
        url = reverse("ocd_live:opportunity_detail", kwargs={"slug": self.opportunity.slug})
        initial_views = self.opportunity.views_count
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projet Élevage Rentable")
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.views_count, initial_views + 1)

    def test_booking_session_service_and_confirmation(self):
        booking = create_booking_for_session(
            self.user,
            self.session,
            whatsapp_number="+237680000000",
        )
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.amount_paid, Decimal("2500.00"))
        self.assertTrue(booking.ticket_code.startswith("OCD-"))

        # Confirmation simulation
        confirm_booking_payment(booking, transaction_ref="TX-12345")
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.transaction_ref, "TX-12345")

    def test_slot_booking_capacity_management(self):
        slot = Slot.objects.create(
            session=self.session,
            title="Audit Projet Privé",
            expert_name="Expert Terrain",
            start_time=timezone.now() + timedelta(days=3),
            end_time=timezone.now() + timedelta(days=3, minutes=45),
            capacity=1,
            booked_count=0,
            price_xaf=Decimal("10000.00"),
        )
        self.assertFalse(slot.is_full)
        booking = create_booking_for_slot(self.user, slot, whatsapp_number="+237680000000")
        confirm_booking_payment(booking, transaction_ref="TX-SLOT-01")
        
        slot.refresh_from_db()
        self.assertEqual(slot.booked_count, 1)
        self.assertTrue(slot.is_full)

    def test_dashboard_requires_login(self):
        url = reverse("ocd_live:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.user)
        response_auth = self.client.get(url)
        self.assertEqual(response_auth.status_code, 200)
        self.assertContains(response_auth, "Mon Espace Membre")

    # =========================================================================
    # TESTS DU NOUVEAU SYSTÈME DE RÉSERVATION LIVE PITCH & VENTE
    # =========================================================================

    def test_statut_initial_et_calcul_prix_package(self):
        """Vérifie que prix_total = package.prix_xaf et statut initial = en_attente_paiement."""
        booking = LiveBooking.objects.create(
            nom_complet="Samuel Eto'o",
            telephone_whatsapp="+237699001122",
            email="samuel@fecafoot.cm",
            nom_entreprise="Samuel Sports Brand",
            secteur_activite=LiveBooking.SecteurActivite.COMMERCE,
            titre_du_live="Lancement de notre nouvelle gamme de maillots",
            description_activite="Présentation en avant-première et vente exclusive",
            produits_services="Maillots officiels 25 000 XAF",
            package=self.live_pkg_business,
            slot=self.live_slot,
            date_choisie=self.live_slot.date,
            heure_choisie=self.live_slot.heure_debut,
            mode_paiement=LiveBooking.ModePaiement.MTN_MOMO,
        )

        # Vérification du code de réservation unique généré auto
        self.assertTrue(booking.code_reservation.startswith("OCD-"))
        # Statut initial sans preuve
        self.assertEqual(booking.statut, LiveBooking.Statut.EN_ATTENTE_PAIEMENT)
        # Prix et durée synchronisés depuis le package
        self.assertEqual(booking.prix_total, Decimal("20000.00"))
        self.assertEqual(booking.duree_minutes, 120)

        # Quand le client ajoute sa référence ou sa preuve, statut -> en_attente_validation_admin
        booking.reference_paiement = "MOMO-20261108-999"
        booking.save()
        self.assertEqual(booking.statut, LiveBooking.Statut.EN_ATTENTE_VALIDATION)

    def test_anti_double_booking_sur_meme_creneau(self):
        """Vérifie qu'un créneau validé devient indisponible et bloque tout double booking."""
        booking1 = LiveBooking.objects.create(
            nom_complet="Client Un",
            telephone_whatsapp="+237677112233",
            email="client1@test.cm",
            nom_entreprise="Entreprise 1",
            secteur_activite=LiveBooking.SecteurActivite.TECH,
            titre_du_live="Pitch Solution IA E-Shelle",
            description_activite="Démo IA",
            produits_services="Logiciel IA",
            package=self.live_pkg_business,
            slot=self.live_slot,
            date_choisie=self.live_slot.date,
            heure_choisie=self.live_slot.heure_debut,
            mode_paiement=LiveBooking.ModePaiement.ORANGE_MONEY,
            statut=LiveBooking.Statut.VALIDEE_ADMIN,
        )

        # Le slot doit être devenu non disponible automatiquement
        self.live_slot.refresh_from_db()
        self.assertFalse(self.live_slot.est_disponible)
        self.assertFalse(self.live_slot.est_reservable)

        # Une tentative de réservation via le formulaire sur ce même slot doit être rejetée
        post_data = {
            "nom_complet": "Client Deux",
            "telephone_whatsapp": "699887766",
            "email": "client2@test.cm",
            "nom_entreprise": "Entreprise 2",
            "secteur_activite": LiveBooking.SecteurActivite.COMMERCE,
            "titre_du_live": "Deuxième Pitch",
            "description_activite": "Présentation concurrente",
            "produits_services": "Produit 2",
            "package_id": self.live_pkg_business.id,
            "slot_id": self.live_slot.id,
            "mode_paiement": "MTN MoMo",
        }
        res = self.client.post(reverse("ocd_live:reservation"), post_data)
        # La requête ne doit pas rediriger avec succès car le créneau n'est pas disponible
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Ce créneau")

    def test_formulaire_public_reservation_creation_et_redirection(self):
        """Vérifie la soumission du formulaire complet et la redirection vers la page de suivi."""
        slot_libre = LiveSlot.objects.create(
            date=timezone.localdate() + timedelta(days=5),
            heure_debut=time(10, 0),
            heure_fin=time(12, 0),
            est_disponible=True,
        )

        post_data = {
            "nom_complet": "Jean Paul Kemgne",
            "telephone_whatsapp": "680625082",
            "email": "kemgne@eshelle.cm",
            "nom_entreprise": "Agri Vert Cameroun",
            "secteur_activite": "Agriculture & Élevage",
            "titre_du_live": "Comment produire 5 tonnes de tomates sous serre",
            "description_activite": "Présentation des intrants et semences certifiées",
            "produits_services": "Semences F1, Kits goutte-à-goutte",
            "lien_site_ou_page": "https://agrivert.cm",
            "lien_whatsapp": "https://wa.me/237680625082",
            "package_id": self.live_pkg_decouverte.id,
            "slot_id": slot_libre.id,
            "mode_paiement": "MTN MoMo",
            "reference_paiement": "TX-MOMO-8877",
        }

        response = self.client.post(reverse("ocd_live:reservation"), post_data)
        self.assertEqual(response.status_code, 302)

        booking = LiveBooking.objects.filter(email="kemgne@eshelle.cm").first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.statut, LiveBooking.Statut.EN_ATTENTE_VALIDATION)
        self.assertEqual(booking.prix_total, Decimal("10000.00"))
        self.assertEqual(response.url, reverse("ocd_live:suivi", kwargs={"code": booking.code_reservation}))

    def test_fiche_pdf_generation_view(self):
        """Vérifie que la vue PDF renvoie un fichier PDF A4 valide."""
        booking = LiveBooking.objects.create(
            nom_complet="Paul Biya",
            telephone_whatsapp="+237680000000",
            email="test@e-shelle.com",
            nom_entreprise="Test Enterprise",
            secteur_activite=LiveBooking.SecteurActivite.SERVICES,
            titre_du_live="Présentation des Services Numériques",
            description_activite="Pitch digital",
            produits_services="Services Web",
            package=self.live_pkg_decouverte,
            slot=self.live_slot,
            date_choisie=self.live_slot.date,
            heure_choisie=self.live_slot.heure_debut,
            mode_paiement=LiveBooking.ModePaiement.MTN_MOMO,
            statut=LiveBooking.Statut.VALIDEE_ADMIN,
        )

        url = reverse("ocd_live:fiche_pdf", kwargs={"code": booking.code_reservation})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(len(response.content) > 1000)


