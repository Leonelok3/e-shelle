from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
import io

@override_settings(MEDIA_ROOT="/tmp/django_test_media")  # isole les fichiers de test
class PhotosFlowTests(TestCase):
    def _fake_image(self, w=800, h=1000, color=(200, 200, 200)):
        img = Image.new("RGB", (w, h), color)
        bio = io.BytesIO()
        img.save(bio, format="JPEG")
        bio.seek(0)
        return SimpleUploadedFile("test.jpg", bio.read(), content_type="image/jpeg")

    def test_full_flow_generate_then_result(self):
        # 1) Home
        r = self.client.get(reverse("photos:index"))
        self.assertEqual(r.status_code, 200)

        # 2) Submit (👉 fichier dans data, pas de FILES=, pas de format="multipart")
        img = self._fake_image()
        r2 = self.client.post(reverse("photos:submit"), {
            "photo_type": "dv_lottery",
            "image": img,
        })
        self.assertEqual(r2.status_code, 302)  # redirection vers result

        # 3) Result page
        r3 = self.client.get(r2["Location"])
        self.assertEqual(r3.status_code, 200)
        self.assertContains(r3, "Résultat")

    def test_pay_and_download_block(self):
        img = self._fake_image()
        r2 = self.client.post(reverse("photos:submit"), {
            "photo_type": "dv_lottery",
            "image": img,
        })
        self.assertEqual(r2.status_code, 302)

        # Récupère job_id depuis l'URL /visa-photo/result/<uuid>/
        result_url = r2["Location"].rstrip("/")
        job_id = result_url.split("/")[-1]

        # Sans payer → 404
        resp_dl_block = self.client.get(reverse("photos:download", args=[job_id]))
        self.assertEqual(resp_dl_block.status_code, 404)

        # Mock paiement
        self.client.get(reverse("photos:pay", args=[job_id]))

        # Download ok
        resp_dl = self.client.get(reverse("photos:download", args=[job_id]))
        self.assertEqual(resp_dl.status_code, 200)
        self.assertIn(resp_dl["Content-Type"], ("image/jpeg", "application/octet-stream"))
