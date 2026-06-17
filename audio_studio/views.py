from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView, TemplateView

from .forms import MusicTrackForm, VoiceOverForm, VoiceProfileForm
from .models import MusicTrackJob, VoiceOverJob, VoiceProfile
from .services import generate_music_track, generate_voiceover_audio


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "audio_studio/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["voices"] = VoiceProfile.objects.filter(owner=user)[:8]
        ctx["voice_jobs"] = VoiceOverJob.objects.filter(user=user)[:8]
        ctx["music_jobs"] = MusicTrackJob.objects.filter(user=user)[:8]
        ctx["voice_form"] = VoiceProfileForm()
        ctx["voiceover_form"] = VoiceOverForm(user=user)
        ctx["music_form"] = MusicTrackForm()
        return ctx


class VoiceProfileCreateView(LoginRequiredMixin, CreateView):
    model = VoiceProfile
    form_class = VoiceProfileForm
    template_name = "audio_studio/form_page.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Voix enregistree. Vous pouvez maintenant preparer une voix-off.")
        return super().form_valid(form)

    def get_success_url(self):
        return "/audio-studio/"


class VoiceOverCreateView(LoginRequiredMixin, CreateView):
    model = VoiceOverJob
    form_class = VoiceOverForm
    template_name = "audio_studio/form_page.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        try:
            generate_voiceover_audio(self.object)
            messages.success(self.request, "Voix-off generee. Le fichier est pret a telecharger.")
        except Exception as exc:
            self.object.status = VoiceOverJob.Status.FAILED
            self.object.error_message = str(exc)
            self.object.save(update_fields=["status", "error_message"])
            messages.error(self.request, f"Generation voix-off impossible: {exc}")
        return response

    def get_success_url(self):
        return "/audio-studio/"


class MusicTrackCreateView(LoginRequiredMixin, CreateView):
    model = MusicTrackJob
    form_class = MusicTrackForm
    template_name = "audio_studio/form_page.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        try:
            generate_music_track(self.object)
            messages.success(self.request, "Musique generee. Le fichier est pret a telecharger.")
        except Exception as exc:
            self.object.status = MusicTrackJob.Status.FAILED
            self.object.error_message = str(exc)
            self.object.save(update_fields=["status", "error_message"])
            messages.error(self.request, f"Generation musique impossible: {exc}")
        return response

    def get_success_url(self):
        return "/audio-studio/"
