from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from .models import ProspectBusiness, whatsapp_status_q


class VerificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.client.force_login(self.user)
        self.prospect = ProspectBusiness.objects.create(nom="Test", whatsapp="+237699123456")

    def verify(self, status="confirmed", number="+237699123456"):
        return self.client.post(f"/commercial-agent/prospects/{self.prospect.pk}/whatsapp-verification/", {"verification": status, "number": number})

    def test_confirm_and_invalidate_after_number_change(self):
        self.assertFalse(ProspectBusiness.objects.filter(whatsapp_status_q("confirmed")).exists())
        self.assertEqual(self.verify().status_code, 302)
        self.assertTrue(ProspectBusiness.objects.filter(whatsapp_status_q("confirmed")).exists())
        ProspectBusiness.objects.filter(pk=self.prospect.pk).update(whatsapp="+237699123457")
        self.prospect.refresh_from_db()
        self.assertEqual(self.prospect.effective_whatsapp_verification, "unknown")
        self.assertFalse(ProspectBusiness.objects.filter(whatsapp_status_q("confirmed")).exists())

    def test_absent_and_stale_submission(self):
        self.assertEqual(self.verify(number="old").status_code, 409)
        self.assertEqual(self.verify("absent").status_code, 302)
        self.assertTrue(ProspectBusiness.objects.filter(whatsapp_status_q("absent")).exists())
        self.assertFalse(ProspectBusiness.objects.filter(whatsapp_status_q("confirmed")).exists())

    def test_post_and_staff_required(self):
        url = f"/commercial-agent/prospects/{self.prospect.pk}/whatsapp-verification/"
        self.assertEqual(self.client.get(url).status_code, 405)
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.verify().status_code, 302)
        self.prospect.refresh_from_db()
        self.assertEqual(self.prospect.whatsapp_verification, "unknown")

    @patch("commercial_agent.views.render", return_value=HttpResponse())
    def test_default_list_and_unknown_filter(self, render):
        self.client.get("/commercial-agent/prospects/")
        self.assertEqual(list(render.call_args.args[2]["page_obj"]), [])
        self.client.get("/commercial-agent/prospects/?whatsapp_status=unknown&q=Test&page=2")
        context = render.call_args.args[2]
        self.assertEqual(list(context["page_obj"]), [self.prospect])
        self.assertIn("whatsapp_status=unknown", context["pagination_query"])
        self.assertNotIn("page=", context["pagination_query"])
        self.verify()
        self.client.get("/commercial-agent/prospects/")
        self.assertEqual(list(render.call_args.args[2]["page_obj"]), [self.prospect])
