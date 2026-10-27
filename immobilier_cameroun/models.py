"""
models.py — immobilier_cameroun
Marketplace immobilière professionnelle — e-shelle.com
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


# ─────────────────────────────────────────────────────────────────
# CHOIX / CONSTANTES
# ─────────────────────────────────────────────────────────────────

class RoleImmo(models.TextChoices):
    PROPRIETAIRE = "PROPRIETAIRE", "Propriétaire"
    AGENT        = "AGENT",        "Agent immobilier"
    PROMOTEUR    = "PROMOTEUR",    "Promoteur"
    ADMIN        = "ADMIN",        "Administrateur"


class TypeCompte(models.TextChoices):
    GRATUIT = "GRATUIT", "Gratuit"
    PREMIUM = "PREMIUM", "Premium"


class TypeBien(models.TextChoices):
    APPARTEMENT_MEUBLE     = "APPARTEMENT_MEUBLE",     "Appartement meublé"
    APPARTEMENT_NON_MEUBLE = "APPARTEMENT_NON_MEUBLE", "Appartement non meublé"
    STUDIO                 = "STUDIO",                  "Studio"
    VILLA                  = "VILLA",                   "Villa"
    DUPLEX                 = "DUPLEX",                  "Duplex"
    BUREAU                 = "BUREAU",                  "Bureau"
    BOUTIQUE               = "BOUTIQUE",                "Boutique / Commerce"
    TERRAIN                = "TERRAIN",                 "Terrain"
    AUTRE                  = "AUTRE",                   "Autre"


class TypeTransaction(models.TextChoices):
    LOCATION   = "LOCATION",   "Location"
    VENTE      = "VENTE",      "Vente"
    COLOCATION = "COLOCATION", "Colocation"


class Devise(models.TextChoices):
    XAF = "XAF", "Franc CFA (XAF)"
    EUR = "EUR", "Euro (EUR)"
    USD = "USD", "Dollar (USD)"


class PeriodePrix(models.TextChoices):
    PAR_MOIS  = "PAR_MOIS",  "Par mois"
    PAR_JOUR  = "PAR_JOUR",  "Par jour"
    PRIX_FIXE = "PRIX_FIXE", "Prix fixe"


class StatutBien(models.TextChoices):
    BROUILLON             = "BROUILLON",             "Brouillon"
    EN_ATTENTE_VALIDATION = "EN_ATTENTE_VALIDATION", "En attente de validation"
    PUBLIE                = "PUBLIE",                "Publié"
    RESERVE               = "RESERVE",               "Réservé"
    LOUE_VENDU            = "LOUE_VENDU",            "Loué / Vendu"
    REFUSE                = "REFUSE",                "Refusé"
    ARCHIVE               = "ARCHIVE",               "Archivé"


class NomEquipement(models.TextChoices):
    WIFI               = "WIFI",               "Wi-Fi"
    CLIMATISATION      = "CLIMATISATION",      "Climatisation"
    PARKING            = "PARKING",            "Parking"
    GARDIEN            = "GARDIEN",            "Gardien"
    GROUPE_ELECTROGENE = "GROUPE_ELECTROGENE", "Groupe électrogène"
    PISCINE            = "PISCINE",            "Piscine"
    SALLE_SPORT        = "SALLE_SPORT",        "Salle de sport"
    ASCENSEUR          = "ASCENSEUR",          "Ascenseur"
    BALCON             = "BALCON",             "Balcon"
    TERRASSE           = "TERRASSE",           "Terrasse"
    CUISINE_EQUIPEE    = "CUISINE_EQUIPEE",    "Cuisine équipée"
    LAVE_LINGE         = "LAVE_LINGE",         "Lave-linge"
    TV_CABLE           = "TV_CABLE",           "TV câble"
    EAU_COURANTE       = "EAU_COURANTE",       "Eau courante"
    GENERATEUR         = "GENERATEUR",         "Générateur"
    CITERNE_EAU        = "CITERNE_EAU",        "Citerne d'eau"
    CLIM_DANS_CHAMBRES = "CLIM_DANS_CHAMBRES", "Clim dans les chambres"
    MEUBLE_COMPLET     = "MEUBLE_COMPLET",     "Meublé complet"


class StatutVisite(models.TextChoices):
    EN_ATTENTE = "EN_ATTENTE", "En attente"
    CONFIRME   = "CONFIRME",   "Confirmé"
    ANNULE     = "ANNULE",     "Annulé"


class MotifSignalement(models.TextChoices):
    FAUX_ANNONCE       = "FAUX_ANNONCE",       "Fausse annonce"
    PRIX_INCORRECT     = "PRIX_INCORRECT",     "Prix incorrect"
    PHOTOS_INCORRECTES = "PHOTOS_INCORRECTES", "Photos incorrectes"
    BIEN_INEXISTANT    = "BIEN_INEXISTANT",    "Bien inexistant"
    AUTRE              = "AUTRE",              "Autre"


class StatutSoumission(models.TextChoices):
    RECU          = "RECU",          "Reçu"
    EN_TRAITEMENT = "EN_TRAITEMENT", "En traitement"
    PUBLIE        = "PUBLIE",        "Publié"
    REJETE        = "REJETE",        "Rejeté"


VILLES_CAMEROUN = [
    ("Yaoundé", "Yaoundé"), ("Douala", "Douala"), ("Bafoussam", "Bafoussam"),
    ("Bamenda", "Bamenda"), ("Garoua", "Garoua"), ("Maroua", "Maroua"),
    ("Ngaoundéré", "Ngaoundéré"), ("Bertoua", "Bertoua"), ("Ebolowa", "Ebolowa"),
    ("Kribi", "Kribi"), ("Limbé", "Limbé"), ("Kumba", "Kumba"),
    ("Nkongsamba", "Nkongsamba"), ("Edéa", "Edéa"), ("Autre", "Autre"),
]

ICONES_EQUIPEMENT = {
    "WIFI": "fa-wifi", "CLIMATISATION": "fa-snowflake", "PARKING": "fa-car",
    "GARDIEN": "fa-shield-halved", "GROUPE_ELECTROGENE": "fa-bolt",
    "PISCINE": "fa-water-ladder", "SALLE_SPORT": "fa-dumbbell",
    "ASCENSEUR": "fa-elevator", "BALCON": "fa-door-open", "TERRASSE": "fa-sun",
    "CUISINE_EQUIPEE": "fa-utensils", "LAVE_LINGE": "fa-shirt",
    "TV_CABLE": "fa-tv", "EAU_COURANTE": "fa-faucet", "GENERATEUR": "fa-plug",
    "CITERNE_EAU": "fa-droplet", "CLIM_DANS_CHAMBRES": "fa-wind",
    "MEUBLE_COMPLET": "fa-couch",
}


# ─────────────────────────────────────────────────────────────────
# UPLOAD PATHS
# ─────────────────────────────────────────────────────────────────

def photo_profil_upload(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return f"immobilier/profils/{instance.user.id}/{uuid.uuid4().hex[:8]}.{ext}"


def photo_bien_upload(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    slug = instance.bien.slug or "bien"
    return f"immobilier/biens/{slug}/{uuid.uuid4().hex[:8]}.{ext}"


def soumission_upload(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return f"immobilier/soumissions/{uuid.uuid4().hex[:12]}.{ext}"


# ─────────────────────────────────────────────────────────────────
# PROFIL IMMOBILIER
# ─────────────────────────────────────────────────────────────────

class ProfilImmo(models.Model):
    """Profil étendu spécifique à l'application immobilière."""
    user                    = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="profil_immo"
    )
    role                    = models.CharField(
        max_length=20, choices=RoleImmo.choices, default=RoleImmo.PROPRIETAIRE
    )
    compte_type             = models.CharField(
        max_length=10, choices=TypeCompte.choices, default=TypeCompte.GRATUIT
    )
    telephone               = models.CharField("Téléphone", max_length=20, blank=True)
    whatsapp                = models.CharField("WhatsApp", max_length=20, blank=True)
    ville                   = models.CharField(
        max_length=100, blank=True, choices=VILLES_CAMEROUN
    )
    quartier                = models.CharField(max_length=100, blank=True)
    photo_profil            = models.ImageField(
        upload_to=photo_profil_upload, null=True, blank=True
    )
    bio                     = models.TextField(blank=True)
    date_expiration_premium = models.DateField(null=True, blank=True)
    est_verifie             = models.BooleanField(default=False)
    created_at              = models.DateTimeField(auto_now_add=True)
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Profil immobilier"
        verbose_name_plural = "Profils immobiliers"

    def __str__(self):
        return f"{self.user.username} [{self.get_compte_type_display()}]"

    @property
    def est_premium_actif(self):
        if self.compte_type != TypeCompte.PREMIUM:
            return False
        if self.date_expiration_premium and self.date_expiration_premium < timezone.now().date():
            return False
        return True

    @property
    def nb_biens_actifs(self):
        return self.user.biens_immo.filter(
            statut__in=[StatutBien.PUBLIE, StatutBien.EN_ATTENTE_VALIDATION]
        ).count()


# ─────────────────────────────────────────────────────────────────
# BIEN IMMOBILIER
# ─────────────────────────────────────────────────────────────────

class Bien(models.Model):
    # — Identification —
    titre            = models.CharField("Titre", max_length=200)
    slug             = models.SlugField("Slug", unique=True, blank=True, max_length=230)

    # — Classification —
    type_bien        = models.CharField(
        "Type de bien", max_length=30,
        choices=TypeBien.choices, default=TypeBien.APPARTEMENT_MEUBLE
    )
    type_transaction = models.CharField(
        "Transaction", max_length=20,
        choices=TypeTransaction.choices, default=TypeTransaction.LOCATION
    )

    # — Description —
    description      = models.TextField("Description")

    # — Prix —
    prix             = models.DecimalField("Prix", max_digits=14, decimal_places=0)
    devise           = models.CharField(
        "Devise", max_length=3, choices=Devise.choices, default=Devise.XAF
    )
    periode_prix     = models.CharField(
        "Période", max_length=15,
        choices=PeriodePrix.choices, default=PeriodePrix.PAR_MOIS
    )

    # — Caractéristiques —
    surface                = models.FloatField("Surface (m²)", null=True, blank=True)
    nombre_pieces          = models.PositiveIntegerField("Pièces", default=1)
    nombre_chambres        = models.PositiveIntegerField("Chambres", default=1)
    nombre_salles_bain     = models.PositiveIntegerField("Salles de bain", default=1)
    etage                  = models.IntegerField("Étage", null=True, blank=True)
    nombre_etages_immeuble = models.IntegerField("Nb étages immeuble", null=True, blank=True)

    # — Localisation —
    ville            = models.CharField("Ville", max_length=100, choices=VILLES_CAMEROUN)
    quartier         = models.CharField("Quartier", max_length=150)
    adresse_complete = models.TextField("Adresse complète", blank=True)
    latitude         = models.DecimalField(
        "Latitude", max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude        = models.DecimalField(
        "Longitude", max_digits=10, decimal_places=7, null=True, blank=True
    )

    # — Statut & mise en avant —
    statut             = models.CharField(
        "Statut", max_length=25,
        choices=StatutBien.choices, default=StatutBien.BROUILLON,
        db_index=True
    )
    est_mis_en_avant   = models.BooleanField("Mis en avant", default=False, db_index=True)
    est_coup_de_coeur  = models.BooleanField("Coup de cœur", default=False)
    date_disponibilite = models.DateField("Disponible le", null=True, blank=True)

    # — Propriétaire / Admin —
    proprietaire     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="biens_immo", verbose_name="Propriétaire"
    )
    publie_par_admin = models.BooleanField("Publié par admin", default=False)
    note_admin       = models.TextField("Note admin (interne)", blank=True)

    # — Dates —
    created_at       = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at       = models.DateTimeField("Modifié le", auto_now=True)
    date_publication = models.DateTimeField("Publié le", null=True, blank=True)

    # — Statistiques —
    vues             = models.PositiveIntegerField("Vues", default=0)

    # — SEO —
    meta_description = models.CharField("Meta description", max_length=300, blank=True)
    meta_keywords    = models.CharField("Meta keywords", max_length=200, blank=True)

    class Meta:
        verbose_name        = "Bien immobilier"
        verbose_name_plural = "Biens immobiliers"
        ordering            = ["-est_mis_en_avant", "-est_coup_de_coeur", "-date_publication"]
        indexes             = [
            models.Index(fields=["statut", "ville"]),
            models.Index(fields=["type_bien", "type_transaction"]),
        ]

    def __str__(self):
        return f"{self.titre} — {self.ville}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from .utils import generer_slug_unique
            self.slug = generer_slug_unique(self.titre, Bien)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("immobilier:detail_bien", kwargs={"slug": self.slug})

    # — Propriétés utiles —

    @property
    def photo_principale(self):
        photo = self.photos.filter(est_photo_principale=True).first()
        return photo or self.photos.order_by("ordre").first()

    @property
    def prix_formate(self):
        from .utils import formater_prix
        return formater_prix(self.prix, self.devise)

    @property
    def est_disponible(self):
        return self.statut == StatutBien.PUBLIE

    @property
    def nb_favoris(self):
        return self.favoris.count()

    # — Partage réseaux sociaux —

    def _url_absolue(self):
        try:
            from django.contrib.sites.models import Site
            domain = Site.objects.get_current().domain
        except Exception:
            domain = "e-shelle.com"
        return f"https://{domain}{self.get_absolute_url()}"

    @property
    def whatsapp_source_phone(self):
        """Numéro WhatsApp de la source / démarcheur (si le bien provient d'un import WhatsApp)."""
        draft = self.whatsapp_drafts.filter(source_phone__gt="").first()
        return draft.source_phone if draft else None

    def get_whatsapp_url(self):
        from .utils import generer_lien_whatsapp
        return generer_lien_whatsapp(self)

    def get_whatsapp_source_url(self):
        """Lien direct wa.me vers le numéro source démarcheur."""
        phone = self.whatsapp_source_phone
        if phone:
            from .utils import generer_lien_whatsapp
            return generer_lien_whatsapp(self, numero=phone)
        return self.get_whatsapp_url()

    def get_partage_facebook_url(self):
        import urllib.parse
        return f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(self._url_absolue())}"

    def get_partage_twitter_url(self):
        import urllib.parse
        texte = urllib.parse.quote(f"{self.titre} — {self.prix_formate} à {self.ville}")
        url   = urllib.parse.quote(self._url_absolue())
        return f"https://twitter.com/intent/tweet?text={texte}&url={url}"

    def get_partage_linkedin_url(self):
        import urllib.parse
        return f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(self._url_absolue())}"

    def get_partage_telegram_url(self):
        import urllib.parse
        texte = urllib.parse.quote(f"{self.titre} — {self.prix_formate} à {self.ville}")
        url   = urllib.parse.quote(self._url_absolue())
        return f"https://t.me/share/url?url={url}&text={texte}"

    def get_partage_tiktok_url(self):
        """TikTok ne fournit pas d'API de partage directe — on copie juste le lien."""
        return self._url_absolue()


# ─────────────────────────────────────────────────────────────────
# PHOTO BIEN
# ─────────────────────────────────────────────────────────────────

class PhotoBien(models.Model):
    bien               = models.ForeignKey(Bien, on_delete=models.CASCADE, related_name="photos")
    image              = models.ImageField("Image", upload_to=photo_bien_upload)
    legende            = models.CharField("Légende", max_length=200, blank=True)
    est_photo_principale = models.BooleanField("Photo principale", default=False)
    ordre              = models.PositiveIntegerField("Ordre", default=0)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Photo du bien"
        verbose_name_plural = "Photos du bien"
        ordering            = ["ordre", "created_at"]

    def __str__(self):
        return f"Photo #{self.ordre} — {self.bien.titre}"

    def save(self, *args, **kwargs):
        # Garantit une seule photo principale par bien
        if self.est_photo_principale:
            PhotoBien.objects.filter(
                bien=self.bien, est_photo_principale=True
            ).exclude(pk=self.pk).update(est_photo_principale=False)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────
# ÉQUIPEMENT BIEN
# ─────────────────────────────────────────────────────────────────

class EquipementBien(models.Model):
    bien = models.ForeignKey(Bien, on_delete=models.CASCADE, related_name="equipements")
    nom  = models.CharField("Équipement", max_length=30, choices=NomEquipement.choices)

    class Meta:
        verbose_name        = "Équipement"
        verbose_name_plural = "Équipements"
        unique_together     = [("bien", "nom")]

    def __str__(self):
        return f"{self.get_nom_display()} — {self.bien.titre}"

    @property
    def icone(self):
        return ICONES_EQUIPEMENT.get(self.nom, "fa-check-circle")


# ─────────────────────────────────────────────────────────────────
# DEMANDE DE VISITE
# ─────────────────────────────────────────────────────────────────

class DemandeVisite(models.Model):
    bien           = models.ForeignKey(
        Bien, on_delete=models.CASCADE, related_name="demandes_visite"
    )
    nom_complet    = models.CharField("Nom complet", max_length=150)
    telephone      = models.CharField("Téléphone", max_length=20)
    email          = models.EmailField("Email", blank=True)
    message        = models.TextField("Message", blank=True)
    date_souhaitee = models.DateField("Date souhaitée", null=True, blank=True)
    statut         = models.CharField(
        "Statut", max_length=15,
        choices=StatutVisite.choices, default=StatutVisite.EN_ATTENTE
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Demande de visite"
        verbose_name_plural = "Demandes de visite"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"Visite [{self.nom_complet}] → {self.bien.titre}"


# ─────────────────────────────────────────────────────────────────
# FAVORIS
# ─────────────────────────────────────────────────────────────────

class FavorisBien(models.Model):
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favoris_immo"
    )
    bien       = models.ForeignKey(Bien, on_delete=models.CASCADE, related_name="favoris")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Favori"
        verbose_name_plural = "Favoris"
        unique_together     = [("user", "bien")]

    def __str__(self):
        return f"{self.user.username} ♥ {self.bien.titre}"


# ─────────────────────────────────────────────────────────────────
# SIGNALEMENT
# ─────────────────────────────────────────────────────────────────

class SignalementBien(models.Model):
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="signalements_immo"
    )
    bien        = models.ForeignKey(Bien, on_delete=models.CASCADE, related_name="signalements")
    motif       = models.CharField("Motif", max_length=25, choices=MotifSignalement.choices)
    description = models.TextField("Description", blank=True)
    traite      = models.BooleanField("Traité", default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Signalement"
        verbose_name_plural = "Signalements"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"[{self.get_motif_display()}] — {self.bien.titre}"


# ─────────────────────────────────────────────────────────────────
# SOUMISSION DE BIEN (workflow propriétaire → admin publie)
# ─────────────────────────────────────────────────────────────────

class DemandeSoumissionBien(models.Model):
    nom_complet            = models.CharField("Nom complet", max_length=150)
    telephone              = models.CharField("Téléphone", max_length=20)
    email                  = models.EmailField("Email", blank=True)
    type_bien              = models.CharField(
        "Type de bien", max_length=30, choices=TypeBien.choices
    )
    ville                  = models.CharField("Ville", max_length=100, choices=VILLES_CAMEROUN)
    quartier               = models.CharField("Quartier", max_length=150)
    description_rapide     = models.TextField("Description rapide")
    photos_jointes         = models.FileField(
        "Photos jointes", upload_to=soumission_upload, null=True, blank=True
    )
    message_complementaire = models.TextField("Message complémentaire", blank=True)
    statut                 = models.CharField(
        "Statut", max_length=15,
        choices=StatutSoumission.choices, default=StatutSoumission.RECU
    )
    note_admin             = models.TextField("Note admin", blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Soumission de bien"
        verbose_name_plural = "Soumissions de biens"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"Soumission — {self.nom_complet} | {self.get_type_bien_display()} à {self.ville}"


# ─────────────────────────────────────────────────────────────────
# BROUILLONS WHATSAPP
# ─────────────────────────────────────────────────────────────────
from .models_whatsapp_draft import WhatsappImmoDraft
