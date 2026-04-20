from django import forms
from .models import ConsultationRequest


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = ConsultationRequest
        fields = [
            "full_name",
            "email",
            "phone",
            "country",
            "consultation_type",
            "destination_country",
            "message",
            "budget",
            "preferred_date",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Ex : Jean Dupont",
                "class": "consult-input",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "votre@email.com",
                "class": "consult-input",
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "+237 6XX XXX XXX (WhatsApp bienvenu)",
                "class": "consult-input",
            }),
            "country": forms.TextInput(attrs={
                "placeholder": "Ex : Cameroun, Côte d'Ivoire…",
                "class": "consult-input",
            }),
            "consultation_type": forms.Select(attrs={
                "class": "consult-select",
            }),
            "destination_country": forms.TextInput(attrs={
                "placeholder": "Ex : Canada, Allemagne, France…",
                "class": "consult-input",
            }),
            "message": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Décrivez votre situation actuelle, vos objectifs, vos questions…",
                "class": "consult-textarea",
            }),
            "budget": forms.Select(attrs={
                "class": "consult-select",
            }),
            "preferred_date": forms.DateInput(attrs={
                "type": "date",
                "class": "consult-input",
            }),
        }
        labels = {
            "full_name": "Nom complet *",
            "email": "Adresse email *",
            "phone": "Téléphone / WhatsApp",
            "country": "Pays de résidence actuel",
            "consultation_type": "Type de consultation *",
            "destination_country": "Pays de destination visé",
            "message": "Votre message *",
            "budget": "Budget indicatif",
            "preferred_date": "Date souhaitée pour la consultation",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields["full_name"].initial = user.get_full_name() or user.username
            self.fields["email"].initial = user.email
