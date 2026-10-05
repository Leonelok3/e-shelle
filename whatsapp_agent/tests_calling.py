import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ContactWhatsApp, ConversationWhatsApp, WhatsAppCall
from .views import _handle_call_events


class WhatsAppCallingTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="call-staff", is_staff=True)
        self.client.force_login(user)
        self.contact = ContactWhatsApp.objects.create(numero="+237699000001", consentement_confirme=True)
        self.conversation = ConversationWhatsApp.objects.create(contact=self.contact)

    @patch("whatsapp_agent.views.initiate_call")
    @patch("whatsapp_agent.views.get_call_permission")
    def test_outgoing_call_requires_meta_permission(self, get_permission, initiate):
        get_permission.return_value = {
            "permission": {"status": "no_permission"},
            "actions": [{"action_name": "start_call", "can_perform_action": False}],
        }
        response = self.client.post(
            reverse("whatsapp_agent:wa_api_start_call", args=[self.conversation.pk]),
            data=json.dumps({"sdp_offer": "v=0\r\n"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        initiate.assert_not_called()
        self.assertFalse(WhatsAppCall.objects.exists())

    @patch("whatsapp_agent.views.initiate_call", return_value={"calls": [{"id": "meta-call-1"}]})
    @patch("whatsapp_agent.views.get_call_permission")
    def test_outgoing_call_starts_only_when_meta_allows_it(self, get_permission, initiate):
        get_permission.return_value = {
            "permission": {"status": "temporary"},
            "actions": [{"action_name": "start_call", "can_perform_action": True}],
        }
        response = self.client.post(
            reverse("whatsapp_agent:wa_api_start_call", args=[self.conversation.pk]),
            data=json.dumps({"sdp_offer": "v=0\r\n"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        call = WhatsAppCall.objects.get()
        self.assertEqual(call.meta_call_id, "meta-call-1")
        self.assertEqual(call.status, WhatsAppCall.STATUS_CONNECTING)
        self.assertEqual(initiate.call_args.args[2], str(call.pk))

    def test_incoming_call_webhook_is_idempotent(self):
        payload = {
            "calls": [{
                "id": "meta-inbound-1",
                "direction": "USER_INITIATED",
                "event": "connect",
                "from": "237699000001",
                "session": {"sdp_type": "offer", "sdp": "v=0\r\n"},
            }],
        }
        _handle_call_events(payload, {})
        _handle_call_events(payload, {})
        call = WhatsAppCall.objects.get(meta_call_id="meta-inbound-1")
        self.assertEqual(call.direction, WhatsAppCall.DIRECTION_INBOUND)
        self.assertEqual(call.status, WhatsAppCall.STATUS_RINGING)
        self.assertEqual(call.sdp_offer, "v=0\r\n")
        self.assertEqual(call.conversation.non_lus_count, 1)

    @patch("whatsapp_agent.views.post_call_action")
    def test_incoming_call_is_claimed_by_one_staff_user(self, post_action):
        call = WhatsAppCall.objects.create(
            conversation=self.conversation,
            contact=self.contact,
            meta_call_id="meta-inbound-claimed",
            direction=WhatsAppCall.DIRECTION_INBOUND,
            status=WhatsAppCall.STATUS_RINGING,
            sdp_offer="v=0\r\n",
        )
        url = reverse("whatsapp_agent:wa_api_call_action", args=[call.pk])
        response = self.client.post(
            url,
            data=json.dumps({"action": "pre_accept", "sdp_answer": "v=0\r\n"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        call.refresh_from_db()
        self.assertEqual(call.status, WhatsAppCall.STATUS_CONNECTING)
        self.assertEqual(call.initiated_by.username, "call-staff")

        other_staff = get_user_model().objects.create_user(username="other-call-staff", is_staff=True)
        self.client.force_login(other_staff)
        response = self.client.post(
            url,
            data=json.dumps({"action": "accept", "sdp_answer": "v=0\r\n"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        post_action.assert_called_once()
