from django.test import TestCase, override_settings


class PublicMetaReviewPagesTests(TestCase):
    def test_whatsapp_business_page_explains_setup_offer_and_limits(self):
        response = self.client.get("/services/whatsapp-business/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "25 000 FCFA")
        self.assertContains(response, "5 000 FCFA par 30 jours")
        self.assertContains(response, "ne garantit pas qu’un numéro ou un compte ne sera jamais limité ou suspendu")
        self.assertContains(response, "https://wa.me/237680625082?")

    def test_contact_page_shows_business_locations_and_contacts(self):
        response = self.client.get("/services/contact/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Siège Social: Bepanda, Douala, BP 4241, Littoral, Cameroun")
        self.assertContains(response, "Bureau Technique:")
        self.assertContains(response, "Bafoussam, Région de l")
        self.assertContains(response, "Ouest, Cameroun")
        self.assertContains(response, "Business ID: 1837509733943082 | App ID: 1841260056892991")
        self.assertContains(response, "+237 680 625 082")
        self.assertContains(response, "e.shelleltd@gmail.com")
        self.assertContains(response, "Lun-Sam 8h-18h (WAT)")

    def test_global_footer_has_business_information_and_legal_links(self):
        response = self.client.get("/services/contact/")

        self.assertContains(response, "SaaS E-commerce Platform for SMEs in Cameroon")
        self.assertContains(response, "Business ID: 1837509733943082")
        self.assertContains(response, "App ID Meta: 1841260056892991")
        self.assertContains(response, "E-Shelle est officiellement Tech Provider Meta.")
        self.assertContains(response, 'href="/services/whatsapp-business/"')
        self.assertContains(response, "Installation WhatsApp Business API")
        self.assertContains(response, 'href="/privacy-policy"')
        self.assertContains(response, 'href="/terms"')
        self.assertContains(response, 'href="/about"')

    @override_settings(LANGUAGE_CODE="en")
    def test_meta_app_review_pages_are_public_and_truthful(self):
        pages = {
            "/privacy-policy": (
                "Privacy Policy",
                "WhatsApp Business Platform Data",
                "vps3581805",
                "We do not sell personal data.",
            ),
            "/terms": (
                "Terms of Service",
                "SaaS e-commerce platform for SMEs in Cameroon",
                "Bepanda, Douala, BP 4241",
            ),
            "/about": (
                "About E-Shelle",
                "Djiala Feuguim Leonel",
                "Bafoussam",
                "E-Shelle is a Meta Tech Provider",
                "Meta permissions, account eligibility and configuration",
            ),
        }
        for path, expected_text in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                for text in expected_text:
                    self.assertContains(response, text)
