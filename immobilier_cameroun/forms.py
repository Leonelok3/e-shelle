"""
forms.py — immobilier_cameroun
Formulaires : publication de bien, profil, visite, soumission, signalement, recherche
"""
from django import forms
from django.forms import inlineformset_factory
from django.conf import settings
from .agency import agency_profiles

from .models import (
    Bien, PhotoBien, EquipementBien, ProfilImmo,
    DemandeVisite, DemandeSoumissionBien, SignalementBien,
    TypeBien, TypeTransaction, Devise, PeriodePrix,
    StatutBien, NomEquipement, MotifSignalement, VILLES_CAMEROUN,
)
from .utils import valider_telephone_cm

MAX_PHOTOS   = getattr(settings, "IMMOBILIER_MAX_PHOTOS_PAR_BIEN", 10)
MAX_BIENS    = getattr(settings, "IMMOBILIER_MAX_BIENS_GRATUIT", 3)
MAX_IMG_MB   = getattr(settings, "IMMOBILIER_TAILLE_MAX_IMAGE_MB", 5)
MAX_IMG_SIZE = MAX_IMG_MB * 1024 * 1024


# ─────────────────────────────────────────────────────────────────
# FORMULAIRE BIEN (création / modification)
# ─────────────────────────────────────────────────────────────────

class BienForm(forms.ModelForm):
    # Équipements — champ multiple checkboxes
    equipements = forms.MultipleChoiceField(
        choices=NomEquipement.choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "equipements-cb"}),
        required=False,
        label="Équipements & commodités",
    )

    class Meta:
        model  = Bien
        fields = [
            "agence", "titre", "type_bien", "type_transaction",
            "description", "prix", "devise", "periode_prix",
            "surface", "nombre_pieces", "nombre_chambres", "nombre_salles_bain",
            "etage", "nombre_etages_immeuble",
            "ville", "quartier", "adresse_complete", "latitude", "longitude",
            "date_disponibilite",
            "meta_description", "meta_keywords",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Ex : Appartement meublé 3 pièces à Bastos"
            }),
            "agence": forms.Select(attrs={"class": "form-select"}),
            "type_bien":        forms.Select(attrs={"class": "form-select"}),
            "type_transaction": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control", "rows": 6,
                "placeholder": "Décrivez votre bien en détail (min. 50 caractères)…"
            }),
            "prix": forms.NumberInput(attrs={"class": "form-control", "placeholder": "150000"}),
            "devise":       forms.Select(attrs={"class": "form-select"}),
            "periode_prix": forms.Select(attrs={"class": "form-select"}),
            "surface": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Ex : 75"}),
            "nombre_pieces":       forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "nombre_chambres":     forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "nombre_salles_bain":  forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "etage":               forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "nombre_etages_immeuble": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "ville":            forms.Select(attrs={"class": "form-select"}),
            "quartier":         forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex : Bastos, Bonanjo, Omnisports…"}),
            "adresse_complete": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "latitude":  forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "date_disponibilite": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "meta_description": forms.TextInput(attrs={"class": "form-control"}),
            "meta_keywords":    forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        owner_id = self.instance.proprietaire_id or getattr(user, "pk", None)
        self.fields["agence"].queryset = agency_profiles(owner_id)
        self.fields["agence"].empty_label = "Annonce indépendante"

        # Pré-remplir les équipements si on modifie un bien existant
        if self.instance.pk:
            equip_existants = list(
                self.instance.equipements.values_list("nom", flat=True)
            )
            self.fields["equipements"].initial = equip_existants

    def clean_agence(self):
        if self.instance.pk and "agence" not in self.data:
            return self.instance.agence
        return self.cleaned_data["agence"]

    def clean_titre(self):
        titre = self.cleaned_data.get("titre", "").strip()
        if len(titre) < 10:
            raise forms.ValidationError("Le titre doit contenir au moins 10 caractères.")
        return titre

    def clean_description(self):
        desc = self.cleaned_data.get("description", "").strip()
        if len(desc) < 50:
            raise forms.ValidationError("La description doit contenir au moins 50 caractères.")
        return desc

    def clean_prix(self):
        prix = self.cleaned_data.get("prix")
        if prix is not None and prix <= 0:
            raise forms.ValidationError("Le prix doit être supérieur à 0.")
        return prix

    def clean(self):
        cleaned = super().clean()

        # Vérification quota biens gratuits (seulement à la création)
        if self.user and not self.instance.pk:
            try:
                profil = self.user.profil_immo
                if not profil.est_premium_actif and profil.nb_biens_actifs >= MAX_BIENS:
                    raise forms.ValidationError(
                        f"Compte Gratuit : vous ne pouvez pas avoir plus de {MAX_BIENS} biens actifs. "
                        "Passez en Premium pour publier des biens illimités."
                    )
            except Exception as e:
                if "ValidationError" in type(e).__name__:
                    raise
        return cleaned

    def save(self, commit=True):
        bien = super().save(commit=commit)
        if commit:
            self.save_equipements()
        return bien

    def save_equipements(self):
        self.instance.equipements.all().delete()
        EquipementBien.objects.bulk_create(
            EquipementBien(bien=self.instance, nom=nom) for nom in self.cleaned_data.get("equipements", [])
        )


# ─────────────────────────────────────────────────────────────────
# FORMSET PHOTOS
# ─────────────────────────────────────────────────────────────────

class PhotoBienForm(forms.ModelForm):
    class Meta:
        model  = PhotoBien
        fields = ["image", "legende", "est_photo_principale", "ordre"]
        widgets = {
            "image":   forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "legende": forms.TextInput(attrs={"class": "form-control", "placeholder": "Légende optionnelle"}),
            "est_photo_principale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ordre":   forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # Validation taille
            if hasattr(image, "size") and image.size > MAX_IMG_SIZE:
                raise forms.ValidationError(
                    f"L'image ne doit pas dépasser {MAX_IMG_MB} MB."
                )
            # Validation type MIME
            content_type = getattr(image, "content_type", "")
            if content_type and not content_type.startswith("image/"):
                raise forms.ValidationError("Le fichier doit être une image (JPG, PNG, WebP).")
        return image


PhotoBienFormSet = inlineformset_factory(
    Bien, PhotoBien,
    form=PhotoBienForm,
    extra=3,
    max_num=MAX_PHOTOS,
    validate_max=True,
    can_delete=True,
)


# ─────────────────────────────────────────────────────────────────
# PROFIL IMMOBILIER
# ─────────────────────────────────────────────────────────────────

class ProfilImmoForm(forms.ModelForm):
    class Meta:
        model  = ProfilImmo
        fields = [
            "role", "telephone", "whatsapp",
            "ville", "quartier", "photo_profil", "bio",
        ]
        widgets = {
            "role":        forms.Select(attrs={"class": "form-select"}),
            "telephone":   forms.TextInput(attrs={"class": "form-control", "placeholder": "+237 6XX XXX XXX"}),
            "whatsapp":    forms.TextInput(attrs={"class": "form-control", "placeholder": "+237 6XX XXX XXX"}),
            "ville":       forms.Select(attrs={"class": "form-select"}),
            "quartier":    forms.TextInput(attrs={"class": "form-control"}),
            "photo_profil": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "bio":         forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_telephone(self):
        tel = self.cleaned_data.get("telephone", "").strip()
        if tel and not valider_telephone_cm(tel):
            raise forms.ValidationError(
                "Numéro de téléphone invalide. Format attendu : +237 6XX XXX XXX"
            )
        return tel

    def clean_whatsapp(self):
        wa = self.cleaned_data.get("whatsapp", "").strip()
        if wa and not valider_telephone_cm(wa):
            raise forms.ValidationError(
                "Numéro WhatsApp invalide. Format attendu : +237 6XX XXX XXX"
            )
        return wa


# ─────────────────────────────────────────────────────────────────
# DEMANDE DE VISITE
# ─────────────────────────────────────────────────────────────────

class DemandeVisiteForm(forms.ModelForm):
    class Meta:
        model  = DemandeVisite
        fields = ["nom_complet", "telephone", "email", "message", "date_souhaitee"]
        widgets = {
            "nom_complet": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Votre nom complet"
            }),
            "telephone": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "+237 6XX XXX XXX"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control", "placeholder": "votre@email.com (optionnel)"
            }),
            "message": forms.Textarea(attrs={
                "class": "form-control", "rows": 3,
                "placeholder": "Précisez vos disponibilités ou toute information utile…"
            }),
            "date_souhaitee": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
        }

    def clean_telephone(self):
        tel = self.cleaned_data.get("telephone", "").strip()
        if not valider_telephone_cm(tel):
            raise forms.ValidationError(
                "Numéro de téléphone invalide. Exemple : +237 677 123 456"
            )
        return tel


# ─────────────────────────────────────────────────────────────────
# SOUMISSION BIEN (formulaire public)
# ─────────────────────────────────────────────────────────────────

class DemandeSoumissionBienForm(forms.ModelForm):
    class Meta:
        model  = DemandeSoumissionBien
        fields = [
            "nom_complet", "telephone", "email",
            "type_bien", "ville", "quartier",
            "description_rapide", "photos_jointes", "message_complementaire",
        ]
        widgets = {
            "nom_complet":   forms.TextInput(attrs={"class": "form-control"}),
            "telephone":     forms.TextInput(attrs={"class": "form-control", "placeholder": "+237 6XX XXX XXX"}),
            "email":         forms.EmailInput(attrs={"class": "form-control"}),
            "type_bien":     forms.Select(attrs={"class": "form-select"}),
            "ville":         forms.Select(attrs={"class": "form-select"}),
            "quartier":      forms.TextInput(attrs={"class": "form-control"}),
            "description_rapide": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "photos_jointes": forms.FileInput(attrs={"class": "form-control", "accept": "image/*,.zip"}),
            "message_complementaire": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_telephone(self):
        tel = self.cleaned_data.get("telephone", "").strip()
        if not valider_telephone_cm(tel):
            raise forms.ValidationError("Numéro de téléphone invalide.")
        return tel


# ─────────────────────────────────────────────────────────────────
# SIGNALEMENT
# ─────────────────────────────────────────────────────────────────

class SignalementForm(forms.ModelForm):
    class Meta:
        model  = SignalementBien
        fields = ["motif", "description"]
        widgets = {
            "motif":       forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control", "rows": 3,
                "placeholder": "Précisez le problème constaté…"
            }),
        }


# ─────────────────────────────────────────────────────────────────
# RECHERCHE
# ─────────────────────────────────────────────────────────────────

class RechercheForm(forms.Form):
    q = forms.CharField(
        required=False, label="Recherche",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ville, quartier, type de bien…",
        }),
    )
    type_bien = forms.ChoiceField(
        choices=[("", "Tous les types")] + TypeBien.choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    type_transaction = forms.ChoiceField(
        choices=[("", "Location & Vente")] + TypeTransaction.choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ville = forms.ChoiceField(
        choices=[("", "Toutes les villes")] + VILLES_CAMEROUN,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    prix_min = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Min XAF"}),
    )
    prix_max = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Max XAF"}),
    )
    chambres_min = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Min chambres"}),
    )
    tri = forms.ChoiceField(
        choices=[
            ("-date_publication", "Plus récents"),
            ("prix", "Prix croissant"),
            ("-prix", "Prix décroissant"),
            ("-vues", "Plus vus"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
