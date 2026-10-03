from django import forms
from rencontres.utils.geography import HORIZONS, AFRICA, EUROPE
from rencontres.forms.profile_forms import LANGUES_CHOICES


PAYS_CHOICES = [
    ('', 'Tous les pays'),
    ('Cameroun', 'Cameroun'), ('Côte d\'Ivoire', 'Côte d\'Ivoire'),
    ('Sénégal', 'Sénégal'), ('Mali', 'Mali'), ('Burkina Faso', 'Burkina Faso'),
    ('RDC', 'RDC (Congo-Kinshasa)'), ('Congo', 'Congo-Brazzaville'),
    ('Gabon', 'Gabon'), ('Togo', 'Togo'), ('Bénin', 'Bénin'),
    ('Niger', 'Niger'), ('Tchad', 'Tchad'), ('Guinée', 'Guinée'),
    ('Madagascar', 'Madagascar'), ('Rwanda', 'Rwanda'), ('Burundi', 'Burundi'),
    ('Nigeria', 'Nigeria'), ('Ghana', 'Ghana'), ('Kenya', 'Kenya'),
    ('Éthiopie', 'Éthiopie'), ('Tanzanie', 'Tanzanie'), ('Ouganda', 'Ouganda'),
    ('France', 'France'), ('Belgique', 'Belgique'), ('Suisse', 'Suisse'),
    ('Canada', 'Canada'), ('USA', 'États-Unis'), ('Royaume-Uni', 'Royaume-Uni'),
    ('Allemagne', 'Allemagne'), ('Italie', 'Italie'), ('Espagne', 'Espagne'),
]

RELIGION_CHOICES = [
    ('', 'Toutes'),
    ('chretien', 'Chrétien(ne)'),
    ('musulman', 'Musulman(e)'),
    ('aucune', 'Aucune'),
    ('spirituel', 'Spirituel(le)'),
    ('autre', 'Autre'),
]

# Preserve historical values, while covering the wider international audience.
existing_countries = {value for value, _ in PAYS_CHOICES}
PAYS_CHOICES += [(country, country) for country in sorted(set(AFRICA + EUROPE))
                 if country not in existing_countries]


class FiltresRechercheForm(forms.Form):
    horizon = forms.ChoiceField(
        choices=[(value, label) for value, label, _ in HORIZONS], required=False,
        initial='monde', label='Mon horizon de rencontre',
        widget=forms.Select(attrs={'class': 'form-select'}))
    ville = forms.CharField(max_length=100, required=False, label='Ville',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Paris, Montréal, Dakar…'}))
    langue = forms.ChoiceField(choices=[('', 'Toutes les langues')] + LANGUES_CHOICES,
        required=False, label='Une langue en commun',
        widget=forms.Select(attrs={'class': 'form-select'}))
    age_min = forms.IntegerField(
        min_value=18, max_value=99, required=False,
        label="Âge minimum",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '18'})
    )
    age_max = forms.IntegerField(
        min_value=18, max_value=99, required=False,
        label="Âge maximum",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '60'})
    )
    pays = forms.ChoiceField(
        choices=PAYS_CHOICES, required=False,
        label="Pays de résidence",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    religion = forms.ChoiceField(
        choices=RELIGION_CHOICES, required=False,
        label="Religion",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    distance_km = forms.IntegerField(
        min_value=10, max_value=20000, required=False,
        label="Distance max (km)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    avec_photo = forms.BooleanField(
        required=False, initial=True,
        label="Avec photo uniquement",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    verifie_seulement = forms.BooleanField(
        required=False,
        label="Profils vérifiés uniquement",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    # Filtres premium uniquement
    niveau_etude = forms.ChoiceField(
        choices=[
            ('', 'Tous niveaux'),
            ('bac2', 'BAC+2 minimum'),
            ('licence', 'Licence minimum'),
            ('master', 'Master minimum'),
            ('doctorat', 'Doctorat'),
        ],
        required=False,
        label="Niveau d'études",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned = super().clean()
        age_min = cleaned.get('age_min')
        age_max = cleaned.get('age_max')
        if age_min and age_max and age_min > age_max:
            raise forms.ValidationError(
                "L'âge minimum doit être inférieur à l'âge maximum."
            )
        horizon = cleaned.get('horizon') or 'monde'
        country = cleaned.get('pays')
        region = {'afrique': AFRICA, 'europe': EUROPE, 'canada': ('Canada',)}.get(horizon)
        if region and country and country not in region:
            self.add_error('pays', 'Choisissez un pays de cet horizon ou sélectionnez Sans frontières.')
        return cleaned
