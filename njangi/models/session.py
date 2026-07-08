"""
Njangi+ — Modèles Séance & Cotisation
"""
from django.db import models
from django.utils import timezone


class Session(models.Model):
    """Séance de tontine — réunion périodique du groupe."""

    STATUS_CHOICES = [
        ("planned",    "Planifiée"),
        ("in_progress","En cours"),
        ("completed",  "Clôturée"),
        ("cancelled",  "Annulée"),
    ]

    group          = models.ForeignKey("njangi.Group", on_delete=models.CASCADE, related_name="sessions")
    session_number = models.PositiveIntegerField(verbose_name="Numéro de séance")
    cycle          = models.PositiveIntegerField(default=1, verbose_name="Cycle")
    date           = models.DateField(verbose_name="Date de la séance")
    beneficiary    = models.ForeignKey(
        "njangi.Membership", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sessions_as_beneficiary",
        verbose_name="Bénéficiaire de la main"
    )

    # Montants
    total_collected  = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Total collecté (FCFA)")
    hand_amount      = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Main versée (FCFA)")
    penalties_collected = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Pénalités collectées (FCFA)")

    status     = models.CharField(max_length=15, choices=STATUS_CHOICES, default="planned")
    notes      = models.TextField(blank=True, verbose_name="Notes / PV de séance")
    opened_at  = models.DateTimeField(null=True, blank=True)
    closed_at  = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL, null=True,
        related_name="njangi_sessions_created"
    )

    class Meta:
        verbose_name = "Séance"
        verbose_name_plural = "Séances"
        ordering = ["-date", "-session_number"]
        unique_together = ("group", "session_number", "cycle")

    def __str__(self):
        return f"{self.group.name} — Séance #{self.session_number} ({self.date})"

    def open(self, user):
        self.status = "in_progress"
        self.opened_at = timezone.now()
        self.created_by = user
        self.save(update_fields=["status", "opened_at", "created_by"])

    def close(self, user):
        """Clôture la séance : calcule totaux et verse la main."""
        from njangi.models.fund import FundTransaction
        contributions = self.contributions.filter(status="paid")
        self.total_collected = sum(c.amount_paid for c in contributions)
        self.hand_amount = self.total_collected
        self.closed_at = timezone.now()
        self.status = "completed"
        self.save()

        # Mise à jour des totaux du bénéficiaire
        if self.beneficiary:
            self.beneficiary.total_received += self.hand_amount
            self.beneficiary.save(update_fields=["total_received"])

        # Enregistrement dans le fond commun (pénalités)
        if self.penalties_collected > 0:
            FundTransaction.objects.create(
                group=self.group,
                type="penalty_in",
                amount=self.penalties_collected,
                description=f"Pénalités séance #{self.session_number}",
                created_by=user,
            )

    @property
    def attendance_rate(self):
        total = self.contributions.count()
        paid = self.contributions.filter(status="paid").count()
        return round(paid / total * 100) if total else 0

    @property
    def formatted_hand(self):
        return f"{int(self.hand_amount):,}".replace(",", " ") + " FCFA"


class Contribution(models.Model):
    """Cotisation d'un membre à une séance."""

    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("paid",    "Payée"),
        ("late",    "En retard"),
        ("partial", "Partielle"),
        ("excused", "Excusée"),
    ]
    PAYMENT_METHOD_CHOICES = [
        ("mtn_momo",    "MTN Mobile Money"),
        ("orange_money","Orange Money"),
        ("cash",        "Espèces"),
        ("transfer",    "Virement"),
    ]

    membership = models.ForeignKey("njangi.Membership", on_delete=models.CASCADE, related_name="contributions")
    session    = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="contributions")

    amount_due  = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Montant dû (FCFA)")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Montant payé (FCFA)")

    paid_at           = models.DateTimeField(null=True, blank=True)
    payment_method    = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    transaction_ref   = models.CharField(max_length=100, blank=True, verbose_name="Référence transaction")

    is_late       = models.BooleanField(default=False)
    days_late     = models.PositiveSmallIntegerField(default=0)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Pénalité (FCFA)")
    penalty_paid  = models.BooleanField(default=False)

    PRESENCE_CHOICES = [
        ("present", "Présent"),
        ("absent",  "Absent"),
        ("excused", "Absence Signalée"),
    ]
    presence = models.CharField(
        max_length=10,
        choices=PRESENCE_CHOICES,
        default="present",
        verbose_name="Présence"
    )

    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="njangi_contributions_recorded"
    )

    class Meta:
        verbose_name = "Cotisation"
        verbose_name_plural = "Cotisations"
        unique_together = ("membership", "session")
        ordering = ["-session__date"]

    def __str__(self):
        return f"{self.membership.user} — {self.session} ({self.get_status_display()})"

    def mark_paid(self, amount, method, ref="", user=None):
        from django.utils import timezone
        self.amount_paid = amount
        self.payment_method = method
        self.transaction_ref = ref
        self.paid_at = timezone.now()
        self.status = "paid" if amount >= self.amount_due else "partial"
        self.recorded_by = user
        self.save()

        # Mettre à jour les totaux du membre
        self.membership.total_contributed += amount
        self.membership.save(update_fields=["total_contributed"])

    def toggle_paid(self, user=None):
        from django.utils import timezone
        if self.status == "paid":
            # Repasser en attente
            amount_to_subtract = self.amount_paid
            self.amount_paid = 0
            self.payment_method = ""
            self.transaction_ref = ""
            self.paid_at = None
            self.status = "pending"
            self.recorded_by = None
            self.save()
            
            # Mettre a jour les totaux du membre
            self.membership.total_contributed = max(0, self.membership.total_contributed - amount_to_subtract)
            self.membership.save(update_fields=["total_contributed"])
        else:
            # Marquer comme payee
            amount_to_add = self.amount_due
            self.amount_paid = amount_to_add
            self.payment_method = "cash"
            self.transaction_ref = "Valide par le bureau"
            self.paid_at = timezone.now()
            self.status = "paid"
            self.recorded_by = user
            self.save()
            
            # Mettre a jour les totaux du membre
            self.membership.total_contributed += amount_to_add
            self.membership.save(update_fields=["total_contributed"])

    @property
    def balance_due(self):
        return self.amount_due - self.amount_paid

    @property
    def formatted_amount_due(self):
        return f"{int(self.amount_due):,}".replace(",", " ") + " FCFA"
