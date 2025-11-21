from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, UserChecklist

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg", "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_UPLOAD_MB = 10


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["pays_origine", "niveau_etude", "domaine_etude",
                  "budget_disponible", "telephone"]
        labels = {
            "pays_origine": _("Pays d’origine"),
            "niveau_etude": _("Niveau d’étude actuel"),
            "domaine_etude": _("Domaine d’étude / Filière"),
            "budget_disponible": _("Budget disponible (FCFA)"),
            "telephone": _("Téléphone"),
        }
        widgets = {
            "pays_origine": forms.Select(attrs={"class": "form-select"}),
            "niveau_etude": forms.Select(attrs={"class": "form-select"}),
            "domaine_etude": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Informatique"}),
            "budget_disponible": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "10000"}),
            "telephone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+237..."}),
        }

    def clean_budget_disponible(self):
        v = self.cleaned_data.get("budget_disponible")
        if v is not None and v < 0:
            raise ValidationError(_("Le budget ne peut pas être négatif."))
        return v


class ChecklistUpdateForm(forms.ModelForm):
    class Meta:
        model = UserChecklist
        fields = ["statut", "fichier", "notes"]
        labels = {
            "statut": _("Statut"),
            "fichier": _("Fichier"),
            "notes":  _("Notes"),
        }
        widgets = {
            "statut": forms.Select(attrs={"class": "form-select"}),
            "fichier": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_fichier(self):
        f = self.cleaned_data.get("fichier")
        if not f:
            return f
        if f.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise ValidationError(_(f"Fichier trop volumineux (≤ {MAX_UPLOAD_MB} Mo)."))
        ctype = getattr(f, "content_type", None)
        if ctype and ctype not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(_("Type de fichier non pris en charge. PDF/JPG/PNG/DOCX uniquement."))
        ext = (f.name.rsplit(".", 1)[-1] or "").lower()
        if ctype is None and ext not in {"pdf", "jpg", "jpeg", "png", "docx"}:
            raise ValidationError(_("Extension non autorisée. PDF/JPG/PNG/DOCX uniquement."))
        return f
