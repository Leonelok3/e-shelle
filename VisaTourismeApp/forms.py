from django import forms
from .models import (
    VisaTourismRequest,
    DESTINATION_CHOICES,
    DUREE_CHOICES,
    BUDGET_CHOICES,
)


class VisaTourismeForm(forms.ModelForm):
    """
    FORMULAIRE UTILISATEUR – ÉTAPE 1
    Sert UNIQUEMENT à collecter les informations du demandeur.
    Les champs d’analyse sont exclus volontairement.
    """

    a_un_emploi = forms.TypedChoiceField(
        label="Vous avez un emploi / une activité professionnelle ?",
        choices=((True, "Oui"), (False, "Non")),
        widget=forms.RadioSelect(attrs={"class": "vtm-radio"}),
        coerce=lambda x: x == 'True',
        required=True,
    )

    a_invitation = forms.TypedChoiceField(
        label="Vous avez une lettre d’invitation (famille / ami / hôtel / agence) ?",
        choices=((True, "Oui"), (False, "Non")),
        widget=forms.RadioSelect(attrs={"class": "vtm-radio"}),
        coerce=lambda x: x == 'True',
        required=True,
    )

    a_deja_voyage = forms.TypedChoiceField(
        label="Vous avez déjà voyagé à l’étranger ?",
        choices=((True, "Oui"), (False, "Non")),
        widget=forms.RadioSelect(attrs={"class": "vtm-radio"}),
        coerce=lambda x: x == 'True',
        required=True,
    )

    destination = forms.ChoiceField(
        label="Destination",
        choices=DESTINATION_CHOICES,
        widget=forms.Select(attrs={"class": "vtm-select"}),
        required=True,
    )

    duree_sejour = forms.ChoiceField(
        label="Durée du séjour",
        choices=DUREE_CHOICES,
        widget=forms.Select(attrs={"class": "vtm-select"}),
        required=True,
    )

    budget = forms.ChoiceField(
        label="Budget estimé",
        choices=BUDGET_CHOICES,
        widget=forms.Select(attrs={"class": "vtm-select"}),
        required=True,
    )

    class Meta:
        model = VisaTourismRequest

        # 🚨 CHAMPS AUTORISÉS UNIQUEMENT
        fields = [
            "full_name",
            "email",
            "phone",
            "destination",
            "nationalite",
            "pays_residence",
            "duree_sejour",
            "objet_voyage",
            "a_un_emploi",
            "a_invitation",
            "a_deja_voyage",
            "budget",
            "age",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "vtm-input",
                "placeholder": "Nom complet",
            }),
            "email": forms.EmailInput(attrs={
                "class": "vtm-input",
                "placeholder": "Email",
            }),
            "phone": forms.TextInput(attrs={
                "class": "vtm-input",
                "placeholder": "Téléphone / WhatsApp",
            }),
            "nationalite": forms.TextInput(attrs={
                "class": "vtm-input",
                "placeholder": "Nationalité",
            }),
            "pays_residence": forms.TextInput(attrs={
                "class": "vtm-input",
                "placeholder": "Pays de résidence",
            }),
            "age": forms.NumberInput(attrs={
                "class": "vtm-input",
                "min": 16,
                "placeholder": "Âge",
            }),
            "objet_voyage": forms.Textarea(attrs={
                "class": "vtm-input",
                "rows": 3,
                "placeholder": "Ex : Tourisme, visite familiale, découverte culturelle…",
            }),
        }
