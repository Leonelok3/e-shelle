from django.db import models


DESTINATION_CHOICES = [
    ('schengen', 'Espace Schengen (France, Belgique, Espagne, etc.)'),
    ('uk', 'Royaume-Uni'),
    ('usa', 'États-Unis'),
    ('canada', 'Canada'),
    ('autre', 'Autre pays'),
]

DUREE_CHOICES = [
    ('moins_15', 'Moins de 15 jours'),
    ('15_30', '15 à 30 jours'),
    ('30_90', '30 à 90 jours'),
]

BUDGET_CHOICES = [
    ('faible', 'Faible'),
    ('moyen', 'Moyen'),
    ('eleve', 'Élevé'),
]


class VisaTourismRequest(models.Model):
    # Infos de base utilisateur
    full_name = models.CharField("Nom complet", max_length=150, blank=True)
    email = models.EmailField("Email", blank=True)
    phone = models.CharField("Téléphone / WhatsApp", max_length=50, blank=True)

    # Profil visa
    destination = models.CharField("Destination", max_length=20, choices=DESTINATION_CHOICES)
    nationalite = models.CharField("Nationalité", max_length=100)
    pays_residence = models.CharField("Pays de résidence", max_length=100)
    duree_sejour = models.CharField("Durée du séjour", max_length=20, choices=DUREE_CHOICES)
    objet_voyage = models.TextField("Objet du voyage")
    a_un_emploi = models.BooleanField("A un emploi / activité pro", default=False)
    a_invitation = models.BooleanField("A une lettre d’invitation", default=False)
    a_deja_voyage = models.BooleanField("A déjà voyagé à l’étranger", default=False)
    budget = models.CharField("Budget", max_length=10, choices=BUDGET_CHOICES)
    age = models.PositiveIntegerField("Âge")

    # Analyse générée
    score_chances = models.PositiveIntegerField("Score de chances (%)", default=0)
    niveau_risque = models.CharField("Niveau de risque", max_length=50, default="À analyser")
    points_forts = models.TextField("Points forts", blank=True)
    points_faibles = models.TextField("Points à renforcer", blank=True)

    # Résultats détaillés (1 élément par ligne)
    documents = models.TextField("Documents requis", blank=True)
    etapes = models.TextField("Étapes clés", blank=True)
    remarques_destination = models.TextField("Remarques destination", blank=True)
    conseils = models.TextField("Conseils", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande Visa Tourisme"
        verbose_name_plural = "Demandes Visa Tourisme"

    def __str__(self):
        return f"Visa {self.get_destination_display()} - {self.full_name or 'Sans nom'} ({self.created_at:%d/%m/%Y})"

    # Helpers pour les templates
    def documents_list(self):
        return [x for x in self.documents.split('\n') if x.strip()]

    def etapes_list(self):
        return [x for x in self.etapes.split('\n') if x.strip()]

    def remarques_list(self):
        return [x for x in self.remarques_destination.split('\n') if x.strip()]

    def conseils_list(self):
        return [x for x in self.conseils.split('\n') if x.strip()]

    def points_forts_list(self):
        return [x for x in self.points_forts.split('\n') if x.strip()]

    def points_faibles_list(self):
        return [x for x in self.points_faibles.split('\n') if x.strip()]


class VisaCreditWallet(models.Model):
    """
    Petit wallet de crédits lié à l'email.
    Tu peux recharger depuis l'admin ou plus tard via ton système global de Shelles.
    """
    email = models.EmailField("Email", unique=True)
    solde = models.PositiveIntegerField("Crédits disponibles", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wallet de crédits Visa Tourisme"
        verbose_name_plural = "Wallets de crédits Visa Tourisme"

    def __str__(self):
        return f"{self.email} – {self.solde} crédits"
