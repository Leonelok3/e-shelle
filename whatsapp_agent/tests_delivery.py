import hashlib
import hmac
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Campagne, MessageEnvoi, WhatsAppTestSend
from .services import WhatsAppService


class DeliveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", first_name="Leonel", is_staff=True)
        self.client.force_login(self.user)
        self.campaign = Campagne.objects.create(nom="Test", message_template="Bonjour")
        self.original = MessageEnvoi.objects.create(campagne=self.campaign,
            numero_whatsapp="+237699000001", message_final="Bonjour")
        self.url = reverse("whatsapp_agent:wa_test", args=[self.campaign.pk])

    @patch("whatsapp_agent.services.requests.post")
    def test_hello_world_uses_english_and_no_body_parameters(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"messages": [{"id": "wamid.test"}]}
        result = WhatsAppService.envoyer_message("+237699000002", "template:hello_world", template_params=["Client"])
        self.assertTrue(result["success"])
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], "237699000002")
        self.assertEqual(payload["template"], {"name": "hello_world", "language": {"code": "en_US"}})

    @patch("whatsapp_agent.services.WhatsAppService.envoyer_message")
    def test_campaign_template_is_not_prefixed_with_free_text(self, send):
        send.return_value = {"success": True, "message_id": "wamid.test", "erreur": ""}
        self.original.message_final = "template:deutsch_space_decouvert"
        self.original.save()
        response = self.client.post(self.url, {"numero_test": "+237699000002"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(send.call_args.args[1], "template:deutsch_space_decouvert")
        self.assertEqual(send.call_args.kwargs["template_params"], ["Leonel"])
        record = WhatsAppTestSend.objects.get()
        self.assertEqual(record.statut, "accepte")
        self.assertEqual(record.numero, "+237699000002")
        self.original.refresh_from_db()
        self.assertEqual(self.original.statut, "en_attente")
        self.assertEqual(self.campaign.messages.count(), 1)

    @patch("whatsapp_agent.services.WhatsAppService.envoyer_message")
    def test_explicit_template_language_and_parameters(self, send):
        send.return_value = {"success": True, "message_id": "wamid.test", "erreur": ""}
        self.client.post(self.url, {"numero_test": "+237699000002", "template_name": "hello_world",
            "template_language": "en_US", "template_params": "[]"})
        self.assertEqual(send.call_args.kwargs["template_name"], "hello_world")
        self.assertEqual(send.call_args.kwargs["template_language"], "en_US")
        self.assertEqual(send.call_args.kwargs["template_params"], [])

    @patch("whatsapp_agent.services.WhatsAppService.envoyer_message")
    def test_invalid_number_or_parameters_never_send(self, send):
        for fields in ({"numero_test": "123"}, {"numero_test": "+237699000002", "template_params": "{}"}):
            self.client.post(self.url, fields)
        send.assert_not_called()
        self.assertFalse(WhatsAppTestSend.objects.exists())

    @override_settings(WHATSAPP_DRY_RUN=True)
    @patch("whatsapp_agent.services.requests.post")
    def test_simulation_cannot_claim_real_delivery(self, post):
        self.client.post(self.url, {"numero_test": "+237699000002"})
        post.assert_not_called()
        self.assertEqual(WhatsAppTestSend.objects.get().statut, "simulation")

    def webhook(self, status, errors=None, signature=True):
        payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
            "statuses": [{"id": "wamid.test", "status": status, "errors": errors or []}]
        }}]}]}
        body = json.dumps(payload)
        signed = "sha256=" + hmac.new(b"test-secret", body.encode(), hashlib.sha256).hexdigest()
        return self.client.post("/whatsapp/webhook/", body, content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signed if signature else "invalid")

    def test_delivery_receipts_are_saved_and_out_of_order_sent_does_not_regress(self):
        record = WhatsAppTestSend.objects.create(campagne=self.campaign, numero="+237699000002",
            whatsapp_message_id="wamid.test", statut="accepte")
        for status in ["delivered", "read", "sent"]:
            self.assertEqual(self.webhook(status).status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.statut, "lu")

    def test_async_meta_error_is_visible(self):
        record = WhatsAppTestSend.objects.create(campagne=self.campaign, numero="+237699000002",
            whatsapp_message_id="wamid.test", statut="accepte")
        self.webhook("failed", [{"code": 131047, "title": "Re-engagement message"}])
        record.refresh_from_db()
        self.assertEqual(record.statut, "echec")
        self.assertIn("131047", record.erreur)

    def test_unsigned_receipt_is_rejected(self):
        self.assertEqual(self.webhook("delivered", signature=False).status_code, 403)

    @patch("whatsapp_agent.services.requests.post")
    def test_meta_rejection_is_not_success(self, post):
        post.return_value.status_code = 400
        post.return_value.json.return_value = {"error": {"code": 132001, "message": "Template does not exist"}}
        result = WhatsAppService.envoyer_template("+237699000002", "unknown")
        self.assertFalse(result["success"])
        self.assertIn("132001", result["erreur"])

    @patch("whatsapp_agent.services.WhatsAppService.envoyer_message")
    def test_nonstaff_cannot_send_test(self, send):
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.client.post(self.url, {"numero_test": "+237699000002"}).status_code, 302)
        send.assert_not_called()
