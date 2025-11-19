from django import forms
from .models import UserProfile, ActionStep, JobApplication


class UserProfileForm(forms.ModelForm):
    PAYS_CHOICES = [
        ("Canada", "Canada"),
        ("France", "France"),
        ("Allemagne", "Allemagne"),
        ("Belgique", "Belgique"),
        ("Royaume-Uni", "Royaume-Uni"),
        ("Autre", "Autre"),
    ]

    pays_cibles_select = forms.MultipleChoiceField(
        label="Pays ciblés",
        choices=PAYS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Tu peux cocher plusieurs pays.",
    )

    class Meta:
        model = UserProfile
        fields = [
            "nom",
            "email",
            "pays_residence",
            "domaine_metier",
            "niveau_etudes",
            "annees_experience",
            "niveau_anglais",
            "niveau_langue_pays",
            "budget",
            "horizon_depart",
        ]
        labels = {
            "nom": "Nom ou pseudo",
            "email": "Email",
            "pays_residence": "Pays de résidence actuel",
            "domaine_metier": "Métier / domaine",
            "niveau_etudes": "Niveau d'études",
            "annees_experience": "Années d'expérience",
            "niveau_anglais": "Niveau d'anglais",
            "niveau_langue_pays": "Niveau dans la langue du pays ciblé",
            "budget": "Budget approximatif",
            "horizon_depart": "Horizon de départ souhaité",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.pays_cibles:
            pays_list = [p.strip() for p in self.instance.pays_cibles.split(",") if p]
            self.fields["pays_cibles_select"].initial = pays_list

        for name, field in self.fields.items():
            if name == "pays_cibles_select":
                continue
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned_data = super().clean()
        pays_cibles = cleaned_data.get("pays_cibles_select")
        if pays_cibles:
            cleaned_data["pays_cibles"] = ", ".join(pays_cibles)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        pays_cibles = self.cleaned_data.get("pays_cibles_select", [])
        instance.pays_cibles = ", ".join(pays_cibles)
        if commit:
            instance.save()
        return instance


class ActionStepStatusForm(forms.ModelForm):
    class Meta:
        model = ActionStep
        fields = ["statut"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["statut"].widget.attrs.setdefault(
            "class", "form-select form-select-sm"
        )


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = [
            "user_profile",
            "titre_poste",
            "entreprise",
            "pays",
            "ville",
            "lien_offre",
            "source",
            "statut",
            "date_candidature",
            "commentaire",
        ]
    widgets = {
            "date_candidature": forms.DateInput(
                attrs={"type": "date"}
            ),
            "commentaire": forms.Textarea(
                attrs={"rows": 3}
            ),
        }
    labels = {
            "user_profile": "Profil lié à cette candidature",
            "titre_poste": "Titre du poste",
            "entreprise": "Entreprise",
            "pays": "Pays",
            "ville": "Ville",
            "lien_offre": "Lien vers l'offre",
            "source": "Source (job board, contact…)",
            "statut": "Statut de la candidature",
            "date_candidature": "Date de candidature",
            "commentaire": "Notes / suivi",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css_class = "form-control"
            if isinstance(field.widget, forms.Select):
                css_class = "form-select"
            field.widget.attrs.setdefault("class", css_class + " form-control-sm")


class CVAnalysisForm(forms.Form):
    user_profile = forms.ModelChoiceField(
        queryset=UserProfile.objects.all(),
        required=False,
        label="Associer à un profil",
        help_text="Optionnel : tu peux lier cette analyse à un profil Visa Travail.",
    )
    intitule_poste = forms.CharField(
        label="Poste ciblé",
        required=True,
        help_text="Ex : Développeur Python, Infirmier, Soudeur, Data Analyst…",
    )
    pays_cible = forms.CharField(
        label="Pays ciblé principal",
        required=True,
        help_text="Ex : Canada, Allemagne, Belgique…",
    )
    cv_texte = forms.CharField(
        label="Colle ici le contenu de ton CV",
        widget=forms.Textarea(attrs={"rows": 14}),
        help_text="Tu peux copier-coller ton CV complet (sans mise en page).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "form-control form-control-sm")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select form-select-sm")
            else:
                field.widget.attrs.setdefault("class", "form-control form-control-sm")
