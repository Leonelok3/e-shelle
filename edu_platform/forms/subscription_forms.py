"""
Formulaires d'abonnement et paiement Mobile Money.
"""
from django import forms
from django.core.validators import RegexValidator

PHONE_VALIDATOR = RegexValidator(
    regex=r'^\+?237[0-9]{8,9}$',
    message="Numéro camerounais requis. Format : +237XXXXXXXXX"
)


class PaymentInitForm(forms.Form):
    """Formulaire de paiement Mobile Money."""
    PROVIDER_CHOICES = [
        ('orange_money', 'Orange Money'),
        ('mtn_momo', 'MTN MoMo'),
    ]

    plan_id = forms.IntegerField(widget=forms.HiddenInput())

    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        label='Opérateur Mobile Money',
        widget=forms.RadioSelect(attrs={'class': 'provider-radio'})
    )

    phone_number = forms.CharField(
        max_length=20,
        label='Numéro Mobile Money',
        validators=[PHONE_VALIDATOR],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237 6XX XXX XXX',
            'autocomplete': 'tel',
            'inputmode': 'tel',
        }),
        help_text="Le numéro qui sera débité. Doit avoir du crédit suffisant."
    )

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].replace(' ', '').replace('-', '')
        if not phone.startswith('+'):
            phone = '+' + phone
        return phone

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get('provider')
        phone = cleaned.get('phone_number', '')

        if provider == 'orange_money' and phone:
            # Orange Money : préfixes 069, 065, 055, etc.
            if not any(phone.startswith(p) for p in ['+23769', '+23765', '+23766', '+23755', '+23756']):
                # Ne pas bloquer si le numéro n'est pas strictement Orange — Orange accepte d'autres prefixes
                pass

        return cleaned
