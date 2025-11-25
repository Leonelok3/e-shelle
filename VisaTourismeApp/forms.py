from django import forms
from .models import (
    VisaTourismRequest,
    DESTINATION_CHOICES,
    DUREE_CHOICES,
    BUDGET_CHOICES,
)


class VisaTourismeForm(forms.ModelForm):
    # Radios Oui/Non pour les booléens
    a_un_emploi = forms.TypedChoiceField(
        label="Vous avez un emploi / une activité professionnelle ?",
        choices=(('True', 'Oui'), ('False', 'Non')),
        coerce=lambda x: x == 'True',
        widget=forms.RadioSelect,
        required=True,
    )

    a_invitation = forms.TypedChoiceField(
        label="Vous avez une lettre d’invitation (famille/ami/hôtel/agence) ?",
        choices=(('True', 'Oui'), ('False', 'Non')),
        coerce=lambda x: x == 'True',
        widget=forms.RadioSelect,
        required=True,
    )

    a_deja_voyage = forms.TypedChoiceField(
        label="Vous avez déjà voyagé à l’étranger ?",
        choices=(('True', 'Oui'), ('False', 'Non')),
        coerce=lambda x: x == 'True',
        widget=forms.RadioSelect,
        required=True,
    )

    destination = forms.ChoiceField(choices=DESTINATION_CHOICES)
    duree_sejour = forms.ChoiceField(choices=DUREE_CHOICES)
    budget = forms.ChoiceField(choices=BUDGET_CHOICES)

    class Meta:
        model = VisaTourismRequest
        fields = [
            'full_name',
            'email',
            'phone',
            'destination',
            'nationalite',
            'pays_residence',
            'duree_sejour',
            'objet_voyage',
            'a_un_emploi',
            'a_invitation',
            'a_deja_voyage',
            'budget',
            'age',
        ]
        labels = {
            'full_name': "Nom complet",
            'email': "Email (pour recevoir le plan détaillé)",
            'phone': "Téléphone / WhatsApp",
            'destination': "Destination principale",
            'nationalite': "Votre nationalité",
            'pays_residence': "Pays de résidence",
            'duree_sejour': "Durée prévue du séjour",
            'objet_voyage': "Objet du voyage (tourisme, visite familiale, etc.)",
            'budget': "Niveau de budget approximatif",
            'age': "Votre âge",
        }
        widgets = {
            'objet_voyage': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_age(self):
        age = self.cleaned_data['age']
        if age < 1 or age > 100:
            raise forms.ValidationError("Âge invalide.")
        return age
