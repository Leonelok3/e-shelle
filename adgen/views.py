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

        # Lire le prompt personnalisé et la durée s'ils sont fournis
        custom_prompt = None
        duration = 5
        if request.content_type == "application/json" or request.body.startswith(b"{"):
            try:
                data = json.loads(request.body)
                custom_prompt = data.get("prompt")
                duration = int(data.get("duration", 5))
            except Exception:
                pass
        else:
            custom_prompt = request.POST.get("prompt")
            duration = int(request.POST.get("duration", 5))

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
        
        prompt = prompt[:1200]
        if duration not in [5, 10]:
            duration = 5

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
