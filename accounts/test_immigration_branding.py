from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs, unquote
from django.test import SimpleTestCase, RequestFactory, override_settings
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.contrib.auth.models import AnonymousUser
from allauth.account.adapter import DefaultAccountAdapter
from accounts.adapters import AccountAdapter
from accounts.models import AppPlan, CustomUser
from accounts.views import upgrade, _envoyer_code_verification
from core.branding import public_text
from core.whatsapp import payment_request_url
from edu_cm.immigration_domain import ImmigrationDomainMiddleware
from pathlib import Path

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [str(Path(__file__).resolve().parent.parent / "templates")],
              "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request",
                         "django.contrib.auth.context_processors.auth"]}}]

class PublicIdentityTests(SimpleTestCase):
    def test_payment_link_has_correct_phone_and_cleans_stored_plan_labels(self):
        link = payment_request_url(brand="Immigration97", service="E-Shelle Premium",
                                   details="Groupe E-SHELLE", amount="9 000 FCFA", user=AnonymousUser())
        self.assertEqual(urlparse(link).path, "/237693649944")
        message = parse_qs(urlparse(link).query)["text"][0]
        self.assertIn("Bonjour Immigration97", message)
        self.assertIn("9 000 FCFA", message)
        self.assertNotIn("shelle", message.lower())

    @override_settings(WHATSAPP_SUPPORT="237680625082")
    def test_other_apps_keep_their_contact(self):
        link = payment_request_url(service="E-Shelle Premium")
        self.assertEqual(urlparse(link).path, "/237680625082")
        self.assertIn("E-Shelle", unquote(link))
        self.assertEqual(public_text("E-Shelle"), "E-Shelle")

    @override_settings(ROOT_URLCONF="accounts.test_brand_urls", TEMPLATES=TEMPLATES)
    def test_legacy_upgrade_renders_clean_prep_offer_without_saving_plan(self):
        request = RequestFactory().get("/accounts/upgrade/?app=prep", HTTP_HOST="e-shelle.com")
        ImmigrationDomainMiddleware(lambda r: None)(request)
        request.user = CustomUser(username="learner", email="learner@example.com")
        plan = AppPlan(app_key="prep", name="E-Shelle Français Premium", level="pro",
                       price_xaf=9000, duration_days=30, is_active=True,
                       features=["Groupe WhatsApp E-Shelle"], description="Coach E-Shelle")
        with patch("accounts.views.AppPlan.objects.filter") as query, patch(
                "accounts.views.AppSubscription.get_active_for_user", return_value=None):
            query.return_value.exclude.return_value.order_by.return_value.filter.return_value = [plan]
            response = upgrade(request)
        html = response.content.decode()
        self.assertIn("Immigration97", html)
        self.assertIn("wa.me/237693649944", html)
        self.assertNotIn("shelle", html.lower())
        self.assertNotIn("237680625082", html)
        self.assertEqual(plan.name, "E-Shelle Français Premium")
        self.assertEqual(plan.features, ["Groupe WhatsApp E-Shelle"])

    @override_settings(DEFAULT_FROM_EMAIL="E-Shelle <old@example.com>",
                       IMMIGRATION97_DEFAULT_FROM_EMAIL="Immigration97 <mail@example.com>")
    def test_verification_email_brand_and_configured_sender(self):
        request = SimpleNamespace(site_brand="Immigration97")
        user = SimpleNamespace(first_name="Learner", username="learner", email="learner@example.com")
        with patch("accounts.views.send_mail") as send:
            _envoyer_code_verification(user, "123456", request=request)
        payload = send.call_args.kwargs
        self.assertNotIn("shelle", (payload["subject"] + payload["message"] + payload["html_message"]).lower())
        self.assertIn("Immigration97", payload["subject"])
        self.assertEqual(payload["from_email"], "Immigration97 <mail@example.com>")

    @override_settings(IMMIGRATION97_DEFAULT_FROM_EMAIL="Immigration97 <mail@example.com>")
    def test_allauth_email_body_and_subject_are_branded(self):
        request = RequestFactory().get("/")
        request.is_immigration97 = True
        adapter = AccountAdapter(request)
        original = EmailMultiAlternatives("E-Shelle", "E-Shelle reset", "old@example.com", ["user@example.com"])
        original.attach_alternative("<p>E-Shelle</p>", "text/html")
        with patch.object(DefaultAccountAdapter, "render_mail", return_value=original):
            message = adapter.render_mail("account/email/password_reset", "user@example.com", {"request": request})
        self.assertEqual(message.subject, "Immigration97")
        self.assertEqual(message.body, "Immigration97 reset")
        self.assertEqual(message.alternatives[0][0], "<p>Immigration97</p>")
        self.assertEqual(message.from_email, "Immigration97 <mail@example.com>")

    def test_receipt_uses_brand_contact_and_preserves_amount(self):
        from billing.pdf import build_receipt_pdf
        from decimal import Decimal
        from django.utils import timezone
        receipt = SimpleNamespace(receipt_number="R-123", issued_at=timezone.now(),
            get_status_display=lambda: "Payé", client_full_name="Learner",
            client_email="user@example.com", client_phone="", service_name="E-Shelle Premium",
            service_description="Préparation E-Shelle", amount=Decimal("9000"), currency="XAF",
            payment_method="MTN", transaction_id="TX-123")
        with patch("billing.pdf.canvas.Canvas") as canvas:
            build_receipt_pdf(receipt, brand="Immigration97")
        text = " ".join(str(call.args[-1]) for call in canvas.return_value.drawString.call_args_list)
        self.assertNotIn("shelle", text.lower())
        self.assertIn("+237 693 649 944", text)
        self.assertIn("9 000 XAF", text)
        self.assertEqual(receipt.service_name, "E-Shelle Premium")

    def test_allauth_html_only_email_is_supported(self):
        request = RequestFactory().get("/")
        request.is_immigration97 = True
        original = EmailMessage("E-Shelle", "<p>E-Shelle</p>", "old@example.com", ["user@example.com"])
        with patch.object(DefaultAccountAdapter, "render_mail", return_value=original):
            message = AccountAdapter().render_mail("prefix", "user@example.com", {"request": request})
        self.assertEqual(message.body, "<p>Immigration97</p>")

    def test_historical_nested_feedback_is_branded_without_mutation(self):
        original = {"recommendations": ["Cours E-SHELLE"], "score": 90}
        self.assertEqual(public_text(original, "Immigration97"),
                         {"recommendations": ["Cours Immigration97"], "score": 90})
        self.assertEqual(original["recommendations"], ["Cours E-SHELLE"])
