from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


# ------------------------------
# 🔹 Modèle de template de CV
# ------------------------------
class CVTemplate(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom du modèle")
    description = models.TextField(verbose_name="Description")
    industry = models.CharField(max_length=100, verbose_name="Secteur d'activité")
    country = models.CharField(max_length=50, verbose_name="Pays")
    popularity_score = models.IntegerField(default=0, verbose_name="Score de popularité")
    html_template = models.TextField(verbose_name="Template HTML")
    thumbnail = models.ImageField(upload_to='cv_templates/', null=True, blank=True, verbose_name="Aperçu")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    style_type = models.CharField(
        max_length=50,
        choices=[
            ('professional', 'Professionnel'),
            ('creative', 'Créatif'),
            ('traditional', 'Traditionnel'),
            ('modern', 'Moderne'),
            ('canadian', 'Canadien'),
            ('european', 'Européen'),
            ('american', 'Américain'),
        ],
        default='professional',
        verbose_name="Type de style"
    )

    is_active = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        ordering = ['-popularity_score', '-created_at']
        verbose_name = "Modèle de CV"
        verbose_name_plural = "Modèles de CV"

    def __str__(self):
        return f"{self.name} - {self.industry} ({self.country})"


# ------------------------------
# 🔹 Modèle principal de CV
# ------------------------------
class CV(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cvs', verbose_name="Utilisateur")
    template = models.ForeignKey(CVTemplate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Modèle de CV")
    profession = models.CharField(max_length=100, verbose_name="Profession/Titre du poste", null=True, blank=True)
    pays_cible = models.CharField(max_length=100, verbose_name="Pays ciblé", null=True, blank=True)

    current_step = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(3)], verbose_name="Étape actuelle")
    step1_completed = models.BooleanField(default=False, verbose_name="Étape 1 complétée")
    step2_completed = models.BooleanField(default=False, verbose_name="Étape 2 complétée")
    step3_completed = models.BooleanField(default=False, verbose_name="Étape 3 complétée")

    data = models.JSONField(
        default=dict, blank=True, verbose_name="Données du CV",
        help_text="Structure: {personal_info, experiences, education, skills, languages, summary, etc.}"
    )

    is_completed = models.BooleanField(default=False, verbose_name="CV complété")
    is_published = models.BooleanField(default=False, verbose_name="CV publié")

    last_analysis = models.JSONField(null=True, blank=True, verbose_name="Dernière analyse IA")
    quality_score = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score de qualité"
    )

    # 🆕 Résumé professionnel
    summary = models.TextField(blank=True, verbose_name="Résumé professionnel")

    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création", null=True, blank=True)
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification", null=True, blank=True)
    date_completion = models.DateTimeField(null=True, blank=True, verbose_name="Date de finalisation")

    class Meta:
        ordering = ['-date_modification']
        verbose_name = "CV"
        verbose_name_plural = "CVs"
        indexes = [
            models.Index(fields=['utilisateur', '-date_modification']),
            models.Index(fields=['is_completed', 'is_published']),
        ]

    def __str__(self):
        username = self.utilisateur.username if self.utilisateur else 'Inconnu'
        profession = self.profession if self.profession else 'Sans titre'
        return f"CV de {username} - {profession}"

    def get_completion_percentage(self):
        total_steps = 3
        completed_steps = sum([self.step1_completed, self.step2_completed, self.step3_completed])
        return int((completed_steps / total_steps) * 100)

    def mark_step_completed(self, step_number):
        if step_number == 1:
            self.step1_completed = True
        elif step_number == 2:
            self.step2_completed = True
        elif step_number == 3:
            self.step3_completed = True

        if self.step1_completed and self.step2_completed and self.step3_completed:
            self.is_completed = True
            if not self.date_completion:
                self.date_completion = timezone.now()

        self.save()

    # -------- Helpers d'accès au JSON --------
    def get_personal_info(self):
        return self.data.get('personal_info', {})

    def get_experiences(self):
        return self.data.get('experiences', [])

    def get_education(self):
        return self.data.get('education', [])

    def get_skills(self):
        return self.data.get('skills', [])

    def get_languages(self):
        return self.data.get('languages', [])

    def get_summary(self):
        return self.summary or self.data.get('summary', '')

    # -------- ✅ Alias de compatibilité pour les templates (aucune migration) --------
    @property
    def nom(self):
        pi = self.get_personal_info() or {}
        return pi.get('nom') or getattr(self.utilisateur, "last_name", "") or ""

    @property
    def prenom(self):
        pi = self.get_personal_info() or {}
        return pi.get('prenom') or getattr(self.utilisateur, "first_name", "") or ""

    @property
    def email(self):
        pi = self.get_personal_info() or {}
        return pi.get('email') or getattr(self.utilisateur, "email", "") or ""

    @property
    def telephone(self):
        pi = self.get_personal_info() or {}
        return pi.get('telephone') or ""

    @property
    def titre(self):
        pi = self.get_personal_info() or {}
        return pi.get('titre') or (self.profession or "")

    @property
    def ville(self):
        pi = self.get_personal_info() or {}
        return pi.get('ville') or ""

    @property
    def province(self):
        pi = self.get_personal_info() or {}
        return pi.get('province') or ""

    @property
    def pays(self):
        pi = self.get_personal_info() or {}
        return pi.get('pays') or (self.pays_cible or "")

    @property
    def linkedin(self):
        pi = self.get_personal_info() or {}
        return pi.get('linkedin') or ""


# ------------------------------
# 🔹 Expériences professionnelles
# ------------------------------
class Experience(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='experiences')
    title = models.CharField(max_length=200, verbose_name="Intitulé du poste")
    company = models.CharField(max_length=200, verbose_name="Entreprise")
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    location = models.CharField(max_length=150, null=True, blank=True, verbose_name="Lieu")
    description_raw = models.TextField(verbose_name="Description brute")
    description_optimised = models.TextField(blank=True, verbose_name="Description optimisée IA")

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Expérience professionnelle"
        verbose_name_plural = "Expériences professionnelles"

    def __str__(self):
        return f"{self.title} chez {self.company}"

    # ✅ Alias templates (aucune migration)
    @property
    def titre_poste(self):
        return self.title

    @property
    def entreprise(self):
        return self.company

    @property
    def date_debut(self):
        return self.start_date

    @property
    def date_fin(self):
        return self.end_date

    @property
    def lieu(self):
        return self.location or ""

    @property
    def description(self):
        # fallback si un template appelle "description"
        return self.description_optimised or self.description_raw or ""


# ------------------------------
# 🔹 Formations
# ------------------------------
class Education(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="education_set")
    diploma = models.CharField(max_length=150, verbose_name="Diplôme")
    institution = models.CharField(max_length=150, verbose_name="Institution")
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    location = models.CharField(max_length=100, verbose_name="Lieu")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Formation"
        verbose_name_plural = "Formations"

    def __str__(self):
        return f"{self.diploma} - {self.institution}"

    # ✅ Alias templates (aucune migration)
    @property
    def diplome(self):
        return self.diploma

    @property
    def ecole(self):
        return self.institution

    @property
    def date_debut(self):
        return self.start_date

    @property
    def date_fin(self):
        return self.end_date

    @property
    def lieu(self):
        return self.location or ""


# ------------------------------
# 🆕 Compétences
# ------------------------------
class Skill(models.Model):
    class Category(models.TextChoices):
        TECHNIQUE = "technique", "Compétence Technique"
        SOFT = "soft", "Compétence Interpersonnelle"
        OUTIL = "outil", "Outil / Logiciel"

    SKILL_LEVELS = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
        ('expert', 'Expert'),
    ]

    # ✅ Si tu as déjà ce champ en DB, on le garde (sinon migration nécessaire).
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='skills', null=True, blank=True)

    level = models.CharField(
        max_length=50,
        choices=SKILL_LEVELS,
        blank=True,
        verbose_name="Niveau"
    )
    name = models.CharField(max_length=150)
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        db_index=True,
    )

    def __str__(self) -> str:
        try:
            cat = self.get_category_display()
        except Exception:
            cat = self.category or ""
        return f"{self.name} ({cat})" if cat else self.name

    # ✅ Alias FR pour compatibilité
    @property
    def nom(self) -> str:
        return self.name

    @property
    def libelle(self) -> str:
        return self.name

    class Meta:
        ordering = ["category", "name"]
        verbose_name = "Compétence"
        verbose_name_plural = "Compétences"


# ------------------------------
# 🆕 Langues
# ------------------------------
class Language(models.Model):
    LANGUAGE_LEVELS = [
        ('A1', 'A1 - Débutant'),
        ('A2', 'A2 - Élémentaire'),
        ('B1', 'B1 - Intermédiaire'),
        ('B2', 'B2 - Intermédiaire avancé'),
        ('C1', 'C1 - Avancé'),
        ('C2', 'C2 - Maîtrise'),
        ('natif', 'Langue maternelle'),
    ]

    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='languages')
    name = models.CharField(max_length=100, verbose_name="Langue")
    level = models.CharField(max_length=20, choices=LANGUAGE_LEVELS, verbose_name="Niveau")

    class Meta:
        ordering = ['name']
        verbose_name = "Langue"
        verbose_name_plural = "Langues"

    def __str__(self):
        return f"{self.name} - {self.get_level_display()}"

    # ✅ Alias templates
    @property
    def langue(self):
        return self.name

    @property
    def niveau(self):
        return self.level


# ------------------------------
# 🆕 Expériences de bénévolat
# ------------------------------
class Volunteer(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='volunteers')
    organization = models.CharField(max_length=200, verbose_name="Organisation")
    role = models.CharField(max_length=200, verbose_name="Rôle")
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    location = models.CharField(max_length=150, blank=True, verbose_name="Lieu")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Expérience bénévole"
        verbose_name_plural = "Expériences bénévoles"

    def __str__(self):
        return f"{self.role} @ {self.organization}"


# ------------------------------
# 🆕 Centres d'intérêt / Loisirs
# ------------------------------
class Hobby(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='hobbies')
    name = models.CharField(max_length=100, verbose_name="Nom du loisir")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        ordering = ['name']
        verbose_name = "Centre d'intérêt"
        verbose_name_plural = "Centres d'intérêt"

    def __str__(self):
        return self.name


# ------------------------------
# 🆕 Certifications
# ------------------------------
class Certification(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200, verbose_name="Nom de la certification")
    organization = models.CharField(max_length=200, verbose_name="Organisme")
    date_obtained = models.DateField(verbose_name="Date d'obtention")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Date d'expiration")
    credential_id = models.CharField(max_length=100, blank=True, verbose_name="ID de certification")
    credential_url = models.URLField(blank=True, verbose_name="URL de vérification")

    class Meta:
        ordering = ['-date_obtained']
        verbose_name = "Certification"
        verbose_name_plural = "Certifications"

    def __str__(self):
        return f"{self.name} - {self.organization}"

    # ✅ Alias templates
    @property
    def organisme(self):
        return self.organization


# ------------------------------
# 🆕 Projets personnels
# ------------------------------
class Project(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200, verbose_name="Titre du projet")
    description = models.TextField(verbose_name="Description")
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    url = models.URLField(blank=True, verbose_name="URL du projet")
    technologies = models.CharField(max_length=300, blank=True, verbose_name="Technologies utilisées")

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Projet"
        verbose_name_plural = "Projets"

    def __str__(self):
        return self.title

    # ✅ Alias templates
    @property
    def nom(self):
        return self.title

    @property
    def lien(self):
        return self.url


# ------------------------------
# 🔹 Historique des exports
# ------------------------------
class CVExportHistory(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='exports')
    export_format = models.CharField(
        max_length=10,
        choices=[('pdf', 'PDF'), ('docx', 'Word'), ('json', 'JSON')],
        default='pdf',
        verbose_name="Format d'export"
    )
    exported_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'export")
    file_size = models.IntegerField(null=True, blank=True, help_text="Taille en bytes")

    class Meta:
        ordering = ['-exported_at']
        verbose_name = "Historique d'export"
        verbose_name_plural = "Historique des exports"

    def __str__(self):
        return f"Export {self.export_format} - {self.exported_at.strftime('%d/%m/%Y %H:%M')}"
