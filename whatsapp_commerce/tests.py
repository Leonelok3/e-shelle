import os
import json
import hashlib
import hmac
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile
from .inbox import process_business_whatsapp_webhook, send_business_reply
from .models import (
	BusinessWhatsAppConnection,
	BusinessWhatsAppContact,
	BusinessWhatsAppMessage,
	BusinessCatalogWhatsAppSync,
	ProductView,
	ProductWhatsAppSync,
	ScheduledBusinessWhatsAppMessage,
)
from .onboarding import MetaOnboardingError, connect_business
from .services import get_whatsapp_schema_extension, send_abandoned_cart_whatsapp, sync_product_to_whatsapp_catalog
from .entitlements import whatsapp_entitlements
from .automations import schedule_template_follow_up, send_due_template_follow_ups


class BusinessWhatsAppTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.owner = user_model.objects.create_user(username="wa-owner", password="not-used")
		self.other_owner = user_model.objects.create_user(username="wa-other", password="not-used")
		self.business = BusinessProfile.objects.create(
			owner=self.owner,
			module=BusinessProfile.Module.GENERAL,
			name="Boutique A",
		)
		self.other_business = BusinessProfile.objects.create(
			owner=self.other_owner,
			module=BusinessProfile.Module.GENERAL,
			name="Boutique B",
		)

	@patch("whatsapp_commerce.onboarding.requests.request")
	def test_embedded_signup_exchanges_token_registers_and_subscribes(self, request):
		responses = []
		for data in (
			{"access_token": "business-token-secret"},
			{"success": True},
			{"success": True},
		):
			response = Mock(ok=True)
			response.json.return_value = data
			responses.append(response)
		request.side_effect = responses

		with self.settings(
			WHATSAPP_TECH_PROVIDER_APP_ID="app-id",
			WHATSAPP_TECH_PROVIDER_APP_SECRET="app-secret",
			WHATSAPP_GRAPH_API_VERSION="v25.0",
		):
			connection, active = connect_business(
				self.business,
				code="one-time-code",
				waba_id="123456",
				phone_number_id="654321",
				meta_business_id="777",
				pin="123456",
			)

		self.assertTrue(active)
		self.assertEqual(connection.status, BusinessWhatsAppConnection.Status.ACTIVE)
		self.assertTrue(connection.phone_registered)
		self.assertTrue(connection.webhook_subscribed)
		self.assertNotIn("business-token-secret", connection.access_token_encrypted)
		self.assertEqual(request.call_count, 3)
		self.assertEqual(request.call_args_list[1].kwargs["json"]["pin"], "123456")
		self.assertTrue(request.call_args_list[2].args[1].endswith("/123456/subscribed_apps"))
		self.assertEqual(request.call_args_list[2].kwargs["headers"]["Authorization"], "Bearer business-token-secret")

	def test_webhook_routes_inbound_messages_to_the_matching_business(self):
		first = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="1001",
			phone_number_id="2001",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		first.set_access_token("first-token")
		first.save(update_fields=["access_token_encrypted"])
		second = BusinessWhatsAppConnection.objects.create(
			business=self.other_business,
			waba_id="1002",
			phone_number_id="2002",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		second.set_access_token("second-token")
		second.save(update_fields=["access_token_encrypted"])
		payload = {
			"entry": [
				{
					"id": "1001",
					"changes": [{
						"value": {
							"metadata": {"phone_number_id": "2001"},
							"contacts": [{"wa_id": "237699000001", "profile": {"name": "Amina"}}],
							"messages": [{
								"id": "wamid-business-1",
								"from": "237699000001",
								"type": "text",
								"text": {"body": "Bonjour"},
								"timestamp": "1791374400",
							}],
						},
					}],
				},
				{
					"id": "1002",
					"changes": [{
						"value": {
							"metadata": {"phone_number_id": "wrong-phone"},
							"messages": [{
								"id": "wamid-wrong-phone",
								"from": "237699000002",
								"type": "text",
								"text": {"body": "Must not be assigned"},
							}],
						},
					}],
				},
			],
		}

		process_business_whatsapp_webhook(payload)
		process_business_whatsapp_webhook(payload)

		self.assertEqual(BusinessWhatsAppContact.objects.filter(business=self.business).count(), 1)
		self.assertEqual(BusinessWhatsAppContact.objects.filter(business=self.other_business).count(), 0)
		contact = BusinessWhatsAppContact.objects.get(business=self.business)
		self.assertEqual(contact.display_name, "Amina")
		self.assertFalse(contact.marketing_opt_in)
		self.assertEqual(BusinessWhatsAppMessage.objects.filter(contact=contact).count(), 1)

	def test_stop_webhook_cancels_pending_follow_up(self):
		connection = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="stop-waba",
			phone_number_id="stop-phone",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000014",
			marketing_opt_in=True,
			consent_source="Formulaire daté 2026-10-01",
			consented_at=timezone.now(),
		)
		scheduled = ScheduledBusinessWhatsAppMessage.objects.create(
			contact=contact,
			connection=connection,
			template_name="rappel_service",
			template_language="fr",
			scheduled_for=timezone.now() + timezone.timedelta(hours=1),
		)
		process_business_whatsapp_webhook({
			"entry": [{
				"id": "stop-waba",
				"changes": [{
					"value": {
						"metadata": {"phone_number_id": "stop-phone"},
						"messages": [{
							"id": "wamid-stop-business",
							"from": "237699000014",
							"type": "text",
							"text": {"body": "STOP"},
						}],
					},
				}],
			}],
		})
		contact.refresh_from_db()
		scheduled.refresh_from_db()
		self.assertFalse(contact.marketing_opt_in)
		self.assertIsNotNone(contact.opted_out_at)
		self.assertEqual(scheduled.status, ScheduledBusinessWhatsAppMessage.Status.CANCELLED)

	@override_settings(WHATSAPP_APP_SECRET="webhook-test-secret")
	def test_tenant_webhook_does_not_copy_client_message_into_internal_inbox(self):
		from whatsapp_agent.models import MessageWhatsApp

		connection = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="3001",
			phone_number_id="4001",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		connection.set_access_token("business-token")
		connection.save(update_fields=["access_token_encrypted"])
		body = json.dumps({
			"object": "whatsapp_business_account",
			"entry": [{
				"id": "3001",
				"changes": [{
					"value": {
						"metadata": {"phone_number_id": "4001"},
						"messages": [{
							"id": "wamid-tenant-private",
							"from": "237699000003",
							"type": "text",
							"text": {"body": "Message privé client"},
						}],
					},
				}],
			}],
		})
		signature = "sha256=" + hmac.new(
			b"webhook-test-secret",
			body.encode(),
			hashlib.sha256,
		).hexdigest()

		response = self.client.post(
			"/whatsapp/webhook/",
			body,
			content_type="application/json",
			HTTP_X_HUB_SIGNATURE_256=signature,
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(BusinessWhatsAppMessage.objects.filter(wa_message_id="wamid-tenant-private").count(), 1)
		self.assertFalse(MessageWhatsApp.objects.exists())

	def test_customer_stop_prevents_business_reply_without_meta_call(self):
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000001",
			last_inbound_at=timezone.now(),
			opted_out_at=timezone.now(),
		)
		with patch("whatsapp_commerce.inbox._request_meta") as request:
			with self.assertRaisesMessage(MetaOnboardingError, "Ce contact a demandé"):
				send_business_reply(contact, "Réponse")
		request.assert_not_called()

	def test_business_dashboard_is_owner_scoped(self):
		self.client.force_login(self.other_owner)
		response = self.client.get(
			reverse("whatsapp_commerce:business_dashboard", args=[self.business.pk])
		)
		self.assertEqual(response.status_code, 404)
		self.client.force_login(self.owner)
		response = self.client.get(
			reverse("whatsapp_commerce:business_dashboard", args=[self.business.pk])
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "WhatsApp Business")

	@override_settings(WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True)
	def test_dashboard_shows_template_follow_up_controls_only_for_consented_contact(self):
		self.business.plan = BusinessProfile.Plan.BUSINESS
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=10)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="wa-ui-waba",
			phone_number_id="wa-ui-phone",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000016",
			marketing_opt_in=True,
			consent_source="Formulaire daté 2026-10-01",
			consented_at=timezone.now(),
		)
		self.client.force_login(self.owner)
		response = self.client.get(
			reverse("whatsapp_commerce:business_dashboard", args=[self.business.pk]),
			{"contact": contact.pk},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Charger les modèles approuvés de mon WABA")
		self.assertContains(response, "Planifier la relance")

	def test_signup_completion_rejects_invalid_session_state(self):
		self.client.force_login(self.owner)
		response = self.client.post(
			reverse("whatsapp_commerce:business_connect_complete", args=[self.business.pk]),
			data=json.dumps({"state": "wrong"}),
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 403)

	def test_whatsapp_entitlements_follow_active_plan_and_trial(self):
		self.assertFalse(whatsapp_entitlements(self.business)["can_use_crm"])
		self.business.plan = BusinessProfile.Plan.PRO
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=3)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		pro_features = whatsapp_entitlements(self.business)
		self.assertTrue(pro_features["can_connect"])
		self.assertTrue(pro_features["can_use_crm"])
		self.assertFalse(pro_features["can_sync_catalog"])

		self.business.plan = BusinessProfile.Plan.BUSINESS
		self.business.is_trial = True
		self.business.save(update_fields=["plan", "is_trial", "updated_at"])
		self.assertTrue(whatsapp_entitlements(self.business)["can_sync_catalog"])

		self.business.subscription_expires_at = timezone.now() - timezone.timedelta(days=1)
		self.business.save(update_fields=["subscription_expires_at", "updated_at"])
		self.assertFalse(whatsapp_entitlements(self.business)["can_use_crm"])

	def test_contact_pipeline_update_is_owner_scoped(self):
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000001",
		)
		other_contact = BusinessWhatsAppContact.objects.create(
			business=self.other_business,
			phone="+237699000002",
		)
		self.business.plan = BusinessProfile.Plan.PRO
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=3)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		self.client.force_login(self.owner)
		url = reverse(
			"whatsapp_commerce:business_contact_update",
			args=[self.business.pk, contact.pk],
		)
		response = self.client.post(url, {
			"pipeline_status": BusinessWhatsAppContact.PipelineStatus.QUALIFIED,
			"tags": "prioritaire, vendeur, prioritaire",
			"notes": "Rappeler après démonstration",
			"next_follow_up_at": "2030-02-03",
		})
		self.assertEqual(response.status_code, 302)
		contact.refresh_from_db()
		self.assertEqual(contact.pipeline_status, BusinessWhatsAppContact.PipelineStatus.QUALIFIED)
		self.assertEqual(contact.tags, ["prioritaire", "vendeur"])
		self.assertEqual(contact.notes, "Rappeler après démonstration")
		self.assertEqual(str(contact.next_follow_up_at), "2030-02-03")

		response = self.client.post(
			reverse(
				"whatsapp_commerce:business_contact_update",
				args=[self.business.pk, other_contact.pk],
			),
			{"pipeline_status": "won"},
		)
		self.assertEqual(response.status_code, 404)

	def test_expired_plan_hides_crm_contacts_without_deleting_them(self):
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000003",
		)
		self.business.plan = BusinessProfile.Plan.PRO
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=1)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		self.business.subscription_expires_at = timezone.now() - timezone.timedelta(seconds=1)
		self.business.save(update_fields=["subscription_expires_at", "updated_at"])
		self.client.force_login(self.owner)
		response = self.client.get(
			reverse("whatsapp_commerce:business_dashboard", args=[self.business.pk])
		)
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, contact.phone)
		self.assertTrue(BusinessWhatsAppContact.objects.filter(pk=contact.pk).exists())

	@override_settings(WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True)
	@patch("whatsapp_commerce.automations._request_meta")
	def test_follow_up_requires_consent_and_approved_template(self, request):
		self.business.plan = BusinessProfile.Plan.BUSINESS
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=10)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		connection = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="wa-template-waba",
			phone_number_id="wa-template-phone",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		connection.set_access_token("tenant-template-token")
		connection.save(update_fields=["access_token_encrypted"])
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000010",
		)
		request.return_value = {
			"data": [{
				"name": "suivi_client",
				"status": "APPROVED",
				"language": "fr",
				"category": "UTILITY",
				"components": [{"type": "BODY", "text": "Bonjour {{1}}, votre commande est prête."}],
			}],
		}
		kwargs = {
			"template_name": "suivi_client",
			"template_language": "fr",
			"body_parameters": ["Amina"],
			"scheduled_for": timezone.now() + timezone.timedelta(hours=1),
			"created_by": self.owner,
		}
		with self.assertRaisesMessage(MetaOnboardingError, "consentement marketing explicite"):
			schedule_template_follow_up(contact, **kwargs)
		request.assert_not_called()

		contact.marketing_opt_in = True
		contact.consent_source = "Formulaire site 2026-10-01"
		contact.consented_at = timezone.now()
		contact.save(update_fields=["marketing_opt_in", "consent_source", "consented_at"])
		scheduled = schedule_template_follow_up(contact, **kwargs)
		self.assertEqual(scheduled.status, ScheduledBusinessWhatsAppMessage.Status.SCHEDULED)
		self.assertEqual(scheduled.connection, connection)
		self.assertEqual(scheduled.body_parameters, ["Amina"])
		self.assertEqual(request.call_count, 1)
		self.assertEqual(request.call_args.args[1], "wa-template-waba/message_templates")

	@override_settings(WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True)
	@patch("whatsapp_commerce.automations._request_meta")
	def test_due_follow_up_sends_approved_template_once_and_records_meta_id(self, request):
		self.business.plan = BusinessProfile.Plan.BUSINESS
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=10)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		connection = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="wa-send-waba",
			phone_number_id="wa-send-phone",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		connection.set_access_token("tenant-send-token")
		connection.save(update_fields=["access_token_encrypted"])
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000011",
			marketing_opt_in=True,
			consent_source="Formulaire daté 2026-10-01",
			consented_at=timezone.now(),
		)
		scheduled = ScheduledBusinessWhatsAppMessage.objects.create(
			contact=contact,
			connection=connection,
			template_name="rappel_service",
			template_language="fr",
			body_parameters=["Amina"],
			scheduled_for=timezone.now() - timezone.timedelta(minutes=1),
			created_by=self.owner,
		)
		request.side_effect = [
			{"data": [{
				"name": "rappel_service",
				"status": "APPROVED",
				"language": "fr",
				"category": "UTILITY",
				"components": [{"type": "BODY", "text": "Bonjour {{1}}"}],
			}]},
			{"messages": [{"id": "wamid-scheduled-1"}]},
		]

		self.assertEqual(send_due_template_follow_ups(), 1)
		self.assertEqual(send_due_template_follow_ups(), 0)
		scheduled.refresh_from_db()
		self.assertEqual(scheduled.status, ScheduledBusinessWhatsAppMessage.Status.SENT)
		self.assertEqual(scheduled.wa_message_id, "wamid-scheduled-1")
		self.assertEqual(request.call_count, 2)
		send_payload = request.call_args.kwargs["payload"]
		self.assertEqual(send_payload["to"], "237699000011")
		self.assertEqual(send_payload["template"]["name"], "rappel_service")
		self.assertEqual(
			send_payload["template"]["components"][0]["parameters"][0]["text"],
			"Amina",
		)
		self.assertTrue(BusinessWhatsAppMessage.objects.filter(
			wa_message_id="wamid-scheduled-1",
			contact=contact,
			message_type="template",
		).exists())

	def test_revoking_consent_cancels_scheduled_messages(self):
		self.business.plan = BusinessProfile.Plan.PRO
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=10)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000012",
			marketing_opt_in=True,
			consent_source="Formulaire daté 2026-10-01",
			consented_at=timezone.now(),
		)
		connection = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="wa-cancel-waba",
			phone_number_id="wa-cancel-phone",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		scheduled = ScheduledBusinessWhatsAppMessage.objects.create(
			contact=contact,
			connection=connection,
			template_name="rappel_service",
			template_language="fr",
			scheduled_for=timezone.now() + timezone.timedelta(hours=1),
		)
		self.client.force_login(self.owner)
		response = self.client.post(reverse(
			"whatsapp_commerce:business_contact_consent",
			args=[self.business.pk, contact.pk],
		))
		self.assertEqual(response.status_code, 302)
		contact.refresh_from_db()
		scheduled.refresh_from_db()
		self.assertFalse(contact.marketing_opt_in)
		self.assertEqual(scheduled.status, ScheduledBusinessWhatsAppMessage.Status.CANCELLED)

	@override_settings(WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True)
	@patch("whatsapp_commerce.automations._request_meta")
	def test_opted_out_contact_is_not_sent_a_due_template(self, request):
		self.business.plan = BusinessProfile.Plan.BUSINESS
		self.business.subscription_expires_at = timezone.now() + timezone.timedelta(days=10)
		self.business.save(update_fields=["plan", "subscription_expires_at", "updated_at"])
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000013",
			marketing_opt_in=False,
			opted_out_at=timezone.now(),
		)
		connection = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="wa-optout-waba",
			phone_number_id="wa-optout-phone",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		scheduled = ScheduledBusinessWhatsAppMessage.objects.create(
			contact=contact,
			connection=connection,
			template_name="rappel_service",
			template_language="fr",
			scheduled_for=timezone.now() - timezone.timedelta(minutes=1),
		)
		self.assertEqual(send_due_template_follow_ups(), 0)
		request.assert_not_called()
		scheduled.refresh_from_db()
		self.assertEqual(scheduled.status, ScheduledBusinessWhatsAppMessage.Status.FAILED)

	@patch("whatsapp_commerce.automations._request_meta")
	def test_disabled_automation_flag_cancels_queue_without_meta_request(self, request):
		contact = BusinessWhatsAppContact.objects.create(
			business=self.business,
			phone="+237699000015",
		)
		connection = BusinessWhatsAppConnection.objects.create(
			business=self.business,
			waba_id="wa-disabled-waba",
			phone_number_id="wa-disabled-phone",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		scheduled = ScheduledBusinessWhatsAppMessage.objects.create(
			contact=contact,
			connection=connection,
			template_name="rappel_service",
			template_language="fr",
			scheduled_for=timezone.now() - timezone.timedelta(minutes=1),
		)
		self.assertEqual(send_due_template_follow_ups(), 0)
		request.assert_not_called()
		scheduled.refresh_from_db()
		self.assertEqual(scheduled.status, ScheduledBusinessWhatsAppMessage.Status.CANCELLED)


@override_settings(WHATSAPP_COMMERCE_ENABLED=True)
class WhatsAppCommerceServiceTests(TestCase):
	def test_business_catalog_price_parser_accepts_xaf_amounts_only(self):
		from .business_catalog import _price_in_minor_units

		self.assertEqual(_price_in_minor_units("2 500 XAF"), 250000)
		self.assertEqual(_price_in_minor_units("1,250 FCFA"), 125000)
		self.assertIsNone(_price_in_minor_units("Prix à discuter"))
		self.assertIsNone(_price_in_minor_units("2 500,50 XAF"))
		self.assertIsNone(_price_in_minor_units("Promo 20% - 2 500 XAF"))

	@patch("whatsapp_commerce.business_catalog._image_url", return_value="https://e-shelle.com/media/item.jpg")
	@patch("whatsapp_commerce.business_catalog._request_meta")
	@override_settings(WHATSAPP_COMMERCE_ENABLED=False)
	def test_business_catalog_sync_uses_own_waba_catalog_and_xaf_price(self, request, image_url):
		owner = get_user_model().objects.create_user(username="catalog-owner", password="test-password")
		business = BusinessProfile.objects.create(
			owner=owner,
			module=BusinessProfile.Module.GENERAL,
			name="Business catalogue",
			plan=BusinessProfile.Plan.BUSINESS,
			subscription_expires_at=timezone.now() + timezone.timedelta(days=10),
		)
		connection = BusinessWhatsAppConnection.objects.create(
			business=business,
			waba_id="801",
			phone_number_id="802",
			catalog_id="",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		connection.set_access_token("tenant-token")
		connection.save(update_fields=["access_token_encrypted"])
		item = BusinessCatalogItem.objects.create(
			business=business,
			title="Panier de fruits",
			description="Fruits locaux",
			price_label="2 500 XAF",
		)
		request.side_effect = [
			{"data": [{"id": "881", "name": "Catalogue"}]},
			{"id": "meta-item-801"},
		]

		from .business_catalog import sync_business_catalog_item

		self.assertTrue(sync_business_catalog_item(item))
		sync = BusinessCatalogWhatsAppSync.objects.get(business_catalog_item=item)
		self.assertEqual(sync.connection, connection)
		self.assertEqual(sync.whatsapp_product_id, "meta-item-801")
		self.assertEqual(sync.sync_status, BusinessCatalogWhatsAppSync.Status.SYNCED)
		self.assertEqual(request.call_args_list[0].args[:2], ("GET", "801/product_catalogs"))
		self.assertEqual(request.call_args_list[1].args[:2], ("POST", "881/products"))
		self.assertEqual(request.call_args_list[1].kwargs["token"], "tenant-token")
		product_data = request.call_args_list[1].kwargs["form_data"]
		self.assertEqual(product_data["price"], 250000)
		self.assertEqual(product_data["currency"], "XAF")
		self.assertIn(f"?produit={item.pk}", product_data["url"])

	@patch("whatsapp_commerce.business_catalog._request_meta")
	def test_business_catalog_sync_rejects_plan_without_catalog_entitlement(self, request):
		owner = get_user_model().objects.create_user(username="pro-owner", password="test-password")
		business = BusinessProfile.objects.create(
			owner=owner,
			module=BusinessProfile.Module.GENERAL,
			name="Business Pro",
			plan=BusinessProfile.Plan.PRO,
			subscription_expires_at=timezone.now() + timezone.timedelta(days=10),
		)
		connection = BusinessWhatsAppConnection.objects.create(
			business=business,
			waba_id="901",
			phone_number_id="902",
			status=BusinessWhatsAppConnection.Status.ACTIVE,
		)
		connection.set_access_token("pro-token")
		connection.save(update_fields=["access_token_encrypted"])
		item = BusinessCatalogItem.objects.create(business=business, title="Item", price_label="1000")

		from .business_catalog import sync_business_catalog_item

		self.assertFalse(sync_business_catalog_item(item))
		request.assert_not_called()

	@patch.dict(os.environ, {
		"WABA_ID": "waba-test",
		"WHATSAPP_PHONE_NUMBER_ID": "phone-test",
		"WHATSAPP_ACCESS_TOKEN": "test-token",
		"WHATSAPP_CATALOG_ID": "catalog-test",
	})
	@patch("whatsapp_commerce.services.requests.request")
	def test_product_sync_uses_catalog_id_and_records_meta_id(self, request):
		response = Mock(status_code=200)
		response.json.return_value = {"id": "meta-product-1"}
		request.return_value = response
		product = {
			"id": 17,
			"boutique_id": 3,
			"titre": "Formation test",
			"description": "Description produit",
			"prix": "2500",
			"is_published": True,
			"url": "https://e-shelle.com/boutique/formation-test/",
			"image_url": "https://e-shelle.com/media/product.jpg",
		}

		self.assertTrue(sync_product_to_whatsapp_catalog(product))

		sync = ProductWhatsAppSync.objects.get(boutique_product_id=17, waba_id="waba-test")
		self.assertEqual(sync.whatsapp_product_id, "meta-product-1")
		self.assertEqual(sync.sync_status, "synced")
		self.assertTrue(request.call_args.args[1].endswith("/catalog-test/products"))
		self.assertEqual(request.call_args.kwargs["data"]["retailer_id"], "17")

	@patch.dict(os.environ, {
		"WABA_ID": "waba-test",
		"WHATSAPP_PHONE_NUMBER_ID": "phone-test",
		"WHATSAPP_ACCESS_TOKEN": "test-token",
		"WHATSAPP_CATALOG_ID": "catalog-test",
	})
	@patch("whatsapp_commerce.services.requests.request", side_effect=requests.RequestException("offline"))
	def test_meta_failure_is_swallowed_and_recorded(self, request):
		product = {
			"id": 18,
			"boutique_id": 3,
			"titre": "Produit test",
			"description": "Description",
			"prix": "1000",
			"is_published": True,
			"url": "https://e-shelle.com/boutique/produit-test/",
			"image_url": "https://e-shelle.com/media/product.jpg",
		}

		self.assertFalse(sync_product_to_whatsapp_catalog(product))
		self.assertEqual(ProductWhatsAppSync.objects.get(boutique_product_id=18).sync_status, "failed")

	@patch("whatsapp_commerce.services.requests.request")
	def test_abandoned_message_requires_phone_consent(self, request):
		view = ProductView.objects.create(
			boutique_product_id=7,
			visitor_phone="+237699000001",
			whatsapp_opt_in=False,
		)

		self.assertFalse(send_abandoned_cart_whatsapp(view))
		request.assert_not_called()

	def test_schema_extension_is_additive(self):
		extension = get_whatsapp_schema_extension({
			"id": 4,
			"slug": "produit-test",
			"titre": "Produit test",
			"url": "https://e-shelle.com/boutique/produit-test/",
		})

		self.assertEqual(extension["additionalProperty"][0]["value"], "WhatsApp officiel")
