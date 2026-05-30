from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from tchaslucpay.accounts.models import ClientProfile, CollecteurProfile
from tchaslucpay.transactions.models import Transaction, TransactionStatus, TransactionType


@dataclass
class RiskProfile:
    level: str
    label: str
    css_class: str
    score: int
    reasons: list[str]


def _today_bounds():
    now = timezone.localtime(timezone.now())
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def score_client_risk(client):
    today_start, _ = _today_bounds()
    reasons = []
    score = 0

    if not client.national_id:
        score += 35
        reasons.append("CNI manquante")
    if not client.national_id_expiry:
        score += 25
        reasons.append("Date expiration CNI manquante")
    elif client.national_id_expiry <= timezone.localdate():
        score += 50
        reasons.append("CNI expiree")

    transactions = Transaction.objects.filter(account=client.user, status=TransactionStatus.POSTED)
    today_count = transactions.filter(created_at__gte=today_start).count()
    if today_count >= 5:
        score += 25
        reasons.append("Nombre eleve d'operations aujourd'hui")

    last_tx = transactions.order_by("-created_at").first()
    if last_tx is None:
        score += 15
        reasons.append("Aucune operation historique")
    else:
        inactivity_days = (timezone.now() - last_tx.created_at).days
        if inactivity_days >= 14:
            score += 20
            reasons.append(f"Inactif depuis {inactivity_days} jours")

    if client.solde < Decimal("1000"):
        score += 10
        reasons.append("Solde tres faible")

    if score >= 60:
        return RiskProfile("eleve", "Risque eleve", "danger", min(score, 100), reasons)
    if score >= 30:
        return RiskProfile("moyen", "Risque moyen", "warning", score, reasons)
    return RiskProfile("faible", "Risque faible", "success", score, reasons or ["Profil regulier"])


def enrich_clients_with_risk(clients):
    enriched = list(clients)
    for client in enriched:
        client.risk = score_client_risk(client)
    return enriched


def build_anti_fraud_alerts():
    today_start, now = _today_bounds()
    alerts = []

    clients = ClientProfile.objects.select_related("user", "trusted_collecteur__user")
    for client in clients:
        risk = score_client_risk(client)
        if risk.level == "eleve":
            alerts.append({
                "level": "danger",
                "title": f"Client a verifier: {client.user.get_full_name() or client.user.username}",
                "message": ", ".join(risk.reasons),
                "agent": "Anti-fraude",
            })

    repeated = (
        Transaction.objects.filter(status=TransactionStatus.POSTED, created_at__gte=today_start)
        .values("account__username", "account__first_name", "account__last_name")
        .annotate(nb=Count("id"), total=Sum("amount"))
        .filter(nb__gte=4)
    )
    for item in repeated:
        name = f"{item['account__first_name']} {item['account__last_name']}".strip() or item["account__username"]
        alerts.append({
            "level": "warning",
            "title": f"Operations multiples: {name}",
            "message": f"{item['nb']} operations aujourd'hui pour {item['total'] or 0:,.0f} XAF.".replace(",", " "),
            "agent": "Anti-fraude",
        })

    small_deposits = Transaction.objects.filter(
        status=TransactionStatus.POSTED,
        transaction_type=TransactionType.DEPOSIT,
        created_at__gte=today_start,
        amount__lt=Decimal("1000"),
    ).count()
    if small_deposits:
        alerts.append({
            "level": "warning",
            "title": "Depots proches du minimum",
            "message": f"{small_deposits} depot(s) entre 500 et 999 XAF aujourd'hui.",
            "agent": "Anti-fraude",
        })

    inactive_collectors = CollecteurProfile.objects.filter(is_active=True).exclude(
        user__tchaslucpay_collected_transactions__created_at__gte=today_start
    )
    for collecteur in inactive_collectors[:5]:
        alerts.append({
            "level": "info",
            "title": f"Collecteur sans depot: {collecteur.user.get_full_name() or collecteur.user.username}",
            "message": f"Aucune collecte enregistree aujourd'hui sur la zone {collecteur.zone}.",
            "agent": "Superviseur",
        })

    if not alerts:
        alerts.append({
            "level": "success",
            "title": "Aucune anomalie critique",
            "message": "Les operations du jour sont coherentes avec les regles terrain.",
            "agent": "Anti-fraude",
        })
    return alerts[:12]


def build_supervisor_summary():
    today_start, _ = _today_bounds()
    tx_today = Transaction.objects.filter(status=TransactionStatus.POSTED, created_at__gte=today_start)
    deposits = tx_today.filter(transaction_type=TransactionType.DEPOSIT)
    by_collector = (
        deposits.values("collector__username", "collector__first_name", "collector__last_name")
        .annotate(total=Sum("amount"), nb=Count("id"))
        .order_by("-total")
    )
    best = by_collector.first()
    best_name = ""
    if best:
        best_name = f"{best['collector__first_name']} {best['collector__last_name']}".strip() or best["collector__username"]

    return {
        "date": timezone.localdate(),
        "total_collecte": deposits.aggregate(total=Sum("amount"))["total"] or Decimal("0"),
        "nb_depots": deposits.count(),
        "nb_clients_servis": deposits.values("account").distinct().count(),
        "montant_moyen": deposits.aggregate(avg=Avg("amount"))["avg"] or Decimal("0"),
        "meilleur_collecteur": best_name or "Aucun depot",
        "classement_collecteurs": by_collector[:5],
    }


def build_collector_coach(collecteur):
    today_start, _ = _today_bounds()
    clients = ClientProfile.objects.filter(trusted_collecteur=collecteur).select_related("user")
    suggestions = []
    priority_clients = []

    for client in clients:
        last_tx = Transaction.objects.filter(account=client.user, status=TransactionStatus.POSTED).order_by("-created_at").first()
        risk = score_client_risk(client)
        client.risk = risk
        days = (timezone.now() - last_tx.created_at).days if last_tx else 999
        if days >= 7 or risk.level != "faible":
            priority_clients.append(client)

    today_total = (
        Transaction.objects.filter(
            collector=collecteur.user,
            status=TransactionStatus.POSTED,
            transaction_type=TransactionType.DEPOSIT,
            created_at__gte=today_start,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    if priority_clients:
        suggestions.append("Commencez par les clients inactifs ou a risque moyen/eleve.")
    if today_total < Decimal("100000"):
        suggestions.append("Objectif terrain: viser au moins 100 000 XAF de depots aujourd'hui.")
    suggestions.append("Rappel: aucun retrait terrain. Orientez le client vers l'agence.")

    return {
        "today_total": today_total,
        "priority_clients": priority_clients[:6],
        "suggestions": suggestions,
    }


def build_agency_report():
    return {
        "summary": build_supervisor_summary(),
        "alerts": build_anti_fraud_alerts(),
        "clients": enrich_clients_with_risk(
            ClientProfile.objects.select_related("user", "trusted_collecteur__user").order_by("user__first_name", "user__last_name")[:25]
        ),
    }
