from django import forms
from .models import CanadaCVProfile, CanadaCVExperience, CanadaCVEducation, CanadaCVLanguage

class CanadaCVProfileForm(forms.ModelForm):
    class Meta:
        model = CanadaCVProfile
        fields = [
            "first_name", "last_name", "email", "phone", 
            "address", "linkedin", "target_sector", "target_provinces"
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Prénom"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom de famille"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Adresse email"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Numéro de téléphone"}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ville, Pays actuel"}),
            "linkedin": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://linkedin.com/in/nom"}),
            "target_sector": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Technologies, Services de Santé"}),
            "target_provinces": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Québec, Ontario"}),
        }


class CanadaCVExperienceForm(forms.ModelForm):
    class Meta:
        model = CanadaCVExperience
        fields = [
            "title", "company", "city", "province_country", 
            "start_date", "end_date", "is_current", "description"
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Intitulé du poste"}),
            "company": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom de l'entreprise"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ville"}),
            "province_country": forms.TextInput(attrs={"class": "form-control", "placeholder": "Province ou Pays"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(attrs={
                "class": "form-control", 
                "rows": 5, 
                "placeholder": "Décrivez vos responsabilités et vos résultats. Ex: - Augmentation de 20% des ventes grâce à... - Gestion d'une équipe de..."
            }),
        }


class CanadaCVEducationForm(forms.ModelForm):
    class Meta:
        model = CanadaCVEducation
        fields = [
            "degree", "school", "city", "province_country", 
            "start_year", "end_year"
        ]
        widgets = {
            "degree": forms.TextInput(attrs={"class": "form-control", "placeholder": "Intitulé du diplôme ou formation"}),
            "school": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom de l'école ou université"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ville"}),
            "province_country": forms.TextInput(attrs={"class": "form-control", "placeholder": "Province ou Pays"}),
            "start_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Année de début"}),
            "end_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Année de fin (laisser vide si en cours)"}),
        }


class CanadaCVLanguageForm(forms.ModelForm):
    class Meta:
        model = CanadaCVLanguage
        fields = ["language", "proficiency", "certificate"]
        widgets = {
            "language": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Français, Anglais"}),
            "proficiency": forms.Select(attrs={"class": "form-select"}),
            "certificate": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: TEF Canada (Niveaux CLB 9), IELTS 7.0 (optionnel)"}),
        }
