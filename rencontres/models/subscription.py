from django.db import models
from django.utils import timezone


class PlanPremiumRencontre(models.Model):
    """Plans premium spécifiques à l'app de rencontre."""
    NOM_CHOICES = [
        ('silver', '3 jours'),
        ('gold', '10 jours'),
        ('platinum', '1 mois'),
    ]
    nom = models.CharField(max_length=20, choices=NOM_CHOICES, unique=True)
    prix_mensuel = models.DecimalField(max_digits=10, decimal_places=2)
    prix_annuel = models.DecimalField(max_digits=10, decimal_places=2)
    prix_xaf_mensuel = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        help_text="Prix en FCFA (Mobile Money)"
    )
    prix_xaf_annuel = models.DecimalField(
        max_digits=12, decimal_places=0, default=0
    )
    duree_jours = models.PositiveSmallIntegerField(default=30)

    # Fonctionnalités
    likes_par_jour = models.IntegerField(default=10, help_text="-1 = illimité")
    super_likes_par_jour = models.IntegerField(default=1)
    messages_par_jour = models.IntegerField(default=20, help_text="-1 = illimité")
    peut_voir_qui_a_like = models.BooleanField(default=False)
    peut_rembobiner = models.BooleanField(default=False)
    boost_profil_par_semaine = models.IntegerField(default=0)
    photos_max = models.IntegerField(default=6)
    badge_premium = models.BooleanField(default=True)
    filtre_avance = models.BooleanField(default=False)
    sans_publicite = models.BooleanField(default=False)
    mode_incognito = models.BooleanField(default=False)
    stats_profil = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Plan premium rencontre"
        verbose_name_plural = "Plans premium rencontre"

    def get_icon(self):
        icons = {'silver': '⚡', 'gold': '💗', 'platinum': '👑'}
        return icons.get(self.nom, '⭐')

    def __str__(self):
        return f"{self.get_nom_display()} — {int(self.prix_xaf_mensuel)} FCFA"


class AbonnementRencontre(models.Model):
    profil = models.ForeignKey(
        'rencontres.ProfilRencontre',
        on_delete=models.CASCADE,
        related_name='abonnements'
    )
    plan = models.ForeignKey(
        PlanPremiumRencontre,
        on_delete=models.PROTECT
    )
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField()
    est_actif = models.BooleanField(default=True)
    renouvellement_auto = models.BooleanField(default=True)
    payment_reference = models.CharField(
        max_length=200, blank=True,
        help_text="Référence de paiement dans billing/ ou payments/"
    )

    class Meta:
        verbose_name = "Abonnement rencontre"
        verbose_name_plural = "Abonnements rencontre"
        ordering = ['-date_debut']

    def est_valide(self):
        return self.est_actif and self.date_fin > timezone.now()

    def jours_restants(self):
        if not self.est_valide():
            return 0
        delta = self.date_fin - timezone.now()
        return max(0, delta.days)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mettre à jour le statut premium du profil selon tous ses abonnements.
        has_active = AbonnementRencontre.objects.filter(
            profil=self.profil,
            est_actif=True,
            date_fin__gt=timezone.now(),
        ).exists()
        self.profil.est_premium = has_active
        self.profil.save(update_fields=['est_premium'])

    def __str__(self):
        return f"{self.profil} — {self.plan} (valide: {self.est_valide()})"
