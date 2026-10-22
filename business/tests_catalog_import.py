from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, Mock

from .catalog_import import CatalogImportError, import_catalog_csv
from .models import BusinessCatalogItem, BusinessProfile


class TchokosCatalogImportTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="tchokos-owner")
        self.business = BusinessProfile.objects.create(
            owner=self.owner,
            module=BusinessProfile.Module.GENERAL,
            name="Tchokos Sarl",
            city="Douala",
        )

    def upload(self, content):
        return SimpleUploadedFile("catalogue.csv", content.encode("utf-8"), content_type="text/csv")

    def test_csv_import_creates_and_updates_by_sku_without_deleting_missing_products(self):
        existing = BusinessCatalogItem.objects.create(
            business=self.business,
            sku="TC-01",
            title="Ancien produit",
            price_label="500 FCFA",
        )
        untouched = BusinessCatalogItem.objects.create(
            business=self.business,
            sku="TC-02",
            title="Produit conservé",
        )
        csv_file = self.upload(
            "sku,nom,prix_detail,prix_gros,stock,categorie\n"
            "TC-01,Riz 25 kg,25000,22000,12,Céréales\n"
            "TC-03,Huile 5 L,7000,6300,8,Épicerie\n"
        )

        result = import_catalog_csv(self.business, csv_file)

        existing.refresh_from_db()
        self.assertEqual(result, {"created": 1, "updated": 1, "total": 2})
        self.assertEqual(existing.title, "Riz 25 kg")
        self.assertEqual(existing.category, "Céréales")
        self.assertEqual(existing.price_label, "25000 FCFA")
        self.assertEqual(existing.prix_gros_xaf, 22000)
        self.assertEqual(existing.stock_quantity, 12)
        self.assertTrue(BusinessCatalogItem.objects.filter(pk=untouched.pk).exists())
        self.assertEqual(BusinessCatalogItem.objects.filter(business=self.business).count(), 3)

    def test_tchokos_ten_product_sample_import(self):
        csv_file = self.upload(
            "sku,nom,prix_detail,prix_gros,stock,categorie\n"
            "TC-01,Ciment 50 kg,4850,4500,120,Ciment\n"
            "TC-02,Carreaux 60x60,8500,7900,80,Carrelage\n"
            "TC-03,Toles bac,12000,10800,45,Toiture\n"
            "TC-04,Fer 8 mm,3500,3200,200,Fer\n"
            "TC-05,Fer 10 mm,5200,4800,160,Fer\n"
            "TC-06,Peinture 20 L,18500,17000,35,Peinture\n"
            "TC-07,Pointes 5 cm,2500,2200,90,Quincaillerie\n"
            "TC-08,Tuyau PVC 100,6500,5900,55,Plomberie\n"
            "TC-09,Robinet lavabo,7500,6800,40,Plomberie\n"
            "TC-10,Tole lisse,9500,8700,60,Toiture\n"
        )

        result = import_catalog_csv(self.business, csv_file)

        self.assertEqual(result, {"created": 10, "updated": 0, "total": 10})
        cement = BusinessCatalogItem.objects.get(business=self.business, sku="TC-01")
        tiles = BusinessCatalogItem.objects.get(business=self.business, sku="TC-02")
        sheets = BusinessCatalogItem.objects.get(business=self.business, sku="TC-03")
        self.assertEqual(cement.price_label, "4850 FCFA")
        self.assertEqual(tiles.price_label, "8500 FCFA")
        self.assertEqual(sheets.category, "Toiture")
        self.assertEqual(BusinessCatalogItem.objects.filter(business=self.business).count(), 10)

    @patch("business.models.BusinessCatalogItem.image.field.storage.url", return_value="https://cdn.example/product.jpg")
    @patch("business.models.BusinessCatalogItem.image.field.storage.save", return_value="business/catalogue/product.jpg")
    @patch("e_shelle_ai.services.openai_service.EshelleAIService")
    @patch("phone_ocr_agent.services.extract_from_image")
    def test_photo_import_creates_product(self, extract_image, ai_service, _save_image, _image_url):
        from types import SimpleNamespace

        from .catalog_import import import_from_photo

        extract_image.return_value = SimpleNamespace(text="Ciment 32.5 4850 FCFA prix gros 4500 stock 120")
        completion = Mock()
        completion.choices = [
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"sku":"TC-PHOTO-01","nom":"Ciment 32.5","nom_en":"Cement 32.5","prix_detail":4850,"prix_gros":4500,"stock":120,"categorie":"Ciment"}'
                )
            )
        ]
        ai_service.return_value.client.chat.completions.create.return_value = completion
        photo = SimpleUploadedFile("ciment.jpg", b"image-bytes", content_type="image/jpeg")

        result = import_from_photo(photo, self.business.pk)

        product = BusinessCatalogItem.objects.get(business=self.business, sku="TC-PHOTO-01")
        self.assertTrue(result["created"])
        self.assertEqual(result["product"]["nom"], "Ciment 32.5")
        self.assertEqual(product.title_en, "Cement 32.5")
        self.assertEqual(product.price_label, "4850 FCFA")
        extract_image.assert_called_once_with(photo)

    def test_invalid_file_does_not_partially_import(self):
        csv_file = self.upload(
            "sku,nom,prix_detail,prix_gros,stock,categorie\n"
            "TC-01,Riz 25 kg,25000,22000,12,Céréales\n"
            "TC-02,Huile 5 L,invalid,6300,8,Épicerie\n"
        )

        with self.assertRaises(CatalogImportError):
            import_catalog_csv(self.business, csv_file)

        self.assertFalse(BusinessCatalogItem.objects.filter(business=self.business).exists())

    def test_business_owner_can_upload_csv_from_catalog_page(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("business:catalog_import_csv", args=[self.business.pk]),
            {
                "catalog_csv": self.upload(
                    "sku,nom,prix_detail,prix_gros,stock,categorie\n"
                    "TC-01,Riz 25 kg,25000,22000,12,Céréales\n"
                )
            },
        )

        self.assertRedirects(
            response,
            reverse("business:catalog_manage", args=[self.business.pk]),
        )
        self.assertTrue(
            BusinessCatalogItem.objects.filter(
                business=self.business,
                sku="TC-01",
                prix_gros_xaf=22000,
                stock_quantity=12,
            ).exists()
        )

    def test_another_business_owner_cannot_import_catalog(self):
        other_owner = get_user_model().objects.create_user(username="other-business-owner")
        self.client.force_login(other_owner)

        response = self.client.post(
            reverse("business:catalog_import_csv", args=[self.business.pk]),
            {"catalog_csv": self.upload("invalid")},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(BusinessCatalogItem.objects.filter(business=self.business).exists())
