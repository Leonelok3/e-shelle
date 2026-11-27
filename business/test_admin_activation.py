from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.affiliates import get_or_create_affiliate_profile
from billing.models import Commission
from billing.models import Referral
from payments.models import Transaction as Payment
from whatsapp_commerce.entitlements import whatsapp_entitlements

from .models import BusinessActivationCode, BusinessProfile, PaymentRequest, ProviderPlan
from .services import provider_subscription_payments, verified_provider_whatsapp_payment


class AdminActivationTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.admin = users.create_superuser(username="payment-admin")
        self.owner = users.create_user(username="premium-owner")
        affiliate = get_or_create_affiliate_profile(users.create_user(username="premium-partner"))
        Referral.objects.create(affiliate=affiliate, referred_user=self.owner)
        self.business = BusinessProfile.objects.create(name="Premium test", owner=self.owner, city="Douala")
        self.plan = ProviderPlan.objects.create(
            name="Premium test", code="admin-premium", plan_level=BusinessProfile.Plan.PREMIUM,
            monthly_price_xaf=30000, duration_days=30, included_ai_credits=50, included_boost_days=7,
        )

    def create_code(self, method="virement", reference="V-105"):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:business_businessactivationcode_add"), {
            "business": self.business.pk, "plan": self.plan.pk, "amount_paid_xaf": self.plan.monthly_price_xaf,
            "payment_method": method, "payment_reference": reference, "unlocks_whatsapp_onboarding": "on", "_save": "Enregistrer",
        })
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", {}).get("adminform"))
        return BusinessActivationCode.objects.get(payment_reference=reference)

    def create_request(self, method, reference):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:business_paymentrequest_add"), {
            "business": self.business.pk, "requested_by": self.owner.pk, "plan": self.plan.pk,
            "amount_xaf": self.plan.monthly_price_xaf, "method": method, "payment_reference": reference, "_save": "Enregistrer",
        })
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", {}).get("adminform"))
        return PaymentRequest.objects.get(payment_reference=reference)

    def confirm_request(self, payment):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:business_paymentrequest_changelist"), {
            "action": "confirm_requests", "_selected_action": str(payment.pk), "index": "0",
        })
        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()

    def test_code_from_admin_activates_premium_and_is_single_use_for_the_owner(self):
        code = self.create_code()
        self.assertEqual(code.created_by, self.admin)
        self.assertFalse(code.is_used)
        redeem = reverse("business:redeem_activation_code")
        self.client.force_login(get_user_model().objects.create_user(username="wrong-owner"))
        self.client.post(redeem, {"code": code.code})
        code.refresh_from_db()
        self.assertFalse(code.is_used)
        self.client.force_login(self.owner)
        response = self.client.post(redeem, {"code": code.code.lower()})
        self.assertEqual(response.url, reverse("business:dashboard") + f"?business={self.business.pk}")
        self.business.refresh_from_db()
        expiry = self.business.subscription_expires_at
        self.assertEqual(self.business.plan, BusinessProfile.Plan.PREMIUM)
        self.assertTrue(whatsapp_entitlements(self.business)["can_connect"])
        self.assertEqual(self.business.ai_credits, 50)
        self.assertEqual(verified_provider_whatsapp_payment(self.business).metadata["provider_manual_method"], "virement")
        self.assertEqual(Commission.objects.get().amount, Decimal("9000.00"))
        self.client.post(redeem, {"code": code.code})
        self.business.refresh_from_db()
        self.assertEqual(self.business.subscription_expires_at, expiry)
        self.assertEqual(provider_subscription_payments(self.business).count(), 1)

    def test_cash_and_deposit_direct_confirmation_extend_plan_and_share_reference_guard(self):
        cash = self.create_request("cash", "Reçu-001")
        self.assertEqual(cash.status, PaymentRequest.Status.PENDING)
        self.assertFalse(provider_subscription_payments(self.business).exists())
        self.confirm_request(cash)
        self.assertEqual(cash.status, PaymentRequest.Status.CONFIRMED)
        self.business.refresh_from_db()
        first_expiry = self.business.subscription_expires_at
        self.confirm_request(cash)
        duplicate = self.create_code(method="cash", reference="reçu-001")
        self.client.force_login(self.owner)
        self.client.post(reverse("business:redeem_activation_code"), {"code": duplicate.code})
        duplicate.refresh_from_db()
        self.assertFalse(duplicate.is_used)
        self.assertEqual(provider_subscription_payments(self.business).count(), 1)
        deposit = self.create_request("deposit", "D-302")
        self.confirm_request(deposit)
        self.business.refresh_from_db()
        self.assertEqual(self.business.subscription_expires_at, first_expiry + timedelta(days=30))
        self.assertEqual(Payment.objects.filter(utilisateur=self.owner, methode="manual", statut="succes").count(), 2)
        self.assertEqual(Commission.objects.count(), 2)

    def test_premium_grant_for_a_pending_arrangement_creates_no_paid_record(self):
        self.client.force_login(self.admin)
        page = self.client.get(reverse("admin:business_businessprofile_changelist"))
        self.assertContains(page, "Enregistrer un paiement")
        self.client.post(reverse("admin:business_businessprofile_changelist"), {
            "action": "activate_premium_30_days", "_selected_action": str(self.business.pk), "index": "0",
        })
        self.business.refresh_from_db()
        self.assertEqual(self.business.plan, BusinessProfile.Plan.PREMIUM)
        self.assertFalse(provider_subscription_payments(self.business).exists())
        self.assertFalse(Commission.objects.exists())
        self.assertIsNone(verified_provider_whatsapp_payment(self.business))
