from django import forms
from .models import Appointment


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["service", "client_name", "client_phone", "date", "time", "note"]
        widgets = {
            "date": forms.HiddenInput(),
            "time": forms.HiddenInput(),
            "service": forms.HiddenInput(),
            "note": forms.Textarea(attrs={"rows": 2, "placeholder": "Précisions éventuelles (optionnel)"}),
            "client_name": forms.TextInput(attrs={"placeholder": "Votre nom complet"}),
            "client_phone": forms.TextInput(attrs={"placeholder": "Ex : 690 00 00 00"}),
        }
