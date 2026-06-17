import re

from django import forms

from .models import Prestataire


class PrestataireForm(forms.ModelForm):
    """Formulaire d'enregistrement avec validation du code et de l'expiration."""

    class Meta:
        model = Prestataire
        fields = ["nom_complet", "code_premium", "date_expiration", "adresse"]

    def clean_code_premium(self):
        """Normalise le code premium en majuscules."""

        code = (self.cleaned_data.get("code_premium") or "").strip().upper()
        if not code:
            raise forms.ValidationError("Le code Shelle Premium est obligatoire.")
        return code

    def clean_date_expiration(self):
        """Valide le format MM/AA attendu pour la date d'expiration."""

        valeur = (self.cleaned_data.get("date_expiration") or "").strip()
        if not re.match(r"^(0[1-9]|1[0-2])/\d{2}$", valeur):
            raise forms.ValidationError("Utilisez le format MM/AA, par exemple 03/29.")
        return valeur

