"""
payments/models.py — Module Paiements E-Shelle
Transactions Mobile Money, historique, remboursements.
"""
from django.db import models
from django.conf import settings
import uuid


class Transaction(models.Model):
    METHODES = [
        ("campay",     "CamPay (Mobile Money)"),
        ("mtn_momo",   "MTN Mobile Money"),
        ("airtel",     "Airtel Money"),
        ("orange",     "Orange Money"),
        ("carte",      "Carte bancaire"),
        ("virement",   "Virement bancaire"),
        ("gratuit",    "Gratuit (coupon)"),
    ]
    STATUTS = [
        ("initie",     "Initié"),
        ("en_attente", "En attente de confirmation"),
        ("pending_awaiting_manual_validation", "En attente de validation manuelle"),
        ("succes",     "Succès"),
        ("echec",      "Échec"),
        ("expire",     "Expiré"),
        ("rembourse",  "Remboursé"),
    ]
    TYPES = [
        ("achat_cours",        "Achat formation"),
        ("achat_produit",      "Achat produit boutique"),
        ("abonnement",         "Abonnement Pro/Enterprise"),
        ("service",            "Paiement service"),
        ("remboursement",      "Remboursement"),
        ("premium_marketplac", "Pack Premium marketplace"),
        ("boost_annonce",      "Boost annonce/bien/véhicule"),
    ]

    reference    = models.CharField(max_length=40, unique=True, blank=True)
    utilisateur  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="transactions",
        null=True,
        blank=True,
    )
    type_tx      = models.CharField(max_length=20, choices=TYPES)
    methode      = models.CharField(max_length=20, choices=METHODES, default="mtn_momo")
    montant      = models.DecimalField(max_digits=12, decimal_places=2)
    devise       = models.CharField(max_length=5, default="XAF")
    telephone    = models.CharField(max_length=25, blank=True,
                                     help_text="Numéro Mobile Money")
    statut       = models.CharField(max_length=40, choices=STATUTS, default="initie")
    # Références externes (API paiement)
    ref_operateur = models.CharField(max_length=200, blank=True,
                                      help_text="Référence de l'opérateur MTN/Airtel")
    ref_interne  = models.CharField(max_length=200, blank=True)
    # Objet payé
    commande     = models.ForeignKey("boutique.Commande", on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="transactions")
    whatsapp_draft_order = models.OneToOneField(
        "whatsapp_commerce.WhatsAppDraftOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transaction",
    )
    payment_link = models.URLField(max_length=1000, blank=True)
    formation    = models.ForeignKey("formations.Formation", on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="transactions")
    metadata     = models.JSONField(default=dict, blank=True)
    erreur       = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Transaction"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"TX-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        buyer = self.utilisateur.username if self.utilisateur_id else self.telephone or "client WhatsApp"
        return f"{self.reference} — {buyer} — {self.montant} {self.devise} ({self.statut})"


class PlanPremiumApp(models.Model):
    """
    Plans premium par application — gérable depuis l'admin Django.
    Remplace les dicts hardcodés dans views.py.
    """
    MODULE_CHOICES = [
        ("annonces",   "📋 Annonces Cam"),
        ("immo",       "🏠 Immobilier"),
        ("auto",       "🚗 Auto Cameroun"),
        ("agro",       "🌿 E-Shelle Agro"),
        ("gaz",        "🔥 E-Shelle Gaz"),
        ("pharma",     "💊 E-Shelle Pharma"),
        ("pressing",   "👔 E-Shelle Pressing"),
        ("formations", "📚 Formations"),
        ("boutique",   "🛒 Boutique"),
        ("rencontres", "❤️ E-Shelle Love"),
        ("njangi",     "💰 Njangi"),
        ("general",    "🌐 Général (toutes apps)"),
    ]

    module       = models.CharField("Application", max_length=30, choices=MODULE_CHOICES)
    slug         = models.SlugField("Identifiant", max_length=30,
                                     help_text="ex: starter, pro, expert — sans espaces")
    nom          = models.CharField("Nom du plan", max_length=50)
    emoji        = models.CharField("Emoji", max_length=10, default="⭐")
    prix         = models.PositiveIntegerField("Prix (FCFA)")
    duree_jours  = models.PositiveIntegerField("Durée (jours)", default=30)
    description  = models.TextField("Description courte", blank=True,
                                     help_text="Phrase d'accroche affichée sous le nom du plan")
    benefices    = models.JSONField(
        "Bénéfices",
        default=list,
        help_text='Liste JSON des bénéfices. Ex: ["30 jours Premium","Annonces illimitées"]'
    )
    populaire    = models.BooleanField("Plan populaire ⭐", default=False)
    couleur      = models.CharField("Couleur hex", max_length=20, default="#4CAF50",
                                     help_text="Ex: #8B5CF6 pour violet")
    actif        = models.BooleanField("Actif", default=True)
    ordre        = models.PositiveSmallIntegerField("Ordre d'affichage", default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("module", "slug")]
        ordering        = ["module", "ordre", "prix"]
        verbose_name    = "Plan Premium (par app)"
        verbose_name_plural = "Plans Premium (par app)"

    def __str__(self):
        return f"{self.get_module_display()} — {self.nom} ({self.prix:,} FCFA/{self.duree_jours}j)"

    def to_dict(self):
        """Retourne le plan au format compatible avec l'ancien dict PLANS_PREMIUM."""
        return {
            "nom":         self.nom,
            "emoji":       self.emoji,
            "prix":        self.prix,
            "duree_jours": self.duree_jours,
            "couleur":     self.couleur,
            "populaire":   self.populaire,
            "features":    self.benefices if isinstance(self.benefices, list) else [],
            "description": self.description,
        }


class Coupon(models.Model):
    """Codes promo et réductions."""
    TYPES = [
        ("pourcent",  "Pourcentage de réduction"),
        ("fixe",      "Montant fixe"),
        ("gratuit",   "Accès gratuit"),
    ]

    code         = models.CharField(max_length=50, unique=True)
    type_coupon  = models.CharField(max_length=10, choices=TYPES, default="pourcent")
    valeur       = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                        help_text="Valeur (% ou FCFA selon le type)")
    max_utilisations = models.PositiveIntegerField(default=0,
                                                     help_text="0 = illimité")
    nb_utilisations  = models.PositiveIntegerField(default=0)
    date_debut   = models.DateTimeField(null=True, blank=True)
    date_fin     = models.DateTimeField(null=True, blank=True)
    actif        = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Coupon"

    def __str__(self):
        return f"{self.code} ({self.valeur}{'%' if self.type_coupon == 'pourcent' else ' FCFA'})"

    @property
    def est_valide(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.actif:
            return False
        if self.date_debut and now < self.date_debut:
            return False
        if self.date_fin and now > self.date_fin:
            return False
        if self.max_utilisations > 0 and self.nb_utilisations >= self.max_utilisations:
            return False
        return True
