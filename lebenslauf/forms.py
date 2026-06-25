from django import forms
from .models import GermanCVProfile, CVExperience, CVEducation, CVLanguage


class CVProfileForm(forms.ModelForm):
    class Meta:
        model  = GermanCVProfile
        exclude = ["user", "created_at", "updated_at"]
        widgets = {
            "date_of_birth":   forms.DateInput(attrs={"type": "date"}),
            "goethe_cert_date": forms.DateInput(attrs={"type": "date"}),
            "target_cities":   forms.TextInput(attrs={"placeholder": "Ex: Berlin, Hamburg, Koeln"}),
            "target_sector":   forms.TextInput(attrs={"placeholder": "Ex: Gesundheit, Informatik"}),
            "phone":           forms.TextInput(attrs={"placeholder": "+237 6XX XX XX XX"}),
            "address":         forms.TextInput(attrs={"placeholder": "Douala, Cameroun"}),
            "linkedin":        forms.URLInput(attrs={"placeholder": "https://linkedin.com/in/..."}),
        }


class CVExperienceForm(forms.ModelForm):
    class Meta:
        model  = CVExperience
        exclude = ["user", "order"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date":   forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "- Prise en charge des patients...\n- Gestion des medicaments...\n- Coordination avec l'equipe..."
            }),
        }


class CVEducationForm(forms.ModelForm):
    class Meta:
        model  = CVEducation
        exclude = ["user", "order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class CVLanguageForm(forms.ModelForm):
    class Meta:
        model  = CVLanguage
        exclude = ["user"]
