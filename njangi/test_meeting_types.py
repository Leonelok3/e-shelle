from django.test import TestCase
from django.urls import reverse

from .models import Group
from .tests import make_user, make_group


class MeetingTypeTests(TestCase):
    def setUp(self):
        self.user = make_user("meeting_creator")
        self.client.force_login(self.user)
        self.url = reverse("njangi:create_group")
        self.data = {
            "name": "Réunion test", "frequency": "monthly",
            "contribution_amount": "10000", "fund_loan_rate": "10",
            "fund_deposit_rate": "5", "base_fund_required": "0",
            "penalty_per_day": "1000",
        }

    def test_selector_and_creation_for_each_type(self):
        page = self.client.get(self.url)
        self.assertContains(page, 'name="meeting_type"')
        for value, label in Group.MEETING_TYPE_CHOICES:
            with self.subTest(meeting_type=value):
                self.assertContains(page, f'<option value="{value}"')
                response = self.client.post(self.url, {
                    **self.data, "name": f"Réunion {label}", "meeting_type": value,
                })
                group = Group.objects.get(name=f"Réunion {label}")
                self.assertEqual(group.meeting_type, value)
                self.assertRedirects(response, reverse("njangi:bureau_dashboard", kwargs={"slug": group.slug}))
                self.assertTrue(group.memberships.filter(user=self.user, role="president").exists())
                detail = self.client.get(reverse("njangi:group_detail", kwargs={"slug": group.slug}))
                self.assertContains(detail, f'rounded-full">{label}</span>')

    def test_invalid_or_missing_type_does_not_create_group(self):
        for value in ("invalid", ""):
            response = self.client.post(self.url, {**self.data, "meeting_type": value})
            self.assertEqual(response.status_code, 200)
            self.assertIn("meeting_type", response.context["form"].errors)
        self.assertFalse(Group.objects.exists())

    def test_selection_is_preserved_on_validation_error(self):
        response = self.client.post(self.url, {**self.data, "name": "", "meeting_type": "church"})
        self.assertContains(response, '<option value="church" selected>Église</option>', html=True)

    def test_default_for_existing_creation_paths(self):
        self.assertEqual(make_group(self.user).meeting_type, "other")
