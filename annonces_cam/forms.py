"""
forms.py — annonces_cam
"""
import re
from django import forms
from django.forms import inlineformset_factory

from .models import (
    Annonce, PhotoAnnonce, ProfilVendeur, SignalementAnnonce,
    EtatProduit, DeviseAnnonce, ModeContact, VILLES_CHOICES,
)


def valider_telephone(valeur):
    nettoye = re.sub(r"[\s\-\(\)]", "", valeur)
    if not re.match(r"^\+?[0-9]{8,15}$", nettoye):
        raise forms.ValidationError("Numéro de téléphone invalide.")
    return nettoye


# ─────────────────────────────────────────────────────────────────
# ANNONCE
# ─────────────────────────────────────────────────────────────────

class AnnonceForm(forms.ModelForm):

    class Meta:
        model  = Annonce
        fields = [
            "titre", "categorie", "description", "etat_produit",
            "prix", "devise", "prix_a_debattre", "gratuit",
            "ville", "quartier", "adresse_precise",
            "telephone_contact", "whatsapp_contact", "email_contact", "mode_contact",
        ]
        widgets = {
            "titre":             forms.TextInput(attrs={"class": "ann-input", "placeholder": "Ex : iPhone 14 Pro, canapé, parcelle, service…"}),
            "categorie":         forms.Select(attrs={"class": "ann-input"}),
            "description":       forms.Textarea(attrs={"class": "ann-input", "rows": 6, "placeholder": "Décrivez le produit ou service en détail…"}),
            "etat_produit":      forms.Select(attrs={"class": "ann-input"}),
            "prix":              forms.NumberInput(attrs={"class": "ann-input", "placeholder": "Ex : 50000"}),
            "devise":            forms.Select(attrs={"class": "ann-input"}),
            "prix_a_debattre":   forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "gratuit":           forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ville":             forms.Select(attrs={"class": "ann-input"}, choices=VILLES_CHOICES),
            "quartier":          forms.TextInput(attrs={"class": "ann-input", "placeholder": "Quartier"}),
            "adresse_precise":   forms.TextInput(attrs={"class": "ann-input", "placeholder": "Adresse précise (optionnel)"}),
            "telephone_contact": forms.TextInput(attrs={"class": "ann-input", "placeholder": "+237 6XX XX XX XX"}),
            "whatsapp_contact":  forms.TextInput(attrs={"class": "ann-input", "placeholder": "+237 6XX XX XX XX (optionnel)"}),
            "email_contact":     forms.EmailInput(attrs={"class": "ann-input", "placeholder": "email@exemple.com (optionnel)"}),
            "mode_contact":      forms.Select(attrs={"class": "ann-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limite catégories aux sous-catégories uniquement
        from .models import Categorie
        self.fields["categorie"].queryset = Categorie.objects.filter(parent__isnull=False, est_active=True).select_related("parent").order_by("parent__nom", "nom")

    def clean_telephone_contact(self):
        return valider_telephone(self.cleaned_data.get("telephone_contact", ""))

    def clean(self):
        cleaned = super().clean()
        gratuit = cleaned.get("gratuit")
        prix_a_debattre = cleaned.get("prix_a_debattre")
        prix = cleaned.get("prix")
        if not gratuit and not prix_a_debattre and not prix:
            self.add_error("prix", "Renseignez un prix, cochez 'Prix à débattre' ou 'Gratuit'.")
        return cleaned


PhotoAnnonceFormSet = inlineformset_factory(
    Annonce, PhotoAnnonce,
    fields=["image", "legende", "est_photo_principale", "ordre"],
    extra=5, can_delete=True, max_num=10,
    widgets={
        "image":   forms.ClearableFileInput(attrs={"class": "ann-input", "accept": "image/*"}),
        "legende": forms.TextInput(attrs={"class": "ann-input", "placeholder": "Légende (optionnel)"}),
        "ordre":   forms.NumberInput(attrs={"class": "ann-input", "min": 0}),
    }
)


# ─────────────────────────────────────────────────────────────────
# PROFIL VENDEUR
# ─────────────────────────────────────────────────────────────────

class ProfilVendeurForm(forms.ModelForm):
    class Meta:
        model  = ProfilVendeur
        fields = ["nom_boutique", "description_boutique", "telephone", "whatsapp", "ville", "photo_profil"]
        widgets = {
            "nom_boutique":          forms.TextInput(attrs={"class": "ann-input", "placeholder": "Nom de votre boutique"}),
            "description_boutique":  forms.Textarea(attrs={"class": "ann-input", "rows": 3, "placeholder": "Décrivez votre activité…"}),
            "telephone":             forms.TextInput(attrs={"class": "ann-input", "placeholder": "+237 6XX XX XX XX"}),
            "whatsapp":              forms.TextInput(attrs={"class": "ann-input", "placeholder": "+237 6XX XX XX XX"}),
            "ville":                 forms.Select(attrs={"class": "ann-input"}, choices=VILLES_CHOICES),
            "photo_profil":          forms.ClearableFileInput(attrs={"class": "ann-input", "accept": "image/*"}),
        }

    def clean_telephone(self):
        val = self.cleaned_data.get("telephone", "")
        if val:
            return valider_telephone(val)
        return val

    def clean_whatsapp(self):
        val = self.cleaned_data.get("whatsapp", "")
        if val:
            return valider_telephone(val)
        return val


# ─────────────────────────────────────────────────────────────────
# SIGNALEMENT
# ─────────────────────────────────────────────────────────────────

class SignalementAnnonceForm(forms.ModelForm):
    class Meta:
        model  = SignalementAnnonce
        fields = ["motif", "description"]
        widgets = {
            "motif":       forms.Select(attrs={"class": "ann-input"}),
            "description": forms.Textarea(attrs={"class": "ann-input", "rows": 4, "placeholder": "Détaillez le problème…"}),
        }


# ─────────────────────────────────────────────────────────────────
# RECHERCHE
# ─────────────────────────────────────────────────────────────────

class RechercheAnnonceForm(forms.Form):
    q         = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "ann-input", "placeholder": "Que voulez-vous acheter ou trouver ?"})
    )
    categorie = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    ville     = forms.ChoiceField(
        required=False,
        choices=VILLES_CHOICES,
        widget=forms.Select(attrs={"class": "ann-input"})
    )
    etat      = forms.ChoiceField(
        required=False,
        choices=[("", "Tous états")] + list(EtatProduit.choices),
        widget=forms.Select(attrs={"class": "ann-input"})
    )
    prix_min  = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"class": "ann-input", "placeholder": "Prix min"})
    )
    prix_max  = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"class": "ann-input", "placeholder": "Prix max"})
    )


# ─────────────────────────────────────────────────────────────────
# MESSAGE
# ─────────────────────────────────────────────────────────────────

class MessageAnnonceForm(forms.Form):
    contenu = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(attrs={
            "class": "ann-input",
            "rows": 3,
            "placeholder": "Votre message…",
        })
    )
