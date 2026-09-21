from django import forms
from .models import ImmigrationJourney


class JourneyForm(forms.ModelForm):
    class Meta:
        model = ImmigrationJourney
        fields = ['goal', 'exam', 'working_level', 'target_level', 'daily_minutes']
        labels = {'goal': 'Mon objectif', 'exam': 'Le test que je prépare',
                  'working_level': 'Mon niveau de travail actuel', 'target_level': 'Le niveau que je souhaite travailler',
                  'daily_minutes': 'Le temps que je peux consacrer chaque jour'}
        help_texts = {'working_level': 'Vous pourrez faire le bilan de départ pour choisir un point de départ adapté.'}

    def clean(self):
        data = super().clean()
        levels = [item[0] for item in ImmigrationJourney.LEVELS]
        if data.get('target_level') in levels and data.get('working_level') in levels:
            if levels.index(data['target_level']) < levels.index(data['working_level']):
                self.add_error('target_level', 'Choisissez votre niveau actuel ou un niveau supérieur.')
        return data
