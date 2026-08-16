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

import threading
from django.db import connection

class GenerateView(LoginRequiredMixin, UsageLimitMixin, View):
    """Déclenche la génération IA de façon asynchrone (thread arrière-plan) puis redirige immédiatement."""

    def get(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)

        if campaign.status == "done":
            return redirect("adgen:detail", pk=pk)

        if campaign.status == "processing":
            messages.info(request, "Génération déjà en cours...")
            return redirect("adgen:detail", pk=pk)

        if not self.check_daily_limit(request.user):
            messages.error(request, "Vous avez atteint votre limite journalière de générations (10/jour).")
            return redirect("adgen:detail", pk=pk)

        # Passer le statut à "processing" immédiatement
        campaign.status = "processing"
        campaign.save(update_fields=["status", "updated_at"])

        # Lancer le traitement lourd dans un thread d'arrière-plan
        def bg_run(campaign_id):
            # Fermer la connexion actuelle pour que le thread en ouvre une nouvelle propre
            connection.close()
            try:
                from .services.module_engine import ModuleEngine
                # Recharger l'instance dans ce thread pour éviter les conflits d'état Django
                t_campaign = AdCampaign.objects.get(pk=campaign_id)
                engine = ModuleEngine(t_campaign)
                engine.run()
            except Exception as e:
                logger.error(f"[AdGen Background Thread] Échec de la génération #{campaign_id}: {e}")
                try:
                    t_campaign = AdCampaign.objects.get(pk=campaign_id)
                    t_campaign.status = "failed"
                    t_campaign.save(update_fields=["status", "updated_at"])
                except Exception:
                    pass
            finally:
                connection.close()

        thread = threading.Thread(target=bg_run, args=(campaign.pk,))
        thread.daemon = True
        thread.start()

        messages.info(request, "Génération de votre campagne lancée en arrière-plan...")
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

def generate_ad_music(output_filepath, duration=30.0, style="piano"):
    """
    Génère un fond sonore synthétique haut de gamme de la durée demandée
    avec plusieurs styles sélectionnables (piano, acoustic, synth, jazz).
    """
    import math
    import struct
    import wave
    
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    samples = [0.0] * num_samples
    
    # Dictionnaire global des notes
    notes = {
        # Basses
        'E2': 82.41, 'G2': 98.00, 'A2': 110.00, 'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00,
        # Medium
        'A3': 220.00, 'B3': 246.94, 'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00,
        # Aigus
        'A4': 440.00, 'B4': 493.88, 'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F#4': 369.99, 'G5': 783.99, 'B4_high': 493.88
    }
    
    if style == "acoustic":
        # Progression Guitare Acoustique Gmaj7 -> Cadd9 -> Em7 -> D
        chords = [
            # Gmaj7
            [('G2', 0.0, 0.4), ('D3', 0.15, 0.3), ('G3', 0.3, 0.3), ('B3', 0.45, 0.3), ('F#4', 0.6, 0.25), ('B3', 1.0, 0.2), ('G3', 1.5, 0.2), ('D3', 2.0, 0.2)],
            # Cadd9
            [('C3', 0.0, 0.4), ('G3', 0.15, 0.3), ('C4', 0.3, 0.3), ('D4', 0.45, 0.3), ('E4', 0.6, 0.25), ('D4', 1.0, 0.2), ('C4', 1.5, 0.2), ('G3', 2.0, 0.2)],
            # Em7
            [('E2', 0.0, 0.4), ('B2', 0.15, 0.3), ('D3', 0.3, 0.3), ('G3', 0.45, 0.3), ('B3', 0.6, 0.25), ('G3', 1.0, 0.2), ('D3', 1.5, 0.2), ('B2', 2.0, 0.2)],
            # D
            [('D3', 0.0, 0.4), ('A3', 0.15, 0.3), ('D4', 0.3, 0.3), ('F#4', 0.45, 0.3), ('D4', 0.6, 0.25), ('A3', 1.0, 0.2), ('D3', 1.5, 0.2), ('A3', 2.0, 0.2)]
        ]
        chord_dur = 3.75 # 4 accords * 3.75 = 15s
    
    elif style == "synth":
        # Progression Synth Pop Amin -> Fmaj -> Cmaj -> Gmaj avec arpégiateur rapide (1/8 de note)
        arp_notes = [
            # Amin
            ['A2', 'E3', 'A3', 'C4', 'E4', 'C4', 'A3', 'E3'],
            # Fmaj
            ['F2', 'C3', 'F3', 'A3', 'C4', 'A3', 'F3', 'C3'],
            # Cmaj
            ['C2', 'G2', 'C3', 'E3', 'G3', 'E3', 'C3', 'G2'],
            # Gmaj
            ['G2', 'D3', 'G3', 'B3', 'D4', 'B3', 'G3', 'D3']
        ]
        chord_dur = 3.75
        chords = []
        for c_idx, notes_list in enumerate(arp_notes):
            chord_chords = []
            for note_idx in range(12): # 12 notes par accord (chacune dure 0.3s)
                note_name = notes_list[note_idx % len(notes_list)]
                chord_chords.append((note_name, note_idx * 0.3, 0.25))
            chords.append(chord_chords)
            
    elif style == "jazz":
        # Rhodes Jazz Lounge Am9 -> Dm9 -> G13 -> Cmaj9
        chords = [
            # Am9 (A2, C3, E3, G3, B3)
            [('A2', 0.0, 0.4), ('C3', 0.3, 0.3), ('E3', 0.6, 0.3), ('G3', 0.9, 0.3), ('B3', 1.2, 0.25)],
            # Dm9 (D3, F3, A3, C4, E4)
            [('D3', 0.0, 0.4), ('F3', 0.3, 0.3), ('A3', 0.6, 0.3), ('C4', 0.9, 0.3), ('E4', 1.2, 0.25)],
            # G13 (G2, B2, F3, A3, E4)
            [('G2', 0.0, 0.4), ('B2', 0.3, 0.3), ('F3', 0.6, 0.3), ('A3', 0.9, 0.3), ('E4', 1.2, 0.25)],
            # Cmaj9 (C3, E3, G3, B3, D4)
            [('C3', 0.0, 0.4), ('E3', 0.3, 0.3), ('G3', 0.6, 0.3), ('B3', 0.9, 0.3), ('D4', 1.2, 0.25)]
        ]
        chord_dur = 3.75
        
    else:
        # Piano plucks par défaut (Cmaj7 -> Amin7 -> Fmaj7 -> G7)
        chords = [
            [('C3', 0.0, 0.4), ('E3', 0.25, 0.3), ('G3', 0.5, 0.3), ('B3', 0.75, 0.3), ('C4', 1.0, 0.2), ('E4', 1.25, 0.2)],
            [('A2', 0.0, 0.4), ('C3', 0.25, 0.3), ('E3', 0.5, 0.3), ('G3', 0.75, 0.3), ('A3', 1.0, 0.2), ('E3', 1.25, 0.2)],
            [('F2', 0.0, 0.4), ('A3', 0.25, 0.3), ('C4', 0.5, 0.3), ('E4', 0.75, 0.3), ('F3', 1.0, 0.2), ('A3', 1.25, 0.2)],
            [('G2', 0.0, 0.4), ('B4_high', 0.25, 0.3), ('D4', 0.5, 0.3), ('G4', 0.75, 0.3), ('B4_high', 1.0, 0.2), ('D3', 1.25, 0.2)],
        ]
        chord_dur = 3.75

    # Calcul du nombre de répétitions nécessaires pour remplir toute la durée de la vidéo
    loop_duration = len(chords) * chord_dur
    num_loops = math.ceil(duration / loop_duration)
    
    for loop_idx in range(num_loops):
        loop_start_time = loop_idx * loop_duration
        for chord_idx, plucks in enumerate(chords):
            chord_start_time = loop_start_time + (chord_idx * chord_dur)
            for note_name, delay, base_vol in plucks:
                freq = notes.get(note_name, 440.0)
                pluck_time = chord_start_time + delay
                start_sample = int(pluck_time * sample_rate)
                
                # Si la note commence après la fin de la vidéo, on l'ignore
                if start_sample >= num_samples:
                    continue
                
                note_duration = 0.8 if style == "synth" else 2.2
                note_samples = int(note_duration * sample_rate)
                
                for i in range(note_samples):
                    idx = start_sample + i
                    if idx >= num_samples:
                        break
                    t = i / sample_rate
                    
                    # Enveloppes
                    if style == "synth":
                        if t < 0.005:
                            envelope = (t / 0.005) * base_vol
                        else:
                            envelope = math.exp(-(t - 0.005) * 5.0) * base_vol
                    else:
                        if t < 0.012:
                            envelope = (t / 0.012) * base_vol
                        else:
                            decay_rate = 1.2 if style == "jazz" else 1.8
                            envelope = math.exp(-(t - 0.012) * decay_rate) * base_vol
                    
                    # Synthèse instrumentale
                    if style == "synth":
                        val = math.sin(2 * math.pi * freq * t) + 0.3 * math.copysign(0.2, math.sin(2 * math.pi * 2 * freq * t))
                        vol_factor = 0.12
                    elif style == "jazz":
                        tremolo = 1.0 + 0.35 * math.sin(2 * math.pi * 4.5 * t)
                        val = (math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(2 * math.pi * 2 * freq * t)) * tremolo
                        vol_factor = 0.16
                    elif style == "acoustic":
                        val = math.sin(2 * math.pi * freq * t) + 0.4 * math.sin(2 * math.pi * 2 * freq * t) + 0.2 * math.sin(2 * math.pi * 3 * freq * t)
                        vol_factor = 0.14
                    else:
                        val = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * 2 * freq * t)
                        vol_factor = 0.15
                        
                    samples[idx] += val * envelope * vol_factor
                
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


def get_premium_font() -> str:
    """
    Télécharge ou localise la police premium Outfit-Bold.ttf
    depuis Google Fonts et la stocke dans media/fonts/
    """
    import os
    import urllib.request
    from django.conf import settings
    
    font_dir = os.path.join(settings.MEDIA_ROOT, "fonts")
    os.makedirs(font_dir, exist_ok=True)
    font_path = os.path.join(font_dir, "Outfit-Bold.ttf")
    
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-Bold.ttf"
            logger.info(f"[AdGen] Téléchargement de la police premium depuis {url}...")
            urllib.request.urlretrieve(url, font_path)
            logger.info(f"[AdGen] Police premium téléchargée : {font_path}")
        except Exception as e:
            logger.warning(f"[AdGen] Échec du téléchargement de la police: {e}")
            return ""
            
    return font_path


def wrap_text(text: str, max_chars: int = 18) -> str:
    """
    Sépare le texte par des sauts de ligne pour éviter qu'il ne déborde de l'écran.
    """
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 > max_chars:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + 1
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)


def is_bg_light(bg_config: dict) -> bool:
    """
    Détermine si l'arrière-plan configuré est clair ou sombre.
    """
    if not bg_config:
        return False # Par défaut sombre
    
    bg_type = bg_config.get("bg_type", "color")
    
    # Résolution de la couleur principale de référence
    ref_color = "#050910"
    if bg_type == "color":
        ref_color = bg_config.get("bg_color", "#050910")
    elif bg_type == "gradient":
        colors = bg_config.get("bg_gradient", [])
        if colors:
            ref_color = colors[0]
    elif bg_type == "template":
        template = bg_config.get("bg_template", "dark")
        light_templates = ["minimal", "fashion", "medical"]
        if template in light_templates:
            return True
        return False
        
    try:
        hex_val = ref_color.lstrip('#')
        if len(hex_val) == 3:
            hex_val = ''.join(c*2 for c in hex_val)
        r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return luminance > 140
    except Exception:
        return False


def prepare_image_for_veo(image_field, bg_config: dict = None) -> bytes:
    """
    Crée une image de 1280x720 (16:9) avec l'image du produit ajustée au centre
    dans un espace de 405x720 (9:16), sur le fond configuré (couleur, gradient ou template).
    """
    from PIL import Image, ImageDraw
    import io
    
    img = Image.open(image_field)
    img = img.convert("RGBA")
    
    # Dimensions cibles
    canvas_w = 1280
    canvas_h = 720
    center_w = 405  # 720 * 9 / 16
    center_h = 720
    
    w, h = img.size
    img_ratio = w / h
    box_ratio = center_w / center_h
    
    # Redimensionnement de l'image pour loger dans la box centrale
    if img_ratio > box_ratio:
        new_w = center_w
        new_h = int(center_w / img_ratio)
    else:
        new_h = center_h
        new_w = int(center_h * img_ratio)
        
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Créer le canvas 1280x720 sur le fond personnalisé
    bg = Image.new("RGBA", (canvas_w, canvas_h))
    draw = ImageDraw.Draw(bg)
    
    bg_type = "color"
    if bg_config:
        bg_type = bg_config.get("bg_type", "color")
        
    if bg_type == "color":
        color_hex = bg_config.get("bg_color", "#050910")
        hex_val = color_hex.lstrip('#')
        r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(r, g, b, 255))
        
    elif bg_type == "gradient":
        colors_hex = bg_config.get("bg_gradient", ["#050910", "#1e293b"])
        if len(colors_hex) < 2:
            colors_hex.append("#1e293b")
        hex1 = colors_hex[0].lstrip('#')
        hex2 = colors_hex[1].lstrip('#')
        r1, g1, b1 = int(hex1[0:2], 16), int(hex1[2:4], 16), int(hex1[4:6], 16)
        r2, g2, b2 = int(hex2[0:2], 16), int(hex2[2:4], 16), int(hex2[4:6], 16)
        
        for x in range(canvas_w):
            factor = x / canvas_w
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            draw.line([(x, 0), (x, canvas_h)], fill=(r, g, b, 255))
            
    elif bg_type == "template":
        template = bg_config.get("bg_template", "dark")
        if template == "minimal":
            draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(245, 245, 247, 255))
        elif template == "luxury":
            draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(10, 10, 12, 255))
            # Fines lignes dorées décoratives
            draw.line([(0, 10), (canvas_w, 10)], fill=(212, 175, 55, 255), width=3)
            draw.line([(0, canvas_h-10), (canvas_w, canvas_h-10)], fill=(212, 175, 55, 255), width=3)
        elif template == "tech":
            draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(11, 19, 43, 255))
            # Subtils cercles futuristes bleutés
            draw.ellipse([(-50, -50), (250, 250)], outline=(0, 180, 216, 50), width=1)
            draw.ellipse([(canvas_w-250, canvas_h-250), (canvas_w+50, canvas_h+50)], outline=(0, 180, 216, 50), width=1)
        elif template == "modern":
            # Dégradé vibrant violet vers bleu
            for x in range(canvas_w):
                factor = x / canvas_w
                r = int(108 + (20 - 108) * factor)
                g = int(63 + (120 - 63) * factor)
                b = int(232 + (240 - 232) * factor)
                draw.line([(x, 0), (x, canvas_h)], fill=(r, g, b, 255))
        elif template == "fashion":
            # Dégradé rose poudré et beige chaleureux
            for x in range(canvas_w):
                factor = x / canvas_w
                r = int(245 + (230 - 245) * factor)
                g = int(220 + (200 - 220) * factor)
                b = int(215 + (190 - 215) * factor)
                draw.line([(x, 0), (x, canvas_h)], fill=(r, g, b, 255))
        elif template == "food":
            # Dégradé jaune-orange chaleureux
            for x in range(canvas_w):
                factor = x / canvas_w
                r = int(251 + (245 - 251) * factor)
                g = int(146 + (85 - 146) * factor)
                b = int(60 + (30 - 60) * factor)
                draw.line([(x, 0), (x, canvas_h)], fill=(r, g, b, 255))
        elif template == "automotive":
            # Fond texturé sombre gris carbone
            draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(20, 24, 30, 255))
            for y in range(0, canvas_h, 40):
                draw.line([(0, y), (canvas_w, y+120)], fill=(255, 255, 255, 6), width=2)
        else:
            # Dark / Fallback
            draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(5, 9, 16, 255))
            
    else:
        # Par défaut, fond sombre E-Shelle
        draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(5, 9, 16, 255))
        
    # Calcul des coordonnées de centrage pour la zone 9:16
    offset_x = (canvas_w - new_w) // 2
    offset_y = (canvas_h - new_h) // 2
    
    bg.paste(img_resized, (offset_x, offset_y), img_resized)
    
    final_img = bg.convert("RGB")
    out_buf = io.BytesIO()
    final_img.save(out_buf, format="JPEG", quality=90)
    return out_buf.getvalue()


def add_voiceover_to_video(video_url: str, text: str, campaign_id: int, music_style: str = "piano", duration: float = 30.0) -> str:
    """
    Télécharge la vidéo muette de 8s, génère le fond musical sur-mesure (piano, acoustic, etc.) 
    répété selon la durée cible, étire la vidéo à la durée configurée, effectue un recadrage vertical 
    dynamique (crop 9:16 + floating subtil + zoom lent), et applique une timeline d'incrustation 
    d'overlays professionnels adaptés au contraste de l'arrière-plan.
    """
    import os
    import subprocess
    import requests
    from django.conf import settings
    from .models import AdCampaign
    
    slogan_file = ""
    price_file = ""
    contact_file = ""
    
    try:
        logger.info(f"[AdGen Video Processing] Démarrage du moteur de scènes {duration}s, crop vertical 9:16 et mixage audio pour la campagne #{campaign_id}...")
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, "adgen", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        is_local = False
        silent_video_path = ""
        
        # 1. Résolution du chemin de la vidéo muette
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
            
        # 2. Générer le fond musical adapté à la durée demandée
        audio_path = os.path.join(temp_dir, f"music_{campaign_id}.wav")
        generate_ad_music(audio_path, duration=duration, style=music_style)
        logger.info(f"[AdGen Video Processing] Fond musical de {duration}s ({music_style}) généré à : {audio_path}")
            
        # 3. Récupérer les informations de la campagne et les configurations du background
        campaign = AdCampaign.objects.get(pk=campaign_id)
        clean_title = campaign.nom_produit.replace("'", " ").replace('"', " ").strip()
        clean_city = (campaign.ville_label or campaign.ville or "").replace("'", " ").replace('"', " ").strip()
        
        bg_config = {}
        try:
            content = campaign.content
            if isinstance(content.raw_json, dict):
                bg_config = content.raw_json.get("bg_config", {})
        except Exception:
            pass
            
        # Formatage intelligent du prix (ajout de XAF par défaut si numérique)
        price_raw = campaign.prix.replace("'", " ").replace('"', " ").strip()
        clean_digits = price_raw.replace(" ", "").replace(".", "").replace(",", "")
        if clean_digits.isdigit():
            clean_price = f"Prix: {price_raw} XAF"
        else:
            upper_price = price_raw.upper()
            if not any(suffix in upper_price for suffix in ["XAF", "FCFA", "CFA", " F", "FRANC"]):
                clean_price = f"Prix: {price_raw} XAF"
            else:
                if not upper_price.startswith("PRIX"):
                    clean_price = f"Prix: {price_raw}"
                else:
                    clean_price = price_raw
        
        phone = campaign.cible.strip()
        if phone:
            contact_text = f"WhatsApp: {phone}\n({clean_city})"
        else:
            contact_text = f"Commander sur\nWhatsApp ({clean_city})"
            
        # Déterminer la coloration en fonction du contraste automatique du background
        is_light = is_bg_light(bg_config)
        if is_light:
            text_color = "0x0a0a0a"       # Noir
            accent_color = "0xc2410c"     # Orange foncé / brique
            box_color = "white@0.85"       # Boîte claire très lisible
            contact_box_color = "0xdcfce7@0.9" # Vert clair doux
            contact_text_color = "0x14532d"
        else:
            text_color = "white"
            accent_color = "0xffd91f"     # Doré / Jaune vif
            box_color = "black@0.65"       # Boîte sombre protectrice
            contact_box_color = "0x14532d@0.75" # Vert WhatsApp foncé
            contact_text_color = "white"
            
        # 4. Écrire le prix et le contact dans des fichiers temporaires
        price_file = os.path.join(temp_dir, f"price_{campaign_id}.txt").replace('\\', '/')
        contact_file = os.path.join(temp_dir, f"contact_{campaign_id}.txt").replace('\\', '/')
        
        with open(price_file, "w", encoding="utf-8") as f:
            f.write(wrap_text(clean_price, 15))
            
        with open(contact_file, "w", encoding="utf-8") as f:
            f.write(wrap_text(contact_text, 22))
            
        # 5. Construire les filtres d'incrustation de texte et d'effets visuels
        font_path = get_premium_font()
        font_opt = f":fontfile='{font_path}'" if (font_path and os.path.exists(font_path)) else ""
        
        # Filigrane de marque E-SHELLE.COM (haut droit, discret et permanent)
        w_filter = (
            f"drawtext=text='E-SHELLE.COM':x=w-tw-w*0.06:y=h*0.04{font_opt}:fontsize=w*0.032:fontcolor=white:alpha=0.45"
        )
        
        # Scène 1 [0s - 13s] : Titre (apparition lettre par lettre)
        # Animation lettre par lettre (glissade depuis le haut avec léger décalage stagger)
        title_filters = []
        char_w = 26
        if len(clean_title) > 18:
            title_fontsize = "w*0.045"
            char_w = 21
        else:
            title_fontsize = "w*0.055"
            char_w = 26
            
        # Fond de boîte englobant le titre (s'affiche doucement à 0.5s et se retire à 13.5s)
        box_w = len(clean_title) * char_w + 30
        title_box_filter = (
            f"drawbox=x=w*0.08-15:y=h*0.12-10:w={box_w}:h=w*0.065+20:color={box_color}:t=fill:"
            f"alpha='if(lt(t,0.5),0,if(lt(t,1.5),t-0.5,if(lt(t,13.5),1,if(lt(t,14.5),14.5-t,0))))'"
        )
        title_filters.append(title_box_filter)
        
        start_t = 0.5
        stagger = 0.08
        char_duration = 0.4
        
        for i, char in enumerate(clean_title):
            char_delay = start_t + (i * stagger)
            x_pos = f"w*0.08 + {i * char_w}"
            y_expr = f"h*0.12 - max(0, 50 * (1 - (t - {char_delay}) / {char_duration}))"
            alpha_expr = f"if(lt(t,{char_delay}),0,if(lt(t,13.5),clip((t - {char_delay})/{char_duration},0,1),if(lt(t,14.5),14.5-t,0)))"
            
            safe_char = char.replace("'", "\\'").replace(":", "\\:")
            title_filters.append(
                f"drawtext=text='{safe_char}':x='{x_pos}':y='{y_expr}':alpha='{alpha_expr}'{font_opt}:"
                f"fontsize={title_fontsize}:fontcolor={text_color}"
            )
            
        # Scène 2 [9s - 18s] : Avantage / Message commercial (Slide montant depuis le bas)
        slogan_file = os.path.join(temp_dir, f"slogan_{campaign_id}.txt").replace('\\', '/')
        clean_desc = campaign.description.replace("'", " ").replace('"', " ").strip()
        slogan_text = clean_desc[:45] + "..." if len(clean_desc) > 45 else clean_desc
        with open(slogan_file, "w", encoding="utf-8") as f:
            f.write(wrap_text(slogan_text, 22))
            
        s_filter = (
            f"drawtext=textfile='{slogan_file}':x=w*0.08:y='h*0.35 + max(0, 50 * (1 - (t-9.0)/1.0))'{font_opt}:"
            f"fontsize=w*0.048:fontcolor={text_color}:box=1:boxcolor={box_color}:boxborderw=10:"
            f"alpha='if(lt(t,9.0),0,if(lt(t,10.0),t-9.0,if(lt(t,17.0),1,if(lt(t,18.0),18.0-t,0))))'"
        )
        
        # Scène 3 [18s - 30s] : Prix (Slide rapide depuis la gauche avec léger overshoot)
        p_filter = (
            f"drawtext=textfile='{price_file}':x='if(lt(t,18.0),-w,w*0.08-max(0,w*(1-(t-18.0)/1.2)))':y=h*0.48{font_opt}:"
            f"fontsize=w*0.070:fontcolor={accent_color}:box=1:boxcolor={box_color}:boxborderw=15:"
            f"alpha='if(lt(t,18.0),0,if(lt(t,19.0),t-18.0,if(lt(t,duration-1.0),1,duration-t)))'"
        )
        
        # Contacts (Persistant de 0s à 30s, alignement fixe en zone basse sécurisée)
        c_filter = (
            f"drawtext=textfile='{contact_file}':x=w*0.08:y=h*0.84{font_opt}:fontsize=w*0.048:fontcolor={contact_text_color}:"
            f"box=1:boxcolor={contact_box_color}:boxborderw=12:alpha='if(lt(t,0.2),0,if(lt(t,1.2),t-0.2,1))'"
        )
        
        # Enchaînement des filtres vidéo :
        # - setpts étire la vitesse temporelle de 8s de base à la durée cible
        # - crop applique le recadrage 9:16 avec zoom lent de 8% et un floating de 8px
        speed_ratio = duration / 8.0
        crop_zoom_filter = (
            f"setpts={speed_ratio}*PTS,"
            f"crop=w='ih*9/16*(1-0.08*t/{duration})':h='ih*(1-0.08*t/{duration})':"
            f"x='(in_w-out_w)/2':y='(in_h-out_h)/2 + 8*sin(2*PI*t/6)'"
        )
        
        vf_chain = f"{crop_zoom_filter},{w_filter},{','.join(title_filters)},{s_filter},{p_filter},{c_filter}"
        
        # 6. Fusionner, étirer la vidéo et incruster les textes animés avec ffmpeg
        output_dir = os.path.join(settings.MEDIA_ROOT, "adgen", "videos")
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"ad_video_{campaign_id}.mp4"
        output_filepath = os.path.join(output_dir, output_filename)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", silent_video_path,
            "-i", audio_path,
            "-filter:v", vf_chain,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-shortest",
            output_filepath
        ]
        
        logger.info(f"[AdGen Video Processing] Lancement ffmpeg {duration}s: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"[AdGen Video Processing] ffmpeg a échoué: {res.stderr}")
            raise RuntimeError(f"ffmpeg error: {res.stderr}")
            
        # Nettoyer les fichiers temporaires
        try:
            if not is_local:
                os.remove(silent_video_path)
            os.remove(audio_path)
            if os.path.exists(price_file): os.remove(price_file)
            if os.path.exists(contact_file): os.remove(contact_file)
            if os.path.exists(slogan_file): os.remove(slogan_file)
        except Exception:
            pass
            
        media_url_base = settings.MEDIA_URL
        if not media_url_base.endswith("/"):
            media_url_base += "/"
        final_url = f"{media_url_base}adgen/videos/{output_filename}"
        logger.info(f"[AdGen Video Processing] Succès ! Vidéo finale de {duration}s générée : {final_url}")
        return final_url
    except Exception as e:
        logger.error(f"[AdGen Video Processing] Échec de l'étirement, de l'incrustation de texte ou du mixage: {e}")
        # Nettoyage en cas de crash
        try:
            if price_file and os.path.exists(price_file): os.remove(price_file)
            if contact_file and os.path.exists(contact_file): os.remove(contact_file)
            if slogan_file and os.path.exists(slogan_file): os.remove(slogan_file)
        except Exception:
            pass
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

        # Lire le prompt personnalisé, la voix-off, la musique, la durée et l'arrière-plan s'ils sont fournis
        custom_prompt = None
        voiceover_text = None
        music_style = "piano"
        duration = 30
        bg_config = {}
        style_preset = "modern"
        
        if request.content_type == "application/json" or request.body.startswith(b"{"):
            try:
                data = json.loads(request.body)
                custom_prompt = data.get("prompt")
                voiceover_text = data.get("voiceover_text")
                music_style = data.get("music_style", "piano")
                duration = int(data.get("duration", 30))
                bg_config = data.get("bg_config", {})
                style_preset = data.get("style_preset", "modern")
            except Exception:
                pass
        else:
            custom_prompt = request.POST.get("prompt")
            voiceover_text = request.POST.get("voiceover_text")
            music_style = request.POST.get("music_style", "piano")
            duration = int(request.POST.get("duration", 30))
            style_preset = request.POST.get("style_preset", "modern")
            # Reconstruire bg_config
            bg_config = {
                "bg_type": request.POST.get("bg_type", "color"),
                "bg_color": request.POST.get("bg_color", "#050910"),
                "bg_gradient": request.POST.getlist("bg_gradient") or [request.POST.get("bg_color_1", "#050910"), request.POST.get("bg_color_2", "#1e293b")],
                "bg_template": request.POST.get("bg_template", "dark")
            }

        # Enregistrer le texte de la voix-off et le style de musique en base
        if voiceover_text is not None:
            content.voice_over = voiceover_text.strip()
        
        if not isinstance(content.raw_json, dict):
            content.raw_json = {}
        content.raw_json["music_style"] = music_style
        content.raw_json["duration"] = duration
        content.raw_json["bg_config"] = bg_config
        content.raw_json["style_preset"] = style_preset
        content.save(update_fields=["voice_over", "raw_json"])

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
        
        # Veo reference_to_video ne supporte QUE 8 secondes au départ
        veo_duration = 8

        # Encodage de l'image du produit si présente avec l'arrière-plan personnalisé
        image_b64 = None
        if campaign.photo_produit:
            import base64
            try:
                padded_image_bytes = prepare_image_for_veo(campaign.photo_produit, bg_config=bg_config)
                image_b64 = base64.b64encode(padded_image_bytes).decode("utf-8")
                logger.info(f"[AdGen Video Generation] Image du produit ajustée en 16:9 avec fond personnalisé pour Veo.")
            except Exception as e:
                logger.warning(f"Failed to pad campaign product image, using fallback: {e}")
                try:
                    with campaign.photo_produit.open("rb") as img_file:
                        image_b64 = base64.b64encode(img_file.read()).decode("utf-8")
                except Exception:
                    pass

        # Lancer la génération au format paysage 16:9
        result = start_google_video(prompt, aspect_ratio="16:9", image_b64=image_b64, duration=veo_duration)

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
        
        # Récupérer la durée, le style de musique et autres configurations
        music_style = "piano"
        duration = 30.0
        if isinstance(content.raw_json, dict):
            music_style = content.raw_json.get("music_style", "piano")
            duration = float(content.raw_json.get("duration", 30.0))
        video_url = add_voiceover_to_video(video_url, "bg_music", campaign.pk, music_style=music_style, duration=duration)
            
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
