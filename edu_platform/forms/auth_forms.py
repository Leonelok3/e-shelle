"""
Formulaires d'authentification EduCam Pro.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import RegexValidator

User = get_user_model()

PHONE_VALIDATOR = RegexValidator(
    regex=r'^\+?237[0-9]{8,9}$',
    message="Numéro camerounais requis. Format : +237XXXXXXXXX"
)


class EduRegisterForm(forms.Form):
    """Formulaire d'inscription à EduCam Pro."""
    first_name = forms.CharField(
        max_length=50,
        label='Prénom',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre prénom',
            'autocomplete': 'given-name',
        })
    )
    last_name = forms.CharField(
        max_length=50,
        label='Nom',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom de famille',
            'autocomplete': 'family-name',
        })
    )
    email = forms.EmailField(
        label='Adresse email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com',
            'autocomplete': 'email',
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        label='Numéro de téléphone',
        validators=[PHONE_VALIDATOR],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+237 6XX XXX XXX',
            'autocomplete': 'tel',
        })
    )
    password1 = forms.CharField(
        label='Mot de passe',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum 8 caractères',
            'id': 'id_password1',
        })
    )
    password2 = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Répétez votre mot de passe',
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un compte avec cet email existe déjà.")
        return email

    def clean_phone_number(self):
        from edu_platform.models import EduProfile
        phone = self.cleaned_data['phone_number']
        if not phone.startswith('+'):
            phone = '+' + phone
        if EduProfile.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("Ce numéro est déjà associé à un compte.")
        return phone

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError({'password2': "Les mots de passe ne correspondent pas."})
        return cleaned


class EduLoginForm(AuthenticationForm):
    """Formulaire de connexion avec style EduCam.

    Accepte l'email OU le username dans le champ « username ».
    Si la valeur ressemble à un email, on recherche le username correspondant
    avant de laisser AuthenticationForm faire l'authentification.
    """
    username = forms.CharField(
        label='Adresse email ou identifiant',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com',
            'autofocus': True,
            'inputmode': 'email',
        })
    )
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre mot de passe',
        })
    )

    def clean_username(self):
        raw = self.cleaned_data.get('username', '').strip()
        # Si ça ressemble à un email, résoudre en username
        if '@' in raw:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=raw)
                return user.username
            except User.DoesNotExist:
                pass  # AuthenticationForm affichera l'erreur standard
        return raw


class ActivateCodeForm(forms.Form):
    """Formulaire de saisie et activation d'un code d'accès."""
    code = forms.CharField(
        max_length=19,  # XXXX-XXXX-XXXX-XXXX = 19 chars
        label='Code d\'accès',
        widget=forms.TextInput(attrs={
            'class': 'form-control code-input',
            'placeholder': 'XXXX-XXXX-XXXX-XXXX',
            'maxlength': '19',
            'autocomplete': 'off',
            'autocapitalize': 'characters',
            'style': 'letter-spacing: 0.3em; font-family: monospace; font-size: 1.4rem;',
        })
    )

    def clean_code(self):
        code = self.cleaned_data['code'].upper().strip()
        # Valider le format XXXX-XXXX-XXXX-XXXX
        parts = code.split('-')
        if len(parts) != 4 or not all(len(p) == 4 for p in parts):
            raise forms.ValidationError(
                "Format invalide. Le code doit être au format XXXX-XXXX-XXXX-XXXX."
            )
        return code
