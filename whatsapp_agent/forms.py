from django import forms

from .models import Campagne


class CampagneForm(forms.ModelForm):
    """Formulaire de creation et edition de campagne WhatsApp."""

    class Meta:
        model = Campagne
        fields = [
            "nom",
            "description",
            "filtre_role",
            "filtre_ville",
            "filtre_date_inscription_depuis",
            "message_template",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "wa-input", "placeholder": "Promotion week-end"}),
            "description": forms.Textarea(attrs={"class": "wa-input", "rows": 3}),
            "filtre_role": forms.TextInput(attrs={"class": "wa-input", "placeholder": "vendeur, acheteur, premium ou tous"}),
            "filtre_ville": forms.TextInput(attrs={"class": "wa-input", "placeholder": "Douala, Yaounde..."}),
            "filtre_date_inscription_depuis": forms.DateInput(attrs={"class": "wa-input", "type": "date"}),
            "message_template": forms.Textarea(
                attrs={
                    "class": "wa-input",
                    "rows": 8,
                    "placeholder": "Bonjour {{prenom}}, decouvrez nos offres E-Shelle...",
                    "data-message-input": "true",
                }
            ),
        }
