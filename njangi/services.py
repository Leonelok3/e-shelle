"""
Njangi+ — Services métier

InterestCalculationService  : Calcul des intérêts mensuels proportionnels
DistributionCalculator      : Calcul de la "bouffe" avec déductions automatiques
ReliabilityScoreService     : Calcul du score de fiabilité des membres
"""
import logging
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone

logger = logging.getLogger("njangi")


def _first_day(year: int, month: int) -> date:
    return date(year, month, 1)


def _last_day(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 1 — Calcul des intérêts mensuels
# ═══════════════════════════════════════════════════════════════════════════

class InterestCalculationService:
    """
    Moteur de calcul des intérêts proportionnels pour un groupe/mois.

    Algorithme :
      1. Identifier les dépôts actifs pendant le mois → pool total
      2. Identifier les prêts actifs pendant le mois → encours total
      3. Intérêts générés = Σ (loan.amount × loan.rate/100) par prêt actif
      4. Pour chaque déposant :
           pool_share = deposit / pool_total
           interest_earned = pool_share × total_interest_generated
      5. Stocker dans MemberMonthlyStatement + MonthlyGroupInterest
    """

    @classmethod
    @transaction.atomic
    def calculate_month(cls, group, year: int, month: int):
        """
        Calcule et enregistre les intérêts du mois pour un groupe.
        Retourne le MonthlyGroupInterest créé ou mis à jour.
        """
        from njangi.models.fund import FundDeposit
        from njangi.models.loan import Loan
        from njangi.models.wallet import MonthlyGroupInterest, MemberMonthlyStatement

        first = _first_day(year, month)
        last  = _last_day(year, month)

        # ── 1. Dépôts actifs ce mois ──────────────────────────────────────────
        # Un dépôt est actif ce mois si :
        #   - il a été déposé avant ou pendant le mois
        #   - et il n'a pas été retiré avant le début du mois
        active_deposits = FundDeposit.objects.filter(
            membership__group=group,
            deposited_at__date__lte=last,
        ).filter(
            Q(status="active") | Q(withdrawn_at__date__gte=first)
        ).select_related("membership__user")

        pool_total = sum(d.amount for d in active_deposits)

        # ── 2. Prêts actifs ce mois ───────────────────────────────────────────
        # Un prêt est actif ce mois si :
        #   - décaissé avant ou pendant le mois
        #   - et pas encore remboursé avant le début du mois
        active_loans = Loan.objects.filter(
            membership__group=group,
            disbursed_at__date__lte=last,
        ).filter(
            Q(status="active") |
            Q(status="completed", completed_at__date__gte=first) |
            Q(status="defaulted")
        )

        loans_outstanding = sum(l.amount_approved for l in active_loans)
        nb_active_loans   = active_loans.count()

        # ── 3. Intérêts générés ce mois ───────────────────────────────────────
        # Chaque prêt génère : montant × taux_mensuel / 100
        total_interest = sum(
            Decimal(str(loan.amount_approved)) * Decimal(str(loan.interest_rate)) / Decimal("100")
            for loan in active_loans
        )
        total_interest = int(total_interest)

        # ── 4. Enregistrement MonthlyGroupInterest ────────────────────────────
        record, _ = MonthlyGroupInterest.objects.update_or_create(
            group=group, year=year, month=month,
            defaults={
                "total_pool":               int(pool_total),
                "total_loans_outstanding":  int(loans_outstanding),
                "total_interest_generated": total_interest,
                "nb_active_loans":          nb_active_loans,
                "nb_depositors":            active_deposits.count(),
                "is_calculated":            True,
                "calculated_at":            timezone.now(),
            }
        )

        # ── 5. Répartition par déposant ───────────────────────────────────────
        # Regrouper les dépôts par membership (un membre peut avoir plusieurs dépôts)
        deposits_by_member = {}
        for deposit in active_deposits:
            mid = deposit.membership_id
            deposits_by_member[mid] = deposits_by_member.get(mid, Decimal("0")) + deposit.amount

        nb_depositors = len(deposits_by_member)

        for membership_id, deposit_amt in deposits_by_member.items():
            pool_share_pct = (
                Decimal(str(deposit_amt)) / Decimal(str(pool_total)) * 100
                if pool_total else Decimal("0")
            )
            interest_earned = int(
                Decimal(str(deposit_amt)) / Decimal(str(pool_total)) * total_interest
                if pool_total else Decimal("0")
            )
            contribution_to_loans = int(
                Decimal(str(deposit_amt)) / Decimal(str(pool_total)) * Decimal(str(loans_outstanding))
                if pool_total else Decimal("0")
            )

            # Cumulatif des mois précédents
            from njangi.models.wallet import MemberMonthlyStatement as MMS
            prev_cumul = MMS.objects.filter(
                membership_id=membership_id,
                monthly_record__year__lte=year,
            ).exclude(monthly_record=record).aggregate(
                total=Sum("interest_earned")
            )["total"] or 0

            cumulative = int(prev_cumul) + interest_earned
            wallet_balance = int(deposit_amt) + cumulative

            MemberMonthlyStatement.objects.update_or_create(
                membership_id=membership_id,
                monthly_record=record,
                defaults={
                    "deposit_balance":       int(deposit_amt),
                    "pool_share_pct":        round(float(pool_share_pct), 2),
                    "contribution_to_loans": contribution_to_loans,
                    "interest_earned":       interest_earned,
                    "cumulative_interest":   cumulative,
                    "wallet_balance":        wallet_balance,
                }
            )

        logger.info(
            f"[Njangi] Intérêts calculés — {group.name} {month:02d}/{year} | "
            f"Pool: {int(pool_total):,} FCFA | "
            f"Prêts: {nb_active_loans} | "
            f"Intérêts: {total_interest:,} FCFA | "
            f"Déposants: {nb_depositors}"
        )
        return record

    @classmethod
    def calculate_all_months(cls, group, from_date: date = None):
        """
        Recalcule tous les mois depuis from_date (ou depuis le début du groupe).
        """
        start = from_date or group.start_date
        today = date.today()

        year, month = start.year, start.month
        records = []
        while (year, month) <= (today.year, today.month):
            record = cls.calculate_month(group, year, month)
            records.append(record)
            month += 1
            if month > 12:
                month = 1
                year += 1
        return records

    @classmethod
    def get_member_evolution(cls, membership, last_n_months: int = 12):
        """
        Retourne l'évolution mensuelle des avoirs d'un membre (pour graphique).
        """
        from njangi.models.wallet import MemberMonthlyStatement
        # Django ne supporte pas l'indexation négative → on prend les N derniers en ordre décroissant puis on inverse
        statements = list(
            MemberMonthlyStatement.objects.filter(
                membership=membership
            ).select_related("monthly_record").order_by(
                "-monthly_record__year", "-monthly_record__month"
            )[:last_n_months]
        )
        statements.reverse()  # Chronologique ascendant pour les graphiques

        return [
            {
                "label":       s.period_label,
                "deposit":     int(s.deposit_balance),
                "interest":    int(s.interest_earned),
                "cumulative":  int(s.cumulative_interest),
                "wallet":      int(s.wallet_balance),
            }
            for s in statements
        ]

    @classmethod
    def simulate_next_month(cls, group):
        """
        Simule les intérêts du mois prochain sans enregistrer.
        Retourne un dict avec les projections par membre.
        """
        from njangi.models.fund import FundDeposit
        from njangi.models.loan import Loan

        today = date.today()
        # Prochain mois
        if today.month == 12:
            year, month = today.year + 1, 1
        else:
            year, month = today.year, today.month + 1

        first = _first_day(year, month)
        last  = _last_day(year, month)

        # Dépôts supposés actifs le mois prochain
        active_deposits = FundDeposit.objects.filter(
            membership__group=group, status="active"
        ).select_related("membership__user")

        pool_total = sum(d.amount for d in active_deposits)

        # Prêts supposés encore actifs
        active_loans = Loan.objects.filter(
            membership__group=group, status="active"
        )
        total_interest = sum(
            Decimal(str(l.amount_approved)) * Decimal(str(l.interest_rate)) / 100
            for l in active_loans
        )

        # Projection par déposant
        deposits_by_member = {}
        for d in active_deposits:
            mid = d.membership_id
            deposits_by_member[mid] = {
                "membership": d.membership,
                "deposit":    deposits_by_member.get(mid, {}).get("deposit", Decimal("0")) + d.amount,
            }

        projections = []
        for mid, info in deposits_by_member.items():
            deposit = info["deposit"]
            share = deposit / pool_total if pool_total else Decimal("0")
            projected_interest = int(share * total_interest)
            projections.append({
                "membership":          info["membership"],
                "deposit":             int(deposit),
                "pool_share_pct":      round(float(share * 100), 1),
                "projected_interest":  projected_interest,
            })

        return {
            "year":             year,
            "month":            month,
            "pool_total":       int(pool_total),
            "total_interest":   int(total_interest),
            "nb_active_loans":  active_loans.count(),
            "projections":      sorted(projections, key=lambda x: -x["deposit"]),
        }


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 2 — Calcul de la distribution (bouffe)
# ═══════════════════════════════════════════════════════════════════════════

class DistributionCalculator:
    """
    Calcule le montant net qu'un membre recevra lors de sa distribution (main/bouffe).

    Déductions automatiques :
      1. Fonds de base déficitaire
      2. Prêt actif en cours
      3. Pénalités impayées
      4. Cotisations en retard
    """

    @classmethod
    def preview(cls, membership, gross_amount: Decimal = None) -> dict:
        """
        Retourne le détail complet de la distribution d'un membre.

        Args:
            membership: le Membership du bénéficiaire
            gross_amount: montant brut (si None, = montant collecté de la prochaine séance)

        Returns:
            dict avec gross, deductions détaillées, net, can_receive
        """
        from njangi.models.session import Contribution

        group = membership.group

        # Montant brut
        if gross_amount is None:
            # Estimation : cotisation × nombre de membres actifs
            gross_amount = group.contribution_amount * group.member_count
        gross = int(gross_amount)

        # Les membres absents ou dont l'absence est signalee ne peuvent pas recevoir la tontine (bouffer) de la seance
        from njangi.models.session import Session
        active_session = group.sessions.filter(status="in_progress").first()
        if active_session:
            contribution = active_session.contributions.filter(membership=membership).first()
            if contribution and contribution.presence in ("absent", "excused"):
                return {
                    "membership":        membership,
                    "gross_amount":      gross,
                    "deductions":        [],
                    "total_deductions":  0,
                    "net_amount":        0,
                    "can_receive":       False,
                    "blocked":           True,
                    "blocking_reason":   "Le membre est absent (ou excusé) à cette séance et ne peut pas recevoir la distribution.",
                }

        deductions = []
        total_deductions = 0

        # ── Déduction 1 : Fonds de base déficitaire ──────────────────────────
        deficit = membership.base_fund_deficit
        if deficit > 0:
            deductions.append({
                "label":       "Fonds de base déficitaire",
                "amount":      deficit,
                "description": f"Fonds requis : {int(group.base_fund_required):,} FCFA | Actuel : {int(membership.active_deposit_balance):,} FCFA",
                "type":        "base_fund",
            })
            total_deductions += deficit

        # ── Déduction 2 : Prêt actif ──────────────────────────────────────────
        active_loan = membership.active_loan
        if active_loan:
            balance = int(active_loan.balance_remaining)
            if balance > 0:
                deductions.append({
                    "label":       "Prêt en cours",
                    "amount":      balance,
                    "description": f"Prêt de {active_loan.formatted_amount} — reste dû : {balance:,} FCFA",
                    "type":        "loan",
                })
                total_deductions += balance

        # ── Déduction 3 : Pénalités impayées ──────────────────────────────────
        penalties_unpaid = Contribution.objects.filter(
            membership=membership,
            penalty_amount__gt=0,
            penalty_paid=False,
        ).aggregate(total=Sum("penalty_amount"))["total"] or 0

        if penalties_unpaid:
            deductions.append({
                "label":       "Pénalités impayées",
                "amount":      int(penalties_unpaid),
                "description": f"Cotisations en retard — pénalités accumulées",
                "type":        "penalty",
            })
            total_deductions += int(penalties_unpaid)

        # ── Déduction 4 : Cotisations en retard ──────────────────────────────
        late_contributions = Contribution.objects.filter(
            membership=membership, status="late"
        ).aggregate(
            total=Sum("amount_due")
        )["total"] or 0

        if late_contributions:
            deductions.append({
                "label":       "Cotisations en retard",
                "amount":      int(late_contributions),
                "description": f"Montant des cotisations non réglées",
                "type":        "late_contribution",
            })
            total_deductions += int(late_contributions)

        # ── Calcul final ──────────────────────────────────────────────────────
        net = max(0, gross - total_deductions)
        can_receive = net > 0 and total_deductions < gross

        return {
            "membership":        membership,
            "gross_amount":      gross,
            "deductions":        deductions,
            "total_deductions":  total_deductions,
            "net_amount":        net,
            "can_receive":       can_receive,
            "blocked":           net <= 0,
            "blocking_reason":   "Déductions supérieures ou égales au montant brut" if net <= 0 else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 3 — Score de fiabilité
# ═══════════════════════════════════════════════════════════════════════════

class ReliabilityScoreService:
    """
    Calcule le score de fiabilité d'un membre (0-100).

    Pondérations :
      - Cotisations à l'heure :  +2 pts / séance
      - Cotisation en retard :   -5 pts
      - Cotisation absente :     -10 pts
      - Prêt remboursé à temps : +5 pts
      - Prêt en défaut :         -20 pts
      - Prêt en retard actif :   -10 pts
    Score de base = 100, minimum = 0.
    """

    @classmethod
    def compute(cls, membership) -> int:
        from njangi.models.session import Contribution
        from njangi.models.loan import Loan

        score = 100

        contributions = Contribution.objects.filter(membership=membership)
        for c in contributions:
            if c.status == "paid" and not c.is_late:
                score += 2
            elif c.status in ("late", "partial"):
                score -= 5
            elif c.status == "pending":
                # Si la séance est passée et toujours pending → absent
                if c.session.date < date.today():
                    score -= 10

        loans = Loan.objects.filter(membership=membership)
        for loan in loans:
            if loan.status == "completed":
                score += 5
            elif loan.status == "defaulted":
                score -= 20
            elif loan.status == "active" and loan.is_overdue:
                score -= 10

        return max(0, min(100, score))

    @classmethod
    def update(cls, membership) -> int:
        """Calcule et sauvegarde le score."""
        score = cls.compute(membership)
        membership.reliability_score = score
        membership.save(update_fields=["reliability_score"])
        return score

    @classmethod
    def update_all(cls, group):
        """Met à jour le score de tous les membres d'un groupe."""
        for m in group.memberships.filter(is_active=True):
            cls.update(m)


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 4 — Pénalités automatiques
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# SERVICE 5 — Réconciliation du fond commun
# ═══════════════════════════════════════════════════════════════════════════

class FundReconciliationService:
    """
    Vérifie la cohérence entre les FundTransactions enregistrées
    et les états réels des prêts, dépôts et séances.

    Retourne un rapport avec :
      - Solde calculé depuis les transactions
      - Encours prêts actifs vs sorties loan_out
      - Dépôts actifs vs entrées deposit_in
      - Éventuels écarts (discrepancies)
    """

    @classmethod
    def reconcile(cls, group) -> dict:
        from django.db.models import Sum
        from njangi.models.fund import FundDeposit, FundTransaction
        from njangi.models.loan import Loan

        # ── 1. Solde réel depuis les transactions ─────────────────────────────
        tx_balance = FundTransaction.objects.filter(group=group).aggregate(
            total=Sum("signed_amount")
        )["total"] or 0

        # ── 2. Répartition par type ────────────────────────────────────────────
        tx_by_type = {}
        for row in FundTransaction.objects.filter(group=group).values("type").annotate(
            total=Sum("amount"), count=models.Count("id")
        ):
            tx_by_type[row["type"]] = {"total": int(row["total"]), "count": row["count"]}

        # ── 3. Prêts actifs ───────────────────────────────────────────────────
        active_loans = Loan.objects.filter(membership__group=group, status="active")
        total_active_loans_balance = sum(int(l.balance_remaining) for l in active_loans)
        total_active_loans_approved = int(
            active_loans.aggregate(total=Sum("amount_approved"))["total"] or 0
        )

        # Sorties loan_out enregistrées
        loan_out_total = tx_by_type.get("loan_out", {}).get("total", 0)
        # Remboursements enregistrés
        repayment_total = tx_by_type.get("repayment", {}).get("total", 0)

        loan_discrepancy = loan_out_total - repayment_total - total_active_loans_balance

        # ── 4. Dépôts actifs ──────────────────────────────────────────────────
        active_deposits = FundDeposit.objects.filter(membership__group=group, status="active")
        total_active_deposits = int(
            active_deposits.aggregate(total=Sum("amount"))["total"] or 0
        )
        deposit_in_total  = tx_by_type.get("deposit_in",  {}).get("total", 0)
        deposit_out_total = tx_by_type.get("deposit_out", {}).get("total", 0)

        deposit_discrepancy = deposit_in_total - deposit_out_total - total_active_deposits

        # ── 5. Intérêts attendus vs enregistrés ───────────────────────────────
        from njangi.models.wallet import MonthlyGroupInterest
        total_interest_generated = int(
            MonthlyGroupInterest.objects.filter(group=group).aggregate(
                total=Sum("total_interest_generated")
            )["total"] or 0
        )
        interest_in_total = tx_by_type.get("interest_in", {}).get("total", 0)

        # ── 6. Nombre de transactions & dernière transaction ──────────────────
        tx_count = FundTransaction.objects.filter(group=group).count()
        last_tx  = FundTransaction.objects.filter(group=group).order_by("-created_at").first()

        # ── 7. Rapport final ──────────────────────────────────────────────────
        issues = []
        if abs(loan_discrepancy) > 100:
            issues.append({
                "type":    "loan_mismatch",
                "label":   "Écart prêts",
                "amount":  loan_discrepancy,
                "detail":  f"Sorties prêts: {loan_out_total:,} FCFA | Remboursements: {repayment_total:,} FCFA | Encours actif: {total_active_loans_balance:,} FCFA",
            })
        if abs(deposit_discrepancy) > 100:
            issues.append({
                "type":    "deposit_mismatch",
                "label":   "Écart dépôts",
                "amount":  deposit_discrepancy,
                "detail":  f"Entrées: {deposit_in_total:,} FCFA | Sorties: {deposit_out_total:,} FCFA | Dépôts actifs: {total_active_deposits:,} FCFA",
            })

        return {
            "group":                    group,
            "tx_balance":               int(tx_balance),
            "tx_count":                 tx_count,
            "last_tx":                  last_tx,
            # Prêts
            "active_loans_count":       active_loans.count(),
            "active_loans_balance":     total_active_loans_balance,
            "loan_out_total":           loan_out_total,
            "repayment_total":          repayment_total,
            "loan_discrepancy":         loan_discrepancy,
            # Dépôts
            "active_deposits_count":    active_deposits.count(),
            "active_deposits_total":    total_active_deposits,
            "deposit_in_total":         deposit_in_total,
            "deposit_out_total":        deposit_out_total,
            "deposit_discrepancy":      deposit_discrepancy,
            # Intérêts
            "interest_generated_total": total_interest_generated,
            "interest_in_total":        interest_in_total,
            # Transactions par type
            "tx_by_type":               tx_by_type,
            # Rapport
            "issues":                   issues,
            "is_clean":                 len(issues) == 0,
        }


class PenaltyService:
    """
    Calcule et applique les pénalités de retard sur les cotisations.
    """

    @classmethod
    def apply_penalties(cls, session):
        """
        Applique les pénalités pour une séance :
        - Cotisations not paid après la date de séance → pénalité journalière
        """
        today = date.today()
        if session.date >= today:
            return  # Séance pas encore passée

        total_penalties = Decimal("0")

        for contribution in session.contributions.filter(status__in=("pending", "partial")):
            days_late = (today - session.date).days
            if days_late > 0:
                penalty = days_late * contribution.membership.group.penalty_per_day
                contribution.days_late    = days_late
                contribution.is_late      = True
                contribution.penalty_amount = int(penalty)
                contribution.status        = "late"
                contribution.save(update_fields=[
                    "days_late", "is_late", "penalty_amount", "status"
                ])

                # Mettre à jour les pénalités du membre
                contribution.membership.total_penalties += penalty
                contribution.membership.save(update_fields=["total_penalties"])

                total_penalties += penalty

        # Mettre à jour les pénalités collectées de la séance
        session.penalties_collected = int(total_penalties)
        session.save(update_fields=["penalties_collected"])

        return int(total_penalties)

    @classmethod
    def apply_all_pending(cls, group):
        """Applique les pénalités pour toutes les séances passées d'un groupe."""
        from njangi.models.session import Session
        past_sessions = Session.objects.filter(
            group=group,
            date__lt=date.today(),
            status__in=("planned", "in_progress", "completed"),
        )
        total = 0
        for session in past_sessions:
            total += cls.apply_penalties(session) or 0
        return total
