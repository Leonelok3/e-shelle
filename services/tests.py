from django.test import TestCase


class PublicMetaReviewPagesTests(TestCase):
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
        self.assertContains(response, "Candidature Tech Provider en cours d’examen par Meta.")
        self.assertContains(response, 'href="/privacy-policy"')
        self.assertContains(response, 'href="/terms"')
        self.assertContains(response, 'href="/about"')

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
                "subject to Meta's review and approval",
                "does not claim to be an approved Meta Tech Provider",
            ),
        }
        for path, expected_text in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                for text in expected_text:
                    self.assertContains(response, text)
