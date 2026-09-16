import io
import json
import math
import tempfile
import uuid
import wave
import shutil
import subprocess
import struct
from unittest import skipUnless
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import AppPlan, AppSubscription
from audio_studio.forms import VoiceOverForm
from audio_studio.models import VoiceOverJob, MusicTrackJob
from adgen.models import AdCampaign, AdContent, StudioUsage
from adgen.services.studio_usage import reserve, finish, limits_for, usage_for, StudioLimitError


class StudioTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="studio", password="test")
        self.other = get_user_model().objects.create_user(username="other", password="test")
        self.plan = AppPlan.objects.get(slug="adgen-studio-essentiel")
        self.sub = AppSubscription.objects.create(user=self.user, plan=self.plan, status="active", expires_at=timezone.now() + timedelta(days=30))
        self.campaign = AdCampaign.objects.create(user=self.user, nom_produit="Savon local", description="Savon artisanal", prix="1500", cible="237600000000", modules_selected=["titres"], status="done")
        self.content = AdContent.objects.create(campaign=self.campaign, voice_over="Découvrez notre savon. Commandez aujourd’hui.")
        self.campaign.photo_produit = "adgen/products/test.png"
        self.campaign.save()
        self.client.force_login(self.user)

    def test_new_plans_and_legacy_rights(self):
        self.assertEqual(self.plan.price_xaf, 3000)
        self.assertEqual(limits_for(self.user)["video"], 5)
        old = AppPlan.objects.get(slug="adgen-starter")
        self.assertFalse(old.is_active)
        self.sub.plan = old
        self.sub.save()
        self.assertEqual(limits_for(self.user)["video"], 10)
        self.assertEqual(limits_for(self.user)["text"], 30)

    def test_expired_subscription_with_exhausted_trial_cannot_reserve(self):
        self.sub.expires_at = timezone.now() - timedelta(seconds=1)
        self.sub.save()
        StudioUsage.objects.bulk_create([StudioUsage(user=self.user, resource="text", is_trial=True, status="consumed", request_key=f"trial-{i}") for i in range(3)])
        with self.assertRaises(StudioLimitError):
            reserve(self.user, "voice", 10)

    def test_quota_reservation_and_idempotent_refund(self):
        job = reserve(self.user, "voice", 3000)
        with self.assertRaises(StudioLimitError):
            reserve(self.user, "voice", 1)
        finish(job, release=True)
        finish(job, release=True)
        self.assertEqual(usage_for(self.user).get("voice", 0), 0)
        reserve(self.user, "voice", 3000)

    def test_uncertain_failure_counts_but_allows_next_attempt(self):
        job = reserve(self.user, "voice", 2000)
        finish(job, failed=True)
        with self.assertRaises(StudioLimitError):
            reserve(self.user, "voice", 1001)
        reserve(self.user, "voice", 1000)

    def test_same_request_cannot_generate_twice(self):
        job = reserve(self.user, "music", key="same")
        finish(job)
        with self.assertRaises(StudioLimitError):
            reserve(self.user, "music", key="same")

    def test_rolling_window_and_upgrade_do_not_reset_usage(self):
        job = reserve(self.user, "voice", 3000)
        finish(job)
        self.sub.plan = AppPlan.objects.get(slug="adgen-studio-createur")
        self.sub.save()
        self.assertEqual(usage_for(self.user)["voice"], 3000)
        StudioUsage.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(days=31))
        self.assertEqual(usage_for(self.user).get("voice", 0), 0)

    def test_navigation_and_prefilled_campaign(self):
        response = self.client.get(reverse("adgen:studio_audio"), {"campaign": self.campaign.pk})
        self.assertContains(response, "Voix et musique")
        self.assertEqual(response.context["voiceover_form"].initial["script"], self.content.voice_over)
        self.assertContains(self.client.get(reverse("adgen:detail", args=[self.campaign.pk])), "Associer ces médias")
        self.assertContains(self.client.get(reverse("adgen:studio_pricing")), "3 000 FCFA")
        self.assertEqual(self.client.get(reverse("audio_studio:dashboard")).status_code, 200)

    def test_foreign_campaign_is_not_prefilled(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("adgen:studio_audio"), {"campaign": self.campaign.pk}).status_code, 404)

    def test_old_audio_post_requires_payment_after_trial(self):
        StudioUsage.objects.bulk_create([StudioUsage(user=self.other, resource="text", is_trial=True, status="consumed", request_key=f"trial-{i}") for i in range(3)])
        self.client.force_login(self.other)
        with patch("audio_studio.views.generate_voiceover_audio") as generate:
            response = self.client.post(reverse("audio_studio:voiceover_create"), {})
        self.assertEqual(response.status_code, 302)
        self.assertIn("app=adgen", response.url)
        generate.assert_not_called()

    def test_audio_form_rejects_foreign_profile_and_truncation(self):
        form = VoiceOverForm(user=self.user, data={"title": "Test", "script": "a" * 4001, "mode": "local", "openai_voice": "nova", "request_key": uuid.uuid4()})
        self.assertFalse(form.is_valid())
        self.assertIn("script", form.errors)

    @override_settings(ADGEN_STUDIO_CLONING_ENABLED=True)
    def test_cloning_is_not_an_unmetered_paid_option(self):
        form = VoiceOverForm(user=self.user, data={"title": "Test", "script": "Bonjour", "mode": "clone", "openai_voice": "nova", "request_key": uuid.uuid4()})
        self.assertFalse(form.is_valid())
        self.assertIn("mode", form.errors)

    @override_settings(OPENAI_API_KEY="test-not-a-real-key")
    def test_voice_is_charged_once_and_attached_to_campaign(self):
        def generate(job):
            job.status = "done"
            job.duration_seconds = 8
            job.save()
        data = {"title": "Annonce", "script": "Bonjour à tous", "mode": "local", "openai_voice": "nova", "request_key": str(uuid.uuid4()), "campaign": self.campaign.pk}
        with patch("audio_studio.views.generate_voiceover_audio", side_effect=generate) as generate_mock:
            self.assertEqual(self.client.post(reverse("audio_studio:voiceover_create"), data).status_code, 302)
            self.client.post(reverse("audio_studio:voiceover_create"), data)
            self.assertEqual(generate_mock.call_count, 1)
        self.content.refresh_from_db()
        self.assertEqual(self.content.studio_voice.user_id, self.user.pk)
        self.assertEqual(usage_for(self.user)["voice"], len(data["script"]))

    def test_missing_provider_configuration_is_free(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            self.client.post(reverse("audio_studio:voiceover_create"), {"title": "Annonce", "script": "Bonjour", "mode": "local", "openai_voice": "nova", "request_key": str(uuid.uuid4())})
        self.assertFalse(StudioUsage.objects.filter(user=self.user).exists())

    def test_cannot_attach_another_users_audio(self):
        voice = VoiceOverJob.objects.create(user=self.other, title="Privé", script="Privé", status="done", audio_file="private.mp3")
        self.client.post(reverse("adgen:studio_media", args=[self.campaign.pk]), {"voice": voice.pk})
        self.content.refresh_from_db()
        self.assertIsNone(self.content.studio_voice_id)

    def test_render_reserves_before_dispatch_and_preserves_previous_video(self):
        self.campaign.photo_produit = "adgen/products/test.png"
        self.campaign.save()
        self.content.ad_video_url = "/media/previous.mp4"
        self.content.save()
        with patch("adgen.studio_views.start_render") as start:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse("adgen:api_generate_video_start", args=[self.campaign.pk]), "{}", content_type="application/json")
            self.assertEqual(response.status_code, 200)
            start.assert_called_once()
        self.assertEqual(usage_for(self.user)["video"], 1)
        self.content.refresh_from_db()
        self.assertEqual(self.content.ad_video_url, "/media/previous.mp4")
        second = self.client.post(reverse("adgen:api_generate_video_start", args=[self.campaign.pk]), "{}", content_type="application/json")
        self.assertEqual(second.status_code, 429)

    def test_poll_cannot_use_unrelated_operation(self):
        job = StudioUsage.objects.create(user=self.other, campaign=self.campaign, resource="video", request_key="other")
        response = self.client.get(reverse("adgen:api_generate_video_poll", args=[self.campaign.pk]), {"operation_name": f"studio:{job.pk}"})
        self.assertEqual(response.status_code, 404)
        with patch("adgen.views._check_ad_video_status") as provider:
            response = self.client.get(reverse("adgen:api_generate_video_poll", args=[self.campaign.pk]), {"operation_name": "openai:arbitrary"})
        self.assertEqual(response.status_code, 404)
        provider.assert_not_called()

    def test_sora_new_orders_are_disabled(self):
        response = self.client.post(reverse("adgen:api_generate_video_sora_start", args=[self.campaign.pk]))
        self.assertEqual(response.status_code, 410)

    def test_text_regeneration_keeps_video_state_and_media(self):
        from adgen.services.module_engine import ModuleEngine
        self.content.raw_json = {"video_operation_name": "legacy:1"}
        self.content.save()
        with patch("adgen.services.ai_service.AdGenAIService.generate", return_value={"titles": ["Savon"], "_tokens_used": 15}):
            ModuleEngine(self.campaign).run()
        self.content.refresh_from_db()
        self.assertEqual(self.content.raw_json["video_operation_name"], "legacy:1")
        self.assertEqual(usage_for(self.user)["text"], 1)

    def test_local_render_failure_refunds_once(self):
        from adgen.services.studio_render import run_render
        job = reserve(self.user, "video", campaign=self.campaign)
        with patch("adgen.services.studio_render.close_old_connections"), patch("adgen.services.video_composer.VideoComposer.compose_from_photos", side_effect=RuntimeError("test")):
            run_render(job.pk)
            run_render(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, "released")
        self.assertEqual(usage_for(self.user).get("video", 0), 0)

    @skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required for real media integration")
    def test_real_video_contains_selected_narration(self):
        from adgen.services.video_composer import VideoComposer
        from audio_studio.services import audio_duration
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            photo = io.BytesIO()
            Image.new("RGB", (300, 300), "#8040b0").save(photo, format="PNG")
            self.campaign.photo_produit.save("product.png", ContentFile(photo.getvalue()))
            sample = io.BytesIO()
            rate = 16000
            with wave.open(sample, "wb") as wav:
                wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
                wav.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 1000 * n / rate))) for n in range(rate)))
            voice = VoiceOverJob.objects.create(user=self.user, title="Narration témoin", script="Test", status="done", duration_seconds=1)
            voice.audio_file.save("voice.wav", ContentFile(sample.getvalue()))
            self.content.studio_voice = voice
            self.content.save()
            self.campaign.refresh_from_db()
            composer = VideoComposer(self.campaign, duration=3)
            url = composer.compose_from_photos()
            target = Path(directory) / url.removeprefix("/media/")
            self.assertTrue(target.is_file())
            self.assertAlmostEqual(audio_duration(target), 3, delta=.3)
            decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", str(target), "-ss", "0.2", "-t", "0.5", "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"], capture_output=True, check=True, timeout=30).stdout
            values = struct.unpack("<" + "h" * (len(decoded) // 2), decoded)
            def energy(freq):
                return abs(sum(v * complex(math.cos(2 * math.pi * freq * n / rate), math.sin(2 * math.pi * freq * n / rate)) for n, v in enumerate(values)))
            self.assertGreater(energy(1000), 5 * max(1, energy(900)))
