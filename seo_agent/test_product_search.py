import json
import re
from datetime import timedelta
from unittest.mock import patch
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile


@override_settings(SITE_URL="https://e-shelle.com")
class ProductSearchTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="product-search-owner")
        self.business = BusinessProfile.objects.create(
            owner=self.owner, name="Atelier Ndom", city="Douala", plan=BusinessProfile.Plan.BUSINESS,
            activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            subscription_expires_at=timezone.now() + timedelta(days=7), ai_credits=2,
        )
        self.item = BusinessCatalogItem.objects.create(
            business=self.business, title="Panier en raphia", item_type=BusinessCatalogItem.ItemType.PRODUCT,
            description="Panier tressé à la main.", price_label="19,99 EUR",
        )
        self.path = reverse("whatsapp_commerce:catalogue_offer", args=[self.business.public_slug, self.item.pk])

    def product_schema(self, response):
        self.assertEqual(response.status_code, 200)
        scripts = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', response.content.decode(), re.S)
        return next(data for script in scripts if (data := json.loads(script)).get("@type") == "Product")

    def test_detail_has_canonical_facts_and_storefront_links_to_it(self):
        response = self.client.get(self.path, {"campagne": "test", "utm_source": "whatsapp"})
        url = "https://e-shelle.com" + self.path
        self.assertContains(response, f'<link rel="canonical" href="{url}">', html=True)
        schema = self.product_schema(response)
        self.assertEqual(schema["url"], url)
        self.assertEqual(schema["offers"]["price"], "19.99")
        self.assertEqual(schema["offers"]["priceCurrency"], "EUR")
        self.assertNotIn("availability", schema["offers"])
        self.assertContains(self.client.get(self.business.get_absolute_url()), f'href="{self.path}"')

    def test_unclear_prices_and_unpublished_items_do_not_become_search_facts(self):
        self.item.price_label = "Sur devis"
        self.item.description = "</script><script>texte du vendeur</script>"
        self.item.save()
        schema = self.product_schema(self.client.get(self.path))
        self.assertNotIn("offers", schema)
        self.assertEqual(schema["description"], self.item.description)

        index = self.client.get(reverse("product_sitemap_index"))
        page = self.client.get(reverse("product_sitemap_page", args=[1]))
        self.assertIn("https://e-shelle.com" + reverse("product_sitemap_page", args=[1]), [n.text for n in ElementTree.fromstring(index.content).findall(".//{*}loc")])
        self.assertIn("https://e-shelle.com" + self.path, [n.text for n in ElementTree.fromstring(page.content).findall(".//{*}loc")])
        self.assertContains(self.client.get(reverse("robots_txt")), "/sitemap-produits.xml")
        BusinessCatalogItem.objects.create(business=self.business, title="Offre maintenue", price_label="5000 XAF")
        self.item.is_active = False
        self.item.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(self.path).status_code, 404)
        self.assertNotContains(self.client.get(reverse("product_sitemap_page", args=[1])), self.path)

    def test_owner_reviews_ai_draft_before_it_changes_catalogue(self):
        self.client.force_login(self.owner)
        args = [self.business.pk, self.item.pk]
        prepare = reverse("business:catalog_item_generate_description", args=args)
        publish = reverse("business:catalogue_seo_publish", args=args)
        with patch("e_shelle_ai.services.openai_service.EshelleAIService") as agent:
            agent.return_value.chat_simple.return_value = "Panier en raphia tressé à la main."
            self.client.post(prepare, {"product_facts": "Diamètre 30 cm"})
        self.item.refresh_from_db()
        self.business.refresh_from_db()
        self.assertEqual(self.item.description, "Panier tressé à la main.")
        self.assertEqual(self.business.ai_credits, 1)
        draft = self.client.session["catalogue_seo_draft"]
        self.client.post(publish, {"key": "invalid", "reviewed_description": "Texte incorrect"})
        self.item.refresh_from_db()
        self.assertEqual(self.item.description, "Panier tressé à la main.")
        self.client.post(publish, {"key": draft["key"], "reviewed_description": "Panier en raphia, diamètre 30 cm."})
        self.item.refresh_from_db()
        self.assertEqual(self.item.description, "Panier en raphia, diamètre 30 cm.")
        self.assertNotIn("catalogue_seo_draft", self.client.session)
