from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView, TemplateView
from django.conf import settings
import os
import shutil
from django.urls import reverse
from django.shortcuts import get_object_or_404
from adgen.views import PaidAdGenRequiredMixin
from adgen.models import AdCampaign, AdContent
from adgen.services.studio_usage import reserve, finish, summary_for, StudioLimitError

from .forms import MusicTrackForm, VoiceOverForm, VoiceProfileForm
from .models import MusicTrackJob, VoiceOverJob, VoiceProfile
from .services import generate_music_track, generate_voiceover_audio, register_cloned_voice


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "audio_studio/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["voices"] = VoiceProfile.objects.filter(owner=user)[:8]
        ctx["voice_jobs"] = VoiceOverJob.objects.filter(user=user)[:8]
        ctx["music_jobs"] = MusicTrackJob.objects.filter(user=user)[:8]
        ctx["voice_form"] = VoiceProfileForm()
        initial = {}
        if self.request.GET.get("campaign"):
            campaign = get_object_or_404(AdCampaign, pk=self.request.GET["campaign"], user=user)
            initial = {"campaign": campaign, "title": campaign.nom_produit}
            content = AdContent.objects.filter(campaign=campaign).first()
            initial["script"] = content.voice_over if content else ""
            ctx["campaign"] = campaign
        ctx["voiceover_form"] = VoiceOverForm(user=user, initial=initial)
        ctx["music_form"] = MusicTrackForm(user=user, initial=initial)
        ctx["studio_usage"] = summary_for(user)
        return ctx


class VoiceProfileCreateView(PaidAdGenRequiredMixin, CreateView):
    model = VoiceProfile
    form_class = VoiceProfileForm
    template_name = "audio_studio/form_page.html"

    def form_valid(self, form):
        if VoiceProfile.objects.filter(owner=self.request.user).count() >= 10:
            form.add_error(None, "Vous avez déjà 10 extraits enregistrés. Contactez le support pour gérer votre bibliothèque.")
            return self.form_invalid(form)
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        if self.request.user.is_staff and self.object.consent_confirmed and getattr(settings, "ADGEN_STUDIO_CLONING_ENABLED", False):
            try:
                register_cloned_voice(self.object)
                messages.success(self.request, "Voix enregistree et clonee avec succes. Vous pouvez generer une voix-off avec votre propre voix.")
            except Exception as exc:
                messages.warning(
                    self.request,
                    f"Voix sauvegardee, mais le clonage a echoue pour l'instant ({exc}). "
                    "Vous pouvez reessayer plus tard depuis la generation de voix-off."
                )
        else:
            messages.success(self.request, "Extrait sauvegardé. Le clonage vocal est une option distincte, non incluse dans votre forfait.")
        return response

    def get_success_url(self):
        return reverse("adgen:studio_audio")


class VoiceOverCreateView(PaidAdGenRequiredMixin, CreateView):
    model = VoiceOverJob
    form_class = VoiceOverForm
    template_name = "audio_studio/form_page.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Preflight errors must never consume a customer's allowance.
        if not shutil.which("ffprobe"):
            form.add_error(None, "La préparation audio est temporairement indisponible. Aucun quota consommé.")
            return self.form_invalid(form)
        if not (getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY")) and form.cleaned_data["mode"] == "local":
            form.add_error(None, "La voix-off est temporairement indisponible. Aucun quota consommé.")
            return self.form_invalid(form)
        try:
            reservation = reserve(self.request.user, "voice", len(form.cleaned_data["script"]),
                                  campaign=form.cleaned_data.get("campaign"), key=str(form.cleaned_data["request_key"]))
        except StudioLimitError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
            generate_voiceover_audio(self.object)
            if form.cleaned_data.get("campaign"):
                content, _ = AdContent.objects.get_or_create(campaign=form.cleaned_data["campaign"])
                content.studio_voice = self.object
                content.save(update_fields=["studio_voice"])
            finish(reservation)
            messages.success(self.request, "Voix-off generee. Le fichier est pret a telecharger.")
        except Exception as exc:
            finish(reservation, failed=True)
            if not getattr(self, "object", None):
                raise
            self.object.status = VoiceOverJob.Status.FAILED
            self.object.error_message = str(exc)
            self.object.save(update_fields=["status", "error_message"])
            messages.error(self.request, "La génération a échoué. La tentative reste comptabilisée jusqu’à vérification du fournisseur par le support.")
            return redirect(self.get_success_url())
        return response

    def get_success_url(self):
        return reverse("adgen:studio_audio")


class MusicTrackCreateView(PaidAdGenRequiredMixin, CreateView):
    model = MusicTrackJob
    form_class = MusicTrackForm
    template_name = "audio_studio/form_page.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            reservation = reserve(self.request.user, "music", campaign=form.cleaned_data.get("campaign"),
                                  key=str(form.cleaned_data["request_key"]))
        except StudioLimitError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
            generate_music_track(self.object)
            if form.cleaned_data.get("campaign"):
                content, _ = AdContent.objects.get_or_create(campaign=form.cleaned_data["campaign"])
                content.studio_music = self.object
                content.save(update_fields=["studio_music"])
            finish(reservation)
            messages.success(self.request, "Musique generee. Le fichier est pret a telecharger.")
        except Exception as exc:
            finish(reservation, release=True)
            if not getattr(self, "object", None):
                raise
            self.object.status = MusicTrackJob.Status.FAILED
            self.object.error_message = str(exc)
            self.object.save(update_fields=["status", "error_message"])
            messages.error(self.request, f"Generation musique impossible: {exc}")
            return redirect(self.get_success_url())
        return response

    def get_success_url(self):
        return reverse("adgen:studio_audio")
