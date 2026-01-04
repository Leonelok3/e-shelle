from django import forms
from .models import UserProfile, ActionStep, JobApplication

# ======================================================
# CONSTANTES DESIGN VISA TRAVAIL
# ======================================================
VT_INPUT = "vt-input"
VT_SELECT = "vt-input"
VT_TEXTAREA = "vt-input"


# ======================================================
# PROFIL VISA TRAVAIL (FORM PRINCIPAL)
# ======================================================
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
        widgets = {
            "nom": forms.TextInput(attrs={"class": VT_INPUT}),
            "email": forms.EmailInput(attrs={"class": VT_INPUT}),
            "pays_residence": forms.TextInput(attrs={"class": VT_INPUT}),
            "domaine_metier": forms.TextInput(attrs={"class": VT_INPUT}),
            "niveau_etudes": forms.Select(attrs={"class": VT_SELECT}),
            "annees_experience": forms.NumberInput(attrs={
                "class": VT_INPUT,
                "min": 0,
            }),
            "niveau_anglais": forms.Select(attrs={"class": VT_SELECT}),
            "niveau_langue_pays": forms.Select(attrs={"class": VT_SELECT}),
            "budget": forms.Select(attrs={"class": VT_SELECT}),
            "horizon_depart": forms.Select(attrs={"class": VT_SELECT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pré-remplissage des pays cochés
        if self.instance and self.instance.pk and self.instance.pays_cibles:
            self.fields["pays_cibles_select"].initial = [
                p.strip()
                for p in self.instance.pays_cibles.split(",")
                if p
            ]

        # 👉 Classe unique design Visa Travail
        for name, field in self.fields.items():
            if name == "pays_cibles_select":
                field.widget.attrs["class"] = "vt-checkbox-group"
            else:
                field.widget.attrs["class"] = VT_INPUT

    def clean(self):
        cleaned_data = super().clean()
        pays = cleaned_data.get("pays_cibles_select", [])
        cleaned_data["pays_cibles"] = ", ".join(pays)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.pays_cibles = ", ".join(
            self.cleaned_data.get("pays_cibles_select", [])
        )
        if commit:
            instance.save()
        return instance


# ======================================================
# STATUT DES ÉTAPES (PLAN D’ACTION)
# ======================================================
class ActionStepStatusForm(forms.ModelForm):

    class Meta:
        model = ActionStep
        fields = ["statut"]
        widgets = {
            "statut": forms.Select(attrs={
                "class": "vt-input vt-input-sm"
            })
        }


# ======================================================
# CANDIDATURE À UNE OFFRE
# ======================================================
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
            "user_profile": forms.Select(attrs={"class": VT_SELECT}),
            "titre_poste": forms.TextInput(attrs={"class": VT_INPUT}),
            "entreprise": forms.TextInput(attrs={"class": VT_INPUT}),
            "pays": forms.TextInput(attrs={"class": VT_INPUT}),
            "ville": forms.TextInput(attrs={"class": VT_INPUT}),
            "lien_offre": forms.URLInput(attrs={"class": VT_INPUT}),
            "source": forms.TextInput(attrs={"class": VT_INPUT}),
            "statut": forms.Select(attrs={"class": VT_SELECT}),
            "date_candidature": forms.DateInput(attrs={
                "type": "date",
                "class": VT_INPUT,
            }),
            "commentaire": forms.Textarea(attrs={
                "class": VT_TEXTAREA,
                "rows": 4,
            }),
        }


# ======================================================
# ANALYSE DE CV (COACH CV)
# ======================================================
class CVAnalysisForm(forms.Form):

    user_profile = forms.ModelChoiceField(
        queryset=UserProfile.objects.all(),
        required=False,
        label="Associer à un profil",
        widget=forms.Select(attrs={"class": VT_INPUT}),
    )

    intitule_poste = forms.CharField(
        label="Poste ciblé",
        required=True,
        widget=forms.TextInput(attrs={
            "class": VT_INPUT,
            "placeholder": "Ex : Développeur Python, Infirmier, Soudeur…"
        }),
    )

    pays_cible = forms.CharField(
        label="Pays ciblé principal",
        required=True,
        widget=forms.TextInput(attrs={
            "class": VT_INPUT,
            "placeholder": "Ex : Canada, Allemagne, Belgique…"
        }),
    )

    cv_texte = forms.CharField(
        label="Contenu du CV",
        widget=forms.Textarea(attrs={
            "class": VT_TEXTAREA,
            "rows": 14,
            "placeholder": "Colle ici le contenu complet de ton CV…"
        }),
    )
