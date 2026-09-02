from django import forms

from .models import DrivingSchool


class DrivingSchoolRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(label="Prénom", max_length=120)
    last_name = forms.CharField(label="Nom", max_length=120)
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=False,
        help_text="Requis uniquement si vous n'êtes pas connecté.",
    )

    class Meta:
        model = DrivingSchool
        fields = [
            "name",
            "description",
            "city",
            "address",
            "phone",
            "whatsapp",
            "email",
            "website",
            "price_note",
            "logo",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "name": "Nom de l'auto-école",
            "description": "Présentation du centre",
            "city": "Ville",
            "address": "Adresse ou quartier",
            "phone": "Téléphone",
            "whatsapp": "WhatsApp",
            "email": "Email",
            "website": "Site web",
            "price_note": "Tarif indicatif",
            "logo": "Logo du centre",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and user.is_authenticated:
            for field in ("first_name", "last_name", "password"):
                self.fields.pop(field, None)
        else:
            self.fields["email"].required = True
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "ae-field")

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if not self.user.is_authenticated and len(password) < 8:
            raise forms.ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        return password
