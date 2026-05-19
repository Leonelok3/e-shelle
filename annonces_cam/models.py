"""
models.py — annonces_cam
Marketplace généraliste camerounaise
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


# ─────────────────────────────────────────────────────────────────
# CHOIX
# ─────────────────────────────────────────────────────────────────

class StatutAnnonce(models.TextChoices):
    BROUILLON             = "BROUILLON",             "Brouillon"
    EN_ATTENTE_VALIDATION = "EN_ATTENTE_VALIDATION", "En attente de validation"
    PUBLIEE               = "PUBLIEE",               "Publiée"
    EXPIREE               = "EXPIREE",               "Expirée"
    VENDUE                = "VENDUE",                "Vendue"
    SUSPENDUE             = "SUSPENDUE",             "Suspendue"
    REFUSEE               = "REFUSEE",               "Refusée"
    ARCHIVEE              = "ARCHIVEE",              "Archivée"

class EtatProduit(models.TextChoices):
    NEUF           = "NEUF",           "Neuf"
    COMME_NEUF     = "COMME_NEUF",     "Comme neuf"
    BON_ETAT       = "BON_ETAT",       "Bon état"
    ETAT_CORRECT   = "ETAT_CORRECT",   "État correct"
    POUR_PIECES    = "POUR_PIECES",    "Pour pièces"
    NON_APPLICABLE = "NON_APPLICABLE", "Non applicable (service)"

class DeviseAnnonce(models.TextChoices):
    XAF = "XAF", "XAF (FCFA)"
    EUR = "EUR", "EUR (€)"
    USD = "USD", "USD ($)"

class ModeContact(models.TextChoices):
    TELEPHONE       = "TELEPHONE",       "Téléphone uniquement"
    WHATSAPP        = "WHATSAPP",        "WhatsApp uniquement"
    MESSAGE_INTERNE = "MESSAGE_INTERNE", "Message interne"
    TOUS            = "TOUS",            "Tous les modes"

class TypeBoost(models.TextChoices):
    REMONTEE_TOP       = "REMONTEE_TOP",       "Remontée en tête"
    MISE_EN_AVANT_7J   = "MISE_EN_AVANT_7J",   "Mise en avant 7 jours"
    MISE_EN_AVANT_15J  = "MISE_EN_AVANT_15J",  "Mise en avant 15 jours"
    MISE_EN_AVANT_30J  = "MISE_EN_AVANT_30J",  "Mise en avant 30 jours"
    BADGE_URGENT       = "BADGE_URGENT",       "Badge Urgent 7 jours"
    PACK_COMPLET       = "PACK_COMPLET",       "Pack Complet 30 jours"

PRIX_BOOSTS = {
    "REMONTEE_TOP":      500,
    "MISE_EN_AVANT_7J":  1000,
    "MISE_EN_AVANT_15J": 2000,
    "MISE_EN_AVANT_30J": 3500,
    "BADGE_URGENT":      800,
    "PACK_COMPLET":      5000,
}

DUREE_BOOSTS_JOURS = {
    "MISE_EN_AVANT_7J":  7,
    "MISE_EN_AVANT_15J": 15,
    "MISE_EN_AVANT_30J": 30,
    "BADGE_URGENT":      7,
    "PACK_COMPLET":      30,
}

class MotifSignalement(models.TextChoices):
    FAUSSE_ANNONCE      = "FAUSSE_ANNONCE",      "Annonce fausse / trompeuse"
    ARNAQUE             = "ARNAQUE",             "Arnaque / Fraude"
    PRODUIT_INTERDIT    = "PRODUIT_INTERDIT",    "Produit interdit"
    PRIX_ABUSIF         = "PRIX_ABUSIF",         "Prix abusif"
    CONTENU_INAPPROPRIE = "CONTENU_INAPPROPRIE", "Contenu inapproprié"
    DOUBLON             = "DOUBLON",             "Annonce en double"
    AUTRE               = "AUTRE",               "Autre"

class FrequenceAlerte(models.TextChoices):
    IMMEDIAT     = "IMMEDIAT",     "Immédiat (à chaque nouvelle annonce)"
    QUOTIDIEN    = "QUOTIDIEN",    "Quotidien (résumé du jour)"
    HEBDOMADAIRE = "HEBDOMADAIRE", "Hebdomadaire"

class TypeCompteVendeur(models.TextChoices):
    GRATUIT = "GRATUIT", "Gratuit (5 annonces)"
    PREMIUM = "PREMIUM", "Premium (illimité)"

VILLES_CAMEROUN = [
    "Yaoundé", "Douala", "Bafoussam", "Garoua", "Maroua", "Ngaoundéré",
    "Bertoua", "Ebolowa", "Kribi", "Limbe", "Buea", "Bamenda", "Kumba",
    "Nkongsamba", "Edéa", "Loum", "Mbalmayo", "Sangmélima", "Foumban",
    "Dschang", "Mbouda", "Bafang", "Obala", "Eseka", "Yokadouma",
    "Batouri", "Kousséri", "Mora", "Meiganga", "Tibati",
]

VILLES_CHOICES = [("", "— Choisir une ville —")] + [(v, v) for v in VILLES_CAMEROUN]


# ─────────────────────────────────────────────────────────────────
# MANAGERS
# ─────────────────────────────────────────────────────────────────

class AnnonceManager(models.Manager):

    def publiees(self):
        today = timezone.now().date()
        return self.filter(statut="PUBLIEE", date_expiration__gte=today)

    def en_vedette(self):
        return self.publiees().filter(est_mise_en_avant=True)

    def urgentes(self):
        return self.publiees().filter(est_urgente=True)

    def coups_de_coeur(self):
        return self.publiees().filter(est_coup_de_coeur=True)

    def par_categorie(self, categorie):
        ids = [categorie.pk]
        ids += list(categorie.sous_categories.values_list("pk", flat=True))
        return self.publiees().filter(categorie__in=ids)

    def par_ville(self, ville):
        return self.publiees().filter(ville__iexact=ville)

    def expirant_bientot(self, jours=3):
        today = timezone.now().date()
        limite = today + timezone.timedelta(days=jours)
        return self.filter(statut="PUBLIEE", date_expiration__range=(today, limite))

    def du_vendeur(self, user):
        return self.filter(vendeur=user)

    def actives_du_vendeur(self, user):
        return self.publiees().filter(vendeur=user)

    def recentes(self, n=12):
        return self.publiees().order_by("-date_publication", "-created_at")[:n]


# ─────────────────────────────────────────────────────────────────
# CATEGORIE
# ─────────────────────────────────────────────────────────────────

class Categorie(models.Model):
    nom             = models.CharField(max_length=100)
    slug            = models.SlugField(max_length=120, unique=True)
    parent          = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="sous_categories"
    )
    icone           = models.CharField(max_length=60, default="fa-tag")
    couleur_hex     = models.CharField(max_length=7, default="#607D8B")
    description     = models.TextField(blank=True)
    ordre           = models.IntegerField(default=0)
    est_active      = models.BooleanField(default=True)
    est_vedette     = models.BooleanField(default=False)
    nombre_annonces = models.IntegerField(default=0)
    image_banniere  = models.ImageField(upload_to="annonces/categories/", blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["ordre", "nom"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.nom} › {self.nom}"
        return self.nom

    def get_absolute_url(self):
        return reverse("annonces:annonces_par_categorie", kwargs={"slug_categorie": self.slug})

    @property
    def est_parent(self):
        return self.parent is None

    def get_sous_categories_actives(self):
        return self.sous_categories.filter(est_active=True).order_by("ordre", "nom")


# ─────────────────────────────────────────────────────────────────
# PROFIL VENDEUR
# ─────────────────────────────────────────────────────────────────

class ProfilVendeur(models.Model):
    user                    = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="profil_vendeur"
    )
    nom_boutique            = models.CharField(max_length=150, blank=True)
    description_boutique    = models.TextField(blank=True)
    photo_profil            = models.ImageField(upload_to="annonces/profils/", blank=True, null=True)
    telephone               = models.CharField(max_length=20, blank=True)
    whatsapp                = models.CharField(max_length=20, blank=True)
    ville                   = models.CharField(max_length=100, blank=True)
    compte_type             = models.CharField(max_length=10, choices=TypeCompteVendeur.choices, default=TypeCompteVendeur.GRATUIT)
    date_expiration_premium = models.DateField(blank=True, null=True)
    est_verifie             = models.BooleanField(default=False)
    note_moyenne            = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    nombre_avis             = models.IntegerField(default=0)
    nombre_ventes_reussies  = models.IntegerField(default=0)
    created_at              = models.DateTimeField(auto_now_add=True)
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil vendeur"
        verbose_name_plural = "Profils vendeurs"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_compte_type_display()})"

    @property
    def est_premium(self):
        if self.compte_type == TypeCompteVendeur.PREMIUM:
            if self.date_expiration_premium is None:
                return True
            return self.date_expiration_premium >= timezone.now().date()
        return False

    @property
    def peut_publier(self):
        if self.est_premium:
            return True
        actives = Annonce.objects.filter(
            vendeur=self.user,
            statut__in=[StatutAnnonce.PUBLIEE, StatutAnnonce.EN_ATTENTE_VALIDATION]
        ).count()
        return actives < getattr(settings, "ANNONCES_MAX_ACTIVES_GRATUIT", 5)

    def get_absolute_url(self):
        return reverse("annonces:profil_vendeur_public", kwargs={"user_id": self.user.pk})


# ─────────────────────────────────────────────────────────────────
# ANNONCE
# ─────────────────────────────────────────────────────────────────

class Annonce(models.Model):
    titre                  = models.CharField(max_length=150)
    slug                   = models.SlugField(max_length=200, unique=True, blank=True)
    categorie              = models.ForeignKey(Categorie, on_delete=models.PROTECT, related_name="annonces", limit_choices_to={"parent__isnull": False})
    sous_categorie         = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True, related_name="annonces_sous_cat")
    description            = models.TextField()
    prix                   = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    devise                 = models.CharField(max_length=5, choices=DeviseAnnonce.choices, default=DeviseAnnonce.XAF)
    prix_a_debattre        = models.BooleanField(default=False)
    gratuit                = models.BooleanField(default=False)
    etat_produit           = models.CharField(max_length=20, choices=EtatProduit.choices, default=EtatProduit.BON_ETAT)
    ville                  = models.CharField(max_length=100)
    quartier               = models.CharField(max_length=100, blank=True)
    adresse_precise        = models.CharField(max_length=255, blank=True)
    latitude               = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude              = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    vendeur                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="annonces")
    telephone_contact      = models.CharField(max_length=20)
    whatsapp_contact       = models.CharField(max_length=20, blank=True)
    email_contact          = models.EmailField(blank=True)
    mode_contact           = models.CharField(max_length=20, choices=ModeContact.choices, default=ModeContact.TOUS)
    statut                 = models.CharField(max_length=25, choices=StatutAnnonce.choices, default=StatutAnnonce.EN_ATTENTE_VALIDATION)
    est_mise_en_avant      = models.BooleanField(default=False)
    est_urgente            = models.BooleanField(default=False)
    est_coup_de_coeur      = models.BooleanField(default=False)
    publiee_par_admin      = models.BooleanField(default=False)
    note_admin             = models.TextField(blank=True)
    date_expiration        = models.DateField(null=True, blank=True)
    vues                   = models.IntegerField(default=0)
    nombre_contacts        = models.IntegerField(default=0)
    nombre_favoris         = models.IntegerField(default=0)
    meta_description       = models.CharField(max_length=160, blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    updated_at             = models.DateTimeField(auto_now=True)
    date_publication       = models.DateTimeField(null=True, blank=True)
    date_derniere_remontee = models.DateTimeField(null=True, blank=True)

    objects = AnnonceManager()

    class Meta:
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"
        ordering = ["-est_mise_en_avant", "-date_publication", "-created_at"]
        indexes = [
            models.Index(fields=["statut", "date_expiration"]),
            models.Index(fields=["categorie", "statut"]),
            models.Index(fields=["ville", "statut"]),
            models.Index(fields=["vendeur", "statut"]),
        ]

    def __str__(self):
        return f"{self.titre} — {self.ville} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titre)[:150]
            slug = base
            n = 1
            while Annonce.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("annonces:detail_annonce", kwargs={"slug": self.slug})

    @property
    def photo_principale(self):
        return self.photos.filter(est_photo_principale=True).first() or self.photos.first()

    @property
    def prix_formate(self):
        if self.gratuit:
            return "Gratuit / Don"
        if self.prix_a_debattre or not self.prix:
            return "Prix à débattre"
        p = int(self.prix)
        if self.devise == "XAF":
            return f"{p:,} XAF".replace(",", " ")
        elif self.devise == "EUR":
            return f"{p:,.0f} €"
        return f"{p:,.0f} {self.devise}"

    @property
    def est_expiree(self):
        if self.date_expiration:
            return self.date_expiration < timezone.now().date()
        return False

    @property
    def jours_restants(self):
        if self.date_expiration:
            delta = (self.date_expiration - timezone.now().date()).days
            return max(0, delta)
        return None

    def get_whatsapp_url(self):
        numero = self.whatsapp_contact or self.telephone_contact
        if numero:
            import urllib.parse
            numero = numero.replace("+", "").replace(" ", "")
            msg = f"Bonjour, je suis interesse(e) par votre offre sur E-Shelle Market : {self.titre} - {self.prix_formate}\n{self.get_absolute_url()}"
            return f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"
        return "#"

    def get_partage_facebook_url(self):
        import urllib.parse
        try:
            from django.contrib.sites.models import Site
            domain = Site.objects.get_current().domain
        except Exception:
            domain = "e-shelle.com"
        url = f"https://{domain}{self.get_absolute_url()}"
        return f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(url)}"


# ─────────────────────────────────────────────────────────────────
# PHOTO ANNONCE
# ─────────────────────────────────────────────────────────────────

def photo_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    from django.utils import timezone as tz
    now = tz.now()
    return f"annonces/photos/{now.year}/{now.month:02d}/{filename}"


class PhotoAnnonce(models.Model):
    annonce              = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="photos")
    image                = models.ImageField(upload_to=photo_upload_path)
    legende              = models.CharField(max_length=200, blank=True)
    est_photo_principale = models.BooleanField(default=False)
    ordre                = models.IntegerField(default=0)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordre", "id"]
        verbose_name = "Photo annonce"
        verbose_name_plural = "Photos annonces"

    def __str__(self):
        return f"Photo — {self.annonce.titre[:40]}"


# ─────────────────────────────────────────────────────────────────
# BOOST ANNONCE
# ─────────────────────────────────────────────────────────────────

class BoostAnnonce(models.Model):
    annonce            = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="boosts")
    type_boost         = models.CharField(max_length=25, choices=TypeBoost.choices)
    prix_paye          = models.DecimalField(max_digits=10, decimal_places=0)
    date_debut         = models.DateTimeField(auto_now_add=True)
    date_fin           = models.DateTimeField()
    est_actif          = models.BooleanField(default=False)
    reference_paiement = models.CharField(max_length=100, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Boost annonce"
        verbose_name_plural = "Boosts annonces"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.annonce.titre[:40]} — {self.get_type_boost_display()}"


# ─────────────────────────────────────────────────────────────────
# MESSAGERIE
# ─────────────────────────────────────────────────────────────────

class ConversationAnnonce(models.Model):
    annonce           = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="conversations")
    acheteur          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_acheteur")
    vendeur           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_vendeur")
    created_at        = models.DateTimeField(auto_now_add=True)
    derniere_activite = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("annonce", "acheteur")
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-derniere_activite"]

    def __str__(self):
        return f"Conv: {self.acheteur} → {self.annonce.titre[:40]}"

    def messages_non_lus_pour(self, user):
        return self.messages.filter(lu=False).exclude(expediteur=user).count()


class MessageAnnonce(models.Model):
    conversation = models.ForeignKey(ConversationAnnonce, on_delete=models.CASCADE, related_name="messages")
    expediteur   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_envoyes_annonce")
    destinataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_recus_annonce")
    contenu      = models.TextField(max_length=1000)
    lu           = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.expediteur} → {self.destinataire}: {self.contenu[:50]}"


# ─────────────────────────────────────────────────────────────────
# FAVORIS
# ─────────────────────────────────────────────────────────────────

class FavoriAnnonce(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favoris_annonces")
    annonce    = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="favoris")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "annonce")
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"

    def __str__(self):
        return f"{self.user} aime {self.annonce.titre[:40]}"


# ─────────────────────────────────────────────────────────────────
# SIGNALEMENT
# ─────────────────────────────────────────────────────────────────

class SignalementAnnonce(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    annonce     = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="signalements")
    motif       = models.CharField(max_length=25, choices=MotifSignalement.choices)
    description = models.TextField()
    traite      = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Signalement"
        verbose_name_plural = "Signalements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Signalement: {self.annonce.titre[:40]} — {self.motif}"


# ─────────────────────────────────────────────────────────────────
# ALERTE
# ─────────────────────────────────────────────────────────────────

class AlerteAnnonce(models.Model):
    user                  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alertes_annonces")
    mots_cles             = models.CharField(max_length=200, blank=True)
    categorie             = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True)
    ville                 = models.CharField(max_length=100, blank=True)
    prix_max              = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    etat_produit          = models.CharField(max_length=20, choices=EtatProduit.choices, blank=True)
    frequence             = models.CharField(max_length=15, choices=FrequenceAlerte.choices, default=FrequenceAlerte.QUOTIDIEN)
    est_active            = models.BooleanField(default=True)
    derniere_notification = models.DateTimeField(null=True, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alerte"
        verbose_name_plural = "Alertes"

    def __str__(self):
        return f"Alerte {self.user} — {self.mots_cles or self.categorie}"


# ─────────────────────────────────────────────────────────────────
# AVIS VENDEUR
# ─────────────────────────────────────────────────────────────────

class AvisVendeur(models.Model):
    vendeur     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="avis_recus")
    acheteur    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="avis_donnes")
    annonce     = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="avis")
    note        = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField(blank=True, max_length=500)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("vendeur", "acheteur", "annonce")
        verbose_name = "Avis vendeur"
        verbose_name_plural = "Avis vendeurs"

    def __str__(self):
        return f"Avis {self.note}/5 sur {self.vendeur} par {self.acheteur}"


# ─────────────────────────────────────────────────────────────────
# REMONTEE
# ─────────────────────────────────────────────────────────────────

class RemonteeAnnonce(models.Model):
    annonce    = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="remontees")
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Remontée"
        verbose_name_plural = "Remontées"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Remontée {self.annonce.titre[:40]} par {self.user}"
