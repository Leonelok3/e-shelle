from django import forms

from .models import MusicTrackJob, VoiceOverJob, VoiceProfile


class VoiceProfileForm(forms.ModelForm):
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
    class Meta:
        model = VoiceOverJob
        fields = ["title", "voice_profile", "mode", "script"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex: Voix-off pub restaurant"}),
            "script": forms.Textarea(attrs={"rows": 7, "placeholder": "Collez ici le texte de votre voix-off..."}),
        }
        labels = {
            "title": "Titre",
            "voice_profile": "Voix a utiliser",
            "mode": "Mode de generation",
            "script": "Texte a transformer en audio",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = VoiceProfile.objects.none()
        if user and getattr(user, "is_authenticated", False):
            qs = VoiceProfile.objects.filter(owner=user, is_active=True, consent_confirmed=True)
        self.fields["voice_profile"].queryset = qs
        self.fields["voice_profile"].required = False
        self.fields["mode"].help_text = "Le mode clone demande une integration fournisseur. Le mode test local fonctionne sans API."


class MusicTrackForm(forms.ModelForm):
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
