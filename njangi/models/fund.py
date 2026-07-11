"""
Njangi+ — Fond commun : Dépôts & Transactions
"""
from django.db import models
from django.utils import timezone


class FundDeposit(models.Model):
    """Dépôt volontaire d'un membre dans le fond commun pour générer des intérêts.

    Les intérêts sont calculés UNIQUEMENT sur un mois à la fois et distribués
    proportionnellement à la part du membre dans le pool de prêts actifs.
    Le cumul des intérêts est tracé dans MemberMonthlyStatement.
    """

    STATUS_CHOICES = [
        ("active",    "Actif"),
        ("withdrawn", "Retiré"),
    ]

    membership     = models.ForeignKey("njangi.Membership", on_delete=models.CASCADE, related_name="fund_deposits")
    session        = models.ForeignKey(
        "njangi.Session", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deposits", verbose_name="Séance associée"
    )
    amount         = models.DecimalField(max_digits=14, decimal_places=0, verbose_name="Montant déposé (FCFA)")
    deposited_at   = models.DateTimeField(auto_now_add=True)
    interest_rate  = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Taux d'intérêt (%/mois)")

    # Résultats
    interest_earned = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Intérêts cumulés versés (FCFA)")
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    withdrawn_at    = models.DateTimeField(null=True, blank=True)
    withdrawn_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)

    payment_method  = models.CharField(max_length=20, blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Dépôt fond commun"
        verbose_name_plural = "Dépôts fond commun"
        ordering = ["-deposited_at"]

    def __str__(self):
        return f"{self.membership.user} — {self.formatted_amount} ({self.get_status_display()})"

    @property
    def monthly_interest_potential(self):
        """Intérêts potentiels sur 1 mois si 100% du pool est prêté."""
        return int(self.amount * self.interest_rate / 100)

    # Alias conservé pour compatibilité avec les templates existants
    @property
    def expected_interest(self):
        return self.monthly_interest_potential

    @property
    def current_interest(self):
        """Intérêts réellement gagnés ce mois-ci (depuis les relevés mensuels)."""
        from django.db.models import Sum
        from njangi.models.wallet import MemberMonthlyStatement
        result = MemberMonthlyStatement.objects.filter(
            membership=self.membership
        ).aggregate(total=Sum("interest_earned"))
        return int(result["total"] or 0)

    @property
    def formatted_amount(self):
        return f"{int(self.amount):,}".replace(",", " ") + " FCFA"

    def withdraw(self, user=None):
        """Retirer le dépôt — les intérêts cumulés viennent des relevés mensuels."""
        from django.db.models import Sum
        from njangi.models.wallet import MemberMonthlyStatement

        cumul = MemberMonthlyStatement.objects.filter(
            membership=self.membership
        ).aggregate(total=Sum("interest_earned"))
        cumul_interest = int(cumul["total"] or 0)

        self.interest_earned  = cumul_interest
        self.withdrawn_amount = int(self.amount) + cumul_interest
        self.withdrawn_at     = timezone.now()
        self.status           = "withdrawn"
        self.save()

        # Enregistrer la sortie dans le fond
        FundTransaction.objects.create(
            group=self.membership.group,
            type="deposit_out",
            amount=self.withdrawn_amount,
            description=f"Retrait dépôt + intérêts cumulés — {self.membership.user}",
            reference_deposit=self,
        )


class FundTransaction(models.Model):
    """Mouvement financier du fond commun — audit trail complet."""

    TYPE_CHOICES = [
        ("deposit_in",   "Dépôt entrant"),
        ("deposit_out",  "Retrait dépôt"),
        ("loan_out",     "Prêt accordé"),
        ("repayment",    "Remboursement prêt"),
        ("interest_in",  "Intérêts prêt reçus"),
        ("interest_out", "Intérêts dépôt versés"),
        ("penalty_in",   "Pénalités encaissées"),
        ("hand_paid",    "Main versée au bénéficiaire"),
        ("expense",      "Dépense du groupe"),
        ("adjustment",   "Ajustement manuel"),
    ]

    group       = models.ForeignKey("njangi.Group", on_delete=models.CASCADE, related_name="fund_transactions")
    type        = models.CharField(max_length=15, choices=TYPE_CHOICES)
    amount      = models.DecimalField(max_digits=14, decimal_places=0, verbose_name="Montant (FCFA)")
    # Positif = entrée fond, Négatif = sortie fond
    signed_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    balance_after = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Solde après (FCFA)")

    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    created_by  = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="njangi_fund_transactions"
    )

    # Références optionnelles
    reference_loan    = models.ForeignKey("njangi.Loan", on_delete=models.SET_NULL, null=True, blank=True)
    reference_deposit = models.ForeignKey(FundDeposit, on_delete=models.SET_NULL, null=True, blank=True)
    reference_session = models.ForeignKey("njangi.Session", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Transaction fond commun"
        verbose_name_plural = "Transactions fond commun"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.group.name} — {self.get_type_display()} {self.formatted_amount}"

    def save(self, *args, **kwargs):
        # Définir le signe automatiquement
        outgoing = {"deposit_out", "loan_out", "interest_out", "hand_paid", "expense"}
        self.signed_amount = -self.amount if self.type in outgoing else self.amount
        super().save(*args, **kwargs)

    @property
    def formatted_amount(self):
        return f"{int(self.amount):,}".replace(",", " ") + " FCFA"

    @property
    def is_credit(self):
        return self.signed_amount > 0
