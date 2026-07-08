"""
gaz/models.py — E-Shelle Gaz
Livraison de gaz domestique au Cameroun.
Le client trouve un depot, contacte par WhatsApp/appel, paie a la livraison.
"""
import urllib.parse
from datetime import date
from django.db import models
from django.utils.text import slugify
from django.conf import settings


# ─── Referentiels ────────────────────────────────────────────────────────────

class VilleGaz(models.Model):
    nom    = models.CharField(max_length=80)
    slug   = models.SlugField(max_length=100, unique=True, blank=True)
    region = models.CharField(max_length=80, default="Centre")
    active = models.BooleanField(default=True)
    ordre  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Ville"
        verbose_name_plural = "Villes"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class QuartierGaz(models.Model):
    ville  = models.ForeignKey(VilleGaz, on_delete=models.CASCADE, related_name="quartiers")
    nom    = models.CharField(max_length=100)
    slug   = models.SlugField(max_length=120, unique=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Quartier"
        verbose_name_plural = "Quartiers"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.ville.slug}-{self.nom}")
            self.slug = base[:120]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} ({self.ville.nom})"


class MarqueGaz(models.Model):
    """Marques de gaz vendues (Total, Tradex, Bocom, Victoria, Rainbow...)"""
    nom    = models.CharField(max_length=60)
    slug   = models.SlugField(max_length=80, unique=True, blank=True)
    couleur = models.CharField(max_length=7, default="#FF6B00", help_text="Couleur hex de la marque")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Marque de gaz"
        verbose_name_plural = "Marques de gaz"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


# ─── Depot de gaz ────────────────────────────────────────────────────────────

class DepotGaz(models.Model):
    """Depot / station de gaz avec livraison a domicile."""

    # Identite
    nom            = models.CharField(max_length=150)
    slug           = models.SlugField(max_length=200, unique=True, blank=True)
    description    = models.TextField(blank=True)
    photo          = models.ImageField(upload_to="gaz/depots/", null=True, blank=True)

    # Localisation
    ville          = models.ForeignKey(VilleGaz, on_delete=models.PROTECT, related_name="depots")
    quartier       = models.ForeignKey(QuartierGaz, on_delete=models.SET_NULL,
                        null=True, blank=True, related_name="depots")
    adresse        = models.CharField(max_length=250, blank=True)
    zone_livraison = models.TextField(blank=True,
                        help_text="Quartiers desservis par la livraison")

    # Contact
    telephone      = models.CharField(max_length=20)
    whatsapp       = models.CharField(max_length=20, blank=True,
                        help_text="Numero WhatsApp sans +, ex: 237680625082")
    whatsapp_msg   = models.CharField(max_length=300, blank=True)

    # Produits
    marques        = models.ManyToManyField(MarqueGaz, blank=True, related_name="depots")
    tailles        = models.JSONField(default=list, blank=True,
                        help_text='Ex: ["6kg","12kg","15kg"]')
    prix_6kg       = models.PositiveIntegerField(null=True, blank=True)
    prix_12kg      = models.PositiveIntegerField(null=True, blank=True)
    prix_15kg      = models.PositiveIntegerField(null=True, blank=True)

    # Service
    livraison_rapide = models.BooleanField(default=True)
    delai_livraison  = models.CharField(max_length=60, default="30-60 min")
    horaires         = models.CharField(max_length=150, default="Lun-Sam 7h-20h")
    livraison_nuit   = models.BooleanField(default=False)
    paiement_info    = models.CharField(max_length=200,
                            default="Paiement a la livraison (especes)")
    autres_services  = models.TextField(blank=True,
                            help_text="Autres services proposes (vente d'accessoires, tuyaux...)")

    # ── Souscription mensuelle depot ─────────────────────────────
    PLAN_CHOICES = [
        ("basic",   "Basic — 2 000 FCFA/mois"),
        ("pro",     "Pro — 5 000 FCFA/mois"),
        ("premium", "Premium — 10 000 FCFA/mois"),
    ]
    plan_actif          = models.CharField(max_length=10, choices=PLAN_CHOICES,
                            null=True, blank=True, verbose_name="Plan souscrit")
    abonnement_actif    = models.BooleanField(default=False,
                            help_text="Le depot a paye son abonnement — visible sur la plateforme")
    abonnement_expire_le = models.DateField(null=True, blank=True,
                            help_text="Date d'expiration de l'abonnement")
    montant_paye        = models.PositiveIntegerField(null=True, blank=True,
                            help_text="Montant recu en FCFA")
    ref_paiement        = models.CharField(max_length=100, blank=True,
                            help_text="Reference Orange Money / MTN / etc.")
    notes_admin         = models.TextField(blank=True,
                            help_text="Notes internes (paiements, historique...)")

    # Statut
    is_active    = models.BooleanField(default=False,
                    help_text="Activer apres confirmation du paiement")
    is_verified  = models.BooleanField(default=False)
    is_featured  = models.BooleanField(default=False)
    note_moyenne = models.FloatField(default=0.0)
    nb_avis      = models.PositiveIntegerField(default=0)

    gerant     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name="depots_gaz")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-is_verified", "nom"]
        verbose_name = "Depot de gaz"
        verbose_name_plural = "Depots de gaz"

    def save(self, *args, **kwargs):
        if not self.slug:
            ville_nom = self.ville.nom if self.ville_id else "gaz"
            base = slugify(f"{self.nom}-{ville_nom}")
            slug, n = base, 1
            while DepotGaz.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug[:200]
        if not self.whatsapp_msg:
            self.whatsapp_msg = "Bonjour, je souhaite commander du gaz. Livraison a domicile svp."
        # Synchronisation abonnement → visibilite
        if self.abonnement_actif and self.abonnement_expire_le:
            if self.abonnement_expire_le < date.today():
                self.abonnement_actif = False
                self.is_active = False
        super().save(*args, **kwargs)

    @property
    def abonnement_expire(self):
        """True si l'abonnement est expire."""
        if self.abonnement_expire_le:
            return self.abonnement_expire_le < date.today()
        return True

    @property
    def jours_restants(self):
        """Nombre de jours restants sur l'abonnement."""
        if self.abonnement_expire_le:
            delta = (self.abonnement_expire_le - date.today()).days
            return max(0, delta)
        return 0

    def __str__(self):
        return f"{self.nom} — {self.ville}"

    @property
    def whatsapp_url(self):
        numero = (self.whatsapp or self.telephone).replace(" ", "").replace("+", "")
        msg = self.whatsapp_msg or "Bonjour, je voudrais commander du gaz."
        return f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"

    @property
    def tel_url(self):
        return f"tel:{self.telephone}"

    @property
    def etoiles(self):
        return round(self.note_moyenne)

    @property
    def tailles_display(self):
        mapping = {"3kg": "3 kg", "6kg": "6 kg", "12kg": "12 kg",
                   "15kg": "15 kg", "25kg": "25 kg", "38kg": "38 kg"}
        return [mapping.get(t, t) for t in (self.tailles or [])]


# ─── Avis clients ────────────────────────────────────────────────────────────

class AvisDepot(models.Model):
    depot       = models.ForeignKey(DepotGaz, on_delete=models.CASCADE, related_name="avis")
    auteur      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                    related_name="avis_gaz")
    note        = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaire = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("depot", "auteur")
        ordering = ["-created_at"]
        verbose_name = "Avis"
        verbose_name_plural = "Avis"

    def __str__(self):
        return f"{self.auteur.username} -> {self.depot.nom} ({self.note}*)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        avis = AvisDepot.objects.filter(depot=self.depot)
        self.depot.note_moyenne = avis.aggregate(
            m=models.Avg("note"))["m"] or 0.0
        self.depot.nb_avis = avis.count()
        self.depot.save(update_fields=["note_moyenne", "nb_avis"])
