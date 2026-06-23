from django import forms
from .models import StoryProject


class StoryPromptForm(forms.ModelForm):
    class Meta:
        model = StoryProject
        fields = ['prompt']
        widgets = {
            'prompt': forms.Textarea(attrs={
                'class': 'prompt-input',
                'rows': 6,
                'placeholder': 'Exemple : Raconte l’histoire d’un jeune Camerounais qui obtient un visa pour le Canada.',
            })
        }
        labels = {'prompt': 'Votre idée de vidéo'}
