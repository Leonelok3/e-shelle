from django.conf import settings
from django.db import models


class ContactWhatsApp(models.Model):
    """Contact WhatsApp importe avec autorisation explicite."""

    SOURCE_CSV = "csv"
    SOURCE_EXCEL = "excel"
    SOURCE_MANUEL = "manuel"
    SOURCE_API = "api"

    SOURCES = [
        (SOURCE_CSV, "CSV"),
        (SOURCE_EXCEL, "Excel"),
        (SOURCE_MANUEL, "Manuel"),
        (SOURCE_API, "API"),
    ]

    nom = models.CharField(max_length=180, blank=True)
    numero = models.CharField(max_length=30, unique=True, db_index=True)
    ville = models.CharField(max_length=120, blank=True)
    groupe = models.CharField(max_length=180, blank=True)
    source = models.CharField(max_length=20, choices=SOURCES, default=SOURCE_API)
    consentement_confirme = models.BooleanField(default=False)
    consentement_source = models.CharField(max_length=80, blank=True)
    consentement_le = models.DateTimeField(null=True, blank=True)
    desinscrit = models.BooleanField(default=False)
    desinscrit_le = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    importe_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "Contact WhatsApp autorise"
        verbose_name_plural = "Contacts WhatsApp autorises"

    def __str__(self):
        return self.nom or self.numero


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
    destinataires_contacts = models.ManyToManyField(
        ContactWhatsApp,
        blank=True,
        related_name="campagnes_whatsapp",
        help_text="Contacts WhatsApp selectionnes manuellement pour cette campagne.",
    )

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


class WhatsAppTestSend(models.Model):
    """Delivery receipts for individual tests, excluded from campaign recipients."""

    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE, related_name="tests_envoi")
    numero = models.CharField(max_length=20)
    statut = models.CharField(max_length=20, default="en_attente")
    whatsapp_message_id = models.CharField(max_length=200, blank=True, db_index=True)
    erreur = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-cree_le"]


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

class OutreachLog(models.Model):
    """Historique transversal des contacts marketing par email ou WhatsApp."""

    CANAL_WHATSAPP = "whatsapp"
    CANAL_EMAIL = "email"
    CANAUX = [(CANAL_WHATSAPP, "WhatsApp"), (CANAL_EMAIL, "Email")]

    canal = models.CharField(max_length=20, choices=CANAUX)
    identifiant = models.CharField(max_length=320, db_index=True)
    campagne = models.ForeignKey(Campagne, null=True, blank=True, on_delete=models.SET_NULL, related_name="outreach_logs")
    message_envoi = models.OneToOneField(MessageEnvoi, null=True, blank=True, on_delete=models.SET_NULL, related_name="outreach_log")
    statut = models.CharField(max_length=30, default="envoye")
    sujet = models.CharField(max_length=255, blank=True)
    envoye_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-envoye_le"]
        indexes = [models.Index(fields=["canal", "identifiant", "envoye_le"])]

    def __str__(self):
        return f"{self.canal}: {self.identifiant}"


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


class ConversationWhatsApp(models.Model):
    """Fil de discussion bidirectionnel avec un prospect/client WhatsApp."""

    STATUT_NOUVEAU = "nouveau"
    STATUT_EN_COURS = "en_cours"
    STATUT_INTERESSE = "interesse"
    STATUT_QUALIFIE = "qualifie"
    STATUT_CONVERTI = "converti"
    STATUT_FERME = "ferme"

    STATUTS = [
        (STATUT_NOUVEAU, "Nouveau"),
        (STATUT_EN_COURS, "En cours"),
        (STATUT_INTERESSE, "🔥 Intéressé"),
        (STATUT_QUALIFIE, "⭐ Qualifié"),
        (STATUT_CONVERTI, "✅ Converti / Vendu"),
        (STATUT_FERME, "Archivé / Fermé"),
    ]

    PRIORITE_NORMALE = "normale"
    PRIORITE_HAUTE = "haute"
    PRIORITE_URGENTE = "urgente"

    PRIORITES = [
        (PRIORITE_NORMALE, "Normale"),
        (PRIORITE_HAUTE, "Haute"),
        (PRIORITE_URGENTE, "Urgente"),
    ]

    contact = models.ForeignKey(
        ContactWhatsApp,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    statut = models.CharField(max_length=20, choices=STATUTS, default=STATUT_NOUVEAU, db_index=True)
    priorite = models.CharField(max_length=20, choices=PRIORITES, default=PRIORITE_NORMALE, db_index=True)
    dernier_message_apercu = models.TextField(blank=True)
    dernier_message_le = models.DateTimeField(null=True, blank=True, db_index=True)
    non_lus_count = models.PositiveIntegerField(default=0)

    commercial_prospect = models.ForeignKey(
        "commercial_agent.ProspectBusiness",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations_whatsapp",
    )
    assigne_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations_whatsapp_assignees",
    )
    derniere_campagne = models.ForeignKey(
        Campagne,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations_initiees",
    )
    notes = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-dernier_message_le", "-mis_a_jour_le"]
        verbose_name = "Conversation WhatsApp"
        verbose_name_plural = "Conversations WhatsApp"

    def __str__(self):
        return f"Chat avec {self.contact}"

    @property
    def a_des_non_lus(self):
        return self.non_lus_count > 0


class MessageWhatsApp(models.Model):
    """Message individuel echange dans une conversation WhatsApp (entrant ou sortant)."""

    DIRECTION_ENTRANT = "entrant"
    DIRECTION_SORTANT = "sortant"

    DIRECTIONS = [
        (DIRECTION_ENTRANT, "Entrant (Prospect)"),
        (DIRECTION_SORTANT, "Sortant (E-Shelle)"),
    ]

    STATUT_EN_ATTENTE = "en_attente"
    STATUT_ENVOYE = "envoye"
    STATUT_LIVRE = "livre"
    STATUT_LU = "lu"
    STATUT_RECU = "recu"
    STATUT_ECHEC = "echec"

    STATUTS = [
        (STATUT_EN_ATTENTE, "En attente"),
        (STATUT_ENVOYE, "Envoye"),
        (STATUT_LIVRE, "Livre"),
        (STATUT_LU, "Lu"),
        (STATUT_RECU, "Recu"),
        (STATUT_ECHEC, "Echec"),
    ]

    conversation = models.ForeignKey(
        ConversationWhatsApp,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    direction = models.CharField(max_length=10, choices=DIRECTIONS, default=DIRECTION_ENTRANT, db_index=True)
    texte = models.TextField(blank=True)
    whatsapp_msg_id = models.CharField(max_length=120, blank=True, db_index=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default=STATUT_RECU)

    media_type = models.CharField(max_length=30, blank=True)
    media_url = models.TextField(blank=True)

    envoye_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages_whatsapp_envoyes",
    )
    campagne = models.ForeignKey(
        Campagne,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages_inbox",
    )
    cree_le = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["cree_le"]
        verbose_name = "Message WhatsApp (Chat)"
        verbose_name_plural = "Messages WhatsApp (Chats)"

    def __str__(self):
        dir_label = "<-" if self.direction == self.DIRECTION_ENTRANT else "->"
        return f"{dir_label} {self.conversation.contact.numero}: {self.texte[:40]}"
