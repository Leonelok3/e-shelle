from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import OpportunityCategory, Opportunity, LiveSession, OCDPackage, Slot, Booking
from .services.booking_service import create_booking_for_session, create_booking_for_slot, confirm_booking_payment


class OCDLiveModuleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="investisseur", password="password123", email="invest@e-shelle.com")
        
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

    def test_ocd_live_index_view(self):
        url = reverse("ocd_live:index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Les Opportunités, C'est Dehors !")
        self.assertContains(response, "Projet Élevage Rentable")
        self.assertContains(response, "Masterclass Agrobusiness 1M")

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

