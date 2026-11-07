from django.test import TestCase, override_settings


class PublicMetaReviewPagesTests(TestCase):
    def test_homepage_promotes_all_applications_with_responsive_cta_content(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vous cherchez un autre service E-Shelle")
        self.assertContains(response, "Découvrez nos applications pour les entreprises")
        self.assertContains(response, 'class="home-apps-cta-link" href="/applications/"')
        self.assertContains(response, "Voir toutes les applications E-Shelle")

    def test_homepage_uses_meta_label_and_hides_unverified_content(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E-Shelle est Tech Provider Meta (App ID 1841260056892991)")
        self.assertContains(response, "Créer ma fiche business gratuite")
        self.assertContains(response, "Connecter WhatsApp Business")
        self.assertContains(response, "Mise en service WhatsApp : 25 000 FCFA une fois")
        self.assertContains(response, "5 000 FCFA")
        self.assertContains(response, "15 000 FCFA")
        self.assertContains(response, "30 000 FCFA")
        self.assertContains(response, 'href="/business/restaurants/"')
        self.assertContains(response, 'href="/business/grossistes/"')
        for unpublished_text in (
            "VERCEL",
            "Marcelle Kenfack",
            "Rodrigue Tchakounté",
            "Amadou Bello",
            "automated 80% of client inquiries",
            "a automatisé 80% des réponses",
            "première page",
        ):
            with self.subTest(unpublished_text=unpublished_text):
                self.assertNotContains(response, unpublished_text)

    def test_restaurant_sales_page_uses_existing_registration_and_discovery_routes(self):
        response = self.client.get("/business/restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organisez votre menu")
        self.assertContains(response, "disponibilité des plats")
        self.assertContains(response, 'href="/resto/inscription/"')
        self.assertContains(response, 'href="/resto/restaurants/"')

    def test_wholesale_sales_page_describes_catalogue_and_existing_csv_import(self):
        response = self.client.get("/business/grossistes/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "prix de gros")
        self.assertContains(response, "SKU")
        self.assertContains(response, "Importez un fichier CSV")
        self.assertContains(response, "pas de catégorie « Grossiste » dédiée")
        self.assertContains(response, 'href="/business/onboarding/"')
        self.assertContains(response, 'href="/tarifs/#merchant-plans-title"')

    @override_settings(LANGUAGE_CODE="en")
    def test_sector_sales_pages_include_aligned_english_copy(self):
        pages = {
            "/business/restaurants/": ("Organize your menu", "Register my restaurant"),
            "/business/grossistes/": ("wholesale prices", "Import an existing CSV"),
        }
        for path, expected_copy in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                for text in expected_copy:
                    self.assertContains(response, text)

    def test_whatsapp_business_page_explains_setup_offer_and_limits(self):
        response = self.client.get("/services/whatsapp-business/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "25 000 FCFA")
        self.assertContains(response, "5 000 FCFA par 30 jours")
        self.assertContains(response, "ne garantit pas qu’un numéro ou un compte ne sera jamais limité ou suspendu")
        self.assertContains(response, "/whatsapp-commerce/provider-referral/")

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
        self.assertContains(response, "E-Shelle est Tech Provider Meta (App ID 1841260056892991)")
        self.assertContains(response, 'href="/services/whatsapp-business/"')
        self.assertContains(response, "Installation WhatsApp Business API")
        self.assertContains(response, "Soyez visible. Donnez envie. Gardez le contact.")
        self.assertContains(response, "Être trouvé")
        self.assertContains(response, "Présenter vos offres")
        self.assertContains(response, "Garder le contact")
        self.assertContains(response, "Les campagnes WhatsApp nécessitent une formule éligible")
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
