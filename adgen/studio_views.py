import json
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils import timezone
from audio_studio.models import VoiceOverJob, MusicTrackJob
from accounts.models import AppPlan
from .views import PaidAdGenRequiredMixin
from .models import AdCampaign, AdCinemaClip, AdContent, StudioUsage
from .studio_plans import STUDIO_PLANS
from .services.studio_usage import reserve, summary_for, StudioLimitError
from .services.studio_render import start_render
from .services.studio_storyboard import parse_storyboard
from .services.studio_offers import source_for
from .services import studio_cinema


class StudioMediaForm(forms.Form):
    voice = forms.ModelChoiceField(queryset=VoiceOverJob.objects.none(), required=False, label="Voix-off du montage")
    music = forms.ModelChoiceField(queryset=MusicTrackJob.objects.none(), required=False, label="Ambiance du montage")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["voice"].queryset = VoiceOverJob.objects.filter(user=user, status="done").exclude(audio_file="")
        self.fields["music"].queryset = MusicTrackJob.objects.filter(user=user, status="done").exclude(audio_file="")

    def clean_voice(self):
        voice = self.cleaned_data.get("voice")
        if voice and voice.duration_seconds > 15:
            raise forms.ValidationError("Choisissez une narration de 15 secondes maximum pour ce montage.")
        return voice


class StudioMediaView(PaidAdGenRequiredMixin, View):
    def post(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)
        form = StudioMediaForm(request.POST, user=request.user)
        with transaction.atomic():
            # Same lock order as quota reservations.
            from django.contrib.auth import get_user_model
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if StudioUsage.objects.filter(campaign=campaign, resource="video", status__in=["reserved", "running"]).exists():
                messages.warning(request, "Attendez la fin du montage avant de changer ses médias.")
            elif form.is_valid():
                content, _ = AdContent.objects.get_or_create(campaign=campaign)
                content.studio_voice = form.cleaned_data["voice"]
                content.studio_music = form.cleaned_data["music"]
                content.save(update_fields=["studio_voice", "studio_music"])
                messages.success(request, "Médias associés. Le prochain montage utilisera cette voix et cette ambiance.")
            else:
                messages.error(request, " ".join(str(e) for errors in form.errors.values() for e in errors))
        return redirect("adgen:detail", pk=pk)


class StudioPricingView(TemplateView):
    template_name = "adgen/studio_pricing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["plans"] = AppPlan.objects.filter(slug__in=STUDIO_PLANS, is_active=True).order_by("order")
        if self.request.user.is_authenticated:
            ctx["studio_usage"] = summary_for(self.request.user)
        return ctx


class StudioRenderView(PaidAdGenRequiredMixin, View):
    def post(self, request, pk):
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)
        if not campaign.photo_produit:
            return JsonResponse({"error": "Ajoutez une photo du produit avant le montage."}, status=400)
        if campaign.offer_id:
            offer = source_for(campaign)
            if not offer or offer.price != campaign.prix:
                return JsonResponse({"error": "L’offre ou son prix a changé. Créez un nouveau projet depuis la fiche à jour."}, status=409)
        content = get_object_or_404(AdContent, campaign=campaign)
        try:
            data = json.loads(request.body) if request.content_type == "application/json" else request.POST
            if not isinstance(data, (dict, type(request.POST))):
                raise ValueError()
        except (ValueError, TypeError):
            return JsonResponse({"error": "Demande invalide."}, status=400)
        if content.studio_voice and content.studio_voice.duration_seconds > 15:
            return JsonResponse({"error": "Raccourcissez la voix-off à 15 secondes avant de lancer le montage."}, status=400)
        try:
            storyboard = parse_storyboard(data, campaign)
            if storyboard["auto_captions"] and not content.studio_voice_id:
                raise ValidationError("Associez une voix-off avant de demander ses sous-titres.")
        except ValidationError as exc:
            return JsonResponse({"error": exc.messages[0]}, status=400)
        cinema_requested = data.get("cinema") in (True, "true", "1", "on")
        cinema = AdCinemaClip.objects.filter(campaign=campaign, state="approved").exclude(video="").first() if cinema_requested else None
        if cinema_requested and not cinema:
            return JsonResponse({"error": "Validez d’abord le plan cinéma."}, status=400)
        try:
            with transaction.atomic():
                job = reserve(request.user, "video", campaign=campaign)
                job.payload = {"music_style": str(data.get("music_style", "piano"))[:30], "storyboard": storyboard,
                               "cinema_id": cinema.pk if cinema else None,
                               "studio_media": {"voice_id": content.studio_voice_id, "music_id": content.studio_music_id},
                               "bg_config": data.get("bg_config", {}) if isinstance(data.get("bg_config", {}), dict) else {}}
                job.save(update_fields=["payload"])
                transaction.on_commit(lambda: start_render(job.pk))
        except StudioLimitError as exc:
            return JsonResponse({"error": str(exc), "quota_exceeded": True}, status=429)
        return JsonResponse({"operation_name": f"studio:{job.pk}", "provider": "local", "prompt": ""})


class StudioSoraRetiredView(PaidAdGenRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(AdCampaign, pk=pk, user=request.user)
        return JsonResponse({"error": "Les nouvelles générations Sora sont désactivées. Utilisez le montage photo avec voix-off. Vos anciens crédits sont conservés pour traitement par le support."}, status=410)


class StudioCinemaView(PaidAdGenRequiredMixin, View):
    def post(self, request, pk):
        if not request.user.is_staff or not studio_cinema.enabled():
            raise Http404
        campaign = get_object_or_404(AdCampaign, pk=pk, user=request.user)
        action = request.POST.get("action")
        try:
            if action == "create":
                self.create_clip(request, campaign)
            elif action == "refresh":
                with transaction.atomic():
                    clip = get_object_or_404(AdCinemaClip.objects.select_for_update(), campaign=campaign)
                    if clip.state == "pending":
                        studio_cinema.refresh_clip(clip)
            elif action in {"approve", "reject"}:
                AdCinemaClip.objects.filter(campaign=campaign, state="review").exclude(video="").update(
                    state="approved" if action == "approve" else "rejected",
                )
        except (OSError, ValueError, KeyError) as exc:
            messages.error(request, "Action cinéma indisponible. Vérifiez l’état du plan avant toute nouvelle demande.")
        return redirect("adgen:detail", pk=pk)

    def create_clip(self, request, campaign):
        if request.POST.get("accept_cost") != "yes" or not campaign.photo_produit:
            raise ValueError("Photo et acceptation du coût requises.")
        image = studio_cinema._photo_payload(campaign.photo_produit)
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if AdCinemaClip.objects.filter(campaign=campaign).exists() or AdCinemaClip.objects.filter(
                campaign__user=request.user, created_at__date=timezone.localdate(),
            ).exists():
                messages.warning(request, "Le pilote autorise un plan par campagne et par jour pour ce compte.")
                return
            clip = AdCinemaClip.objects.create(campaign=campaign)
        # The reservation remains persisted if the provider accepted an ambiguous request.
        studio_cinema.start_clip(clip, image)


class StudioCinemaPreviewView(PaidAdGenRequiredMixin, View):
    def get(self, request, pk):
        clip = get_object_or_404(AdCinemaClip.objects.exclude(video=""), campaign_id=pk, campaign__user=request.user)
        response = FileResponse(clip.video.open("rb"), content_type="video/mp4")
        response["Cache-Control"] = "private, no-store"
        return response
