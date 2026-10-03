from django import forms

from .models import Campagne
from .meta_templates import TemplateError, validate_selection


class TemplateSelectionForm(forms.Form):
    meta_template = forms.CharField(required=False, max_length=540)
    meta_params = forms.JSONField(required=False)

    def clean(self):
        data = super().clean()
        key = data.get('meta_template', '')
        if key and 'meta_params' not in self.errors:
            try:
                data['selected'] = validate_selection(key, data.get('meta_params') or [])
            except TemplateError as exc:
                raise forms.ValidationError(str(exc))
        return data

    def apply(self, campaign):
        selected = self.cleaned_data.get('selected')
        campaign.template_meta_name = selected['name'] if selected else ''
        campaign.template_meta_language = selected['language'] if selected else ''
        campaign.template_meta_preview = selected['body'] if selected else ''
        campaign.template_meta_params = (self.cleaned_data.get('meta_params') or []) if selected else []


class CampagneForm(forms.ModelForm):
    """Formulaire de creation et edition de campagne WhatsApp."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message_template'].required = False

    def clean(self):
        data = super().clean()
        if not data.get('message_template') and not self.data.get('meta_template'):
            self.add_error('message_template', 'Renseigne un message ou selectionne un modele Meta.')
        return data

    class Meta:
        model = Campagne
        fields = [
            "nom",
            "description",
            "filtre_role",
            "filtre_ville",
            "filtre_date_inscription_depuis",
            "message_template",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "wa-input", "placeholder": "Promotion week-end"}),
            "description": forms.Textarea(attrs={"class": "wa-input", "rows": 3}),
            "filtre_role": forms.TextInput(attrs={"class": "wa-input", "placeholder": "vendeur, acheteur, premium ou tous"}),
            "filtre_ville": forms.TextInput(attrs={"class": "wa-input", "placeholder": "Douala, Yaounde..."}),
            "filtre_date_inscription_depuis": forms.DateInput(attrs={"class": "wa-input", "type": "date"}),
            "message_template": forms.Textarea(
                attrs={
                    "class": "wa-input",
                    "rows": 8,
                    "placeholder": "Bonjour {{prenom}}, decouvrez nos offres E-Shelle...",
                    "data-message-input": "true",
                }
            ),
        }
