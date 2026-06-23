# billing/tests.py
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import SubscriptionPlan, CreditCode, Subscription, Transaction

User = get_user_model()


class VoucherCodeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", email="u1@test.com", password="pass12345")
        self.plan_7 = SubscriptionPlan.objects.create(
            name="Plan 7 jours",
            slug="plan-7j",
            duration_days=7,
            price_usd=Decimal("0.00"),
            is_active=True,
        )

    def test_credit_code_is_valid_then_used(self):
        cc = CreditCode.objects.create(
            code="TEST-AAAA-BBBB",
            plan=self.plan_7,
            expiration_date=timezone.now() + timedelta(days=10),
        )
        self.assertTrue(cc.is_valid())

        cc.use(user=self.user, ip="127.0.0.1")
        cc.refresh_from_db()

        self.assertEqual(cc.uses_count, 1)
        self.assertTrue(cc.is_used)
        self.assertEqual(cc.used_by_id, self.user.id)
        self.assertEqual(cc.used_ip, "127.0.0.1")

        with self.assertRaises(ValueError):
            cc.use(user=self.user, ip="127.0.0.1")

    def test_credit_code_expired(self):
        cc = CreditCode.objects.create(
            code="EXPIRED-0000-0000",
            plan=self.plan_7,
            expiration_date=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(cc.is_valid())
        with self.assertRaises(ValueError):
            cc.use(user=self.user, ip="127.0.0.1")


class SubscriptionStackingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u2", email="u2@test.com", password="pass12345")
        self.plan_7 = SubscriptionPlan.objects.create(
            name="Plan 7 jours",
            slug="plan-7j-2",
            duration_days=7,
            price_usd=Decimal("0.00"),
            is_active=True,
        )

    def test_activate_or_extend_creates_subscription_if_none(self):
        sub, created = Subscription.activate_or_extend(user=self.user, plan=self.plan_7)
        self.assertTrue(created)
        self.assertEqual(sub.user_id, self.user.id)
        self.assertEqual(sub.plan_id, self.plan_7.id)
        self.assertTrue(sub.expires_at > timezone.now())

    def test_activate_or_extend_stacks_if_active(self):
        now = timezone.now()

        sub1 = Subscription.objects.create(
            user=self.user,
            plan=self.plan_7,
            starts_at=now,
            expires_at=now + timedelta(days=3),
            is_active=True,
        )

        sub2, created = Subscription.activate_or_extend(user=self.user, plan=self.plan_7)
        self.assertFalse(created)
        sub1.refresh_from_db()

        expected_min = (now + timedelta(days=3)) + timedelta(days=7)
        self.assertTrue(sub1.expires_at >= expected_min - timedelta(seconds=2))
        self.assertEqual(sub2.id, sub1.id)


class RedeemViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u3", email="u3@test.com", password="pass12345")

        self.plan_7 = SubscriptionPlan.objects.create(
            name="Plan 7 jours",
            slug="plan-7j-3",
            duration_days=7,
            price_usd=Decimal("0.00"),
            is_active=True,
        )

        self.cc_7 = CreditCode.objects.create(
            code="CODE-7777-7777",
            plan=self.plan_7,
            expiration_date=timezone.now() + timedelta(days=90),
        )

    def test_redeem_creates_subscription_and_transaction(self):
        self.client.force_login(self.user)

        url = reverse("billing:redeem")
        resp = self.client.post(url, data={"code": self.cc_7.code}, follow=True)

        self.assertEqual(resp.status_code, 200)

        sub = Subscription.objects.filter(user=self.user, is_active=True).order_by("-expires_at").first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.plan_id, self.plan_7.id)

        tx = Transaction.objects.filter(user=self.user, related_code=self.cc_7).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.status, "COMPLETED")
        self.assertEqual(tx.payment_method, "CODE")
        self.assertEqual(tx.type, "CREDIT")
        self.assertEqual(tx.related_subscription_id, sub.id)

        self.cc_7.refresh_from_db()
        self.assertTrue(self.cc_7.is_used)
        self.assertEqual(self.cc_7.used_by_id, self.user.id)


class ResellerSystemTests(TestCase):
    def setUp(self):
        self.provider_user = User.objects.create_user(username="prov1", email="prov@test.com", password="password")
        self.reseller_user = User.objects.create_user(username="resell1", email="resell@test.com", password="password")
        
        from business.models import BusinessProfile, BusinessCatalogItem
        from billing.models import AffiliateProfile
        
        # Create business profile
        self.business = BusinessProfile.objects.create(
            owner=self.provider_user,
            name="Resto Saveur",
            slug="resto-saveur",
            module="resto",
            is_active=True
        )
        
        # Create catalog product
        self.product = BusinessCatalogItem.objects.create(
            business=self.business,
            title="Ndolé Crevettes",
            price_label="5000 FCFA",
            is_active=True
        )
        
        # Create reseller profile
        self.reseller_profile = AffiliateProfile.objects.create(
            user=self.reseller_user,
            ref_code="RESELLCODE",
            is_enabled=True
        )

    def test_reseller_flow_verification(self):
        from django.contrib.contenttypes.models import ContentType
        from billing.models import AffiliateProductConfig, ResellerProductLink, ProviderWallet, AffiliateOrder, Commission
        
        ct = ContentType.objects.get_for_model(self.product)
        
        # 1. Create product config
        config = AffiliateProductConfig.objects.create(
            content_type=ct,
            object_id=self.product.id,
            price=Decimal("5000.00"),
            reseller_commission=Decimal("500.00"),
            platform_fee=Decimal("200.00"),
            is_active=True
        )
        
        # 2. Create reseller link
        link = ResellerProductLink.objects.create(
            reseller=self.reseller_profile,
            content_type=ct,
            object_id=self.product.id,
            promo_code="BUY-TEST-123"
        )
        
        # 3. Checkout with empty provider wallet should show unavailable page
        url = reverse("billing:reseller_checkout", kwargs={"promo_code": link.promo_code})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Offre Temporairement Indisponible")
        
        # 4. Recharge provider wallet
        wallet = ProviderWallet.objects.get(business=self.business)
        wallet.credit(Decimal("2000.00"))
        
        # Now checkout should load the form
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Valider la commande")
        
        # Place order
        post_data = {
            "buyer_name": "Jean Dupont",
            "buyer_phone": "+237 677777777",
            "buyer_address": "Douala Makepe",
        }
        resp = self.client.post(url, data=post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Commande Validée !")
        
        # Check order created
        order = AffiliateOrder.objects.filter(provider_profile=self.business).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "PENDING")
        self.assertEqual(order.amount_total, Decimal("5000.00"))
        
        # 5. Validate delivery with incorrect code
        val_url = reverse("billing:validate_delivery", kwargs={"order_id": order.id})
        self.client.force_login(self.provider_user)
        resp = self.client.post(val_url, data={"delivery_code": "0000"}, follow=True)
        self.assertContains(resp, "Code de validation incorrect")
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDING")
        
        # 6. Validate delivery with correct code
        resp = self.client.post(val_url, data={"delivery_code": order.delivery_code}, follow=True)
        self.assertContains(resp, "validée avec succès")
        
        order.refresh_from_db()
        self.assertEqual(order.status, "DELIVERED")
        
        # Verify wallet deducted: 2000 - (500 + 200) = 1300 FCFA
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("1300.00"))
        
        # Verify reseller credited commission
        commission = Commission.objects.filter(affiliate=self.reseller_profile).first()
        self.assertIsNotNone(commission)
        self.assertEqual(commission.amount, Decimal("500.00"))
        self.assertEqual(commission.status, "PAID")

