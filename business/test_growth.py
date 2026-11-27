from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from billing.affiliates import get_or_create_affiliate_profile
from billing.models import Commission, Referral
from dashboard.models import Notification
from payments.models import Transaction as Payment
from salonhub.bookings.models import Appointment
from salonhub.salons.models import Salon, Service
from whatsapp_commerce.models import BusinessWhatsAppBooking, BusinessWhatsAppContact

from .models import BusinessProfile, ProviderPlan
from .services import activate_provider_whatsapp_payment, provider_subscription_payments
from .tasks import notify_first_business_results, remind_expiring_businesses


class GrowthTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user(username="merchant-growth")
        self.partner = users.create_user(username="partner-growth")
        self.affiliate = get_or_create_affiliate_profile(self.partner)
        Referral.objects.create(affiliate=self.affiliate, referred_user=self.owner)
        self.business = BusinessProfile.objects.create(owner=self.owner, name="Boutique du quartier", city="Douala")
        self.plan = ProviderPlan.objects.create(
            code="growth-business", name="Croissance", plan_level=BusinessProfile.Plan.BUSINESS,
            monthly_price_xaf=15000, duration_days=30,
        )

    def payment(self, mode="production"):
        return Payment.objects.create(
            utilisateur=self.owner, methode="campay", type_tx="abonnement",
            statut="pending_awaiting_manual_validation", montant=15000, devise="XAF",
            metadata={
                "product_type": "provider_whatsapp_onboarding",
                "provider_whatsapp_business_id": self.business.pk,
                "provider_whatsapp_plan_code": self.plan.code,
                "provider_whatsapp_amount_xaf": 15000,
                "campay": {"mode": mode, "provider_status": "SUCCESSFUL", "verified_at": timezone.now().isoformat()},
            },
        )

    def test_verified_renewal_extends_existing_expiry_and_records_one_commission(self):
        first, second = self.payment(), self.payment()
        self.assertTrue(activate_provider_whatsapp_payment(first))
        self.business.refresh_from_db()
        expiry = self.business.subscription_expires_at
        self.assertTrue(activate_provider_whatsapp_payment(second))
        self.assertTrue(activate_provider_whatsapp_payment(second))
        self.business.refresh_from_db()
        self.assertEqual(self.business.subscription_expires_at, expiry + timedelta(days=30))
        self.assertEqual(provider_subscription_payments(self.business).count(), 2)
        renewal = Commission.objects.get(affiliate=self.affiliate, transaction__metadata__provider_payment_cycle="renewal")
        self.assertEqual((renewal.amount, renewal.currency, renewal.status), (Decimal("4500.00"), "XAF", "PENDING"))
        self.client.force_login(self.owner)
        page = self.client.get(reverse("business:business_progress", args=[self.business.pk]))
        self.assertContains(page, "Renouveler la formule")
        self.assertIn(f"plan={self.plan.code}", page.context["renewal_url"])

    def test_sandbox_is_excluded_from_real_commissions(self):
        payment = self.payment(mode="sandbox")
        with override_settings(CAMPAY_MODE="production"):
            self.assertFalse(activate_provider_whatsapp_payment(payment))
        self.business.refresh_from_db()
        self.assertEqual(self.business.plan, BusinessProfile.Plan.FREE)
        with override_settings(CAMPAY_MODE="sandbox"):
            self.assertTrue(activate_provider_whatsapp_payment(payment))
        self.assertFalse(Commission.objects.filter(affiliate=self.affiliate).exists())
        self.assertFalse(provider_subscription_payments(self.business).exists())

    def test_partner_only_sees_opted_in_fiches_and_portfolio_has_provider_invite(self):
        portfolio = reverse("business:partner_portfolio")
        progress = reverse("business:business_progress", args=[self.business.pk])
        sharing = reverse("business:business_partner_support", args=[self.business.pk])
        self.client.force_login(self.partner)
        page = self.client.get(portfolio)
        self.assertNotContains(page, self.business.name)
        self.assertIn("onboarding", page.context["invite"])
        self.assertEqual(self.client.get(progress).status_code, 404)
        self.assertEqual(self.client.post(sharing, {"support": "yes"}).status_code, 404)
        self.client.force_login(self.owner)
        self.client.post(sharing, {"support": "yes"})
        self.client.post(sharing, {"support": "yes"})
        self.assertEqual(Notification.objects.filter(destinataire=self.partner, url_action=portfolio).count(), 1)
        self.client.force_login(self.partner)
        self.assertContains(self.client.get(portfolio), self.business.name)
        self.client.force_login(self.owner)
        self.client.post(sharing, {"support": "no"})
        self.client.force_login(self.partner)
        self.assertNotContains(self.client.get(portfolio), self.business.name)

    def test_first_result_and_expiry_notices_are_once_and_lead_to_correct_fiche(self):
        now = timezone.now()
        BusinessProfile.objects.filter(pk=self.business.pk).update(plan=BusinessProfile.Plan.BUSINESS, subscription_expires_at=now + timedelta(days=2))
        self.assertEqual(remind_expiring_businesses(), 1)
        self.assertEqual(remind_expiring_businesses(), 0)
        salon = Salon.objects.create(owner=self.owner, name="Agenda test", city="Douala", whatsapp_number="+237699000010")
        service = Service.objects.create(salon=salon, name="Pose", price=0, duration_minutes=30)
        appointment = Appointment.objects.create(
            salon=salon, service=service, date=timezone.localdate(), time=time(12), client_name="Test",
            client_phone="+237699000018", status=Appointment.Status.CONFIRMED,
        )
        contact = BusinessWhatsAppContact.objects.create(business=self.business, phone="+237699000018")
        BusinessWhatsAppBooking.objects.create(appointment=appointment, contact=contact)
        self.assertEqual(notify_first_business_results(), 1)
        self.assertEqual(notify_first_business_results(), 0)
        routes = Notification.objects.filter(destinataire=self.owner).values_list("url_action", flat=True)
        self.assertEqual(list(routes), [reverse("business:business_progress", args=[self.business.pk])] * 2)
