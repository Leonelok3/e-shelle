"""
boutique/models.py — Module Boutique Digitale E-Shelle
Produits digitaux, panier, commandes, téléchargements, avis.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid


class CategorieProduit(models.Model):
    nom    = models.CharField(max_length=100)
    nom_en = models.CharField(max_length=100, blank=True)
    slug   = models.SlugField(max_length=120, unique=True, blank=True)
    icone  = models.CharField(max_length=10, default="📦")
    ordre  = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Catégorie produit"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

    @property
    def display_name(self):
        from django.utils.translation import get_language
        return (self.nom_en or self.nom) if get_language() == "en" else self.nom


def produit_upload_path(instance, filename):
    return f"boutique/produits/{instance.slug or 'tmp'}/{filename}"

def thumbnail_upload_path(instance, filename):
    return f"boutique/thumbnails/{instance.slug or 'tmp'}/{filename}"


class Produit(models.Model):
    TYPES = [
        ("template",  "Template / Thème"),
        ("ebook",     "Ebook / PDF"),
        ("outil",     "Outil / Logiciel"),
        ("plugin",    "Plugin / Extension"),
        ("pack_ia",   "Pack IA"),
        ("cours",     "Cours standalone"),
        ("autre",     "Autre"),
    ]

    titre         = models.CharField(max_length=200)
    titre_en      = models.CharField(max_length=200, blank=True)
    slug          = models.SlugField(max_length=220, unique=True, blank=True)
    description   = models.TextField()
    description_en = models.TextField(blank=True)
    description_courte = models.CharField(max_length=300, blank=True)
    description_courte_en = models.CharField(max_length=300, blank=True)
    thumbnail     = models.ImageField(upload_to=thumbnail_upload_path, null=True, blank=True)
    # Fichier à télécharger après achat
    fichier       = models.FileField(upload_to=produit_upload_path, null=True, blank=True,
                                      help_text="Fichier digital (zip, pdf, etc.)")
    url_externe   = models.URLField(blank=True, help_text="Lien externe si fichier hébergé ailleurs")
    type_produit  = models.CharField(max_length=20, choices=TYPES, default="template")
    categorie     = models.ForeignKey(CategorieProduit, on_delete=models.PROTECT,
                                       related_name="produits")
    vendeur       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name="produits_vendus", null=True, blank=True)
    prix          = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                         help_text="Prix en FCFA")
    prix_barre    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_published  = models.BooleanField(default=False)
    is_featured   = models.BooleanField(default=False)
    is_gratuit    = models.BooleanField(default=False)
    nb_ventes     = models.PositiveIntegerField(default=0)
    note_moyenne  = models.FloatField(default=0.0)
    nb_avis       = models.PositiveIntegerField(default=0)
    # Tags JSON pour la recherche
    tags          = models.JSONField(default=list, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Produit"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    @property
    def display_title(self):
        from django.utils.translation import get_language
        return (self.titre_en or self.titre) if get_language() == "en" else self.titre

    @property
    def display_description(self):
        from django.utils.translation import get_language
        return (self.description_en or self.description) if get_language() == "en" else self.description

    @property
    def display_short_description(self):
        from django.utils.translation import get_language
        return (self.description_courte_en or self.description_courte or self.display_description) if get_language() == "en" else (self.description_courte or self.description)

    @property
    def thumbnail_url(self):
        return self.thumbnail.url if self.thumbnail else "/static/img/produit-default.jpg"

    @property
    def pourcentage_reduction(self):
        if self.prix_barre and self.prix_barre > self.prix:
            return int((1 - self.prix / self.prix_barre) * 100)
        return 0


class ImageProduit(models.Model):
    """Galerie d'images pour la page produit."""
    produit   = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="images")
    image     = models.ImageField(upload_to="boutique/galerie/")
    alt       = models.CharField(max_length=200, blank=True)
    ordre     = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre"]

    def __str__(self):
        return f"Image {self.ordre} — {self.produit.titre}"


class AvisProduit(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    produit     = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="avis")
    note        = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    titre       = models.CharField(max_length=200, blank=True)
    commentaire = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("utilisateur", "produit")
        ordering = ["-created_at"]
        verbose_name = "Avis produit"

    def __str__(self):
        return f"{self.utilisateur.username} → {self.produit.titre} ({self.note}★)"


# ── Panier ───────────────────────────────────────────────────
class Panier(models.Model):
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                        related_name="panier", null=True, blank=True)
    session_key = models.CharField(max_length=64, blank=True, help_text="Pour les non-connectés")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Panier {self.utilisateur or self.session_key}"

    @property
    def total(self):
        return sum(l.sous_total for l in self.lignes.all())

    @property
    def nb_articles(self):
        return self.lignes.count()


class LignePanier(models.Model):
    panier   = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name="lignes")
    produit  = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("panier", "produit")

    def __str__(self):
        return f"{self.panier} — {self.produit.titre}"

    @property
    def sous_total(self):
        return self.produit.prix * self.quantite


# ── Commande ─────────────────────────────────────────────────
class Commande(models.Model):
    STATUTS = [
        ("en_attente",  "En attente de paiement"),
        ("payee",       "Payée"),
        ("livree",      "Livrée / Téléchargée"),
        ("remboursee",  "Remboursée"),
        ("annulee",     "Annulée"),
    ]

    reference    = models.CharField(max_length=30, unique=True, blank=True)
    utilisateur  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name="commandes")
    statut       = models.CharField(max_length=20, choices=STATUTS, default="en_attente")
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    email_acheteur = models.EmailField(blank=True)
    telephone    = models.CharField(max_length=25, blank=True)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Commande"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.utilisateur.username} — {self.statut}"


class LigneCommande(models.Model):
    commande  = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name="lignes")
    produit   = models.ForeignKey(Produit, on_delete=models.PROTECT)
    quantite  = models.PositiveIntegerField(default=1)
    prix_unit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.commande.reference} — {self.produit.titre}"

    @property
    def sous_total(self):
        return self.prix_unit * self.quantite


class Telechargement(models.Model):
    """Accès de téléchargement après paiement (lien sécurisé + limité)."""
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name="telechargements")
    produit     = models.ForeignKey(Produit, on_delete=models.CASCADE)
    commande    = models.ForeignKey(Commande, on_delete=models.CASCADE)
    token       = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nb_telechargements = models.PositiveIntegerField(default=0)
    max_telechargements = models.PositiveIntegerField(default=5)
    expire_at   = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Téléchargement"

    def __str__(self):
        return f"{self.utilisateur.username} — {self.produit.titre}"

    @property
    def est_valide(self):
        from django.utils import timezone
        if self.expire_at and timezone.now() > self.expire_at:
            return False
        return self.nb_telechargements < self.max_telechargements
