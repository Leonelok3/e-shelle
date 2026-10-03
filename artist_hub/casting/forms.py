"""
artist_hub/casting/forms.py
Formulaires de candidature avec validation stricte :
- Vérification mineurs (< 18 ans : tuteur légal et consentement obligatoires)
- Validation taille, poids et mensurations
- Validation réelle des fichiers images (Pillow) et taille max 5 Mo
- Anti-spam par champ honeypot
- Prévention des doublons (téléphone par session)
"""
import datetime
from PIL import Image
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from artist_hub.casting.models import (
    Candidate,
    CandidateGender,
)
from artist_hub.conf import hub_settings


class CandidateRegistrationForm(forms.Form):
    """
    Formulaire complet de candidature en 4 étapes pour la Fashion Week Douala.
    """

    # --- ÉTAPE 1 : INFORMATIONS PERSONNELLES ---
    first_name = forms.CharField(
        label=_("Prénom"),
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Ex : Jessica", "class": "hub-input"}),
    )
    last_name = forms.CharField(
        label=_("Nom"),
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Ex : Kamga", "class": "hub-input"}),
    )
    birth_date = forms.DateField(
        label=_("Date de naissance"),
        widget=forms.DateInput(attrs={"type": "date", "class": "hub-input", "id": "id_birth_date"}),
        help_text=_("Indiquez votre date de naissance réelle."),
    )
    gender = forms.ChoiceField(
        label=_("Sexe"),
        choices=CandidateGender.choices,
        widget=forms.Select(attrs={"class": "hub-select", "id": "id_gender"}),
    )
    height_cm = forms.IntegerField(
        label=_("Taille (en cm)"),
        min_value=140,
        max_value=230,
        widget=forms.NumberInput(attrs={"placeholder": "Ex : 178", "class": "hub-input", "id": "id_height_cm"}),
        help_text=_("Recommandé : 1m75 pour les femmes, 1m83 pour les hommes."),
    )
    weight_kg = forms.IntegerField(
        label=_("Poids (en kg)"),
        min_value=35,
        max_value=150,
        required=False,
        widget=forms.NumberInput(attrs={"placeholder": "Ex : 58", "class": "hub-input"}),
    )
    measurements = forms.CharField(
        label=_("Mensurations (Poitrine - Taille - Hanches)"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ex : 88-62-92", "class": "hub-input"}),
    )
    city = forms.CharField(
        label=_("Ville de résidence"),
        max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "Ex : Douala, Yaoundé, Paris...", "class": "hub-input"}),
    )
    country = forms.CharField(
        label=_("Pays de résidence"),
        max_length=120,
        initial="Cameroun",
        widget=forms.TextInput(attrs={"placeholder": "Ex : Cameroun", "class": "hub-input", "id": "id_country"}),
    )
    phone = forms.CharField(
        label=_("Numéro WhatsApp officiel"),
        max_length=30,
        widget=forms.TextInput(attrs={"placeholder": "Ex : +237 675 293 836", "class": "hub-input"}),
        help_text=_("Utilisé pour vous contacter et pour le suivi de votre candidature."),
    )
    email = forms.EmailField(
        label=_("Adresse Email"),
        widget=forms.EmailInput(attrs={"placeholder": "Ex : candidat@gmail.com", "class": "hub-input"}),
        help_text=_("Votre fiche officielle y sera envoyée."),
    )
    experience = forms.CharField(
        label=_("Expérience / Défilés précédents"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Débutant(e) accepté(e). Précisez vos expériences éventuelles...", "class": "hub-textarea"}),
    )
    social_links = forms.CharField(
        label=_("Lien Instagram / TikTok"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ex : @mon_instagram", "class": "hub-input"}),
    )

    # --- MINEURS (Conditionnel si âge < 18) ---
    guardian_name = forms.CharField(
        label=_("Nom du tuteur légal (si mineur)"),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nom et prénom du parent / tuteur", "class": "hub-input"}),
    )
    guardian_phone = forms.CharField(
        label=_("Téléphone du tuteur légal (si mineur)"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ex : +237 6...", "class": "hub-input"}),
    )
    parental_consent = forms.BooleanField(
        label=_("J'atteste avoir l'autorisation formelle de mon tuteur légal pour participer à ce casting."),
        required=False,
    )

    # --- ÉTAPE 4 : PHOTOS & VIDÉO ---
    photo_portrait = forms.ImageField(
        label=_("Photo 1 — Portrait / Visage (Sans filtre)"),
        required=True,
        help_text=_("Photo claire et nette du visage (JPG, PNG, WEBP, max 5 Mo)."),
    )
    photo_full_length = forms.ImageField(
        label=_("Photo 2 — Plein pied (Silhouette entière)"),
        required=True,
        help_text=_("Photo de vous debout de la tête aux pieds (JPG, PNG, WEBP, max 5 Mo)."),
    )
    video_url = forms.URLField(
        label=_("Vidéo de présentation (30 à 60s) — Lien"),
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "Lien YouTube, TikTok, Google Drive ou Instagram", "class": "hub-input"}),
        help_text=_("Vidéo de présentation courte : présentez-vous et faites une brève démarche."),
    )
    video_file = forms.FileField(
        label=_("Ou téléverser le fichier vidéo direct (MP4, max 20 Mo)"),
        required=False,
        help_text=_("Optionnel si vous avez renseigné un lien vidéo ci-dessus."),
    )

    # --- CONSENTEMENTS ET MENTIONS LÉGALES ---
    gdpr_consent = forms.BooleanField(
        label=_("J'accepte le traitement de mes coordonnées et photos dans le cadre exclusif de ce casting."),
        required=True,
    )
    selection_disclaimer_accepted = forms.BooleanField(
        label=_("Je comprends que cette inscription gratuite ne garantit pas ma sélection finale par le jury."),
        required=True,
    )

    # --- HONEYPOT ANTI-SPAM (invisible aux humains) ---
    website_url_hp = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"style": "display:none !important; position:absolute; left:-9999px;", "tabindex": "-1"}),
    )

    def __init__(self, *args, session=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    def clean_website_url_hp(self):
        val = self.cleaned_data.get("website_url_hp")
        if val:
            raise ValidationError("Tentative de soumission automatisée détectée.")
        return val

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        # Normalisation légère
        cleaned_phone = "".join(phone.split())
        if self.session:
            exists = Candidate.objects.filter(session=self.session, phone=cleaned_phone).exists()
            if exists:
                raise ValidationError(_("Une candidature existe déjà avec ce numéro de téléphone pour cette session."))
        return cleaned_phone

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get("birth_date")
        if not birth_date:
            return birth_date
        today = datetime.date.today()
        if birth_date > today:
            raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 12:
            raise ValidationError(_("L'âge minimum requis pour participer est de 12 ans."))
        return birth_date

    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get("birth_date")

        # Validation spécifique des mineurs
        if birth_date:
            today = datetime.date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 18:
                guardian_name = cleaned_data.get("guardian_name")
                guardian_phone = cleaned_data.get("guardian_phone")
                parental_consent = cleaned_data.get("parental_consent")

                if not guardian_name:
                    self.add_error("guardian_name", _("Pour les candidats mineurs (< 18 ans), le nom du tuteur est obligatoire."))
                if not guardian_phone:
                    self.add_error("guardian_phone", _("Le téléphone du tuteur légal est obligatoire."))
                if not parental_consent:
                    self.add_error("parental_consent", _("Vous devez obligatoirement certifier l'accord parental."))

        # Validation vidéo : au moins un lien ou un fichier
        video_url = cleaned_data.get("video_url")
        video_file = cleaned_data.get("video_file")
        if not video_url and not video_file:
            self.add_error("video_url", _("Veuillez fournir un lien vidéo de présentation (30-60s) ou téléverser votre vidéo."))

        # Validation de taille des fichiers téléversés
        max_size = hub_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        for photo_field in ["photo_portrait", "photo_full_length"]:
            file = cleaned_data.get(photo_field)
            if file and file.size > max_size:
                self.add_error(photo_field, _(f"La taille de l'image ne doit pas dépasser {hub_settings.MAX_UPLOAD_SIZE_MB} Mo."))

        return cleaned_data
