from django import forms
from .models import DepotGaz, MarqueGaz, VilleGaz, QuartierGaz

class DepotGazForm(forms.ModelForm):
    TAILLES_CHOICES = [
        ("3kg", "3 kg"),
        ("6kg", "6 kg"),
        ("12kg", "12 kg"),
        ("15kg", "15 kg"),
        ("25kg", "25 kg"),
        ("38kg", "38 kg"),
    ]
    tailles = forms.MultipleChoiceField(
        choices=TAILLES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tailles de bouteilles disponibles"
    )

    class Meta:
        model = DepotGaz
        fields = [
            "nom", "description", "photo", "ville", "quartier", "adresse",
            "zone_livraison", "autres_services", "telephone", "whatsapp",
            "marques", "tailles", "prix_6kg", "prix_12kg", "prix_15kg",
            "delai_livraison", "horaires"
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Ex: Dépôt Gaz Plus Akwa"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Présentation de votre dépôt..."}),
            "adresse": forms.TextInput(attrs={"placeholder": "Ex: Face boulangerie, Boulevard de la Liberté"}),
            "zone_livraison": forms.Textarea(attrs={"rows": 2, "placeholder": "Ex: Akwa, Bali, Bonapriso..."}),
            "autres_services": forms.Textarea(attrs={"rows": 2, "placeholder": "Ex: Vente de détendeurs, tuyaux, brûleurs..."}),
            "telephone": forms.TextInput(attrs={"placeholder": "Ex: 699999999"}),
            "whatsapp": forms.TextInput(attrs={"placeholder": "Ex: 237699999999 (sans le +)"}),
            "prix_6kg": forms.NumberInput(attrs={"placeholder": "Optionnel, ex: 2500"}),
            "prix_12kg": forms.NumberInput(attrs={"placeholder": "Optionnel, ex: 5000"}),
            "prix_15kg": forms.NumberInput(attrs={"placeholder": "Optionnel, ex: 6500"}),
            "delai_livraison": forms.TextInput(attrs={"placeholder": "Ex: 30-60 min"}),
            "horaires": forms.TextInput(attrs={"placeholder": "Ex: Lun-Sam 7h-20h, Dim 8h-15h"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ville"].queryset = VilleGaz.objects.filter(active=True)
        self.fields["quartier"].queryset = QuartierGaz.objects.filter(active=True)
        self.fields["marques"].queryset = MarqueGaz.objects.filter(active=True)
        self.fields["marques"].widget = forms.CheckboxSelectMultiple()
        
        # Prepopulate MultipleChoiceField if modifying
        if self.instance and self.instance.pk:
            self.fields["tailles"].initial = self.instance.tailles or []

    def clean_tailles(self):
        return self.cleaned_data.get("tailles") or []
