import json
import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from adgen.models import AdCampaign, AdContent
from adgen.services.timeline_planner import TimelinePlanner
from adgen.views import prepare_image_for_veo
from PIL import Image

User = get_user_model()

class TimelinePlannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.campaign = AdCampaign.objects.create(
            user=self.user,
            nom_produit="Super Robot Mixeur",
            description="Mixeur ultra-rapide de 1000W pour smoothies parfaits et soupes onctueuses. Robuste et durable.",
            prix="15 000 FCFA",
            ancien_prix="20 000 FCFA",
            cible="22890000000"
        )
        self.content = AdContent.objects.create(
            campaign=self.campaign,
            titles=["Super Robot Mixeur", "Mixeur ultra-rapide 1000W"],
            benefits=["Puissance 1000W", "Lames en titane", "Nettoyage facile"],
            voice_over="Découvrez le Super Robot Mixeur ! Un mixeur ultra-rapide de 1000W."
        )

    def test_timeline_timing_30s(self):
        planner = TimelinePlanner(self.campaign, duration=30)
        timeline = planner.get_timeline()
        
        # Verify 4 scenes are generated (Hook, Price, Avantage, CTA)
        self.assertEqual(len(timeline), 4)
        self.assertEqual(timeline["hook"], (0.0, 10.0))
        self.assertEqual(timeline["avantage"], (20.0, 30.0))
        self.assertEqual(timeline["cta"], (0.0, 30.0))
        
        content = planner.get_content_data()
        self.assertEqual(content["hook"], "Super Robot Mixeur")
        self.assertEqual(content["whatsapp"], "22890000000")

    def test_timeline_timing_15s(self):
        planner = TimelinePlanner(self.campaign, duration=15)
        timeline = planner.get_timeline()
        
        # Total duration must equal 15
        total_duration = max(val[1] for val in timeline.values())
        self.assertEqual(total_duration, 15)

    def test_timeline_timing_60s(self):
        planner = TimelinePlanner(self.campaign, duration=60)
        timeline = planner.get_timeline()
        
        total_duration = max(val[1] for val in timeline.values())
        self.assertEqual(total_duration, 60)


class BackgroundRendererTests(TestCase):
    def test_gradient_bilinear_render_horizontal(self):
        bg_config = {
            "bg_type": "gradient",
            "bg_gradient": ["#000000", "#FFFFFF"],
            "bg_grad_dir": "horizontal"
        }
        # Run drawing logic
        img = Image.new("RGBA", (108, 192))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        prepared_img_bytes = prepare_image_for_veo(buf, bg_config=bg_config)
        prepared_img = Image.open(io.BytesIO(prepared_img_bytes))
        
        # Check colors: left pixel should be dark/black, right pixel should be light/white
        pixel_left = prepared_img.getpixel((0, 96))
        pixel_right = prepared_img.getpixel((1279, 96))
        
        self.assertTrue(pixel_left[0] < 50)
        self.assertTrue(pixel_right[0] > 200)

    def test_gradient_bilinear_render_vertical(self):
        bg_config = {
            "bg_type": "gradient",
            "bg_gradient": ["#000000", "#FFFFFF"],
            "bg_grad_dir": "vertical"
        }
        img = Image.new("RGBA", (108, 192))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        prepared_img_bytes = prepare_image_for_veo(buf, bg_config=bg_config)
        prepared_img = Image.open(io.BytesIO(prepared_img_bytes))
        
        # Top pixel should be dark/black, bottom pixel should be light/white
        pixel_top = prepared_img.getpixel((640, 0))
        pixel_bottom = prepared_img.getpixel((640, 719))
        
        self.assertTrue(pixel_top[0] < 50)
        self.assertTrue(pixel_bottom[0] > 200)


class DjangoViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client.login(username="testuser", password="password123")
        
        self.campaign = AdCampaign.objects.create(
            user=self.user,
            nom_produit="Test Produit",
            description="Description du test.",
            prix="5 000 FCFA",
            cible="22890000000"
        )
        self.content = AdContent.objects.create(
            campaign=self.campaign,
            voice_over="Script de test."
        )

    def test_start_video_generation_anonymous(self):
        # Disconnect client
        self.client.logout()
        url = reverse("adgen:api_generate_video_start", kwargs={"pk": self.campaign.pk})
        response = self.client.post(url, data=json.dumps({}), content_type="application/json")
        # Should redirect to login (Django LoginRequiredMixin)
        self.assertEqual(response.status_code, 302)

    def test_start_video_generation_valid(self):
        url = reverse("adgen:api_generate_video_start", kwargs={"pk": self.campaign.pk})
        data = {
            "duration": "15",
            "music_style": "synth",
            "bg_config": {
                "bg_type": "gradient",
                "bg_gradient": ["#111111", "#222222"],
                "bg_grad_dir": "diagonal"
            }
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        resp_json = response.json()
        self.assertIn("operation_name", resp_json)
        
        # Verify db contents updated
        self.content.refresh_from_db()
        self.assertEqual(self.content.raw_json["duration"], 15)
        self.assertEqual(self.content.raw_json["music_style"], "synth")
        self.assertEqual(self.content.raw_json["bg_config"]["bg_grad_dir"], "diagonal")
