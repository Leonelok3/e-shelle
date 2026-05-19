from django import forms

from .models import PrestataireProfile


class PrestataireStatusForm(forms.ModelForm):
    """Formulaire minimal pour basculer la disponibilité terrain."""

    class Meta:
        model = PrestataireProfile
        fields = ["statut"]
        widgets = {
            "statut": forms.Select(attrs={"class": "form-select"}),
        }


class PrestataireProfileForm(forms.ModelForm):
    """Formulaire terrain pour mettre à jour les informations visibles par les clients."""

    class Meta:
        model = PrestataireProfile
        fields = [
            "nom",
            "telephone",
            "photo",
            "ville",
            "quartier_base",
            "zone_couverte",
            "horaires",
            "type_service",
            "type_vehicule",
            "statut",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "ville": forms.TextInput(attrs={"class": "form-control"}),
            "quartier_base": forms.TextInput(attrs={"class": "form-control"}),
            "zone_couverte": forms.TextInput(attrs={"class": "form-control"}),
            "horaires": forms.TextInput(attrs={"class": "form-control"}),
            "type_service": forms.Select(attrs={"class": "form-select"}),
            "type_vehicule": forms.TextInput(attrs={"class": "form-control"}),
            "statut": forms.Select(attrs={"class": "form-select"}),
        }
