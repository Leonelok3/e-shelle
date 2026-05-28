from django import forms

from apps.tibo.models.commerce import CANADIAN_PROVINCES


class CheckoutForm(forms.Form):
    email = forms.EmailField(label="Email")
    full_name = forms.CharField(max_length=160, label="Nom complet")
    phone = forms.CharField(max_length=30, required=False, label="Téléphone")
    line1 = forms.CharField(max_length=180, label="Adresse")
    line2 = forms.CharField(max_length=180, required=False, label="Appartement, suite")
    city = forms.CharField(max_length=120, label="Ville")
    province = forms.ChoiceField(choices=CANADIAN_PROVINCES, label="Province")
    postal_code = forms.CharField(max_length=12, label="Code postal")
    payment_provider = forms.ChoiceField(
        choices=[("stripe", "Stripe"), ("paypal", "PayPal")],
        initial="stripe",
        widget=forms.RadioSelect,
    )

    def address_payload(self):
        return {
            "full_name": self.cleaned_data["full_name"],
            "phone": self.cleaned_data.get("phone", ""),
            "line1": self.cleaned_data["line1"],
            "line2": self.cleaned_data.get("line2", ""),
            "city": self.cleaned_data["city"],
            "province": self.cleaned_data["province"],
            "postal_code": self.cleaned_data["postal_code"],
            "country": "CA",
        }

