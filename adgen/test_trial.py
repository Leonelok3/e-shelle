from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import AppPlan, AppSubscription
from adgen.models import AdCampaign, AdContent, StudioUsage
from adgen.services.studio_usage import reserve, finish, trial_remaining, usage_for, StudioLimitError


class TrialTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="trial")
        self.client.force_login(self.user)

    def exhaust(self):
        for resource in ("text", "music", "video"):
            finish(reserve(self.user, resource))

    def test_three_shared_uses_and_no_monthly_reset(self):
        self.exhaust()
        self.assertEqual(trial_remaining(self.user), 0)
        StudioUsage.objects.update(created_at=timezone.now() - timedelta(days=90))
        with self.assertRaises(StudioLimitError):
            reserve(self.user, "voice", 100)
        self.assertEqual(StudioUsage.objects.count(), 3)

    def test_reserved_jobs_count_and_refund_is_idempotent(self):
        jobs = [reserve(self.user, resource) for resource in ("text", "video", "music")]
        with self.assertRaises(StudioLimitError):
            reserve(self.user, "voice", 10)
        finish(jobs[0], release=True)
        finish(jobs[0], release=True)
        self.assertEqual(trial_remaining(self.user), 1)
        reserve(self.user, "voice", 1000)
        self.assertEqual(trial_remaining(self.user), 0)

    def test_login_access_and_exhausted_generation_gate(self):
        self.assertEqual(self.client.get(reverse("adgen:dashboard")).status_code, 200)
        self.exhaust()
        self.assertEqual(self.client.get(reverse("adgen:dashboard")).status_code, 200)
        response = self.client.get(reverse("adgen:create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("app=adgen", response.url)
        response = self.client.post(reverse("adgen:api_generate", args=[999]))
        self.assertEqual(response.status_code, 402)
        self.client.logout()
        self.assertIn("login", self.client.get(reverse("adgen:dashboard")).url)

    def test_results_remain_accessible_and_deletion_does_not_reset(self):
        campaign = AdCampaign.objects.create(user=self.user, nom_produit="Produit", prix="1000", cible="Clients", status="done")
        AdContent.objects.create(campaign=campaign, titles=["Test"])
        self.exhaust()
        StudioUsage.objects.update(campaign=campaign)
        self.assertEqual(self.client.get(reverse("adgen:detail", args=[campaign.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("adgen:export", args=[campaign.pk])).status_code, 200)
        campaign.delete()
        self.assertEqual(trial_remaining(self.user), 0)

    def test_paid_quota_is_separate_and_trial_voice_is_bounded(self):
        with self.assertRaises(StudioLimitError):
            reserve(self.user, "voice", 1001)
        self.assertEqual(trial_remaining(self.user), 3)
        self.exhaust()
        AppSubscription.objects.create(user=self.user, plan=AppPlan.objects.get(slug="adgen-studio-essentiel"), status="active")
        self.assertEqual(usage_for(self.user), {})
        job = reserve(self.user, "text")
        self.assertFalse(job.is_trial)
        self.assertEqual(usage_for(self.user)["text"], 1)
