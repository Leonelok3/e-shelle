from dataclasses import dataclass
from decimal import Decimal
import secrets
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

from tchaslucpay.accounts.models import ClientProfile, CollecteurProfile

from .models import AccountBalance, Transaction, TransactionStatus, TransactionType
from .signals import transaction_posted


class FinancialServiceError(Exception):
    pass


@dataclass(frozen=True)
class TransactionResult:
    transaction: Transaction
    balance: AccountBalance


def generate_trid(prefix="TX"):
    stamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:12].upper()}"


def generer_trid_unique():
    """Genere un identifiant COL unique avant insertion comptable."""
    date_part = timezone.localtime(timezone.now()).strftime("%y%m%d")
    digits = "0123456789"

    while True:
        random_part = "".join(secrets.choice(digits) for _ in range(10))
        trid = f"COL{date_part}{random_part}"
        if not Transaction.objects.filter(trid=trid).exists():
            return trid


def _signed_amount(transaction_type, amount):
    amount = Decimal(amount)
    debit_types = {TransactionType.WITHDRAWAL, TransactionType.LOAN_DISBURSEMENT, TransactionType.FEE}
    return -amount if transaction_type in debit_types else amount


def _normaliser_type_operation(type_op):
    """Convertit les libelles metier en types acceptes par le modele."""
    if type_op == "RETRAIT":
        return TransactionType.WITHDRAWAL
    if type_op in {"DEPOT", "DEPOSIT"}:
        return TransactionType.DEPOSIT
    if type_op in dict(TransactionType.choices):
        return type_op
    raise ValidationError("Type d'operation non pris en charge.")


@transaction.atomic
def creer_transaction(client_id, collecteur_id, type_op, montant, note=None):
    """Cree une transaction financiere atomique et met a jour le solde client."""
    montant = Decimal(str(montant))
    if montant <= 0:
        raise ValidationError("Le montant doit etre strictement superieur a 0.")
    if type_op == "RETRAIT":
        raise ValidationError("Retrait impossible cote collecteur : les retraits se font uniquement a l'agence.")
    if type_op in {"DEPOT", "DEPOSIT", TransactionType.DEPOSIT} and montant < Decimal("500"):
        raise ValidationError("Alerte impossible : le depot minimum est de 500 XAF.")

    # Verrouillage pessimiste du profil client pour eviter les ecritures concurrentes.
    client = ClientProfile.objects.select_for_update().select_related("user").get(pk=client_id)
    collecteur = CollecteurProfile.objects.select_related("user").get(pk=collecteur_id)

    if not hasattr(client, "solde"):
        raise ValidationError("Le champ solde est requis sur ClientProfile pour executer cette operation.")

    solde_avant = Decimal(str(client.solde))
    transaction_type = _normaliser_type_operation(type_op)

    delta = montant
    solde_apres = solde_avant + delta

    transaction_obj = Transaction.objects.create(
        trid=generer_trid_unique(),
        account=client.user,
        collector=collecteur.user,
        transaction_type=transaction_type,
        status=TransactionStatus.POSTED,
        amount=montant,
        balance_before=solde_avant,
        balance_after=solde_apres,
        description=note or "",
        posted_at=timezone.now(),
        created_by=collecteur.user,
    )

    # Le snapshot et l'ecriture Transaction sont crees avant la mutation du solde.
    client.solde = solde_apres
    client.save(update_fields=["solde"])

    transaction.on_commit(lambda: transaction_posted.send(sender=Transaction, transaction=transaction_obj))
    return transaction_obj


@transaction.atomic
def post_transaction(*, account, amount, transaction_type, created_by, collector=None, description="", external_reference="", metadata=None):
    amount = Decimal(amount)
    if amount <= 0:
        raise FinancialServiceError("Le montant doit etre strictement positif.")

    balance, _ = AccountBalance.objects.select_for_update().get_or_create(account=account)
    balance_before = balance.available_balance
    delta = _signed_amount(transaction_type, amount)
    balance_after = balance_before + delta
    if balance_after < 0:
        raise FinancialServiceError("Solde insuffisant pour cette operation.")

    AccountBalance.objects.filter(pk=balance.pk).update(available_balance=F("available_balance") + delta)
    balance.refresh_from_db()

    entry = Transaction.objects.create(
        trid=generate_trid(),
        account=account,
        collector=collector,
        transaction_type=transaction_type,
        status=TransactionStatus.POSTED,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance.available_balance,
        external_reference=external_reference,
        description=description,
        metadata=metadata or {},
        posted_at=timezone.now(),
        created_by=created_by,
    )
    transaction.on_commit(lambda: transaction_posted.send(sender=Transaction, transaction=entry))
    return TransactionResult(transaction=entry, balance=balance)


def deposit(*, account, amount, created_by, collector=None, description="Depot client", external_reference="", metadata=None):
    return post_transaction(
        account=account,
        amount=amount,
        transaction_type=TransactionType.DEPOSIT,
        created_by=created_by,
        collector=collector,
        description=description,
        external_reference=external_reference,
        metadata=metadata,
    )


def withdraw(*, account, amount, created_by, collector=None, description="Retrait client", external_reference="", metadata=None):
    return post_transaction(
        account=account,
        amount=amount,
        transaction_type=TransactionType.WITHDRAWAL,
        created_by=created_by,
        collector=collector,
        description=description,
        external_reference=external_reference,
        metadata=metadata,
    )


@transaction.atomic
def reverse_transaction(*, transaction_id, created_by, reason):
    original = Transaction.objects.select_for_update().get(pk=transaction_id)
    if original.status == TransactionStatus.REVERSED:
        raise FinancialServiceError("Cette transaction est deja annulee.")
    if original.transaction_type == TransactionType.REVERSAL:
        raise FinancialServiceError("Une ecriture d'annulation ne peut pas etre annulee.")

    opposite = -_signed_amount(original.transaction_type, original.amount)
    reversal_type = TransactionType.DEPOSIT if opposite > 0 else TransactionType.WITHDRAWAL
    result = post_transaction(
        account=original.account,
        amount=abs(opposite),
        transaction_type=reversal_type,
        created_by=created_by,
        collector=original.collector,
        description=f"Annulation: {reason}",
        external_reference=f"REV-{original.trid}",
        metadata={"reversal_of": original.trid, "reason": reason},
    )
    Transaction.objects.filter(pk=result.transaction.pk).update(
        transaction_type=TransactionType.REVERSAL,
        reversed_transaction=original,
    )
    original.status = TransactionStatus.REVERSED
    original.save(update_fields=["status"])
    result.transaction.refresh_from_db()
    return result


def get_statement_queryset(account, *, start=None, end=None):
    qs = Transaction.objects.filter(account=account).select_related("collector", "created_by")
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    return qs.order_by("created_at")


def render_statement_pdf(account, *, start=None, end=None):
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise FinancialServiceError("WeasyPrint doit etre installe pour generer les PDF.") from exc

    html = render_to_string(
        "tchaslucpay/transactions/statement.html",
        {"account": account, "transactions": get_statement_queryset(account, start=start, end=end), "start": start, "end": end},
    )
    return HTML(string=html).write_pdf()
