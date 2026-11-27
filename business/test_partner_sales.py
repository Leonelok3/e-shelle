from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from billing.affiliates import get_or_create_affiliate_profile
from billing.models import Commission, Referral, Transaction

from .models import BusinessProfile, PaymentRequest, ProviderPlan


class PartnerSalesTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.first = get_or_create_affiliate_profile(users.create_user(username="partner-first"))
        self.second = get_or_create_affiliate_profile(users.create_user(username="partner-second"))
        self.owner = users.create_user(username="merchant-partner-sale")
        self.plan = ProviderPlan.objects.create(code="partner-sale-premium", name="Premium", plan_level="premium", monthly_price_xaf=15000)

    def follow_invite_and_create_business(self, affiliate, name):
        self.client.force_login(self.owner)
        onboarding = reverse("business:onboarding")
        invite = reverse("public_ref_redirect", args=[affiliate.ref_code]) + "?" + urlencode({"next": onboarding})
        self.assertRedirects(self.client.get(invite), onboarding, fetch_redirect_response=False)
        response = self.client.post(onboarding, {"name": name, "phone": "+237699000011", "plan": self.plan.code})
        self.assertEqual(response.status_code, 302)
        return BusinessProfile.objects.get(name=name, owner=self.owner)

    def test_invite_keeps_original_partner_and_only_verified_sales_create_statement_lines(self):
        business = self.follow_invite_and_create_business(self.first, "Boutique de test")
        self.follow_invite_and_create_business(self.second, "Deuxième fiche")
        saved = Referral.objects.get(referred_user=self.owner)
        self.assertEqual(saved.affiliate, self.first)
        self.assertEqual(saved.attribution_source, "business_onboarding")
        self.assertEqual(saved.ref_code_at_binding, self.first.ref_code)

        payment = PaymentRequest.objects.create(
            business=business, requested_by=self.owner, plan=self.plan, method=PaymentRequest.Method.CASH, amount_xaf=15000,
        )
        statement = reverse("business:partner_sales")
        self.client.force_login(self.first.user)
        summary = self.client.get(reverse("business:partner_dashboard"))
        self.assertEqual((summary.context["registered_merchants"], summary.context["paid_merchants"]), (1, 0))
        self.assertContains(self.client.get(statement), "Aucune vente avec commission")

        tx = payment.confirm()
        payment.confirm()
        commission = Commission.objects.get(transaction=tx)
        self.assertEqual((commission.affiliate, commission.amount, commission.status), (self.first, Decimal("4500.00"), "PENDING"))
        self.assertEqual(commission.attribution["code"], self.first.ref_code)
        first_ref_code = self.first.ref_code
        type(self.first).objects.filter(pk=self.first.pk).update(ref_code="NEWCODE123")
        page = self.client.get(statement)
        self.assertContains(page, f"ES‑{tx.pk}")
        self.assertContains(page, first_ref_code)
        self.assertNotContains(page, business.name)
        self.assertContains(page, f"Fiche #{business.pk}")
        self.assertEqual(self.client.get(reverse("business:partner_dashboard")).context["conversion_rate"], 100.0)

        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("business:business_progress", args=[business.pk])), first_ref_code)

        self.client.force_login(self.second.user)
        self.assertNotContains(self.client.get(statement), f"ES‑{tx.pk}")

    def test_business_key_sales_and_historical_commissions_are_filterable(self):
        Referral.objects.create(referred_user=self.owner, affiliate=self.first)
        tx = Transaction.objects.create(user=self.owner, amount=9900, currency="XAF", type="CREDIT", status="COMPLETED", metadata={"product_type": "business_key_subscription"})
        self.client.force_login(self.first.user)
        statement = reverse("business:partner_sales")
        page = self.client.get(statement, {"offre": "business_key_subscription", "statut": "PENDING"})
        self.assertContains(page, f"ES‑{tx.pk}")
        self.assertNotContains(page, "Code partenaire ·")
        self.assertNotContains(self.client.get(statement, {"offre": "provider_subscription"}), f"ES‑{tx.pk}")
