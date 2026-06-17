"""
AdGen — Formulaires
"""
from django import forms
from .models import AdCampaign, AdModule, PAYS_CHOICES, VILLE_CHOICES


class CampaignForm(forms.ModelForm):
    ville = forms.ChoiceField(
        choices=VILLE_CHOICES,
        required=False,
        label="Ville cible",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model  = AdCampaign
        fields = ["nom_produit", "description", "photo_produit", "prix", "cible", "pays", "ville"]
        widgets = {
            "nom_produit": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: Huile de palme rouge naturelle",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Décrivez votre produit : composition, avantages, comment ça marche...",
            }),
            "photo_produit": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
            "prix": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: 2500 FCFA",
            }),
            "cible": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: Femmes 25-45 ans, ménagères, revendeuses",
            }),
            "pays": forms.Select(attrs={"class": "form-select"}),
            "ville": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "nom_produit": "Nom du produit",
            "description": "Description du produit",
            "photo_produit": "Photo du produit",
            "prix":        "Prix de vente",
            "cible":       "Audience cible",
            "pays":        "Pays cible",
            "ville":       "Ville cible",
        }

    def clean_nom_produit(self):
        val = self.cleaned_data.get("nom_produit", "").strip()
        if len(val) < 3:
            raise forms.ValidationError("Le nom du produit doit faire au moins 3 caractères.")
        return val

    def clean_description(self):
        val = self.cleaned_data.get("description", "").strip()
        if len(val) < 20:
            raise forms.ValidationError("La description doit faire au moins 20 caractères.")
        # Sécurité : on retire les balises HTML
        import html
        return html.escape(val)

    def clean_prix(self):
        val = self.cleaned_data.get("prix", "").strip()
        if not val:
            raise forms.ValidationError("Le prix est obligatoire.")
        return val
