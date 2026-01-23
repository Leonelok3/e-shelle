# billing/forms.py
from decimal import Decimal
from django import forms


class RedeemCodeForm(forms.Form):
    code = forms.CharField(
        label="Code prépayé",
        max_length=32,
        widget=forms.TextInput(attrs={
            "placeholder": "I97-XXXX-XXXX-XXXX",
            "class": "form-input",
            "autocomplete": "off",
        }),
    )


class WalletReloadForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("1.00"),
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "form-input",
            "placeholder": "50",
        })
    )
    note = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Ex: Recharge pour préparation TEF Canada",
        })
    )
