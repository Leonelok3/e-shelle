from django.test import TestCase
from django.urls import reverse
from .models import Letter

class SmokeTests(TestCase):
    def test_pages_ok(self):
        for name in ["motivation_letter:home", "motivation_letter:generator", "motivation_letter:letter_list"]:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200)

    def test_create_letter_model(self):
        l = Letter.objects.create(full_name="Test", content="Lettre", language="fr", tone="pro", ats_score=80)
        self.assertTrue(l.pk)
