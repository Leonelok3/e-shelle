from django import forms

from .models import DemandeTravaux, MetierArtisan, ProfilArtisan, VilleArtisan


class RechercheArtisanForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "Plombier, maçon, carreleur...", "class": "artisan-input"}))
    ville = forms.ModelChoiceField(required=False, queryset=VilleArtisan.objects.filter(active=True), empty_label="Toutes les villes", widget=forms.Select(attrs={"class": "artisan-input"}))
    metier = forms.ModelChoiceField(required=False, queryset=MetierArtisan.objects.filter(active=True), empty_label="Tous les métiers", widget=forms.Select(attrs={"class": "artisan-input"}))
    urgence = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "artisan-check"}))


class DemandeTravauxForm(forms.ModelForm):
    class Meta:
        model = DemandeTravaux
        fields = ["nom", "telephone", "ville", "metier", "quartier", "besoin", "description", "budget"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "artisan-input"}),
            "telephone": forms.TextInput(attrs={"class": "artisan-input", "placeholder": "+237 6XX XXX XXX"}),
            "ville": forms.Select(attrs={"class": "artisan-input"}),
            "metier": forms.Select(attrs={"class": "artisan-input"}),
            "quartier": forms.TextInput(attrs={"class": "artisan-input"}),
            "besoin": forms.TextInput(attrs={"class": "artisan-input", "placeholder": "Ex : fuite d'eau, carrelage salon, câblage maison..."}),
            "description": forms.Textarea(attrs={"class": "artisan-input", "rows": 4}),
            "budget": forms.NumberInput(attrs={"class": "artisan-input", "placeholder": "Budget estimatif"}),
        }


class ProfilArtisanForm(forms.ModelForm):
    class Meta:
        model = ProfilArtisan
        fields = ["nom_public", "metiers", "ville", "quartier", "zone_intervention", "description", "telephone", "whatsapp", "photo", "disponible_urgence", "intervention_domicile"]
        widgets = {
            "nom_public": forms.TextInput(attrs={"class": "artisan-input"}),
            "metiers": forms.CheckboxSelectMultiple(),
            "ville": forms.Select(attrs={"class": "artisan-input"}),
            "quartier": forms.TextInput(attrs={"class": "artisan-input"}),
            "zone_intervention": forms.TextInput(attrs={"class": "artisan-input"}),
            "description": forms.Textarea(attrs={"class": "artisan-input", "rows": 4}),
            "telephone": forms.TextInput(attrs={"class": "artisan-input"}),
            "whatsapp": forms.TextInput(attrs={"class": "artisan-input"}),
            "photo": forms.FileInput(attrs={"class": "artisan-input", "accept": "image/*"}),
        }
