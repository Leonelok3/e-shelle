import xml.etree.ElementTree as ET
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse

from seo_agent.services import SEOAuditAgent, LocalSEOAgent, build_sitemap_entries


class RobotsTxtTestCase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="e-shelle.com")

    def test_robots_txt_status_and_content_type(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])

    def test_robots_txt_allows_ai_search_bots(self):
        response = self.client.get("/robots.txt")
        content = response.content.decode("utf-8")
        ai_bots = [
            "OAI-SearchBot",
            "ChatGPT-User",
            "Claude-SearchBot",
            "Claude-User",
            "PerplexityBot",
            "GPTBot",
            "ClaudeBot",
            "Google-Extended",
        ]
        for bot in ai_bots:
            self.assertIn(f"User-agent: {bot}", content)

    def test_robots_txt_disallows_private_paths(self):
        response = self.client.get("/robots.txt")
        content = response.content.decode("utf-8")
        self.assertIn("Disallow: /admin/", content)
        self.assertIn("Disallow: /accounts/", content)
        self.assertIn("Disallow: /dashboard/", content)
        self.assertIn("Disallow: /seo/", content)

    def test_robots_txt_references_canonical_sitemap(self):
        response = self.client.get("/robots.txt")
        content = response.content.decode("utf-8")
        expected_sitemap = f"Sitemap: {settings.SITE_URL.rstrip('/')}/sitemap.xml"
        self.assertIn(expected_sitemap, content)


class SitemapXmlTestCase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="e-shelle.com")

    def test_sitemap_xml_status_and_valid_xml(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])
        
        root = ET.fromstring(response.content)
        self.assertTrue(root.tag.endswith("urlset"))
        
        locs = [elem.text for elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertTrue(len(locs) > 10)
        base = settings.SITE_URL.rstrip("/")
        self.assertIn(f"{base}/", locs)
        self.assertIn(f"{base}/resto/", locs)
        self.assertIn(f"{base}/business/local/", locs)

    def test_build_sitemap_entries_structure(self):
        entries = build_sitemap_entries(None)
        self.assertIsInstance(entries, list)
        self.assertTrue(len(entries) > 0)
        first = entries[0]
        self.assertIn("loc", first)
        self.assertIn("label", first)
        self.assertIn("kind", first)


class LLMsTxtTestCase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="e-shelle.com")

    def test_llms_txt_status_and_identity(self):
        response = self.client.get("/llms.txt")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("E-Shelle", content)
        self.assertIn("Cameroon", content)
        self.assertIn("https://e-shelle.com/business/local/", content)
        self.assertIn("https://e-shelle.com/sitemap.xml", content)
        self.assertIn("https://e-shelle.com/robots.txt", content)


class SEOAuditAgentTestCase(TestCase):
    def test_audit_agent_run(self):
        agent = SEOAuditAgent()
        result = agent.run(limit=50)
        self.assertIn("score", result)
        self.assertIn("files_scanned", result)
        self.assertIn("core_signal_pages", result)
        self.assertIn("critical", result)
        self.assertIn("warning", result)
        self.assertIn("issues", result)
        self.assertGreater(result["files_scanned"], 0)
        self.assertGreaterEqual(result["score"], 0)

    def test_template_files_filters_base_and_private(self):
        agent = SEOAuditAgent()
        files = agent._template_files()
        for f in files:
            stem = f.stem.lower()
            self.assertNotEqual(stem, "base")
            self.assertFalse(stem.startswith("base_"))
            self.assertFalse(stem.endswith("_base"))
            parts = {part.lower() for part in f.parts}
            self.assertNotIn("admin_custom", parts)
            self.assertNotIn("bureau", parts)


class LocalSEOTestCase(TestCase):
    def test_local_seo_ideas(self):
        agent = LocalSEOAgent()
        ideas = agent.ideas()
        self.assertGreater(len(ideas), 10)
        first = ideas[0]
        self.assertIn("title", first)
        self.assertIn("url", first)
        self.assertIn("intent", first)
        self.assertIn("cta", first)

    def test_local_seo_prioritized_pages(self):
        agent = LocalSEOAgent()
        priorities = agent.prioritized_pages(limit=10)
        self.assertIsInstance(priorities, list)


class GEOLandingViewTestCase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="e-shelle.com")

    def test_geo_landing_valid(self):
        response = self.client.get("/business/local/douala/restaurants/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Restaurants", content)
        self.assertIn("Douala", content)
        self.assertIn("application/ld+json", content)
        self.assertIn("BreadcrumbList", content)
        self.assertIn("FAQPage", content)

    def test_geo_landing_alias_redirect(self):
        # /business/local/douala/gaz/ should 301 redirect to /business/local/douala/livraison-gaz/
        response = self.client.get("/business/local/douala/gaz/")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/business/local/douala/livraison-gaz/")

    def test_geo_index(self):
        response = self.client.get("/business/local/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Services locaux au Cameroun", content)
        self.assertIn("application/ld+json", content)


class BaseCanonicalAndRobotsTestCase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="e-shelle.com")

    def test_homepage_canonical_and_robots(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn('<link rel="canonical" href="https://e-shelle.com/">', content)
        self.assertIn('max-image-preview:large', content)
        self.assertIn('og:site_name', content)
        self.assertIn('Organization', content)
        self.assertIn('WebSite', content)


class FacebookAutoShareAntiCasseTestCase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="e-shelle.com")

    def test_facebook_auto_share_does_not_break_seo(self):
        # 1. Vérification que le sitemap canonique est toujours 100% valide
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])
        root = ET.fromstring(response.content)
        self.assertTrue(root.tag.endswith("urlset"))

        # 2. Vérification que robots.txt et llms.txt répondent toujours avec succès
        robots_res = self.client.get("/robots.txt")
        self.assertEqual(robots_res.status_code, 200)
        llms_res = self.client.get("/llms.txt")
        self.assertEqual(llms_res.status_code, 200)

        # 3. Vérification du service facebook_auto_share
        from business.models import BusinessProfile, FacebookShareLog
        from core.services.facebook_auto_share import (
            should_share,
            share_premium_to_facebook_page,
            build_aeo_message,
        )

        # Création d'un faux business pour tester le service sans impact
        test_biz = BusinessProfile(
            name="Salon VIP Test",
            slug="salon-vip-test",
            city="Douala",
            district="Akwa",
            module=BusinessProfile.Module.SERVICES,
            plan=BusinessProfile.Plan.PREMIUM,
            activation_status=BusinessProfile.ActivationStatus.ACTIVE,
            is_active=True,
            whatsapp="690000000",
        )

        # Vérification des propriétés ajoutées
        self.assertTrue(test_biz.is_premium)
        self.assertTrue(test_biz.is_published)
        self.assertEqual(test_biz.nom, "Salon VIP Test")

        # Vérification de la construction de message AEO
        msg = build_aeo_message(test_biz)
        self.assertIn("Salon VIP Test", msg)
        self.assertIn("Douala", msg)
        self.assertIn("https://e-shelle.com/business/", msg)

        # Vérification du mode dry_run (ne fait aucun appel HTTP externe)
        post_id = share_premium_to_facebook_page(test_biz, dry_run=True)
        self.assertTrue(bool(post_id))
        self.assertIn("dry_run_post", post_id)

        # Vérification de should_share pour non-premium
        test_biz.plan = BusinessProfile.Plan.FREE
        self.assertFalse(should_share(test_biz))
