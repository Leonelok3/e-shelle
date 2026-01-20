from django import forms

LANG_CHOICES = [
    ("auto", "Détection automatique"),
    ("fr", "Français"),
    ("en", "Anglais"),
    ("de", "Allemand"),
    ("es", "Espagnol"),
    ("pt", "Portugais"),
    ("it", "Italien"),
]

class TranslationForm(forms.Form):
    file = forms.FileField(
        label="Document (.docx uniquement)",
        help_text="Diplôme, relevé, certificat, CV… au format .docx"
    )
    source_lang = forms.ChoiceField(
        label="Langue source",
        choices=LANG_CHOICES,
        initial="auto"
    )
    target_lang = forms.ChoiceField(
        label="Langue cible",
        choices=LANG_CHOICES,
        initial="en"
    )

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and not f.name.lower().endswith(".docx"):
            raise forms.ValidationError("Seuls les fichiers .docx sont acceptés pour la traduction.")
        return f

class CompressionForm(forms.Form):
    file = forms.FileField(
        label="Document PDF",
        help_text="Uniquement .pdf pour la compression"
    )

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Seuls les fichiers .pdf sont acceptés pour la compression.")
        return f


class ConversionForm(forms.Form):
    MODE_CHOICES = [
        ("docx_to_pdf", "DOCX → PDF"),
        ("pdf_to_docx", "PDF → DOCX"),
    ]

    mode = forms.ChoiceField(
        label="Type de conversion",
        choices=MODE_CHOICES,
        initial="docx_to_pdf"
    )

    file = forms.FileField(
        label="Fichier à convertir",
        help_text="DOCX → PDF ou PDF → DOCX (PDF texte recommandé)"
    )

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("mode")
        f = cleaned.get("file")
        if not mode or not f:
            return cleaned

        name = f.name.lower()

        if mode == "docx_to_pdf" and not name.endswith(".docx"):
            raise forms.ValidationError("Pour DOCX → PDF, le fichier doit être en .docx")
        if mode == "pdf_to_docx" and not name.endswith(".pdf"):
            raise forms.ValidationError("Pour PDF → DOCX, le fichier doit être en .pdf")

        return cleaned
