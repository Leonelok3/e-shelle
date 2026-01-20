from django import forms

class NewsletterForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": "Votre email (ex: nom@gmail.com)",
            "class": "a-newsletter__input",
            "autocomplete": "email",
            "required": True,
        })
    )
    country_interest = forms.CharField(required=False, widget=forms.HiddenInput())
    source_page = forms.CharField(required=False, widget=forms.HiddenInput())
