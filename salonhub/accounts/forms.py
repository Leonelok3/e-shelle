from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class OwnerSignUpForm(UserCreationForm):
    """Inscription d'un prestataire (salon / institut de beauté)."""

    first_name = forms.CharField(label="Prénom", max_length=150)
    last_name = forms.CharField(label="Nom", max_length=150)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Téléphone (WhatsApp)", max_length=20)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone",
                   "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        from accounts.models import Role as CustomRole
        user.role = CustomRole.VENDOR
        user.email = self.cleaned_data["email"]
        user.whatsapp = self.cleaned_data["phone"]
        if commit:
            user.save()
        return user
