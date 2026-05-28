from django import forms
from django.contrib.auth import get_user_model
import secrets
import string

from tchaslucpay.accounts.models import ClientProfile, UserRole


class NouvelleTransactionForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=ClientProfile.objects.none(),
        label="Client assigne",
        empty_label="Selectionner un client",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    type_op = forms.ChoiceField(
        label="Type d'operation",
        choices=(("DEPOT", "Depot"), ("RETRAIT", "Retrait")),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    montant = forms.DecimalField(
        label="Montant",
        min_value=1,
        max_digits=18,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "1"}),
    )
    note = forms.CharField(
        label="Note",
        required=False,
        max_length=255,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, collecteur=None, **kwargs):
        super().__init__(*args, **kwargs)
        if collecteur is not None:
            self.fields["client"].queryset = (
                ClientProfile.objects.filter(trusted_collecteur=collecteur)
                .select_related("user", "trusted_collecteur")
                .order_by("user__first_name", "user__last_name", "account_number")
            )


class ClientTerrainForm(forms.Form):
    first_name = forms.CharField(
        label="Prenom",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Nom",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        label="Telephone",
        max_length=25,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    city = forms.CharField(
        label="Ville",
        max_length=80,
        initial="Douala",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    quarter = forms.CharField(
        label="Commerce / quartier",
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    solde_initial = forms.DecimalField(
        label="Solde de départ (optionnel)",
        min_value=0,
        max_digits=18,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": "0",
            "step": "0.01",
            "placeholder": "0 = aucun dépôt enregistré",
        }),
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        User = get_user_model()
        if User.objects.filter(phone_number=phone_number).exists() or ClientProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Ce numero de telephone est deja utilise.")
        return phone_number

    def _generate_username(self):
        """Genere un identifiant client stable et unique."""
        User = get_user_model()
        digits = "".join(ch for ch in self.cleaned_data["phone_number"] if ch.isdigit())
        base = f"client_{digits[-6:] or 'terrain'}"
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base}_{counter}"
        return username

    def _generate_account_number(self):
        """Genere un numero de compte client unique pour le terrain."""
        alphabet = string.digits
        while True:
            suffix = "".join(secrets.choice(alphabet) for _ in range(8))
            account_number = f"TLP-{suffix}"
            if not ClientProfile.objects.filter(account_number=account_number).exists():
                return account_number

    def save(self, collecteur):
        """Cree le compte client et l'assigne automatiquement au collecteur."""
        User = get_user_model()
        user = User.objects.create_user(
            username=self._generate_username(),
            email=self.cleaned_data.get("email", ""),
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            phone_number=self.cleaned_data["phone_number"],
            role=UserRole.CLIENT,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

        return ClientProfile.objects.create(
            user=user,
            account_number=self._generate_account_number(),
            city=self.cleaned_data["city"],
            quarter=self.cleaned_data.get("quarter", ""),
            phone_number=self.cleaned_data["phone_number"],
            solde=self.cleaned_data["solde_initial"],
            trusted_collecteur=collecteur,
        )
