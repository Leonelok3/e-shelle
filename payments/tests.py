import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.admin import AppSubscriptionAdmin
from accounts.models import AppPlan, AppSubscription, PaymentHistory
from boutique.models import Commande
from .campay import CampayClient, CampayError, reconcile_transaction
from .models import Transaction


class CampayClientTests(TestCase):
    def make_transaction(self, **kwargs):
        defaults = {
            "type_tx": "achat_produit",
            "methode": "campay",
            "montant": Decimal("1250"),
            "devise": "XAF",
        }
        defaults.update(kwargs)
        return Transaction.objects.create(**defaults)

    @override_settings(CAMPAY_MODE="sandbox", CAMPAY_TOKEN="sandbox-token")
    def test_payment_link_uses_server_token_and_xaf_amount(self):
        tx = self.make_transaction()
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "link": "https://demo.campay.net/payment/test",
            "reference": "provider-ref-123",
        }

        with patch("payments.campay.requests.request", return_value=response) as request:
            link, reference = CampayClient().create_payment_link(
                tx,
                description="Test payment",
                redirect_url="https://e-shelle.com/payments/campay/return/?token=abc",
            )

        self.assertEqual(link, "https://demo.campay.net/payment/test")
        self.assertEqual(reference, "provider-ref-123")
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Token sandbox-token")
        self.assertEqual(request.call_args.kwargs["json"]["amount"], 1250)
        self.assertEqual(request.call_args.kwargs["json"]["currency"], "XAF")

    def test_reconciliation_records_success_but_does_not_fulfill_order(self):
        user = get_user_model().objects.create_user(username="buyer", password="test")
        order = Commande.objects.create(
            utilisateur=user,
            montant_total=Decimal("1250"),
            statut="en_attente",
        )
        tx = self.make_transaction(
            utilisateur=user,
            commande=order,
            ref_operateur="provider-ref-123",
        )
        provider = Mock(
            mode="sandbox",
            get_transaction=Mock(return_value={
                "reference": "provider-ref-123",
                "amount": 1250,
                "currency": "XAF",
                "status": "SUCCESSFUL",
            }),
        )

        reconcile_transaction(tx, client=provider)

        tx.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(tx.statut, "pending_awaiting_manual_validation")
        self.assertEqual(tx.metadata["campay"]["provider_status"], "SUCCESSFUL")
        self.assertEqual(order.statut, "en_attente")

    def test_reconciliation_rejects_amount_mismatch(self):
        tx = self.make_transaction(ref_operateur="provider-ref-123")
        provider = Mock(
            mode="sandbox",
            get_transaction=Mock(return_value={
                "reference": "provider-ref-123",
                "amount": 1251,
                "currency": "XAF",
                "status": "SUCCESSFUL",
            }),
        )

        with self.assertRaises(CampayError):
            reconcile_transaction(tx, client=provider)

        tx.refresh_from_db()
        self.assertEqual(tx.statut, "initie")

    @override_settings(
        CAMPAY_MODE="sandbox",
        CAMPAY_TOKEN="sandbox-token",
        CAMPAY_PUBLIC_BASE_URL="https://e-shelle.com",
    )
    def test_order_checkout_creates_pending_transaction_without_marking_order_paid(self):
        user = get_user_model().objects.create_user(username="buyer", password="test")
        order = Commande.objects.create(
            utilisateur=user,
            montant_total=Decimal("1250"),
        )
        self.client.force_login(user)

        with patch.object(
            CampayClient,
            "create_payment_link",
            return_value=("https://demo.campay.net/payment/test", "provider-ref-123"),
        ):
            response = self.client.post(
                reverse("payments:campay_order", kwargs={"commande_id": order.pk})
            )

        tx = Transaction.objects.get(commande=order, methode="campay")
        order.refresh_from_db()
        self.assertRedirects(
            response,
            "https://demo.campay.net/payment/test",
            fetch_redirect_response=False,
        )
        self.assertEqual(tx.statut, "en_attente")
        self.assertEqual(tx.ref_operateur, "provider-ref-123")
        self.assertEqual(order.statut, "en_attente")
        with patch.object(CampayClient, "create_payment_link") as create_payment_link:
            retry = self.client.post(
                reverse("payments:campay_order", kwargs={"commande_id": order.pk})
            )

        self.assertRedirects(
            retry,
            "https://demo.campay.net/payment/test",
            fetch_redirect_response=False,
        )
        create_payment_link.assert_not_called()
        self.assertEqual(
            Transaction.objects.filter(commande=order, methode="campay").count(),
            1,
        )

    def test_order_payment_page_keeps_whatsapp_as_an_option(self):
        user = get_user_model().objects.create_user(username="buyer", password="test")
        order = Commande.objects.create(
            utilisateur=user,
            montant_total=Decimal("1250"),
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("payments:initier", kwargs={"commande_id": order.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payments/method_choice.html")
        self.assertContains(response, "Payer avec CamPay")
        self.assertContains(response, "Continuer via WhatsApp")

    @override_settings(
        ALLOWED_HOSTS=["testserver", "immigration97.com"],
        CAMPAY_MODE="sandbox",
        CAMPAY_TOKEN="sandbox-token",
    )
    def test_immigration97_plan_checkout_records_payment_but_keeps_access_pending(self):
        user = get_user_model().objects.create_user(
            username="immigration-buyer",
            password="safe-test-password",
        )
        plan = AppPlan.objects.create(
            app_key="prep",
            slug="prep-premium-test",
            name="Premium test",
            level="pro",
            price_xaf=2500,
            duration_days=30,
            is_free=False,
            is_active=True,
        )
        self.client.force_login(user)

        upgrade = self.client.get(
            reverse("accounts:upgrade") + "?app=prep",
            HTTP_HOST="immigration97.com",
        )
        self.assertEqual(upgrade.status_code, 200)
        self.assertContains(upgrade, "CamPay — 2 500 FCFA")

        with patch.object(
            CampayClient,
            "create_payment_link",
            return_value=("https://demo.campay.net/payment/test", "provider-ref-123"),
        ) as create_payment_link:
            response = self.client.post(
                reverse(
                    "payments:campay_immigration_plan",
                    kwargs={"plan_id": plan.pk},
                ),
                HTTP_HOST="immigration97.com",
            )

        self.assertRedirects(
            response,
            "https://demo.campay.net/payment/test",
            fetch_redirect_response=False,
        )
        self.assertIn(
            "https://immigration97.com/payments/campay/return/",
            create_payment_link.call_args.kwargs["redirect_url"],
        )
        tx = Transaction.objects.get(utilisateur=user, methode="campay")
        subscription = AppSubscription.objects.get(user=user, plan=plan)
        payment = PaymentHistory.objects.get(user=user, method="campay")
        self.assertEqual(tx.statut, "en_attente")
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.subscription, subscription)
        self.assertEqual(subscription.status, "pending")
        self.assertFalse(subscription.is_active)

        with patch.object(CampayClient, "create_payment_link") as create_payment_link:
            retry = self.client.post(
                reverse(
                    "payments:campay_immigration_plan",
                    kwargs={"plan_id": plan.pk},
                ),
                HTTP_HOST="immigration97.com",
            )
        self.assertRedirects(
            retry,
            "https://demo.campay.net/payment/test",
            fetch_redirect_response=False,
        )
        create_payment_link.assert_not_called()
        self.assertEqual(
            Transaction.objects.filter(
                utilisateur=user,
                methode="campay",
                metadata__app_plan_id=plan.pk,
            ).count(),
            1,
        )

        provider = Mock(
            mode="sandbox",
            get_transaction=Mock(return_value={
                "reference": "provider-ref-123",
                "amount": 2500,
                "currency": "XAF",
                "status": "SUCCESSFUL",
            }),
        )
        reconcile_transaction(tx, client=provider)
        payment.refresh_from_db()
        subscription.refresh_from_db()
        self.assertEqual(payment.status, "success")
        self.assertEqual(subscription.status, "pending")
        self.assertFalse(subscription.is_active)

        admin_instance = AppSubscriptionAdmin(AppSubscription, admin.site)
        with patch.object(admin_instance, "message_user"):
            admin_instance.activate_paid_immigration97_subscriptions(
                Mock(),
                AppSubscription.objects.filter(pk=subscription.pk),
            )
        subscription.refresh_from_db()
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.expires_at - subscription.started_at, timedelta(days=30))
    def test_failed_immigration97_payment_cancels_pending_access(self):
        user = get_user_model().objects.create_user(
            username="immigration-failed-buyer",
            password="safe-test-password",
        )
        plan = AppPlan.objects.create(
            app_key="prep",
            slug="prep-premium-failed-test",
            name="Premium failed test",
            level="pro",
            price_xaf=2500,
            duration_days=30,
            is_free=False,
            is_active=True,
        )
        self.client.force_login(user)

        with patch.object(
            CampayClient,
            "create_payment_link",
            return_value=("https://demo.campay.net/payment/test", "provider-ref-failed"),
        ):
            self.client.post(
                reverse(
                    "payments:campay_immigration_plan",
                    kwargs={"plan_id": plan.pk},
                ),
                HTTP_HOST="immigration97.com",
            )

        tx = Transaction.objects.get(utilisateur=user, methode="campay")
        subscription = AppSubscription.objects.get(user=user, plan=plan)
        payment = PaymentHistory.objects.get(user=user, method="campay")
        provider = Mock(
            mode="sandbox",
            get_transaction=Mock(return_value={
                "reference": "provider-ref-failed",
                "amount": 2500,
                "currency": "XAF",
                "status": "FAILED",
            }),
        )

        reconcile_transaction(tx, client=provider)
        payment.refresh_from_db()
        subscription.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        self.assertEqual(subscription.status, "cancelled")
        self.assertFalse(subscription.is_active)

    def test_immigration97_checkout_rejects_plans_for_other_apps(self):
        user = get_user_model().objects.create_user(
            username="immigration-buyer",
            password="safe-test-password",
        )
        plan = AppPlan.objects.create(
            app_key="adgen",
            slug="adgen-premium-test",
            name="AdGen Premium test",
            level="pro",
            price_xaf=2500,
            duration_days=30,
            is_free=False,
            is_active=True,
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse(
                "payments:campay_immigration_plan",
                kwargs={"plan_id": plan.pk},
            )
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Transaction.objects.filter(utilisateur=user).exists())

    def test_webhook_status_is_verified_using_provider_api(self):
        tx = self.make_transaction(ref_operateur="provider-ref-123")
        payload = json.dumps({"reference": "provider-ref-123", "status": "SUCCESSFUL"})

        with patch("payments.views.reconcile_transaction") as reconcile:
            response = self.client.post(
                reverse("payments:campay_webhook"),
                data=payload,
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        reconcile.assert_called_once()
        self.assertEqual(reconcile.call_args.args[0].pk, tx.pk)
        tx.refresh_from_db()
        self.assertEqual(tx.statut, "initie")

    def test_return_page_reports_manual_validation_after_verified_payment(self):
        user = get_user_model().objects.create_user(username="buyer", password="test")
        tx = self.make_transaction(
            utilisateur=user,
            ref_operateur="provider-ref-123",
        )
        token = signing.dumps(
            {"transaction_id": tx.pk},
            salt="payments.campay.return",
        )

        def mark_as_verified(transaction_obj):
            transaction_obj.statut = "pending_awaiting_manual_validation"
            transaction_obj.save(update_fields=["statut"])
            return transaction_obj

        with patch("payments.views.reconcile_transaction", side_effect=mark_as_verified):
            response = self.client.get(
                f"{reverse('payments:campay_return')}?token={token}"
            )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payments/campay_result.html")
        self.assertContains(response, "valider manuellement")
