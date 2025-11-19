from django.db import models


# ============================================================
#  PROFIL UTILISATEUR
# ============================================================
class UserProfile(models.Model):
    NIVEAU_ETUDES_CHOICES = [
        ("LT_BAC", "< Bac"),
        ("BAC", "Bac"),
        ("BAC_PLUS_2_3", "Bac+2/3"),
        ("MASTER", "Master"),
        ("DOCTORAT", "Doctorat"),
    ]

    NIVEAU_LANGUE_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
        ("C1", "C1"),
        ("C2", "C2"),
    ]

    BUDGET_CHOICES = [
        ("INF_1000", "< 1000€"),
        ("1000_3000", "1000–3000€"),
        ("SUP_3000", "> 3000€"),
    ]

    HORIZON_CHOICES = [
        ("LT_6", "Moins de 6 mois"),
        ("6_12", "6–12 mois"),
        ("SUP_12", "> 12 mois"),
    ]

    nom = models.CharField("Nom ou pseudo (optionnel)", max_length=100, blank=True)
    email = models.EmailField("Email (optionnel)", blank=True)

    pays_residence = models.CharField("Pays de résidence actuel", max_length=100)
    pays_cibles = models.CharField(
        "Pays ciblés (séparés par des virgules)", max_length=255
    )

    domaine_metier = models.CharField("Métier / domaine", max_length=150)

    niveau_etudes = models.CharField(
        "Niveau d'études",
        max_length=20,
        choices=NIVEAU_ETUDES_CHOICES,
    )
    annees_experience = models.PositiveIntegerField(
        "Années d'expérience dans ce domaine"
    )

    niveau_anglais = models.CharField(
        "Niveau d'anglais",
        max_length=2,
        choices=NIVEAU_LANGUE_CHOICES,
    )
    niveau_langue_pays = models.CharField(
        "Niveau dans la langue du pays ciblé",
        max_length=2,
        choices=NIVEAU_LANGUE_CHOICES,
    )

    budget = models.CharField(
        "Budget approximatif pour le projet",
        max_length=20,
        choices=BUDGET_CHOICES,
    )
    horizon_depart = models.CharField(
        "Horizon de départ souhaité",
        max_length=20,
        choices=HORIZON_CHOICES,
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom or f"Profil #{self.pk}"


# ============================================================
#  OPTIONS DE VISA (POUR ANALYSE PREMIUM)
# ============================================================
class VisaOption(models.Model):
    DIFFICULTE_CHOICES = [
        ("BAS", "Bas"),
        ("MOYEN", "Moyen"),
        ("ELEVE", "Élevé"),
    ]

    pays = models.CharField(max_length=100)
    nom_programme = models.CharField(max_length=200)

    profil_cible = models.TextField(
        help_text="Court texte expliquant pour qui est destiné ce visa."
    )
    conditions_principales = models.TextField(
        help_text="Liste des conditions, séparées par des tirets ou des sauts de ligne."
    )
    documents_cles = models.TextField(
        help_text="Liste des documents à préparer, séparés par des tirets ou des sauts de ligne."
    )

    lien_officiel = models.URLField(max_length=500)
    difficulte = models.CharField(max_length=10, choices=DIFFICULTE_CHOICES)
    delai_approx = models.CharField(max_length=50)

    min_experience = models.PositiveIntegerField(default=0)
    niveau_langue_min = models.CharField(
        max_length=2,
        choices=UserProfile.NIVEAU_LANGUE_CHOICES,
        default="A1",
    )
    niveau_etude_min = models.CharField(
        max_length=20,
        choices=UserProfile.NIVEAU_ETUDES_CHOICES,
        default="LT_BAC",
    )

    def __str__(self):
        return f"{self.nom_programme} – {self.pays}"


# ============================================================
#  PLAN D’ACTION / TO-DO LIST
# ============================================================
class ActionStep(models.Model):
    STATUT_A_FAIRE = "A_FAIRE"
    STATUT_EN_COURS = "EN_COURS"
    STATUT_TERMINE = "TERMINE"

    STATUT_CHOICES = [
        (STATUT_A_FAIRE, "À faire"),
        (STATUT_EN_COURS, "En cours"),
        (STATUT_TERMINE, "Terminé"),
    ]

    user_profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="actions"
    )
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    statut = models.CharField(
        max_length=10, choices=STATUT_CHOICES, default=STATUT_A_FAIRE
    )
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["ordre", "id"]

    def __str__(self):
        return f"{self.titre} ({self.get_statut_display()})"


# ============================================================
#  MODULE CANDIDATURES (JOB TRACKER)
# ============================================================
class JobApplication(models.Model):
    STATUT_CHOICES = [
        ("A_POSTULER", "À postuler"),
        ("ENVOYEE", "Envoyée"),
        ("ENTRETIEN", "Entretien"),
        ("ACCEPTEE", "Acceptée"),
        ("REFUSEE", "Refusée"),
    ]

    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="job_applications",
    )

    titre_poste = models.CharField("Titre du poste", max_length=200)
    entreprise = models.CharField("Entreprise", max_length=150, blank=True)
    pays = models.CharField("Pays", max_length=100, blank=True)
    ville = models.CharField("Ville", max_length=100, blank=True)

    lien_offre = models.URLField("Lien vers l'offre", max_length=500, blank=True)
    source = models.CharField(
        "Source (site, contact…)", max_length=150, blank=True
    )

    statut = models.CharField(
        "Statut",
        max_length=20,
        choices=STATUT_CHOICES,
        default="A_POSTULER",
    )
    date_candidature = models.DateField(
        "Date de candidature", null=True, blank=True
    )
    commentaire = models.TextField("Notes / suivi", blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.titre_poste} – {self.entreprise or 'Sans entreprise'}"


# ============================================================
#  MODULE JOB BOARD – OFFRES D’EMPLOI PUBLIQUES
# ============================================================
class JobOffer(models.Model):
    TYPE_CONTRAT_CHOICES = [
        ("CDI", "CDI / Permanent"),
        ("CDD", "CDD / Temporaire"),
        ("STAGE", "Stage"),
        ("FREELANCE", "Freelance / Indépendant"),
    ]

    titre = models.CharField("Titre du poste", max_length=200)
    entreprise = models.CharField("Entreprise", max_length=150, blank=True)
    pays = models.CharField("Pays", max_length=100)
    ville = models.CharField("Ville", max_length=100, blank=True)

    domaine = models.CharField("Domaine / métier", max_length=150, blank=True)
    type_contrat = models.CharField(
        "Type de contrat", max_length=20, choices=TYPE_CONTRAT_CHOICES, blank=True
    )
    salaire = models.CharField(
        "Salaire / fourchette (optionnel)", max_length=100, blank=True
    )

    description = models.TextField("Description du poste")
    exigences = models.TextField(
        "Exigences / profil recherché", blank=True
    )
    avantages = models.TextField("Avantages (optionnel)", blank=True)

    lien_candidature = models.URLField(
        "Lien pour postuler (site officiel / job board)",
        max_length=500,
        blank=True,
    )

    date_publication = models.DateField("Date de publication", auto_now_add=True)
    date_expiration = models.DateField(
        "Date d'expiration (optionnel)", null=True, blank=True
    )

    est_active = models.BooleanField("Offre visible", default=True)
    priorite = models.PositiveIntegerField(
        "Niveau de priorité (1 = top)", default=10
    )

    class Meta:
        ordering = ["priorite", "-date_publication"]

    def __str__(self):
        return f"{self.titre} – {self.pays}"
