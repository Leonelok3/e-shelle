from django.conf import settings
from django.db import models
from django.utils import timezone


class ProspectBusiness(models.Model):
    """Prospect commercial suivi par l'agent IA."""

    class Source(models.TextChoices):
        MANUEL = "manuel", "Manuel"
        BUSINESS_PROFILE = "business_profile", "Fiche business"
        USER = "user", "Utilisateur"
        IMPORT = "import", "Import"
        DEMO = "demo", "Demo"

    class Statut(models.TextChoices):
        NOUVEAU = "nouveau", "Nouveau"
        QUALIFIE = "qualifie", "Qualifie"
        CONTACTE = "contacte", "Contacte"
        INTERESSE = "interesse", "Interesse"
        NEGOCIATION = "negociation", "Negociation"
        PAYE = "paye", "Paye"
        PERDU = "perdu", "Perdu"
        A_RELANCER = "a_relancer", "A relancer"

    class Priorite(models.TextChoices):
        BASSE = "basse", "Basse"
        NORMALE = "normale", "Normale"
        HAUTE = "haute", "Haute"
        URGENTE = "urgente", "Urgente"

    nom = models.CharField(max_length=180)
    module = models.CharField(max_length=40, blank=True, db_index=True)
    ville = models.CharField(max_length=100, blank=True)
    quartier = models.CharField(max_length=120, blank=True)
    telephone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    responsable = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)

    source = models.CharField(max_length=30, choices=Source.choices, default=Source.MANUEL)
    statut = models.CharField(max_length=30, choices=Statut.choices, default=Statut.NOUVEAU, db_index=True)
    priorite = models.CharField(max_length=20, choices=Priorite.choices, default=Priorite.NORMALE, db_index=True)
    score = models.PositiveSmallIntegerField(default=0)
    montant_potentiel_xaf = models.PositiveIntegerField(default=0)
    plan_recommande = models.CharField(max_length=40, blank=True)
    prochain_contact = models.DateField(null=True, blank=True)
    dernier_contact = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    business_profile = models.ForeignKey(
        "business.BusinessProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commercial_prospects",
    )
    assigne_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects_commerciaux",
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects_crees",
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score", "prochain_contact", "-cree_le"]
        indexes = [
            models.Index(fields=["statut", "priorite"]),
            models.Index(fields=["module", "ville"]),
        ]
        verbose_name = "Prospect business"
        verbose_name_plural = "Prospects business"

    def __str__(self):
        return self.nom

    @property
    def contact_whatsapp(self):
        return self.whatsapp or self.telephone

    @property
    def is_due(self):
        return bool(self.prochain_contact and self.prochain_contact <= timezone.localdate())


class CampagneProspection(models.Model):
    """Campagne commerciale pour vendre les offres E-Shelle."""

    class Statut(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        ACTIVE = "active", "Active"
        TERMINEE = "terminee", "Terminee"
        PAUSE = "pause", "Pause"

    nom = models.CharField(max_length=180)
    objectif = models.TextField(blank=True)
    module_cible = models.CharField(max_length=40, blank=True)
    ville_cible = models.CharField(max_length=100, blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    prospects = models.ManyToManyField(ProspectBusiness, blank=True, related_name="campagnes_prospection")
    message_base = models.TextField(blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    cree_le = models.DateTimeField(auto_now_add=True)
    lance_le = models.DateTimeField(null=True, blank=True)
    termine_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "Campagne de prospection"
        verbose_name_plural = "Campagnes de prospection"

    def __str__(self):
        return self.nom


class ScriptCommercial(models.Model):
    """Script IA reutilisable pour WhatsApp, appel ou Facebook."""

    class Canal(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        APPEL = "appel", "Appel"
        FACEBOOK = "facebook", "Facebook"
        EMAIL = "email", "Email"

    nom = models.CharField(max_length=160)
    canal = models.CharField(max_length=20, choices=Canal.choices, default=Canal.WHATSAPP)
    module = models.CharField(max_length=40, blank=True)
    contenu = models.TextField()
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["canal", "module", "nom"]
        verbose_name = "Script commercial"
        verbose_name_plural = "Scripts commerciaux"

    def __str__(self):
        return f"{self.nom} ({self.get_canal_display()})"


class RelanceProspect(models.Model):
    """Historique des actions commerciales."""

    class TypeAction(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        APPEL = "appel", "Appel"
        VISITE = "visite", "Visite terrain"
        NOTE = "note", "Note"
        PAIEMENT = "paiement", "Paiement"

    class Resultat(models.TextChoices):
        A_FAIRE = "a_faire", "A faire"
        ENVOYE = "envoye", "Envoye"
        REPONSE = "reponse", "Reponse recue"
        INTERESSE = "interesse", "Interesse"
        REFUS = "refus", "Refus"
        PAYE = "paye", "Paye"

    prospect = models.ForeignKey(ProspectBusiness, on_delete=models.CASCADE, related_name="relances")
    campagne = models.ForeignKey(CampagneProspection, null=True, blank=True, on_delete=models.SET_NULL, related_name="relances")
    type_action = models.CharField(max_length=20, choices=TypeAction.choices, default=TypeAction.WHATSAPP)
    resultat = models.CharField(max_length=20, choices=Resultat.choices, default=Resultat.A_FAIRE)
    message = models.TextField(blank=True)
    montant_xaf = models.PositiveIntegerField(default=0)
    effectue_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    prochaine_relance = models.DateField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "Relance prospect"
        verbose_name_plural = "Relances prospects"

    def __str__(self):
        return f"{self.prospect} - {self.get_type_action_display()}"
