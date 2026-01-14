from django import forms
from django.core.exceptions import FieldError

from .models import (
    CV, CVUpload, Experience, Formation, Skill, Langue,
    Volunteer, Hobby, Certification, Project, Competence
)

# =====================================================
# CONSTANTES
# =====================================================

LANGUAGE_CHOICES = [
    ("fr", "Français"),
    ("en", "Anglais"),
    ("de", "Allemand"),
    ("es", "Espagnol"),
    ("it", "Italien"),
]


# =====================================================
# FORMULAIRES MULTI-STEP CV
# =====================================================

class Step1Form(forms.ModelForm):
    """Étape 1 : Informations personnelles + Configuration CV"""

    class Meta:
        model = CV
        fields = [
            "nom", "prenom", "email", "telephone",
            "ville", "province", "linkedin",
            "titre_poste", "profession", "pays_cible", "language",
        ]
        labels = {
            "nom": "Nom",
            "prenom": "Prénom",
            "email": "Email",
            "telephone": "Téléphone",
            "ville": "Ville",
            "province": "Province/État",
            "linkedin": "LinkedIn (optionnel)",
            "titre_poste": "Titre du poste ciblé",
            "profession": "Profession/Secteur",
            "pays_cible": "Pays ciblé",
            "language": "Langue du CV",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Dupont"}),
            "prenom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Jean"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "jean.dupont@email.com"}),
            "telephone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+33 6 12 34 56 78"}),
            "ville": forms.TextInput(attrs={"class": "form-control", "placeholder": "Paris"}),
            "province": forms.TextInput(attrs={"class": "form-control", "placeholder": "Île-de-France"}),
            "linkedin": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://linkedin.com/in/votre-profil"}),
            "titre_poste": forms.TextInput(attrs={"class": "form-control", "placeholder": "Développeur Full-Stack"}),
            "profession": forms.TextInput(attrs={"class": "form-control", "placeholder": "Informatique / IT"}),
            "pays_cible": forms.TextInput(attrs={"class": "form-control", "placeholder": "Canada"}),
            "language": forms.Select(attrs={"class": "form-control"}, choices=LANGUAGE_CHOICES),
        }

    def save(self, commit=True):
        cv = super().save(commit=False)
        cv.step1_completed = True
        cv.current_step = max(cv.current_step or 1, 2)
        if commit:
            cv.save()
        return cv


class Step3Form(forms.ModelForm):
    """Étape 3 : Résumé professionnel + Finalisation"""

    class Meta:
        model = CV
        fields = ["summary", "resume_professionnel"]
        labels = {
            "summary": "Résumé professionnel (EN)",
            "resume_professionnel": "Résumé professionnel (FR)",
        }
        widgets = {
            "summary": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "Professional summary in English (optional, can be AI-generated)"
            }),
            "resume_professionnel": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "Résumé professionnel en français (optionnel, peut être généré par IA)"
            }),
        }

    def save(self, commit=True):
        cv = super().save(commit=False)
        cv.step3_completed = True
        cv.is_completed = True
        if commit:
            cv.save()
        return cv


# =====================================================
# FORMULAIRES D'EXPÉRIENCE
# =====================================================

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ["title", "company", "location", "start_date", "end_date", "description_raw"]
        labels = {
            "title": "Titre du poste",
            "company": "Entreprise",
            "location": "Lieu",
            "start_date": "Date de début",
            "end_date": "Date de fin (laisser vide si poste actuel)",
            "description_raw": "Description des missions",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Développeur Full-Stack"}),
            "company": forms.TextInput(attrs={"class": "form-control", "placeholder": "Google"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "Paris, France"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description_raw": forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
        }


# =====================================================
# FORMULAIRES ÉDUCATION/FORMATION
# =====================================================

class EducationForm(forms.ModelForm):
    class Meta:
        model = Formation
        fields = ["diploma", "institution", "location", "start_date", "end_date", "description"]
        widgets = {
            "diploma": forms.TextInput(attrs={"class": "form-control"}),
            "institution": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

FormationForm = EducationForm


# =====================================================
# FORMULAIRES COMPÉTENCES
# =====================================================

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Python, Leadership"}),
            "category": forms.Select(attrs={"class": "form-control"}),
        }


class CompetenceForm(forms.ModelForm):
    class Meta:
        model = Competence
        fields = ["nom"]
        widgets = {"nom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Excel"})}


# =====================================================
# FORMULAIRES LANGUES (ANTI-CRASH ✅)
# =====================================================

class LangueForm(forms.ModelForm):
    """
    IMPORTANT: on NE met PAS fields=['langue','niveau'] ici,
    sinon Django crash si le modèle n'a que name/level.
    """

    class Meta:
        model = Langue
        fields = "__all__"  # ✅ ne crash jamais

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        model_fields = {f.name for f in self._meta.model._meta.get_fields() if hasattr(f, "name")}

        # On vide tout puis on remet seulement les bons champs
        for k in list(self.fields.keys()):
            self.fields.pop(k, None)

        # Cas 1 : modèle FR (langue/niveau)
        if "langue" in model_fields and "niveau" in model_fields:
            self.fields["langue"] = forms.CharField(
                required=True,
                label="Langue",
                widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex : Français, Anglais"})
            )
            self.fields["niveau"] = forms.CharField(
                required=True,
                label="Niveau",
                widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex : Courant (C1)"})
            )

        # Cas 2 : modèle EN (name/level)
        elif "name" in model_fields and "level" in model_fields:
            self.fields["name"] = forms.CharField(
                required=True,
                label="Language",
                widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: English"})
            )
            self.fields["level"] = forms.CharField(
                required=True,
                label="Level",
                widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Fluent"})
            )
        else:
            raise FieldError("Le modèle Langue ne contient ni (langue,niveau) ni (name,level). Vérifie models.py.")


class LanguageForm(LangueForm):
    """Alias : même comportement, pour compatibilité."""
    pass


# =====================================================
# FORMULAIRES CERTIFICATIONS
# =====================================================

class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = ["name", "organization", "date_obtained", "expiry_date", "credential_id", "credential_url"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "organization": forms.TextInput(attrs={"class": "form-control"}),
            "date_obtained": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "credential_id": forms.TextInput(attrs={"class": "form-control"}),
            "credential_url": forms.URLInput(attrs={"class": "form-control"}),
        }


# =====================================================
# FORMULAIRES BÉNÉVOLAT
# =====================================================

class VolunteerForm(forms.ModelForm):
    class Meta:
        model = Volunteer
        fields = ["role", "organization", "start_date", "end_date", "description"]
        widgets = {
            "role": forms.TextInput(attrs={"class": "form-control"}),
            "organization": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


# =====================================================
# FORMULAIRES PROJETS
# =====================================================

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "description", "technologies", "start_date", "end_date", "url"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "technologies": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
        }


# =====================================================
# FORMULAIRES LOISIRS
# =====================================================

class HobbyForm(forms.ModelForm):
    class Meta:
        model = Hobby
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Photographie"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


# =====================================================
# FORMULAIRE UPLOAD CV
# =====================================================

class CVUploadForm(forms.ModelForm):
    class Meta:
        model = CVUpload
        fields = ["file"]
        widgets = {
            "file": forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.doc,.docx"}),
        }


from django import forms
from .models import CV

class CVForm(forms.ModelForm):
    class Meta:
        model = CV
        exclude = ("user",)
        # Mets ici les champs QUI EXISTENT réellement dans ton modèle CV
        fields = fields = "__all__"
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 5}),
        }
