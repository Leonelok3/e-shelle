from django import forms
import re


class SubscriptionRequestForm(forms.Form):
    methode = forms.ChoiceField(choices=[('mtn_momo', 'MTN Mobile Money'), ('orange', 'Orange Money')])
    telephone = forms.CharField(max_length=25, label='Téléphone avec indicatif',
                                widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+237 6XX XXX XXX'}))
    reference_client = forms.CharField(max_length=100, required=False, label='Référence du paiement (si déjà effectué)')

    def clean_telephone(self):
        value = re.sub(r'[\s().-]', '', self.cleaned_data['telephone'])
        if not re.fullmatch(r'\+?[0-9]{9,15}', value):
            raise forms.ValidationError('Saisissez un numéro valide de 9 à 15 chiffres.')
        return value
