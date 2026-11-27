import hashlib
import hmac
import io
import json
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile
from whatsapp_agent.media import private_storage
from whatsapp_agent.models import MessageWhatsApp
from .catalog_forwarding import Status, dispatch_catalog_submissions, process_submission
from .catalog_messages import parse_offer
from .models import WhatsAppCatalogSender, WhatsAppCatalogSubmission


@override_settings(
    WHATSAPP_APP_SECRET="catalog-webhook-secret",
    WHATSAPP_CATALOG_IMPORT_WABA_ID="catalog-waba",
    WHATSAPP_CATALOG_IMPORT_PHONE_ID="catalog-receiver-id",
    WHATSAPP_CATALOG_IMPORT_NUMBER="+237699101000",
    WHATSAPP_CATALOG_IMPORT_TOKEN="catalog-import-token",
    SITE_URL="https://e-shelle.com",
)
class CatalogForwardingTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="catalog-whatsapp-owner")
        self.business = BusinessProfile.objects.create(
            owner=self.owner, name="Boutique Electrique", city="Douala",
            plan=BusinessProfile.Plan.BUSINESS, activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=30),
        )
        self.client.force_login(self.owner)
        self.url = reverse("whatsapp_commerce:catalog_forwarding", args=[self.business.pk])
        self.phone = "+237699101001"
        storage = TemporaryDirectory()
        self.addCleanup(storage.cleanup)
        settings_override = override_settings(MEDIA_ROOT=storage.name, WHATSAPP_PRIVATE_MEDIA_ROOT=storage.name + "/private")
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def receive(self, message_id, text="", *, sender=None, waba="catalog-waba", photo=None, valid=True, phone_id="catalog-receiver-id"):
        message = {"from": (sender or self.phone).lstrip("+"), "id": message_id}
        if photo:
            message.update(type="image", image={"id": photo, "caption": text})
        else:
            message.update(type="text", text={"body": text})
        payload = {"object": "whatsapp_business_account", "entry": [{
            "id": waba, "changes": [{"field": "messages", "value": {
                "metadata": {"phone_number_id": phone_id}, "messages": [message],
            }}],
        }]}
        body = json.dumps(payload)
        signature = "sha256=" + hmac.new(b"catalog-webhook-secret", body.encode(), hashlib.sha256).hexdigest()
        return self.client.post("/whatsapp/webhook/", body, content_type="application/json",
                                HTTP_X_HUB_SIGNATURE_256=signature if valid else "bad")

    def pair(self, *, auto=True):
        self.client.post(self.url, {"action": "pair", "sender_phone": self.phone})
        code = self.client.session[f"catalog_pair_{self.business.pk}"]
        self.assertContains(self.client.get(self.url), code)
        self.receive("bad-sender", f"LIER {code}", sender="+237699101002")
        self.receive("bad-waba", f"LIER {code}", waba="unknown-waba")
        self.assertIsNone(WhatsAppCatalogSender.objects.get(business=self.business).phone)
        self.assertEqual(self.receive("bad-signature", f"LIER {code}", valid=False).status_code, 403)
        self.assertEqual(self.receive("pair", f"LIER {code}").status_code, 200)
        self.assertEqual(WhatsAppCatalogSender.objects.get(business=self.business).phone, self.phone)
        if auto:
            self.client.post(self.url, {"action": "settings", "auto_publish": "on"})
        return WhatsAppCatalogSender.objects.get(business=self.business)

    @patch("whatsapp_commerce.catalog_forwarding._request_meta")
    @patch("whatsapp_commerce.catalog_forwarding.retrieve_media")
    def test_forward_caption_and_photo_once_in_background(self, download, meta):
        self.assertContains(self.client.get(self.url), "Du groupe WhatsApp à ta fiche")
        self.pair()
        text = "Ventilateur rechargeable, 18 000 F CFA, réf. VENT-01"
        self.receive("offer", text, photo="meta-image")
        self.receive("offer", text, photo="meta-image")
        self.assertEqual(WhatsAppCatalogSubmission.objects.count(), 1)
        self.assertFalse(MessageWhatsApp.objects.exists())
        download.assert_not_called()
        meta.assert_not_called()

        def download_image(_id, _token, output, **kwargs):
            Image.new("RGB", (24, 24), "#5d413b").save(output, format="JPEG")
            output.seek(0)
            return "image/jpeg"

        download.side_effect = download_image
        submission = WhatsAppCatalogSubmission.objects.get()
        publish = Mock()
        self.assertEqual(dispatch_catalog_submissions(publish), 1)
        self.assertEqual(dispatch_catalog_submissions(publish), 0)
        publish.assert_called_once_with(submission.pk)
        process_submission(submission.pk)
        process_submission(submission.pk)
        item = BusinessCatalogItem.objects.get(business=self.business)
        self.assertEqual((item.title, item.sku, item.price_label), ("Ventilateur rechargeable", "VENT-01", "18 000 F CFA"))
        self.assertIsNone(item.stock_quantity)
        self.assertTrue(item.image.name)
        download.assert_called_once()
        share_path = reverse("whatsapp_commerce:catalogue_offer", args=[self.business.public_slug, item.pk])
        self.assertIn(share_path, meta.call_args.kwargs["payload"]["text"]["body"])
        self.assertContains(self.client.get(self.url), "Ouvrir la page à partager")

    @patch("whatsapp_commerce.tasks.notify_whatsapp_catalog_published.apply_async")
    @patch("whatsapp_commerce.catalog_forwarding._request_meta")
    def test_price_change_requires_owner_validation_and_rejects_stale_copy(self, meta, notify):
        self.pair()
        item = BusinessCatalogItem.objects.create(
            business=self.business, title="Lampe", sku="LAMP-1", price_label="9 000 F CFA", stock_quantity=4,
        )
        self.receive("new-price", "Lampe, 10 000 XAF, SKU LAMP-1")
        draft = WhatsAppCatalogSubmission.objects.get()
        process_submission(draft.pk)
        draft.refresh_from_db()
        self.assertEqual(draft.status, Status.REVIEW)
        item.refresh_from_db()
        self.assertEqual(item.price_label, "9 000 F CFA")
        url = reverse("whatsapp_commerce:catalog_forward_review", args=[self.business.pk, draft.pk])
        self.assertContains(self.client.get(url), "Mettre à jour et publier cet article")
        fields = {"title": "Lampe", "price_amount": "10000", "currency": "XAF", "sku": "lamp-1", "action": "update"}
        self.assertContains(self.client.post(url, {**fields, "item_version": "ancienne"}), "L’article a changé")
        WhatsAppCatalogSubmission.objects.filter(pk=draft.pk).update(title="", sku="")
        self.assertContains(self.client.post(url, {**fields, "action": "publish"}), "Mettre à jour et publier cet article")
        item.refresh_from_db()
        self.assertEqual(item.price_label, "9 000 F CFA")
        other = get_user_model().objects.create_user(username="different-owner")
        self.client.force_login(other)
        self.assertEqual(self.client.post(url, fields).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(url, {**fields, "item_version": f"{item.pk}:{item.updated_at.isoformat()}"}).status_code, 302)
        self.assertEqual(self.client.post(url, fields).status_code, 404)
        item.refresh_from_db()
        self.assertEqual((item.price_label, item.stock_quantity), ("10 000 F CFA", 4))
        notify.assert_called_once()
        meta.assert_called_once()

    @patch("whatsapp_commerce.catalog_forwarding._request_meta")
    def test_wrong_sender_and_ambiguous_offer_never_publish(self, meta):
        self.pair()
        self.receive("not-linked", "Lampe, 5 000 XAF", sender="+237699101002")
        self.receive("not-clear", "Pack de lampes de 18 000–20 000 FCFA")
        draft = WhatsAppCatalogSubmission.objects.get()
        process_submission(draft.pk)
        draft.refresh_from_db()
        self.assertEqual(draft.status, Status.REVIEW)
        self.assertIsNone(draft.price_amount)
        self.assertFalse(BusinessCatalogItem.objects.exists())
        self.assertIn("à valider", meta.call_args.kwargs["payload"]["text"]["body"])

    def test_prices_and_stock_are_explicit(self):
        details, reason = parse_offer("Produit : Câble USB\nPrix : 19,90 EUR\nStock : 0")
        self.assertFalse(reason)
        self.assertEqual((str(details["price_amount"]), details["currency"], details["stock"]), ("19.90", "EUR", 0))
        self.assertTrue(parse_offer("Câble 2000 F")[1])
        self.assertTrue(parse_offer("Câble A 2000 XAF et B 4000 XAF")[1])
        self.assertTrue(parse_offer("Câble 2000 XAF Contact : +237699101002")[1])

    @patch("whatsapp_commerce.catalog_forwarding._request_meta")
    def test_revoking_sender_blocks_pending_auto_publication(self, meta):
        self.pair()
        self.receive("queued", "Ventilateur, 18 000 XAF")
        self.client.post(self.url, {"action": "disconnect"})
        draft = WhatsAppCatalogSubmission.objects.get()
        process_submission(draft.pk)
        draft.refresh_from_db()
        self.assertEqual(draft.status, Status.REJECTED)
        self.assertFalse(BusinessCatalogItem.objects.exists())
        meta.assert_not_called()

    @patch("whatsapp_commerce.catalog_forwarding._request_meta")
    @patch("phone_ocr_agent.services.extract_from_image", return_value=Mock(text="Ventilateur, 18 000 XAF"))
    @patch("whatsapp_commerce.catalog_forwarding.retrieve_media")
    def test_photo_without_caption_suggests_values_for_owner_only(self, download, ocr, meta):
        self.pair()

        def write_image(_id, _token, output, **kwargs):
            Image.new("RGB", (24, 24)).save(output, format="PNG")
            output.seek(0)
            return "image/png"

        download.side_effect = write_image
        self.receive("photo-only", photo="meta-image")
        draft = WhatsAppCatalogSubmission.objects.get()
        process_submission(draft.pk)
        draft.refresh_from_db()
        self.assertEqual((draft.status, draft.title, draft.currency), (Status.REVIEW, "Ventilateur", "XAF"))
        self.assertFalse(BusinessCatalogItem.objects.exists())
        ocr.assert_called_once()
        url = reverse("whatsapp_commerce:catalog_forward_image", args=[self.business.pk, draft.pk])
        photo = self.client.get(url)
        self.assertEqual(photo.status_code, 200)
        self.assertTrue(b"".join(photo.streaming_content).startswith(b"\xff\xd8"))
        other = get_user_model().objects.create_user(username="unauthorized-photo-viewer")
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def process_separate_photo(self):
        def write_image(_id, _token, output, **kwargs):
            Image.new("RGB", (24, 24)).save(output, format="PNG")
            output.seek(0)
            return "image/png"

        self.receive("separate-photo", photo="meta-image")
        draft = WhatsAppCatalogSubmission.objects.get(wa_message_id="separate-photo")
        with patch("whatsapp_commerce.catalog_forwarding.retrieve_media", side_effect=write_image), patch(
            "whatsapp_commerce.catalog_forwarding._suggest_from_photo", return_value={},
        ):
            process_submission(draft.pk)
        draft.refresh_from_db()
        return draft

    @patch("whatsapp_commerce.catalog_forwarding._request_meta")
    @patch("whatsapp_commerce.tasks.notify_whatsapp_catalog_published.apply_async")
    def test_separate_photo_follows_its_draft_until_publication(self, notify, meta):
        self.pair(auto=False)
        self.receive("fan-draft", "Ventilateur, 18 000 XAF, SKU VENT-01")
        target = WhatsAppCatalogSubmission.objects.get(wa_message_id="fan-draft")
        process_submission(target.pk)
        source = self.process_separate_photo()
        url = reverse("whatsapp_commerce:catalog_forward_attach", args=[self.business.pk, source.pk])
        self.assertContains(self.client.get(url, {"q": "VENT-01"}), "Ventilateur")
        preview = self.client.get(url, {"target": f"draft:{target.pk}"})
        self.assertContains(preview, "Confirmer le rattachement au brouillon")
        response = self.client.post(url, {"approval": preview.context["approval"]})
        self.assertEqual(response.status_code, 302)
        source.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual((source.status, source.attached_to_id, source.private_image), (Status.ATTACHED, target.pk, ""))
        self.assertEqual((target.status, str(target.price_amount), target.sku), (Status.REVIEW, "18000.00", "VENT-01"))
        self.assertTrue(private_storage().exists(target.private_image))
        self.assertFalse(BusinessCatalogItem.objects.exists())
        self.assertEqual(self.client.post(url, {"approval": preview.context["approval"]}).status_code, 404)
        self.client.post(response.url, {
            "action": "publish", "title": target.title, "price_amount": "18000",
            "currency": "XAF", "sku": target.sku,
        })
        item = BusinessCatalogItem.objects.get(business=self.business)
        self.assertTrue(item.image.name)
        self.assertEqual(item.price_label, "18 000 F CFA")
        self.assertContains(self.client.get(self.url), reverse("whatsapp_commerce:catalogue_offer", args=[self.business.public_slug, item.pk]))
        notify.assert_called_once()

    @patch("whatsapp_commerce.catalog_forwarding._request_meta")
    def test_published_item_photo_requires_a_fresh_and_scoped_confirmation(self, meta):
        self.pair()
        self.receive("fan-published", "Ventilateur, 18 000 XAF, SKU VENT-01, stock 4")
        process_submission(WhatsAppCatalogSubmission.objects.get(wa_message_id="fan-published").pk)
        item = BusinessCatalogItem.objects.get(business=self.business)
        source = self.process_separate_photo()
        url = reverse("whatsapp_commerce:catalog_forward_attach", args=[self.business.pk, source.pk])
        other = BusinessProfile.objects.create(owner=self.owner, name="Autre fiche de test", city="Douala")
        foreign_item = BusinessCatalogItem.objects.create(business=other, title="Autre ventilateur")
        self.assertEqual(self.client.get(url, {"target": f"item:{foreign_item.pk}"}).status_code, 404)
        preview = self.client.get(url, {"target": f"item:{item.pk}"})
        self.assertContains(preview, "Confirmer la photo de l’article")
        self.client.post(url, {"approval": "signature-invalid"})
        item.stock_quantity = 7
        item.save(update_fields=["stock_quantity", "updated_at"])
        self.client.post(url, {"approval": preview.context["approval"]})
        item.refresh_from_db()
        self.assertFalse(item.image)
        self.assertTrue(private_storage().exists(source.private_image))
        preview = self.client.get(url, {"target": f"item:{item.pk}"})
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url, {"approval": preview.context["approval"]}).status_code, 302)
        item.refresh_from_db()
        previous_path = source.private_image
        source.refresh_from_db()
        self.assertTrue(item.image.name)
        self.assertFalse(private_storage().exists(previous_path))
        self.assertEqual((item.price_label, item.stock_quantity, item.sku), ("18 000 F CFA", 7, "VENT-01"))
        self.assertEqual((source.status, source.item_id), (Status.ATTACHED, item.pk))
