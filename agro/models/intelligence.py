from django.conf import settings
from django.db import models


class PrixMarche(models.Model):
    TENDANCE_CHOICES = [
        ('hausse', 'En hausse'),
        ('stable', 'Stable'),
        ('baisse', 'En baisse'),
    ]

    produit = models.CharField(max_length=120)
    ville = models.CharField(max_length=100)
    prix_moyen = models.DecimalField(max_digits=12, decimal_places=2)
    unite = models.CharField(max_length=30, default='kg')
    tendance = models.CharField(max_length=20, choices=TENDANCE_CHOICES, default='stable')
    date_releve = models.DateField()

    class Meta:
        ordering = ['ville', 'produit']
        verbose_name = "Prix de marche"
        verbose_name_plural = "Prix de marche"
        indexes = [
            models.Index(fields=['ville', 'produit']),
            models.Index(fields=['date_releve']),
        ]

    def __str__(self):
        return f"{self.produit} - {self.ville}: {self.prix_moyen} FCFA/{self.unite}"


class QuestionAgentIA(models.Model):
    AGENT_CHOICES = [
        ('agricole', 'Agent agricole'),
        ('maladies', 'Maladies & photos'),
        ('marche', 'Agent marche'),
        ('finance', 'Finance & stock'),
    ]

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='questions_agro_ia',
    )
    agent_type = models.CharField(max_length=30, choices=AGENT_CHOICES)
    question = models.TextField()
    image = models.ImageField(upload_to='agro/ia/%Y/%m/', null=True, blank=True)
    reponse = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Question agent IA"
        verbose_name_plural = "Questions agents IA"

    def __str__(self):
        return f"{self.get_agent_type_display()} - {self.question[:60]}"


class StockProducteur(models.Model):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stocks_agro',
    )
    produit = models.ForeignKey(
        'agro.ProduitAgro',
        on_delete=models.CASCADE,
        related_name='stocks_producteurs',
    )
    quantite = models.FloatField(default=0)
    seuil_alerte = models.FloatField(default=0)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['produit__nom']
        verbose_name = "Stock producteur"
        verbose_name_plural = "Stocks producteurs"
        unique_together = ['utilisateur', 'produit']

    def __str__(self):
        return f"{self.produit.nom} - {self.quantite} {self.produit.unite_mesure}"

    @property
    def est_en_alerte(self):
        return self.quantite <= self.seuil_alerte
