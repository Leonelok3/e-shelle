from django import forms
from django.core.exceptions import ValidationError

ALLOWED_CT = {"application/pdf",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_SIZE = 3 * 1024 * 1024  # 3 Mo

class FullCoverForm(forms.Form):
    full_name = forms.CharField(label="Nom Complet", max_length=120)
    email = forms.EmailField(label="Email", required=False)
    phone = forms.CharField(label="Téléphone", max_length=50, required=False)

    target_role = forms.CharField(label="Poste visé", max_length=120)
    company = forms.CharField(label="Entreprise", max_length=120)
    keywords = forms.CharField(label="Mots-clés (ATS)", required=False,
                               help_text="Sépare par des virgules : ex. Python, Django, Azure")

    experiences = forms.CharField(
        label="Expériences principales",
        widget=forms.Textarea(attrs={"rows": 5}),
        required=False
    )
    skills = forms.CharField(
        label="Compétences principales",
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False
    )

    tone = forms.ChoiceField(label="Ton", choices=[
        ('pro', 'Professionnel'),
        ('convaincant', 'Convaincant'),
        ('sobre', 'Sobre'),
    ])

    language = forms.ChoiceField(label="Langue", choices=[
        ('fr', 'Français'),
        ('en', 'English'),
    ])

class CVUploadForm(forms.Form):
    cv_file = forms.FileField(
        label="Téléverser un CV (PDF ou DOCX)",
        allow_empty_file=False,
        help_text="Max 3 Mo — PDF/DOCX"
    )

    def clean_cv_file(self):
        f = self.cleaned_data["cv_file"]
        if f.size > MAX_SIZE:
            raise ValidationError("Fichier trop volumineux (max 3 Mo).")
        # Certains navigateurs n'envoient pas toujours un type MIME fiable — on sécurise quand même:
        ct = (getattr(f, "content_type", None) or "").lower()
        name = (getattr(f, "name", "") or "").lower()
        if ct not in ALLOWED_CT and not (name.endswith(".pdf") or name.endswith(".docx")):
            raise ValidationError("Seuls PDF et DOCX sont autorisés.")
        return f
