from django import forms
from django.conf import settings
from adgen.models import AdCampaign
import uuid

from .models import MusicTrackJob, VoiceOverJob, VoiceProfile


class VoiceProfileForm(forms.ModelForm):
    def clean_sample(self):
        sample = self.cleaned_data["sample"]
        if sample.size > 10 * 1024 * 1024:
            raise forms.ValidationError("L'extrait doit peser moins de 10 Mo.")
        return sample

    consent_confirmed = forms.BooleanField(
        required=True,
        label="Je confirme que cette voix m'appartient ou que j'ai une autorisation explicite.",
    )

    class Meta:
        model = VoiceProfile
        fields = ["name", "sample", "consent_confirmed", "consent_note"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ex: Ma voix naturelle"}),
            "sample": forms.ClearableFileInput(attrs={"accept": "audio/*"}),
            "consent_note": forms.TextInput(attrs={"placeholder": "Ex: Ma propre voix pour mes videos E-Shelle"}),
        }
        labels = {
            "name": "Nom de la voix",
            "sample": "Extrait audio de reference",
            "consent_note": "Note de consentement",
        }


class VoiceOverForm(forms.ModelForm):
    request_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
    campaign = forms.ModelChoiceField(queryset=AdCampaign.objects.none(), required=False,
                                     label="Associer à une campagne")
    class Meta:
        model = VoiceOverJob
        fields = ["title", "voice_profile", "mode", "openai_voice", "script"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex: Voix-off pub restaurant"}),
            "script": forms.Textarea(attrs={"rows": 7, "placeholder": "Collez ici le texte de votre voix-off..."}),
        }
        labels = {
            "title": "Titre",
            "voice_profile": "Ma voix enregistree (mode clone uniquement)",
            "mode": "Mode de generation",
            "openai_voice": "Voix IA",
            "script": "Texte a transformer en audio",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["script"].max_length = 4000
        self.fields["script"].widget.attrs["maxlength"] = 4000
        self.fields["campaign"].queryset = AdCampaign.objects.filter(user=user) if user else AdCampaign.objects.none()
        qs = VoiceProfile.objects.none()
        if user and getattr(user, "is_authenticated", False):
            qs = VoiceProfile.objects.filter(owner=user, is_active=True, consent_confirmed=True)
        self.fields["voice_profile"].queryset = qs
        self.fields["voice_profile"].required = False
        self.fields["mode"].help_text = (
            "« Voix IA (OpenAI) » utilise une voix generique. "
            "« Ma voix clonee » utilise votre propre voix enregistree ci-dessus (consentement requis)."
        )

    def clean_script(self):
        script = self.cleaned_data["script"].strip()
        if not script or len(script) > 4000:
            raise forms.ValidationError("Saisissez entre 1 et 4 000 caractères.")
        return script

    def clean(self):
        data = super().clean()
        if data.get("mode") == "clone" and not (self.user and self.user.is_staff and getattr(settings, "ADGEN_STUDIO_CLONING_ENABLED", False)):
            self.add_error("mode", "Le clonage est une option distincte, non incluse dans les forfaits actuels. Choisissez une voix standard.")
        return data


class MusicTrackForm(forms.ModelForm):
    request_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
    campaign = forms.ModelChoiceField(queryset=AdCampaign.objects.none(), required=False,
                                     label="Associer à une campagne")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["campaign"].queryset = AdCampaign.objects.filter(user=user) if user else AdCampaign.objects.none()
        self.fields["prompt"].required = False
        self.fields["prompt"].label = "Note personnelle (ne modifie pas la mélodie)"
    class Meta:
        model = MusicTrackJob
        fields = ["title", "prompt", "mood", "duration_seconds"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex: Musique promo taro"}),
            "prompt": forms.Textarea(attrs={"rows": 4, "placeholder": "Ex: fond afrobeat moderne pour video TikTok food, joyeux et vendeur"}),
            "duration_seconds": forms.NumberInput(attrs={"min": 5, "max": 120}),
        }
        labels = {
            "title": "Titre",
            "prompt": "Description musicale",
            "mood": "Style",
            "duration_seconds": "Duree en secondes",
        }

    def clean_duration_seconds(self):
        value = self.cleaned_data.get("duration_seconds") or 20
        return max(5, min(int(value), 120))
