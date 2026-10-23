from django import forms

from edu_platform.models import ChallengeSubmission, DailyChallenge


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if data in self.empty_values:
            return []
        items = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(item, initial) for item in items]


class ChallengeSubmissionForm(forms.ModelForm):
    files = MultipleFileField(
        label="Photos ou fichier PDF",
        required=False,
        widget=MultipleFileInput(attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf"}),
    )

    class Meta:
        model = ChallengeSubmission
        fields = ("student_name", "student_class", "show_name_on_leaderboard")
        labels = {
            "student_name": "Nom et prénom",
            "student_class": "Classe (facultatif)",
            "show_name_on_leaderboard": "J’accepte que mon nom apparaisse au classement de ce challenge",
        }
        widgets = {
            "student_name": forms.TextInput(attrs={"autocomplete": "name", "maxlength": 120, "class": "form-control"}),
            "student_class": forms.TextInput(attrs={"maxlength": 80, "class": "form-control"}),
            "show_name_on_leaderboard": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.uploads = kwargs.pop("uploads", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        uploads = self.uploads or []
        if not uploads:
            self.add_error("files", "Ajoute au moins une photo ou un PDF.")
            return cleaned
        if len(uploads) > 5:
            self.add_error("files", "Tu peux envoyer au maximum 5 fichiers par challenge.")
        if sum(f.size for f in uploads) > 20 * 1024 * 1024:
            self.add_error("files", "La taille totale des fichiers ne doit pas dépasser 20 Mo.")
        pdfs = 0
        for uploaded in uploads:
            name = uploaded.name.lower()
            if uploaded.size > 10 * 1024 * 1024:
                self.add_error("files", f"{uploaded.name} dépasse la limite de 10 Mo.")
                continue
            if name.endswith(".pdf"):
                pdfs += 1
                if uploaded.read(5) != b"%PDF-":
                    self.add_error("files", f"{uploaded.name} n’est pas un PDF valide.")
            elif name.endswith((".jpg", ".jpeg", ".png", ".webp")):
                try:
                    from PIL import Image
                    uploaded.seek(0)
                    image = Image.open(uploaded)
                    image.verify()
                except Exception:
                    self.add_error("files", f"{uploaded.name} n’est pas une image lisible.")
            else:
                self.add_error("files", "Formats acceptés : PDF, JPG, PNG et WEBP.")
            uploaded.seek(0)
        if pdfs and len(uploads) > 1:
            self.add_error("files", "Envoie un seul PDF, ou jusqu’à 5 photos.")
        return cleaned


class DailyChallengeForm(forms.ModelForm):
    class Meta:
        model = DailyChallenge
        fields = ("title", "instructions", "subject", "level", "exercise_file", "answer_key", "rubric", "total_points", "status", "starts_at", "ends_at", "leaderboard_enabled")
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 3}),
            "answer_key": forms.Textarea(attrs={"rows": 6}),
            "rubric": forms.Textarea(attrs={"rows": 5}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        starts_at, ends_at = cleaned.get("starts_at"), cleaned.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "La date de clôture doit suivre la date de début.")
        return cleaned

    def clean_total_points(self):
        total = self.cleaned_data["total_points"]
        if total < 1:
            raise forms.ValidationError("Le total de points doit être supérieur à zéro.")
        return total
