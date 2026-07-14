from django import forms
from .models import CanadaCVProfile, CanadaCVExperience, CanadaCVEducation, CanadaCVLanguage

class CanadaCVProfileForm(forms.ModelForm):
    class Meta:
        model = CanadaCVProfile
        fields = [
            "first_name", "last_name", "email", "phone", 
            "address", "linkedin", "target_sector", "target_provinces"
        ]
        labels = {
            "first_name": "Prénom / First Name",
            "last_name": "Nom de famille / Last Name",
            "email": "Adresse courriel / Email Address",
            "phone": "Numéro de téléphone / Phone Number",
            "address": "Ville, Pays actuel / City, Current Country",
            "linkedin": "Lien profil LinkedIn / LinkedIn Profile Link",
            "target_sector": "Secteur d'activité ciblé / Target Sector",
            "target_provinces": "Provinces cibles au Canada / Target Provinces",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Prénom / First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom de famille / Last Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "courriel@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+1 514 XXX-XXXX / +237..."}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Douala, Cameroun / Paris, France"}),
            "linkedin": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://linkedin.com/in/nom-utilisateur"}),
            "target_sector": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Technologies, Services de Santé, Transport"}),
            "target_provinces": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Québec, Ontario, Alberta"}),
        }


class CanadaCVExperienceForm(forms.ModelForm):
    class Meta:
        model = CanadaCVExperience
        fields = [
            "title", "company", "city", "province_country", 
            "start_date", "end_date", "is_current", "description"
        ]
        labels = {
            "title": "Intitulé du poste / Job Title",
            "company": "Nom de l'employeur / Company Name",
            "city": "Ville / City",
            "province_country": "Province ou Pays / Province or Country",
            "start_date": "Date de début / Start Date",
            "end_date": "Date de fin / End Date",
            "is_current": "Poste actuel / Currently working here",
            "description": "Description (Tâches & Réalisations) / Description (Duties & Achievements)",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Infirmier, Chauffeur de camion, Développeur Web"}),
            "company": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Hôpital Général, Trans-Canada Logistics"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Douala, Montréal"}),
            "province_country": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Cameroun, Québec, Canada"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(attrs={
                "class": "form-control", 
                "rows": 6, 
                "placeholder": "Saisissez les tâches accomplies de manière simple ou en quelques mots."
            }),
        }


class CanadaCVEducationForm(forms.ModelForm):
    class Meta:
        model = CanadaCVEducation
        fields = [
            "degree", "school", "city", "province_country", 
            "start_year", "end_year"
        ]
        labels = {
            "degree": "Intitulé du diplôme ou formation / Degree or Program Title",
            "school": "Nom de l'établissement / School or University Name",
            "city": "Ville / City",
            "province_country": "Province ou Pays / Province or Country",
            "start_year": "Année de début / Start Year",
            "end_year": "Année de fin / End Year",
        }
        widgets = {
            "degree": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Baccalauréat en Administration des Affaires"}),
            "school": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Université de Douala, Cégep"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Yaoundé"}),
            "province_country": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Cameroun"}),
            "start_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Ex: 2018"}),
            "end_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Ex: 2021 (laisser vide si en cours)"}),
        }


class CanadaCVLanguageForm(forms.ModelForm):
    class Meta:
        model = CanadaCVLanguage
        fields = ["language", "proficiency", "certificate"]
        labels = {
            "language": "Langue / Language",
            "proficiency": "Niveau de maîtrise / Proficiency Level",
            "certificate": "Certificat ou score (Optionnel) / Certificate or Score (Optional)",
        }
        widgets = {
            "language": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Français, Anglais"}),
            "proficiency": forms.Select(attrs={"class": "form-select"}),
            "certificate": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: TEF Canada CLB 9, IELTS 7.0"}),
        }
