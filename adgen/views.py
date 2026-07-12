"""
AdGen — Vues class-based
"""
import json
import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, View, TemplateView
from django.utils import timezone
from django.conf import settings

from .models import AdCampaign, AdContent, AdModule, AdUsageStat
from .forms import CampaignForm

logger = logging.getLogger(__name__)


# ── Mixin limite d'utilisation ─────────────────────────────────────────────────

class UsageLimitMixin:
    """Bloque si l'utilisateur a atteint la limite quotidienne de générations."""

    DAILY_LIMIT = 10

    def check_daily_limit(self, user):
        today = date.today()
        count = AdCampaign.objects.filter(
            user=user,
            created_at__date=today,
            status__in=["done", "processing"],
        ).count()
        return count < self.DAILY_LIMIT


# ── Dashboard ──────────────────────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "adgen/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        campaigns = AdCampaign.objects.filter(user=user).order_by("-created_at")
        stat, _ = AdUsageStat.objects.get_or_create(user=user)
        max_free = getattr(settings, "ADGEN_MAX_CAMPAIGNS_FREE", 5)

        ctx.update({
            "campaigns": campaigns[:20],
            "stat": stat,
            "max_free": max_free,
            "total": campaigns.count(),
            "done": campaigns.filter(status="done").count(),
            "failed": campaigns.filter(status="failed").count(),
            "modules": AdModule.objects.filter(is_active=True),
        })
        return ctx


# ── Création campagne ──────────────────────────────────────────────────────────

class CampaignCreateView(LoginRequiredMixin, UsageLimitMixin, CreateView):
    model         = AdCampaign
    form_class    = CampaignForm
    template_name = "adgen/campaign_create.html"

    def get_initial(self):
        initial = super().get_initial()
        allowed = {"nom_produit", "description", "prix", "cible", "ville"}
        for field in allowed:
            value = self.request.GET.get(field, "").strip()
            if value:
                initial[field] = value
        if self.request.GET.get("source") == "arsenal_ia":
            initial.setdefault("prix", "A confirmer")
            initial.setdefault("cible", "Clients locaux")
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["modules"] = AdModule.objects.filter(is_active=True).order_by("order")
        return ctx

    def form_valid(self, form):
        if not self.check_daily_limit(self.request.user):
            messages.error(self.request, "Limite journalière atteinte (10 générations/jour).")
            return self.form_invalid(form)

        modules_selected = self.request.POST.getlist("modules")
        if not modules_selected:
            messages.error(self.request, "Sélectionnez au moins un module.")
            return self.form_invalid(form)

        campaign = form.save(commit=False)
        campaign.user = self.request.user
        campaign.modules_selected = modules_selected
        campaign.save()

        messages.success(self.request, "Campagne créée. Génération en cours...")
        return redirect("adgen:generate", pk=campaign.pk)


# ── Liste des campagnes ────────────────────────────────────────────────────────

class CampaignListView(LoginRequiredMixin, ListView):
    model               = AdCampaign
    template_name       = "adgen/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by         = 20

    def get_queryset(self):
        return AdCampaign.objects.filter(user=self.request.user).order_by("-created_at")


# ── Détail campagne ────────────────────────────────────────────────────────────

class CampaignDetailView(LoginRequiredMixin, DetailView):
    model               = AdCampaign
    template_name       = "adgen/campaign_detail.html"
    context_object_name = "campaign"

    def get_queryset(self):
        return AdCampaign.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx["content"] = self.object.content
        except AdContent.DoesNotExist:
            ctx["content"] = None
        return ctx


# ── Génération IA (redirige vers detail après) ────────────────────────────────

class GenerateView(LoginRequiredMixin, UsageLimitMixin, View):
    """Déclenche la génération IA de façon synchrone puis redirige."""

    def get(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)

        if campaign.status == "done":
            return redirect("adgen:detail", pk=pk)

        if campaign.status == "processing":
            messages.info(request, "Génération déjà en cours...")
            return redirect("adgen:detail", pk=pk)

        try:
            from .services.module_engine import ModuleEngine
            engine = ModuleEngine(campaign)
            engine.run()
            messages.success(request, "Contenu généré avec succès !")
        except Exception as e:
            logger.error(f"[AdGen] Erreur génération #{pk}: {e}")
            messages.error(request, f"Erreur lors de la génération : {e}")

        return redirect("adgen:detail", pk=pk)


# ── API JSON (AJAX) ────────────────────────────────────────────────────────────

class GenerateAPIView(LoginRequiredMixin, UsageLimitMixin, View):
    """Endpoint AJAX POST — retourne JSON avec le contenu généré."""

    def post(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)

        if not self.check_daily_limit(request.user):
            return JsonResponse({"error": "Limite journalière atteinte."}, status=429)

        if campaign.status == "processing":
            return JsonResponse({"error": "Génération déjà en cours."}, status=409)

        try:
            from .services.module_engine import ModuleEngine
            engine = ModuleEngine(campaign)
            content = engine.run()

            return JsonResponse({
                "status": "done",
                "campaign_id": campaign.pk,
                "tokens_used": content.tokens_used,
                "content": {
                    "titles":      content.titles,
                    "description": content.description_generated,
                    "benefits":    content.benefits,
                    "facebook":    content.facebook_post,
                    "instagram":   content.instagram_post,
                    "whatsapp":    content.whatsapp_message,
                    "hashtags":    content.hashtags,
                    "tiktok":      content.tiktok_script,
                    "chatbot":     content.chatbot_reply,
                }
            })
        except Exception as e:
            return JsonResponse({"error": str(e), "status": "failed"}, status=500)


# ── Export JSON ────────────────────────────────────────────────────────────────

class ExportContentView(LoginRequiredMixin, View):
    """Télécharge le contenu de la campagne en JSON."""

    def get(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)
        try:
            content = campaign.content
        except AdContent.DoesNotExist:
            messages.error(request, "Aucun contenu généré pour cette campagne.")
            return redirect("adgen:detail", pk=pk)

        export = {
            "produit": campaign.nom_produit,
            "pays": campaign.pays_label,
            "ville": campaign.ville_label,
            "modules": campaign.modules_selected,
            "generated_at": content.generated_at.isoformat(),
            "titles": content.titles,
            "description": content.description_generated,
            "benefits": content.benefits,
            "facebook": content.facebook_post,
            "instagram": content.instagram_post,
            "whatsapp": content.whatsapp_message,
            "hashtags": content.hashtags,
            "tiktok_script": content.tiktok_script,
            "chatbot_reply": content.chatbot_reply,
        }

        filename = f"adgen_{campaign.pk}_{campaign.nom_produit[:20].replace(' ', '_')}.json"
        response = HttpResponse(
            json.dumps(export, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ─── Génération Vidéo Publicitaire ───────────────────────────────────────────
from e_shelle_ai.services.tools.google_media_generator import start_google_video, check_google_video_status
from e_shelle_ai.services.quota_service import QuotaService
import base64
import os
import requests
import subprocess
import urllib.parse
import struct
import wave
import math

def generate_ad_music(output_filepath, duration=10.0):
    """
    Génère un fond sonore synthétique haut de gamme (mélodie d'accords plucks piano/guitare)
    de 10 secondes pour accompagner la publicité.
    """
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    
    # Fréquences des notes
    notes = {
        'C3': 130.81, 'E3': 164.81, 'G3': 196.00, 'B3': 246.94,
        'A3': 220.00, 'C4': 261.63, 'E4': 329.63, 'G4': 392.00,
        'F3': 174.61, 'A4': 440.00, 'B4': 493.88, 'D4': 293.66,
        'G3_low': 196.00
    }
    
    # Progression d'accords : 4 accords, chacun durant 2.5 secondes
    chords = [
        # Cmaj7 (C3, E3, G3, B3, C4, E4)
        [('C3', 0.0, 0.4), ('E3', 0.25, 0.3), ('G3', 0.5, 0.3), ('B3', 0.75, 0.3), ('C4', 1.0, 0.2), ('E4', 1.25, 0.2)],
        # Amin7 (A3, C4, E4, G4, A4)
        [('A3', 0.0, 0.4), ('C4', 0.25, 0.3), ('E4', 0.5, 0.3), ('G4', 0.75, 0.3), ('A4', 1.0, 0.2), ('E4', 1.25, 0.2)],
        # Fmaj7 (F3, A4, C4, E4)
        [('F3', 0.0, 0.4), ('A4', 0.25, 0.3), ('C4', 0.5, 0.3), ('E4', 0.75, 0.3), ('F3', 1.0, 0.2), ('A4', 1.25, 0.2)],
        # G7 (G3_low, B4, D4, G4)
        [('G3_low', 0.0, 0.4), ('B4', 0.25, 0.3), ('D4', 0.5, 0.3), ('G4', 0.75, 0.3), ('B4', 1.0, 0.2), ('D4', 1.25, 0.2)],
    ]
    
    samples = [0.0] * num_samples
    
    for chord_idx, plucks in enumerate(chords):
        chord_start_time = chord_idx * 2.5
        for note_name, delay, base_vol in plucks:
            freq = notes.get(note_name, 440.0)
            pluck_time = chord_start_time + delay
            start_sample = int(pluck_time * sample_rate)
            
            # Durée de résonance de la note (1.5s)
            note_duration = 1.5
            note_samples = int(note_duration * sample_rate)
            
            for i in range(note_samples):
                idx = start_sample + i
                if idx >= num_samples:
                    break
                t = i / sample_rate
                # Enveloppe : attaque de 10ms puis décroissance exponentielle
                if t < 0.01:
                    envelope = (t / 0.01) * base_vol
                else:
                    envelope = math.exp(-(t - 0.01) * 2.0) * base_vol
                
                # Synthèse avec harmoniques douces
                val = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * 2 * freq * t)
                samples[idx] += val * envelope * 0.15
                
    # Ecrire le fichier WAV
    with wave.open(output_filepath, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        
        frames = bytearray()
        for s in samples:
            s = max(-1.0, min(1.0, s))
            int_val = int(s * 32767)
            frames.extend(struct.pack('<h', int_val))
        wav.writeframes(bytes(frames))


def add_voiceover_to_video(video_url: str, text: str, campaign_id: int) -> str:
    """
    Télécharge ou lit la vidéo muette de 8 secondes, génère un fond musical 
    professionnel de 10 secondes (guitare/piano plucks), étire la vidéo 
    à 10 secondes (setpts=1.25) et assemble les deux.
    """
    try:
        logger.info(f"[AdGen Video Processing] Démarrage de l'étirement à 10s et mixage audio pour la campagne #{campaign_id}...")
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, "adgen", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        is_local = False
        silent_video_path = ""
        
        # 1. Résolution du chemin de la vidéo muette (8s)
        if video_url.startswith(settings.MEDIA_URL):
            relative_path = video_url[len(settings.MEDIA_URL):]
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]
            local_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            if os.path.exists(local_path):
                silent_video_path = local_path
                is_local = True
                logger.info(f"[AdGen Video Processing] Vidéo muette locale trouvée à : {silent_video_path}")
                
        if not is_local:
            logger.info(f"[AdGen Video Processing] Téléchargement de la vidéo muette depuis : {video_url}")
            video_resp = requests.get(video_url, timeout=30)
            video_resp.raise_for_status()
            
            silent_video_path = os.path.join(temp_dir, f"silent_{campaign_id}.mp4")
            with open(silent_video_path, "wb") as f:
                f.write(video_resp.content)
            
        # 2. Générer le fond musical de 10 secondes (arpeggio piano/guitare)
        audio_path = os.path.join(temp_dir, f"music_{campaign_id}.wav")
        generate_ad_music(audio_path, duration=10.0)
        logger.info(f"[AdGen Video Processing] Fond musical généré à : {audio_path}")
            
        # 3. Fusionner et étirer la vidéo de 8s à 10s (setpts=1.25*PTS) avec ffmpeg
        output_dir = os.path.join(settings.MEDIA_ROOT, "adgen", "videos")
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"ad_video_{campaign_id}.mp4"
        output_filepath = os.path.join(output_dir, output_filename)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", silent_video_path,
            "-i", audio_path,
            "-filter:v", "setpts=1.25*PTS",
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-shortest",
            output_filepath
        ]
        
        logger.info(f"[AdGen Video Processing] Lancement ffmpeg: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"[AdGen Video Processing] ffmpeg a échoué: {res.stderr}")
            raise RuntimeError(f"ffmpeg error: {res.stderr}")
            
        # Nettoyer les fichiers temporaires
        try:
            if not is_local:
                os.remove(silent_video_path)
            os.remove(audio_path)
        except Exception:
            pass
            
        media_url_base = settings.MEDIA_URL
        if not media_url_base.endswith("/"):
            media_url_base += "/"
        final_url = f"{media_url_base}adgen/videos/{output_filename}"
        logger.info(f"[AdGen Video Processing] Succès ! Vidéo finale de 10s générée : {final_url}")
        return final_url
    except Exception as e:
        logger.error(f"[AdGen Video Processing] Échec de l'étirement ou du mixage: {e}")
        return video_url

def clean_video_prompt(prompt: str, campaign) -> str:
    """
    S'assure que le prompt de vidéo ne contient pas de marqueurs temporels ou de texte
    qui gâcheraient le rendu de l'IA (comme 0-3s, Texte:, etc.).
    Si c'est un script brut, génère un prompt d'animation professionnel à la place.
    """
    p = prompt.strip()
    # Si le prompt contient des marqueurs de temps ou des mots-clés de script
    if any(marker in p for marker in ["0-3", "4-12", "13-17", "18-20", "s:", "Texte:", "CTA:", "Voice-over:"]):
        desc_clean = campaign.description.replace("\n", " ").strip()
        p = (
            f"A professional product commercial video showcasing '{campaign.nom_produit}'. "
            f"Animate the product from the image with realistic motion, smooth camera pan, "
            f"cinematic lighting, and studio background. Highlights: {desc_clean[:200]}. "
            f"High-end advertising aesthetic, 4k, crisp, no text on screen, no logo, no watermark, no writing."
        )
    # Éviter que l'IA tente d'écrire du texte/logo à l'écran (qui ressort déformé)
    for forbidden in ["text", "logo", "watermark", "branding", "title", "writing"]:
        if forbidden not in p.lower():
            p += f", no {forbidden}"
    return p

class StartAdVideoView(LoginRequiredMixin, View):
    """
    POST /pub/api/campaign/<pk>/generate-video/start/
    Démarre la génération de vidéo publicitaire avec Google Veo en utilisant la photo du produit.
    """
    def post(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)
        try:
            content = campaign.content
        except AdContent.DoesNotExist:
            return JsonResponse({"error": "Veuillez d'abord générer le contenu textuel de la campagne."}, status=400)

        # Vérifier le quota d'image/vidéo
        quota_service = QuotaService()
        if not quota_service.check_image_quota(request.user):
            upgrade_msg = quota_service.get_upgrade_message(request.user, "image")
            return JsonResponse({"error": upgrade_msg, "quota_exceeded": True}, status=402)

        # Lire le prompt personnalisé, la voix-off et la durée s'ils sont fournis
        custom_prompt = None
        voiceover_text = None
        duration = 8
        if request.content_type == "application/json" or request.body.startswith(b"{"):
            try:
                data = json.loads(request.body)
                custom_prompt = data.get("prompt")
                voiceover_text = data.get("voiceover_text")
                duration = int(data.get("duration", 8))
            except Exception:
                pass
        else:
            custom_prompt = request.POST.get("prompt")
            voiceover_text = request.POST.get("voiceover_text")
            duration = int(request.POST.get("duration", 8))

        # Enregistrer le texte de la voix-off en base pour la récupérer à la fin de la génération
        if voiceover_text is not None:
            content.voice_over = voiceover_text.strip()
            content.save(update_fields=["voice_over"])

        if custom_prompt:
            prompt = custom_prompt.strip()
        else:
            desc_clean = campaign.description.replace("\n", " ").strip()
            prompt = (
                f"A professional, high-quality commercial video showcasing '{campaign.nom_produit}'. "
                f"Based on the product image, naturally animate the scene with realistic motion, "
                f"smooth camera panning, and elegant studio lighting. The video highlights: {desc_clean[:250]}. "
                f"High-end advertising aesthetic, 4k, crisp details."
            )
        
        prompt = clean_video_prompt(prompt, campaign)
        prompt = prompt[:1200]
        # Veo reference_to_video ne supporte QUE 8 secondes
        duration = 8

        # Encodage de l'image du produit si présente
        image_b64 = None
        if campaign.photo_produit:
            try:
                with campaign.photo_produit.open("rb") as img_file:
                    image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to read campaign product image: {e}")

        # Lancer la génération
        result = start_google_video(prompt, aspect_ratio="16:9", image_b64=image_b64, duration=duration)

        if result.get("error"):
            return JsonResponse({"error": f"Impossible de démarrer la génération vidéo : {result['error']}"}, status=500)

        return JsonResponse({
            "operation_name": result["operation_name"],
            "prompt": prompt
        })


class PollAdVideoView(LoginRequiredMixin, View):
    """
    GET /pub/api/campaign/<pk>/generate-video/poll/
    Vérifie le statut et sauvegarde le résultat final de la vidéo.
    """
    def get(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)
        try:
            content = campaign.content
        except AdContent.DoesNotExist:
            return JsonResponse({"error": "Contenu de campagne manquant."}, status=400)

        operation_name = request.GET.get("operation_name")
        if not operation_name:
            return JsonResponse({"error": "Nom de l'opération manquant."}, status=400)

        result = check_google_video_status(operation_name)

        if result.get("error"):
            return JsonResponse({"error": result["error"]}, status=500)

        if not result.get("done"):
            return JsonResponse({"done": False})

        # Vidéo terminée avec succès !
        video_url = result["video_url"]
        
        # Générer le fond sonore publicitaire de 10s et étirer la vidéo à 10s
        video_url = add_voiceover_to_video(video_url, "bg_music", campaign.pk)
            
        content.ad_video_url = video_url
        content.save(update_fields=["ad_video_url"])

        # Incrémenter le quota
        quota_service = QuotaService()
        quota_service.increment_usage(request.user, "image")

        return JsonResponse({
            "done": True,
            "video_url": video_url,
            "quota": quota_service.get_remaining(request.user)
        })
