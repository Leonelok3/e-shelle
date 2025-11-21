from django.db import models
from django.contrib.auth.models import User


# -------------------------
# Profil utilisateur Visa Études
# -------------------------
class UserProfile(models.Model):
    STUDY_LEVELS = [
        ("licence", "Licence"),
        ("master", "Master"),
        ("doctorat", "Doctorat"),
    ]

    COUNTRIES = [
        ("cameroun", "Cameroun"),
        ("senegal", "Sénégal"),
        ("cote_ivoire", "Côte d'Ivoire"),
        ("autre", "Autre"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="visaetude_profile")
    pays_origine = models.CharField(max_length=50, choices=COUNTRIES)
    niveau_etude = models.CharField(max_length=20, choices=STUDY_LEVELS)
    domaine_etude = models.CharField(max_length=100)
    budget_disponible = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil de {self.user.username}"

    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"


# -------------------------
# Pays destination "génériques"
# -------------------------
class Country(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=3, unique=True)  # CAN, USA, FRA, etc.
    description = models.TextField()
    delai_traitement = models.CharField(max_length=100)  # Ex: "2-4 mois"
    cout_visa = models.DecimalField(max_digits=10, decimal_places=2)
    taux_acceptation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="countries/", null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Pays"
        verbose_name_plural = "Pays"


class CountryGuide(models.Model):
    pays = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="guides")
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    ordre = models.IntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pays.nom} - {self.titre}"

    class Meta:
        verbose_name = "Guide Pays"
        verbose_name_plural = "Guides Pays"
        ordering = ["ordre"]


class RequiredDocument(models.Model):
    pays = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="documents_requis")
    nom = models.CharField(max_length=200)
    description = models.TextField()
    exemple = models.FileField(upload_to="documents/exemples/", null=True, blank=True)
    obligatoire = models.BooleanField(default=True)
    ordre = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.pays.nom} - {self.nom}"

    class Meta:
        verbose_name = "Document Requis"
        verbose_name_plural = "Documents Requis"
        ordering = ["ordre"]


class UserChecklist(models.Model):
    STATUS_CHOICES = [
        ("non_commence", "Non commencé"),
        ("en_cours", "En cours"),
        ("complete", "Complété"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="visaetude_checklists")
    pays = models.ForeignKey(Country, on_delete=models.CASCADE)
    document = models.ForeignKey(RequiredDocument, on_delete=models.CASCADE)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="non_commence")
    fichier = models.FileField(upload_to="documents/users/", null=True, blank=True)
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.document.nom}"

    class Meta:
        verbose_name = "Checklist Utilisateur"
        verbose_name_plural = "Checklists Utilisateurs"
        unique_together = ["user", "document"]


class Milestone(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="visaetude_jalons")
    pays = models.ForeignKey(Country, on_delete=models.CASCADE)
    titre = models.CharField(max_length=200)
    description = models.TextField()
    date_prevue = models.DateField()
    complete = models.BooleanField(default=False)
    date_completion = models.DateField(null=True, blank=True)
    ordre = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.titre}"

    class Meta:
        verbose_name = "Jalon"
        verbose_name_plural = "Jalons"
        ordering = ["ordre", "date_prevue"]


class FAQ(models.Model):
    pays = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="faqs", null=True, blank=True)
    question = models.CharField(max_length=500)
    reponse = models.TextField()
    ordre = models.IntegerField(default=0)
    populaire = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ["-populaire", "ordre"]


# -------------------------
# Pays Visa Études (nouveau module)
# -------------------------
class VisaCountry(models.Model):
    slug = models.SlugField(
        unique=True,
        help_text="Identifiant du pays, ex: canada, france, belgique",
    )
    name = models.CharField("Nom du pays", max_length=100)
    short_label = models.CharField(
        "Label court (optionnel)",
        max_length=150,
        blank=True,
        help_text="Ex: Destination francophone abordable pour les masters",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Pays – Visa Études"
        verbose_name_plural = "Pays – Visa Études"

    def __str__(self) -> str:
        return self.name


class VisaResource(models.Model):
    CATEGORY_CHOICES = [
        ("admission", "Admission / Universités"),
        ("visa", "Visa étudiant"),
        ("bourse", "Bourses d’étude"),
        ("rdv", "Prise de rendez-vous"),
        ("divers", "Autres (guides, astuces)"),
    ]
    TYPE_CHOICES = [
        ("video", "Vidéo"),
        ("capture", "Captures d’écran"),
        ("pdf", "PDF / Guide"),
    ]

    country = models.ForeignKey(
        VisaCountry,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    title = models.CharField("Titre de la ressource", max_length=200)
    step_label = models.CharField(
        "Étape / description courte",
        max_length=120,
        blank=True,
        help_text='Ex: "Remplir le formulaire de visa en ligne"',
    )
    category = models.CharField(
        "Catégorie",
        max_length=20,
        choices=CATEGORY_CHOICES,
    )
    resource_type = models.CharField(
        "Type de ressource",
        max_length=20,
        choices=TYPE_CHOICES,
        default="video",
    )
    url = models.URLField(
        "URL",
        help_text="Lien vers la vidéo / page tutoriel / dossier Drive",
    )
    order = models.PositiveIntegerField(
        "Ordre d’affichage",
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["country", "order", "title"]
        verbose_name = "Ressource (vidéo / guide) – Visa Études"
        verbose_name_plural = "Ressources (vidéos / guides) – Visa Études"

    def __str__(self) -> str:
        return f"{self.country.name} – {self.title}"


# -------------------------
# Progression globale (option future)
# -------------------------
class UserProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="visa_progress")
    step_1_profile = models.BooleanField(default=False)
    step_2_country = models.BooleanField(default=False)
    step_3_checklist = models.BooleanField(default=False)
    step_4_documents = models.BooleanField(default=False)
    step_5_coach = models.BooleanField(default=False)

    @property
    def completed_steps(self):
        return sum(
            [
                self.step_1_profile,
                self.step_2_country,
                self.step_3_checklist,
                self.step_4_documents,
                self.step_5_coach,
            ]
        )

    @property
    def current_stage(self):
        return self.completed_steps + 1

    def __str__(self):
        return f"Progression de {self.user.username}"

    class Meta:
        verbose_name = "Progression Visa Études"
        verbose_name_plural = "Progressions Visa Études"


# visaetude/models.py

class University(models.Model):
    name = models.CharField(max_length=255)
    country = models.ForeignKey(VisaCountry, on_delete=models.CASCADE, related_name="universities")
    admission_link = models.URLField(null=True, blank=True)
    advice = models.TextField(null=True, blank=True)  # Conseils pour l'admission dans cette université
    ranking = models.IntegerField(null=True, blank=True)  # Classement de l'université

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Université"
        verbose_name_plural = "Universités"

# visaetude/models.py

class CountryAdvice(models.Model):
    country = models.ForeignKey(VisaCountry, on_delete=models.CASCADE, related_name="advices")
    advice_title = models.CharField(max_length=255)
    advice_content = models.TextField()

    def __str__(self):
        return f"Conseil pour {self.country.name}: {self.advice_title}"

    class Meta:
        verbose_name = "Conseil"
        verbose_name_plural = "Conseils"

# visaetude/models.py

class Scholarship(models.Model):
    country = models.ForeignKey(VisaCountry, on_delete=models.CASCADE, related_name="scholarships")
    scholarship_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    application_link = models.URLField()

    def __str__(self):
        return self.scholarship_name

    class Meta:
        verbose_name = "Bourse"
        verbose_name_plural = "Bourses"
