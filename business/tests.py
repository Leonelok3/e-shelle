from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BusinessProfile, ProviderPlan


class ProviderOnboardingPaymentTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="provider-owner",
            password="test-password",
        )
        self.plan = ProviderPlan.objects.create(
            code="provider-pro",
            name="Pro",
            plan_level=BusinessProfile.Plan.PRO,
            monthly_price_xaf=3000,
            duration_days=30,
            is_active=True,
        )
        self.business = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.GENERAL,
            name="Boutique test",
        )
        self.client.force_login(self.owner)

    def test_onboarding_does_not_grant_free_trial_and_redirects_to_special_offer(self):
        response = self.client.post(
            reverse("business:onboarding"),
            {
                "name": "Nouvelle boutique",
                "phone": "+237699000001",
                "plan": self.plan.code,
            },
        )

        business = BusinessProfile.objects.get(name="Nouvelle boutique")
        self.assertEqual(
            response["Location"],
            f"{reverse('provider_special_offer')}?business={business.pk}&plan={self.plan.code}",
        )
        self.assertEqual(business.plan, BusinessProfile.Plan.FREE)
        self.assertFalse(business.is_trial)
        self.assertIsNone(business.subscription_expires_at)

    def test_free_onboarding_keeps_listing_and_does_not_activate_whatsapp(self):
        response = self.client.post(
            reverse("business:onboarding"),
            {
                "name": "Fiche gratuite",
                "phone": "+237699000002",
                "plan": "free",
            },
        )

        business = BusinessProfile.objects.get(name="Fiche gratuite")
        self.assertEqual(
            response["Location"],
            reverse("business:dashboard"),
        )
        self.assertEqual(business.plan, BusinessProfile.Plan.FREE)
        self.assertFalse(business.is_trial)

    def test_special_offer_uses_server_defined_price_and_starts_mobile_money_checkout(self):
        with override_settings(CAMPAY_PUBLIC_BASE_URL="https://e-shelle.com"):
            with patch("payments.views.CampayClient") as campay_client:
                campay_client.return_value.create_payment_link.return_value = (
                    "https://demo.campay.net/payment/provider",
                    "provider-ref-123",
                )
                campay_client.return_value.mode = "sandbox"
                response = self.client.post(
                    reverse("provider_special_offer"),
                    {
                        "business": self.business.pk,
                        "plan": self.plan.code,
                    },
                )

        self.assertRedirects(
            response,
            "https://demo.campay.net/payment/provider",
            fetch_redirect_response=False,
        )
        from payments.models import Transaction

        payment = Transaction.objects.get(
            utilisateur=self.owner,
            type_tx="abonnement",
            metadata__product_type="provider_whatsapp_onboarding",
        )
        self.assertEqual(payment.montant, 3000)
        self.assertEqual(payment.statut, "en_attente")
        self.assertEqual(
            payment.metadata["provider_whatsapp_business_id"],
            self.business.pk,
        )
        self.assertEqual(
            campay_client.return_value.create_payment_link.call_args.kwargs[
                "description"
            ],
            f"E-Shelle Pro — {self.business.name}",
        )

    def test_special_offer_rejects_another_users_business(self):
        other_owner = get_user_model().objects.create_user(
            username="provider-other",
            password="test-password",
        )
        other_business = BusinessProfile.objects.create(
            owner=other_owner,
            module=BusinessProfile.Module.GENERAL,
            name="Autre boutique",
        )

        response = self.client.get(
            reverse("provider_special_offer"),
            {"business": other_business.pk},
        )

        self.assertEqual(response.status_code, 404)

    def test_paid_provider_pricing_links_to_onboarding_before_checkout(self):
        response = self.client.get(reverse("tarifs"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("business:onboarding")}?plan=pro"',
        )
        self.assertContains(
            response,
            f'href="{reverse("business:onboarding")}?plan=business"',
        )
        self.assertContains(
            response,
            f'href="{reverse("business:onboarding")}?plan=premium"',
        )
