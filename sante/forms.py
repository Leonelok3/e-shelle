from django import forms

from .models import DemandeSante, ProduitSante, ProfessionnelSante


class ProduitSanteForm(forms.ModelForm):
    class Meta:
        model = ProduitSante
        fields = [
            "titre", "type_produit", "categorie", "description", "image", "ville",
            "vendeur_nom", "telephone", "whatsapp", "prix", "prix_barre",
            "stock_disponible", "livraison", "ordonnance_requise",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class ProfessionnelSanteForm(forms.ModelForm):
    class Meta:
        model = ProfessionnelSante
        fields = [
            "nom", "type_pro", "specialites", "ville", "quartier", "adresse",
            "description", "telephone", "whatsapp", "horaires",
            "consultation_domicile", "urgence", "teleconsultation",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "specialites": forms.CheckboxSelectMultiple(),
        }


class DemandeSanteForm(forms.ModelForm):
    class Meta:
        model = DemandeSante
        fields = ["nom", "telephone", "ville", "besoin", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "placeholder": "Décrivez votre besoin, quartier, urgence, produit recherché..."}),
        }
