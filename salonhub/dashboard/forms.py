from django import forms
from salonhub.salons.models import Salon, Service


class SalonForm(forms.ModelForm):
    class Meta:
        model = Salon
        fields = [
            "name",
            "kind",
            "category",
            "description",
            "city",
            "district",
            "address",
            "whatsapp_number",
            "phone_display",
            "email",
            "logo",
            "cover_image",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Décrivez votre établissement..."}),
            "address": forms.TextInput(attrs={"placeholder": "Adresse complète..."}),
            "whatsapp_number": forms.TextInput(attrs={"placeholder": "237690000000"}),
            "phone_display": forms.TextInput(attrs={"placeholder": "690 00 00 00"}),
            "email": forms.EmailInput(attrs={"placeholder": "contact@etablissement.com"}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "name",
            "description",
            "price",
            "duration_minutes",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Description rapide (ex: Avec shampoing)"}),
            "price": forms.NumberInput(attrs={"placeholder": "Prix en FCFA"}),
            "duration_minutes": forms.NumberInput(attrs={"placeholder": "30"}),
        }
