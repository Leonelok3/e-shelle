"""
Njangi+ — Prêts & Remboursements
"""
from django.db import models
from django.utils import timezone


class Loan(models.Model):
    """Prêt accordé à un membre depuis le fond commun."""

    STATUS_CHOICES = [
        ("pending",   "En attente"),
        ("approved",  "Approuvé"),
        ("rejected",  "Refusé"),
        ("active",    "En cours"),
        ("completed", "Remboursé"),
        ("defaulted", "En défaut"),
    ]

    membership        = models.ForeignKey("njangi.Membership", on_delete=models.CASCADE, related_name="loans")
    session           = models.ForeignKey("njangi.Session", on_delete=models.SET_NULL, null=True, blank=True, related_name="loans_granted")
    guarantor         = models.ForeignKey(
        "njangi.Membership", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="guaranteed_loans", verbose_name="Garant"
    )

    amount_requested  = models.DecimalField(max_digits=14, decimal_places=0, verbose_name="Montant demandé (FCFA)")
    amount_approved   = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Montant approuvé (FCFA)")
    interest_rate     = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Taux d'intérêt (%/mois)")
    duration_months   = models.PositiveSmallIntegerField(verbose_name="Durée (mois)")
    purpose           = models.TextField(blank=True, verbose_name="Objet du prêt")

    # Calendrier
    requested_at  = models.DateTimeField(auto_now_add=True)
    approved_at   = models.DateTimeField(null=True, blank=True)
    disbursed_at  = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True, verbose_name="Remboursé le")
    due_date      = models.DateField(null=True, blank=True, verbose_name="Date d'échéance")

    # Montants calculés à l'approbation
    total_interest = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Intérêts totaux (FCFA)")
    total_due      = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Total à rembourser (FCFA)")
    total_repaid   = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Total remboursé (FCFA)")

    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="njangi_loans_reviewed"
    )
    rejection_reason = models.TextField(blank=True)

    payment_method  = models.CharField(max_length=20, blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Prêt"
        verbose_name_plural = "Prêts"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.membership.user} — {self.formatted_amount} ({self.get_status_display()})"

    # ── Propriétés ────────────────────────────────────────────────────────────

    @property
    def formatted_amount(self):
        amt = int(self.amount_approved or self.amount_requested)
        return f"{amt:,}".replace(",", " ") + " FCFA"

    @property
    def balance_remaining(self):
        return max(0, self.total_due - self.total_repaid)

    @property
    def is_overdue(self):
        if self.status != "active" or not self.due_date:
            return False
        return timezone.now().date() > self.due_date

    @property
    def monthly_payment(self):
        """Mensualité de remboursement (amortissement linéaire)."""
        if not self.duration_months:
            return 0
        return int(self.total_due / self.duration_months)

    @property
    def repayment_progress_pct(self):
        if not self.total_due:
            return 0
        return min(100, int(self.total_repaid / self.total_due * 100))

    # ── Méthodes ──────────────────────────────────────────────────────────────

    def compute_totals(self):
        """Calcule intérêts et total à rembourser (méthode simple — intérêts sur capital initial)."""
        principal = self.amount_approved or self.amount_requested
        self.total_interest = int(principal * self.interest_rate / 100 * self.duration_months)
        self.total_due = int(principal) + self.total_interest

    def approve(self, reviewer, amount=None):
        """Approuve le prêt et prépare le décaissement."""
        from dateutil.relativedelta import relativedelta
        self.amount_approved = amount or self.amount_requested
        self.interest_rate   = self.membership.group.fund_loan_rate
        self.compute_totals()
        self.approved_at = timezone.now()
        self.status      = "approved"
        self.reviewed_by = reviewer
        self.save()

    def disburse(self, user=None):
        """Décaisse le prêt : met à jour le fond commun."""
        from dateutil.relativedelta import relativedelta
        from njangi.models.fund import FundTransaction
        from njangi.models.session import Session

        self.disbursed_at = timezone.now()
        self.due_date     = (self.disbursed_at + relativedelta(months=self.duration_months)).date()
        self.status       = "active"
        
        current_session = Session.objects.filter(group=self.membership.group, status="in_progress").first()
        if current_session:
            self.session = current_session

        self.save()

        FundTransaction.objects.create(
            group=self.membership.group,
            type="loan_out",
            amount=self.amount_approved,
            description=f"Prêt décaissé — {self.membership.user}",
            reference_loan=self,
            reference_session=self.session,
            created_by=user,
        )

    def reject(self, reviewer, reason=""):
        self.status = "rejected"
        self.reviewed_by = reviewer
        self.rejection_reason = reason
        self.reviewed_by = reviewer
        self.save()

    def mark_defaulted(self):
        """Marque le prêt en défaut si échu et non remboursé."""
        if self.status == "active" and self.is_overdue:
            self.status = "defaulted"
            self.save(update_fields=["status"])

    def check_completion(self):
        """Clôture le prêt si entièrement remboursé."""
        if self.total_repaid >= self.total_due:
            self.status = "completed"
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at"])


class LoanRepayment(models.Model):
    """Paiement partiel ou total d'un prêt."""

    PAYMENT_METHOD_CHOICES = [
        ("mtn_momo",    "MTN Mobile Money"),
        ("orange_money","Orange Money"),
        ("cash",        "Espèces"),
        ("transfer",    "Virement"),
    ]

    loan           = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    amount_paid    = models.DecimalField(max_digits=14, decimal_places=0, verbose_name="Montant payé (FCFA)")
    principal_part = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Part capital (FCFA)")
    interest_part  = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Part intérêts (FCFA)")
    balance_after  = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Reste dû après (FCFA)")

    paid_at         = models.DateTimeField(auto_now_add=True)
    payment_method  = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True)
    notes           = models.TextField(blank=True)
    recorded_by     = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="njangi_repayments_recorded"
    )

    class Meta:
        verbose_name = "Remboursement"
        verbose_name_plural = "Remboursements"
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.loan.membership.user} — {int(self.amount_paid):,} FCFA ({self.paid_at:%d/%m/%Y})"

    def save(self, *args, **kwargs):
        """Répartit le paiement entre capital et intérêts, met à jour le prêt."""
        from njangi.models.fund import FundTransaction

        is_new = self.pk is None

        # Répartition simple : intérêts d'abord, puis capital
        if is_new:
            interest_remaining = max(0, self.loan.total_interest - sum(
                r.interest_part for r in self.loan.repayments.all()
            ))
            self.interest_part  = min(self.amount_paid, interest_remaining)
            self.principal_part = self.amount_paid - self.interest_part
            self.balance_after  = max(0, self.loan.balance_remaining - self.amount_paid)

        super().save(*args, **kwargs)

        if is_new:
            # Mise à jour du prêt
            self.loan.total_repaid += self.amount_paid
            self.loan.save(update_fields=["total_repaid"])
            self.loan.check_completion()

            # Audit trail fond commun
            FundTransaction.objects.create(
                group=self.loan.membership.group,
                type="repayment",
                amount=self.amount_paid,
                description=f"Remboursement prêt — {self.loan.membership.user}",
                reference_loan=self.loan,
                created_by=self.recorded_by,
            )
            if self.interest_part > 0:
                FundTransaction.objects.create(
                    group=self.loan.membership.group,
                    type="interest_in",
                    amount=self.interest_part,
                    description=f"Intérêts prêt — {self.loan.membership.user}",
                    reference_loan=self.loan,
                    created_by=self.recorded_by,
                )
