from django import forms
from .models import CVUpload
from cv_generator.models import (
    CV, Experience, Education, Skill, Language,
    Volunteer, Hobby, Certification, Project
)

# ------------------------------
# 🔹 FORMULAIRES MULTI-STEP CV
# ------------------------------

class Step1Form(forms.ModelForm):
    nom = forms.CharField(max_length=100, required=True, label="Nom")
    prenom = forms.CharField(max_length=100, required=True, label="Prénom")
    email = forms.EmailField(required=True, label="Email")
    telephone = forms.CharField(max_length=20, required=False, label="Téléphone")

    class Meta:
        model = CV
        fields = ["profession", "pays_cible", "language"]
        labels = {
            "profession": "Profession / Poste ciblé",
            "pays_cible": "Pays ciblé",
            "language": "Langue du CV",
        }
        widgets = {
            "language": forms.Select(attrs={
                "class": "form-control"
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pré-remplissage depuis JSON
        if self.instance and self.instance.data.get("personal_info"):
            pi = self.instance.data["personal_info"]
            self.fields["nom"].initial = pi.get("nom", "")
            self.fields["prenom"].initial = pi.get("prenom", "")
            self.fields["email"].initial = pi.get("email", "")
            self.fields["telephone"].initial = pi.get("telephone", "")

    def save(self, commit=True, user=None):
        cv = super().save(commit=False)

        if user:
            cv.utilisateur = user

        # Stocker infos personnelles
        cv.data["personal_info"] = {
            "nom": self.cleaned_data["nom"],
            "prenom": self.cleaned_data["prenom"],
            "email": self.cleaned_data["email"],
            "telephone": self.cleaned_data["telephone"],
        }

        cv.step1_completed = True

        if commit:
            cv.save()

        return cv


class Step3Form(forms.ModelForm):
    class Meta:
        model = CV
        fields = ["summary", "is_published"]
        widgets = {
            'summary': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Résumé professionnel (optionnel, peut être généré par IA)',
                'class': 'w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-gray-100'
            })
        }

    def save(self, commit=True):
        cv = super().save(commit=False)
        cv.step3_completed = True
        if commit:
            cv.save()
        return cv


# ------------------------------
# 🔹 FORMULAIRES D'EXPÉRIENCE
# ------------------------------
class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['title', 'company', 'start_date', 'end_date', 'location', 'description_raw']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description_raw': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Décrivez vos missions, réalisations et responsabilités...'
            })
        }
        labels = {
            'title': 'Titre du poste',
            'company': 'Entreprise',
            'start_date': 'Date de début',
            'end_date': 'Date de fin (laisser vide si poste actuel)',
            'location': 'Lieu',
            'description_raw': 'Description'
        }


class ExperienceEditForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['title', 'company', 'start_date', 'end_date', 'location', 'description_raw']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description_raw': forms.Textarea(attrs={'rows': 5})
        }


# ------------------------------
# 🔹 FORMULAIRE ÉDUCATION
# ------------------------------
class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['diploma', 'institution', 'start_date', 'end_date', 'location', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Spécialisation, mentions, projets notables...'
            })
        }
        labels = {
            'diploma': 'Diplôme',
            'institution': 'Établissement',
            'start_date': 'Date de début',
            'end_date': 'Date de fin (laisser vide si en cours)',
            'location': 'Lieu',
            'description': 'Description'
        }


# ------------------------------
# 🆕 FORMULAIRE COMPÉTENCES
# ------------------------------
class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'category']  # ✅ Enlève 'level'
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Python, Leadership, Excel'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            })
        }
# ------------------------------
# 🆕 FORMULAIRE LANGUES
# ------------------------------
class LanguageForm(forms.ModelForm):
    class Meta:
        model = Language
        fields = ['name', 'level']
        labels = {
            'name': 'Langue',
            'level': 'Niveau'
        }


# ------------------------------
# 🆕 FORMULAIRE BÉNÉVOLAT
# ------------------------------
class VolunteerForm(forms.ModelForm):
    class Meta:
        model = Volunteer
        fields = [
            "role",
            "start_date",
            "end_date",
            "description",
        ]



# ------------------------------
# 🆕 FORMULAIRE CERTIFICATIONS
# ------------------------------
class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = ['name', 'organization', 'date_obtained', 'expiry_date', 'credential_id', 'credential_url']
        widgets = {
            'date_obtained': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'name': 'Nom de la certification',
            'organization': 'Organisme délivrant',
            'date_obtained': "Date d'obtention",
            'expiry_date': "Date d'expiration (optionnel)",
            'credential_id': 'ID de certification (optionnel)',
            'credential_url': 'URL de vérification (optionnel)'
        }


# ------------------------------
# 🆕 FORMULAIRE PROJETS
# ------------------------------
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'start_date', 'end_date', 'url', 'technologies']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Décrivez le projet, vos contributions et résultats...'
            }),
            'technologies': forms.TextInput(attrs={
                'placeholder': 'Ex: Python, Django, React, PostgreSQL'
            })
        }
        labels = {
            'title': 'Titre du projet',
            'description': 'Description',
            'start_date': 'Date de début',
            'end_date': 'Date de fin (optionnel)',
            'url': 'URL du projet (optionnel)',
            'technologies': 'Technologies utilisées'
        }


# ------------------------------
# 🆕 FORMULAIRE LOISIRS
# ------------------------------
class HobbyForm(forms.ModelForm):
    class Meta:
        model = Hobby
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Détails supplémentaires (optionnel)'
            })
        }
        labels = {
            'name': "Centre d'intérêt",
            'description': 'Description'
        }


# ------------------------------
# 🔹 FORMULAIRE ADMIN CV
# ------------------------------
class CVAdminForm(forms.ModelForm):
    class Meta:
        model = CV
        fields = [
            "profession", "pays_cible", "summary", "current_step",
            "step1_completed", "step2_completed", "step3_completed",
            "is_completed", "is_published"
        ]

class CVUploadForm(forms.ModelForm):
    class Meta:
        model = CVUpload
        fields = ["file"]
