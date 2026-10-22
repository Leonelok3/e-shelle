from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class NjangiAchatGroupe(models.Model):
    class Status(models.TextChoices):
        OPEN = "ouvert", "Ouvert"
        REACHED = "atteint", "Objectif atteint"
        ORDERED = "commande", "Commandé"
        DELIVERED = "livre", "Livré"

    product = models.ForeignKey(
        "business.BusinessCatalogItem",
        on_delete=models.PROTECT,
        related_name="njangi_group_buys",
    )
    quantite_cible = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantite_actuelle = models.PositiveIntegerField(default=0)
    prix_njangi = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    prix_normal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    businesses_participants = models.ManyToManyField(
        "business.BusinessProfile",
        related_name="njangi_group_buys",
        blank=True,
    )
    date_cloture = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    quantite_proposee_par_boutique = models.PositiveIntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def progress_pct(self):
        if not self.quantite_cible:
            return 0
        return min(100, round(self.quantite_actuelle * 100 / self.quantite_cible))

    def economie_par_boutique(self, quantite=None):
        quantity = quantite if quantite is not None else self.quantite_proposee_par_boutique
        return (self.prix_normal - self.prix_njangi) * quantity

    def __str__(self):
        return f"{self.product.title} — {self.quantite_actuelle}/{self.quantite_cible}"


class NjangiAchatParticipation(models.Model):
    class Status(models.TextChoices):
        INVITED = "invite", "Invité"
        ACCEPTED = "accepte", "Accepté"

    achat_groupe = models.ForeignKey(NjangiAchatGroupe, on_delete=models.CASCADE, related_name="participations")
    business = models.ForeignKey("business.BusinessProfile", on_delete=models.CASCADE, related_name="njangi_participations")
    quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INVITED)
    invited_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["achat_groupe", "business"], name="njangi_achat_business_unique"),
        ]

    def __str__(self):
        return f"{self.business.name} — {self.achat_groupe_id}"
