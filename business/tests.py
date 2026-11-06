from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import BusinessCatalogItem, BusinessProfile, ProviderPlan
from .services import collect_business_items, record_provider_plan_payment


class ProviderPlanEntitlementTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="plan-owner",
            password="plan-owner-test-password",
        )
        self.business = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.GENERAL,
            name="Business entitlement",
        )

    def test_expired_paid_plan_resets_paid_benefits_and_ai_credits(self):
        self.business.plan = BusinessProfile.Plan.BUSINESS
        self.business.subscription_expires_at = timezone.now()
        self.business.ai_credits = 3
        self.business.is_verified = True
        self.business.is_trial = True
        self.business.boost_expires_at = timezone.now()
        self.business.save()

        self.assertTrue(self.business.check_expiry())

        self.business.refresh_from_db()
        self.assertEqual(self.business.plan, BusinessProfile.Plan.FREE)
        self.assertEqual(self.business.ai_credits, 0)
        self.assertIsNone(self.business.boost_expires_at)
        self.assertFalse(self.business.is_verified)
        self.assertFalse(self.business.is_trial)

    def test_paid_plan_without_expiration_is_downgraded(self):
        self.business.plan = BusinessProfile.Plan.PRO
        self.business.ai_credits = 5
        self.business.save()

        self.assertTrue(self.business.check_expiry())

        self.business.refresh_from_db()
        self.assertEqual(self.business.plan, BusinessProfile.Plan.FREE)
        self.assertEqual(self.business.ai_credits, 0)

    def test_provider_plan_payment_uses_configured_ai_credits_once(self):
        plan = ProviderPlan.objects.create(
            code="provider-business-custom",
            name="Business",
            plan_level=BusinessProfile.Plan.BUSINESS,
            monthly_price_xaf=15000,
            duration_days=30,
            included_ai_credits=12,
        )
        self.business.ai_credits = 7
        self.business.save(update_fields=["ai_credits"])

        with patch("billing.affiliates.create_commission_for_transaction"):
            record_provider_plan_payment(
                business=self.business,
                plan=plan,
                paid_by=self.owner,
                amount_xaf=plan.monthly_price_xaf,
            )

        self.business.refresh_from_db()
        self.assertEqual(self.business.ai_credits, 12)

    def test_pro_plan_cannot_add_or_publish_catalog_video(self):
        self.business.plan = BusinessProfile.Plan.PRO
        self.business.subscription_expires_at = timezone.now() + timedelta(days=30)
        self.business.save(update_fields=["plan", "subscription_expires_at"])
        self.client.force_login(self.owner)

        self.client.post(
            reverse("business:catalog_manage", kwargs={"business_id": self.business.pk}),
            {"title": "Produit Pro", "video_url": "https://example.com/demo.mp4"},
        )

        item = BusinessCatalogItem.objects.get(business=self.business, title="Produit Pro")
        self.assertEqual(item.video_url, "")

        item.video_url = "https://example.com/existing.mp4"
        item.save(update_fields=["video_url"])
        public_items = collect_business_items(self.business)
        self.assertEqual(public_items[0]["video"], "")

    def test_pro_plan_cannot_replace_existing_catalog_video(self):
        self.business.plan = BusinessProfile.Plan.PRO
        self.business.subscription_expires_at = timezone.now() + timedelta(days=30)
        self.business.save(update_fields=["plan", "subscription_expires_at"])
        self.client.force_login(self.owner)
        item = BusinessCatalogItem.objects.create(
            business=self.business,
            title="Produit existant",
            video_url="https://example.com/existing.mp4",
        )

        self.client.post(
            reverse(
                "business:catalog_item_edit",
                kwargs={"business_id": self.business.pk, "item_id": item.pk},
            ),
            {"title": item.title, "video_url": "https://example.com/replacement.mp4"},
        )

        item.refresh_from_db()
        self.assertEqual(item.video_url, "https://example.com/existing.mp4")


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
            payment.metadata["provider_whatsapp_ai_credits"],
            self.plan.included_ai_credits,
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
