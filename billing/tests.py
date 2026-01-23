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
