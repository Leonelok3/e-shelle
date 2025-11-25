from django import forms


LANG_CHOICES = [
    ('auto', 'Détection automatique'),
    ('fr', 'Français'),
    ('en', 'Anglais'),
    ('de', 'Allemand'),
    ('es', 'Espagnol'),
    ('pt', 'Portugais'),
    ('it', 'italien'),
]


class TranslationForm(forms.Form):
    file = forms.FileField(
        label="Document (.docx uniquement)",
        help_text="Diplôme, relevé, certificat, CV… au format .docx"
    )
    source_lang = forms.ChoiceField(
        label="Langue source",
        choices=LANG_CHOICES,
        initial='auto'
    )
    target_lang = forms.ChoiceField(
        label="Langue cible",
        choices=LANG_CHOICES,
        initial='en'
    )


class CompressionForm(forms.Form):
    file = forms.FileField(
        label="Document PDF",
        help_text="Uniquement .pdf pour la compression"
    )
