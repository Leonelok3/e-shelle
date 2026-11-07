from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    BusinessActivationCode,
    BusinessCatalogItem,
    BusinessKeyPaymentRequest,
    BusinessProfile,
    ProviderPlan,
)
from .services import (
    activate_provider_whatsapp_payment,
    collect_business_items,
    record_provider_plan_payment,
    verified_provider_whatsapp_payment,
)


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

    def test_free_listing_is_visible_for_fourteen_days_then_paused_without_deletion(self):
        self.assertTrue(self.business.is_published)
        self.assertGreater(
            self.business.free_visibility_expires_at,
            timezone.now() + timedelta(days=13),
        )

        self.business.free_visibility_expires_at = timezone.now() - timedelta(seconds=1)
        self.business.save(update_fields=["free_visibility_expires_at", "updated_at"])
        self.assertTrue(self.business.check_expiry())

        self.business.refresh_from_db()
        self.assertFalse(self.business.is_active)
        self.assertFalse(self.business.is_published)
        self.assertTrue(BusinessProfile.objects.filter(pk=self.business.pk).exists())

    def test_public_queryset_excludes_expired_free_and_paid_listings(self):
        self.business.free_visibility_expires_at = timezone.now() - timedelta(seconds=1)
        self.business.save(update_fields=["free_visibility_expires_at", "updated_at"])
        self.assertFalse(BusinessProfile.publicly_visible().filter(pk=self.business.pk).exists())

        self.business.plan = BusinessProfile.Plan.PRO
        self.business.activation_status = BusinessProfile.ActivationStatus.ACTIVE
        self.business.subscription_expires_at = timezone.now() - timedelta(seconds=1)
        self.business.save()
        self.assertFalse(BusinessProfile.publicly_visible().filter(pk=self.business.pk).exists())

    def test_business_key_payment_requires_active_growth_or_premium_subscription(self):
        payment_request = BusinessKeyPaymentRequest.objects.create(
            user=self.owner,
            tier="key",
            amount_xaf=9900,
        )
        with self.assertRaisesMessage(ValueError, "Croissance — Business ou Premium actif"):
            payment_request.confirm()

        self.assertEqual(payment_request.status, BusinessKeyPaymentRequest.Status.PENDING)

        self.business.activate_plan(BusinessProfile.Plan.BUSINESS, ai_credits=20)
        with patch("billing.affiliates.create_commission_for_transaction"):
            payment_request.confirm()
        payment_request.refresh_from_db()
        self.assertEqual(payment_request.status, BusinessKeyPaymentRequest.Status.CONFIRMED)

    def test_ai_delivery_kit_uses_existing_ai_credit_balance(self):
        self.business.activate_plan(BusinessProfile.Plan.PRO, ai_credits=1)
        self.client.force_login(self.owner)
        url = reverse("business:ai_delivery_kit", kwargs={"business_id": self.business.pk})

        with patch("business.views.generate_client_ai_kit") as generate_kit:
            response = self.client.post(url)

        self.assertRedirects(response, url, fetch_redirect_response=False)
        generate_kit.assert_called_once()
        self.business.refresh_from_db()
        self.assertEqual(self.business.ai_credits, 0)

        with patch("business.views.generate_client_ai_kit") as generate_kit:
            self.client.post(url)

        generate_kit.assert_not_called()

    def test_free_plan_rejects_a_sixth_product(self):
        for index in range(5):
            BusinessCatalogItem.objects.create(
                business=self.business,
                title=f"Produit {index + 1}",
            )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("business:catalog_manage", kwargs={"business_id": self.business.pk}),
            {"title": "Produit en trop"},
            follow=True,
        )

        self.assertEqual(BusinessCatalogItem.objects.filter(business=self.business).count(), 5)
        self.assertContains(
            response,
            "Passe à Présence — Pro / Croissance pour ajouter plus de produits.",
        )

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
        self.business.delete()
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

    def test_free_onboarding_rejects_a_second_business_listing(self):
        response = self.client.post(
            reverse("business:onboarding"),
            {
                "name": "Deuxieme boutique",
                "phone": "+237699000003",
                "plan": "free",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("business:dashboard"))
        self.assertFalse(BusinessProfile.objects.filter(name="Deuxieme boutique").exists())
        self.assertContains(response, "Le forfait Gratuit est limité à une fiche Business.")

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

    def test_special_offer_provides_manual_whatsapp_payment_option(self):
        page = self.client.get(
            reverse("provider_special_offer"),
            {"business": self.business.pk, "plan": self.plan.code},
        )

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Contacter E-Shelle sur WhatsApp")
        self.assertContains(page, "code à saisir")
        self.assertContains(page, "Payer par MoMo / Orange Money")

        response = self.client.post(
            reverse("provider_special_offer"),
            {
                "business": self.business.pk,
                "plan": self.plan.code,
                "payment_method": "whatsapp",
            },
        )
        self.assertEqual(response.status_code, 302)
        parsed_url = urlparse(response["Location"])
        self.assertEqual(parsed_url.netloc, "wa.me")
        self.assertEqual(parsed_url.path, "/237680625082")
        message = parse_qs(parsed_url.query)["text"][0]
        self.assertIn(self.business.name, message)
        self.assertIn(self.plan.name, message)
        self.assertIn("3 000 FCFA", message)

    def test_failed_provider_payment_does_not_activate_plan_or_grant_credits(self):
        from payments.models import Transaction

        payment = Transaction.objects.create(
            utilisateur=self.owner,
            type_tx="abonnement",
            methode="campay",
            montant=self.plan.monthly_price_xaf,
            devise="XAF",
            statut="echec",
            metadata={
                "product_type": "provider_whatsapp_onboarding",
                "provider_whatsapp_business_id": self.business.pk,
                "provider_whatsapp_plan_code": self.plan.code,
                "provider_whatsapp_amount_xaf": self.plan.monthly_price_xaf,
                "campay": {"provider_status": "SUCCESSFUL"},
            },
        )

        self.assertFalse(activate_provider_whatsapp_payment(payment))
        self.business.refresh_from_db()
        self.assertEqual(self.business.plan, BusinessProfile.Plan.FREE)
        self.assertEqual(self.business.ai_credits, 0)
        self.assertIsNone(self.business.subscription_expires_at)

    def test_admin_issued_whatsapp_activation_code_unlocks_manual_payment_path(self):
        business_plan = ProviderPlan.objects.create(
            code="provider-business-manual",
            name="Croissance — Business",
            plan_level=BusinessProfile.Plan.BUSINESS,
            monthly_price_xaf=15000,
            duration_days=30,
            included_ai_credits=20,
            is_active=True,
        )
        code = BusinessActivationCode.objects.create(
            business=self.business,
            plan=business_plan,
            amount_paid_xaf=business_plan.monthly_price_xaf,
            payment_method=BusinessActivationCode.PaymentMethod.MTN_MOMO,
            unlocks_whatsapp_onboarding=True,
        )

        with patch("billing.affiliates.create_commission_for_transaction"):
            code.redeem(self.owner)

        from payments.models import Transaction
        from whatsapp_commerce.entitlements import whatsapp_entitlements

        payment = Transaction.objects.get(
            metadata__provider_whatsapp_activation_code_id=code.pk,
        )
        self.assertEqual(payment.methode, "manual")
        self.assertEqual(payment.statut, "succes")
        self.assertIsNotNone(verified_provider_whatsapp_payment(self.business))
        self.business.refresh_from_db()
        self.assertTrue(whatsapp_entitlements(self.business)["can_connect"])
        self.assertRedirects(
            self.client.get(
                reverse("provider_special_offer"),
                {"business": self.business.pk},
            ),
            reverse(
                "whatsapp_commerce:business_dashboard",
                kwargs={"business_id": self.business.pk},
            ),
            fetch_redirect_response=False,
        )

    def test_regular_business_activation_code_does_not_verify_meta_payment(self):
        code = BusinessActivationCode.objects.create(
            business=self.business,
            plan=self.plan,
            amount_paid_xaf=self.plan.monthly_price_xaf,
        )

        with patch("billing.affiliates.create_commission_for_transaction"):
            code.redeem(self.owner)

        self.assertIsNone(verified_provider_whatsapp_payment(self.business))

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
            f'href="{reverse("provider_special_offer")}?business={self.business.pk}&amp;plan=pro"',
        )
        self.assertContains(
            response,
            f'href="{reverse("provider_special_offer")}?business={self.business.pk}&amp;plan=business"',
        )
        self.assertContains(
            response,
            f'href="{reverse("provider_special_offer")}?business={self.business.pk}&amp;plan=premium"',
        )
