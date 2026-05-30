from django.conf import settings
from django.db import models


class Campagne(models.Model):
    """Campagne d'envoi WhatsApp vers les utilisateurs E-Shelle."""

    STATUT_BROUILLON = "brouillon"
    STATUT_VALIDEE = "validee"
    STATUT_EN_COURS = "en_cours"
    STATUT_TERMINEE = "terminee"
    STATUT_ANNULEE = "annulee"

    STATUTS = [
        (STATUT_BROUILLON, "Brouillon"),
        (STATUT_VALIDEE, "Validee"),
        (STATUT_EN_COURS, "En cours"),
        (STATUT_TERMINEE, "Terminee"),
        (STATUT_ANNULEE, "Annulee"),
    ]

    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    message_template = models.TextField(
        help_text="Message a envoyer. Utilise {{prenom}} pour personnaliser."
    )
    statut = models.CharField(max_length=20, choices=STATUTS, default=STATUT_BROUILLON)

    filtre_role = models.CharField(max_length=50, blank=True, help_text="ex: vendeur, acheteur, tous")
    filtre_ville = models.CharField(max_length=100, blank=True)
    filtre_date_inscription_depuis = models.DateField(null=True, blank=True)

    total_destinataires = models.IntegerField(default=0)
    total_envoyes = models.IntegerField(default=0)
    total_livres = models.IntegerField(default=0)
    total_lus = models.IntegerField(default=0)
    total_echecs = models.IntegerField(default=0)

    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    lance_le = models.DateTimeField(null=True, blank=True)
    termine_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "Campagne WhatsApp"
        verbose_name_plural = "Campagnes WhatsApp"

    def __str__(self):
        return self.nom

    @property
    def taux_progression(self):
        if not self.total_destinataires:
            return 0
        return round((self.total_envoyes + self.total_echecs) * 100 / self.total_destinataires)


class MessageEnvoi(models.Model):
    """Message personnalise envoye dans une campagne."""

    STATUT_EN_ATTENTE = "en_attente"
    STATUT_ENVOYE = "envoye"
    STATUT_LIVRE = "livre"
    STATUT_LU = "lu"
    STATUT_ECHEC = "echec"

    STATUTS = [
        (STATUT_EN_ATTENTE, "En attente"),
        (STATUT_ENVOYE, "Envoye"),
        (STATUT_LIVRE, "Livre"),
        (STATUT_LU, "Lu"),
        (STATUT_ECHEC, "Echec"),
    ]

    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    commercial_prospect = models.ForeignKey(
        "commercial_agent.ProspectBusiness",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages_whatsapp",
    )
    destinataire_nom = models.CharField(max_length=180, blank=True)
    numero_whatsapp = models.CharField(max_length=20)
    message_final = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUTS, default=STATUT_EN_ATTENTE)
    whatsapp_message_id = models.CharField(max_length=100, blank=True, db_index=True)
    erreur = models.TextField(blank=True)
    envoye_le = models.DateTimeField(null=True, blank=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-mis_a_jour_le"]
        verbose_name = "Message WhatsApp envoye"
        verbose_name_plural = "Messages WhatsApp envoyes"

    def __str__(self):
        return f"{self.numero_whatsapp} - {self.get_statut_display()}"

    @property
    def destinataire_label(self):
        if self.user_id:
            return self.user.get_full_name() or self.user.username
        if self.destinataire_nom:
            return self.destinataire_nom
        if self.commercial_prospect_id:
            return self.commercial_prospect.nom
        return self.numero_whatsapp


class TemplateWhatsApp(models.Model):
    """Templates approuves Meta (HSM)."""

    nom = models.CharField(max_length=100)
    langue = models.CharField(max_length=10, default="fr")
    contenu_preview = models.TextField()
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nom", "langue"]
        verbose_name = "Template WhatsApp"
        verbose_name_plural = "Templates WhatsApp"

    def __str__(self):
        return f"{self.nom} ({self.langue})"
