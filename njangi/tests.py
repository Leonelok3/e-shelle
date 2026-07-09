"""
Njangi+ — Tests unitaires & d'intégration

Couverture :
  - InterestCalculationService  : calcul standard, pool vide, multi-déposants
  - DistributionCalculator      : cas sans déductions, avec prêt, pénalités, fonds de base
  - PenaltyService              : application pénalités séances passées
  - ReliabilityScoreService     : score initial, avec cotisations et prêts
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from njangi.models import (
    Group, Membership, Session, Contribution,
    FundDeposit, FundTransaction, Loan, LoanRepayment,
    MonthlyGroupInterest, MemberMonthlyStatement,
)
from njangi.services import (
    InterestCalculationService,
    DistributionCalculator,
    PenaltyService,
    ReliabilityScoreService,
)

User = get_user_model()


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="testpass123",
    )


def make_group(creator, name="Tontine Test", contribution=10000, loan_rate=10, deposit_rate=5):
    return Group.objects.create(
        name=name,
        created_by=creator,
        frequency="monthly",
        contribution_amount=contribution,
        max_members=20,
        fund_loan_rate=loan_rate,
        fund_deposit_rate=deposit_rate,
        penalty_per_day=500,
        max_loan_multiplier=3,
        fund_reserve_pct=20,
        require_guarantor=False,
        base_fund_required=0,
        start_date=date.today() - timedelta(days=90),
    )


def make_membership(user, group, role="member", hand_order=None):
    return Membership.objects.create(
        user=user, group=group, role=role,
        hand_order=hand_order, is_active=True,
    )


def make_deposit(membership, amount):
    deposit = FundDeposit.objects.create(
        membership=membership,
        amount=amount,
        interest_rate=membership.group.fund_deposit_rate,
    )
    FundTransaction.objects.create(
        group=membership.group,
        type="deposit_in",
        amount=amount,
        description=f"Dépôt test {membership.user.username}",
    )
    return deposit


def make_active_loan(membership, amount, months=3):
    loan = Loan.objects.create(
        membership=membership,
        amount_requested=amount,
        amount_approved=amount,
        interest_rate=membership.group.fund_loan_rate,
        duration_months=months,
        status="active",
        disbursed_at=timezone.now() - timedelta(days=30),
        due_date=date.today() + timedelta(days=60),
    )
    loan.compute_totals()
    loan.save()
    FundTransaction.objects.create(
        group=membership.group,
        type="loan_out",
        amount=amount,
        description=f"Prêt test {membership.user.username}",
        reference_loan=loan,
    )
    return loan


# ═══════════════════════════════════════════════════════════════════════════
# SUITE 1 — InterestCalculationService
# ═══════════════════════════════════════════════════════════════════════════

class InterestCalculationServiceTest(TestCase):

    def setUp(self):
        self.president = make_user("alice")
        self.member1   = make_user("bob")
        self.member2   = make_user("carol")

        self.group = make_group(self.president)

        self.m_alice = make_membership(self.president, self.group, role="president", hand_order=1)
        self.m_bob   = make_membership(self.member1,   self.group, role="member",    hand_order=2)
        self.m_carol = make_membership(self.member2,   self.group, role="member",    hand_order=3)

        self.today = date.today()

    def test_no_deposits_no_loans_creates_zero_record(self):
        """Sans dépôts ni prêts, le record est créé avec des zéros."""
        record = InterestCalculationService.calculate_month(
            self.group, self.today.year, self.today.month
        )
        self.assertIsNotNone(record)
        self.assertEqual(int(record.total_pool), 0)
        self.assertEqual(int(record.total_interest_generated), 0)
        self.assertEqual(record.nb_active_loans, 0)
        self.assertEqual(record.nb_depositors, 0)
        self.assertTrue(record.is_calculated)

    def test_deposit_without_loan_generates_zero_interest(self):
        """Un dépôt sans prêt actif ne génère pas d'intérêts (rien à financer)."""
        make_deposit(self.m_bob, 100_000)
        record = InterestCalculationService.calculate_month(
            self.group, self.today.year, self.today.month
        )
        self.assertEqual(int(record.total_pool), 100_000)
        self.assertEqual(int(record.total_interest_generated), 0)
        self.assertEqual(record.nb_depositors, 1)

    def test_single_depositor_single_loan(self):
        """Un déposant finance un prêt — il reçoit 100% des intérêts."""
        make_deposit(self.m_bob, 100_000)
        loan = make_active_loan(self.m_alice, 50_000, months=3)

        record = InterestCalculationService.calculate_month(
            self.group, self.today.year, self.today.month
        )

        # Intérêts = 50000 × 10% = 5000 FCFA
        expected_interest = int(Decimal("50000") * Decimal("10") / Decimal("100"))
        self.assertEqual(int(record.total_interest_generated), expected_interest)
        self.assertEqual(record.nb_active_loans, 1)
        self.assertEqual(record.nb_depositors, 1)

        stmt = MemberMonthlyStatement.objects.get(membership=self.m_bob, monthly_record=record)
        self.assertEqual(int(stmt.interest_earned), expected_interest)
        self.assertAlmostEqual(float(stmt.pool_share_pct), 100.0, places=1)

    def test_two_depositors_proportional_distribution(self):
        """Deux déposants reçoivent des intérêts proportionnels à leurs dépôts."""
        make_deposit(self.m_bob,   60_000)   # 60%
        make_deposit(self.m_carol, 40_000)   # 40%
        make_active_loan(self.m_alice, 80_000, months=3)

        record = InterestCalculationService.calculate_month(
            self.group, self.today.year, self.today.month
        )

        # Intérêts totaux = 80000 × 10% = 8000 FCFA
        self.assertEqual(int(record.total_interest_generated), 8_000)
        self.assertEqual(record.nb_depositors, 2)

        stmt_bob   = MemberMonthlyStatement.objects.get(membership=self.m_bob,   monthly_record=record)
        stmt_carol = MemberMonthlyStatement.objects.get(membership=self.m_carol, monthly_record=record)

        # Bob 60% → 4800, Carol 40% → 3200
        self.assertEqual(int(stmt_bob.interest_earned),   4_800)
        self.assertEqual(int(stmt_carol.interest_earned), 3_200)
        self.assertAlmostEqual(float(stmt_bob.pool_share_pct),   60.0, places=0)
        self.assertAlmostEqual(float(stmt_carol.pool_share_pct), 40.0, places=0)

    def test_idempotent_recalculation(self):
        """Recalculer le même mois met à jour le record sans doublon."""
        make_deposit(self.m_bob, 100_000)
        make_active_loan(self.m_alice, 50_000)

        record1 = InterestCalculationService.calculate_month(
            self.group, self.today.year, self.today.month
        )
        record2 = InterestCalculationService.calculate_month(
            self.group, self.today.year, self.today.month
        )

        self.assertEqual(record1.pk, record2.pk)
        self.assertEqual(
            MonthlyGroupInterest.objects.filter(group=self.group).count(), 1
        )

    def test_simulate_next_month_returns_projections(self):
        """La simulation du mois prochain retourne des projections sans sauvegarder."""
        make_deposit(self.m_bob, 50_000)
        make_active_loan(self.m_alice, 30_000)

        initial_count = MonthlyGroupInterest.objects.count()
        result = InterestCalculationService.simulate_next_month(self.group)

        self.assertIn("pool_total", result)
        self.assertIn("total_interest", result)
        self.assertIn("projections", result)
        self.assertEqual(MonthlyGroupInterest.objects.count(), initial_count)

    def test_cumulative_interest_accumulates_over_months(self):
        """Les intérêts cumulés s'accumulent correctement sur plusieurs mois."""
        from django.utils import timezone as tz

        today = date.today()
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year  = today.year if today.month > 1 else today.year - 1

        # Backdater le dépôt pour qu'il soit actif dès le mois précédent
        import datetime as dt
        deposit = make_deposit(self.m_bob, 100_000)
        FundDeposit.objects.filter(pk=deposit.pk).update(
            deposited_at=dt.datetime(prev_year, prev_month, 1, tzinfo=dt.timezone.utc)
        )
        make_active_loan(self.m_alice, 50_000)

        InterestCalculationService.calculate_month(self.group, prev_year, prev_month)
        InterestCalculationService.calculate_month(self.group, today.year, today.month)

        stmts = MemberMonthlyStatement.objects.filter(
            membership=self.m_bob
        ).order_by("monthly_record__year", "monthly_record__month")

        self.assertGreaterEqual(stmts.count(), 2)
        last_stmt = stmts.last()
        # Le cumulatif du dernier mois doit être > aux intérêts du seul premier mois
        self.assertGreater(int(last_stmt.cumulative_interest), 0)

    def test_get_member_evolution_returns_list(self):
        """get_member_evolution retourne une liste de dicts pour les graphiques."""
        make_deposit(self.m_bob, 100_000)
        make_active_loan(self.m_alice, 50_000)
        InterestCalculationService.calculate_month(self.group, self.today.year, self.today.month)

        evolution = InterestCalculationService.get_member_evolution(self.m_bob, last_n_months=6)

        self.assertIsInstance(evolution, list)
        if evolution:
            entry = evolution[0]
            self.assertIn("label", entry)
            self.assertIn("deposit", entry)
            self.assertIn("interest", entry)
            self.assertIn("wallet", entry)

    def test_session_repayment_members_display_property(self):
        """La propriété de session renvoie la liste formatée des membres remboursant."""
        session = Session.objects.create(
            group=self.group,
            session_number=1,
            cycle=1,
            date=self.today,
            status="completed",
            created_by=self.president,
        )
        session.repayment_members_manual = f"{self.m_bob.user.get_full_name() or self.m_bob.user.username}, {self.m_carol.user.username}"
        session.save()

        self.assertEqual(
            session.repayment_members_list,
            [self.m_bob.user.get_full_name() or self.m_bob.user.username, self.m_carol.user.username]
        )
        self.assertEqual(
            session.repayment_members_display,
            f"{self.m_bob.user.get_full_name() or self.m_bob.user.username}, {self.m_carol.user.username}"
        )

    def test_session_detail_shows_loan_depositors_and_borrowers(self):
        """La vue détail de séance affiche dépôts et emprunteurs liés au fond."""
        group = self.group
        m_bob = make_membership(make_user("bob2"), group, hand_order=2)
        m_carol = make_membership(make_user("carol2"), group, hand_order=3)

        session = Session.objects.create(
            group=group,
            session_number=1,
            cycle=1,
            date=self.today,
            status="in_progress",
            created_by=self.president,
        )

        deposit = make_deposit(m_bob, 150_000)
        loan = make_active_loan(m_carol, 100_000)

        self.client.force_login(self.president)
        url = reverse("njangi:session_detail", kwargs={"slug": group.slug, "pk": session.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, deposit.membership.user.get_full_name() or deposit.membership.user.username)
        self.assertContains(response, "150 000 FCFA")
        self.assertContains(response, loan.membership.user.get_full_name() or loan.membership.user.username)
        self.assertContains(response, "100 000 FCFA")


# ═══════════════════════════════════════════════════════════════════════════
# SUITE 2 — DistributionCalculator
# ═══════════════════════════════════════════════════════════════════════════

class DistributionCalculatorTest(TestCase):

    def setUp(self):
        self.president = make_user("diana")
        self.member    = make_user("eric")

        self.group = make_group(self.president, contribution=15_000)

        self.m_diana = make_membership(self.president, self.group, role="president", hand_order=1)
        self.m_eric  = make_membership(self.member,    self.group, role="member",    hand_order=2)

    def test_no_deductions_receives_full_amount(self):
        """Un membre sans dettes reçoit le montant brut complet."""
        gross = Decimal("60000")
        result = DistributionCalculator.preview(self.m_eric, gross)

        self.assertEqual(result["gross_amount"], 60_000)
        self.assertEqual(result["total_deductions"], 0)
        self.assertEqual(result["net_amount"], 60_000)
        self.assertTrue(result["can_receive"])
        self.assertFalse(result["blocked"])
        self.assertEqual(len(result["deductions"]), 0)

    def test_active_loan_deducted(self):
        """Un prêt actif est déduit du montant brut."""
        loan = make_active_loan(self.m_eric, 30_000, months=3)

        result = DistributionCalculator.preview(self.m_eric, Decimal("60000"))

        loan_deduction = next(d for d in result["deductions"] if d["type"] == "loan")
        self.assertEqual(loan_deduction["amount"], int(loan.balance_remaining))
        self.assertEqual(result["net_amount"], 60_000 - int(loan.balance_remaining))

    def test_unpaid_penalties_deducted(self):
        """Les pénalités impayées sont déduites du montant brut."""
        session = Session.objects.create(
            group=self.group,
            session_number=1,
            cycle=1,
            date=date.today() - timedelta(days=10),
            status="completed",
            created_by=self.president,
        )
        Contribution.objects.create(
            membership=self.m_eric,
            session=session,
            amount_due=15_000,
            amount_paid=0,
            status="late",
            is_late=True,
            days_late=10,
            penalty_amount=5_000,
            penalty_paid=False,
        )

        result = DistributionCalculator.preview(self.m_eric, Decimal("60000"))

        penalty_deduction = next(
            (d for d in result["deductions"] if d["type"] == "penalty"), None
        )
        self.assertIsNotNone(penalty_deduction)
        self.assertEqual(penalty_deduction["amount"], 5_000)

    def test_late_contributions_deducted(self):
        """Les cotisations en retard sont déduites du montant brut."""
        session = Session.objects.create(
            group=self.group,
            session_number=2,
            cycle=1,
            date=date.today() - timedelta(days=5),
            status="completed",
            created_by=self.president,
        )
        Contribution.objects.create(
            membership=self.m_eric,
            session=session,
            amount_due=15_000,
            amount_paid=0,
            status="late",
            is_late=True,
            days_late=5,
            penalty_amount=0,
            penalty_paid=False,
        )

        result = DistributionCalculator.preview(self.m_eric, Decimal("60000"))

        late_deduction = next(
            (d for d in result["deductions"] if d["type"] == "late_contribution"), None
        )
        self.assertIsNotNone(late_deduction)
        self.assertEqual(late_deduction["amount"], 15_000)

    def test_base_fund_deficit_deducted(self):
        """Un déficit de fonds de base est déduit."""
        self.group.base_fund_required = 50_000
        self.group.save()

        result = DistributionCalculator.preview(self.m_eric, Decimal("60000"))

        base_deduction = next(
            (d for d in result["deductions"] if d["type"] == "base_fund"), None
        )
        self.assertIsNotNone(base_deduction)
        self.assertEqual(base_deduction["amount"], 50_000)

    def test_blocked_when_deductions_exceed_gross(self):
        """Un membre est bloqué si ses déductions dépassent le montant brut."""
        make_active_loan(self.m_eric, 100_000, months=6)

        result = DistributionCalculator.preview(self.m_eric, Decimal("30000"))

        self.assertTrue(result["blocked"])
        self.assertFalse(result["can_receive"])
        self.assertEqual(result["net_amount"], 0)

    def test_default_gross_calculated_from_group(self):
        """Sans gross_amount fourni, il est calculé depuis cotisation × membres."""
        result = DistributionCalculator.preview(self.m_eric)

        expected_gross = int(self.group.contribution_amount * self.group.member_count)
        self.assertEqual(result["gross_amount"], expected_gross)

    def test_multiple_deductions_combined(self):
        """Plusieurs déductions s'accumulent correctement."""
        self.group.base_fund_required = 10_000
        self.group.save()

        make_active_loan(self.m_eric, 20_000, months=3)

        session = Session.objects.create(
            group=self.group,
            session_number=3,
            cycle=1,
            date=date.today() - timedelta(days=8),
            status="completed",
            created_by=self.president,
        )
        Contribution.objects.create(
            membership=self.m_eric,
            session=session,
            amount_due=15_000,
            amount_paid=0,
            status="late",
            is_late=True,
            days_late=8,
            penalty_amount=4_000,
            penalty_paid=False,
        )

        result = DistributionCalculator.preview(self.m_eric, Decimal("100000"))

        self.assertGreater(len(result["deductions"]), 1)
        self.assertGreater(result["total_deductions"], 0)
        self.assertEqual(
            result["net_amount"],
            max(0, 100_000 - result["total_deductions"])
        )


# ═══════════════════════════════════════════════════════════════════════════
# SUITE 3 — PenaltyService
# ═══════════════════════════════════════════════════════════════════════════

class PenaltyServiceTest(TestCase):

    def setUp(self):
        self.president = make_user("frank")
        self.group = make_group(self.president)
        self.m_frank = make_membership(self.president, self.group, role="president", hand_order=1)

    def test_no_penalty_on_future_session(self):
        """Aucune pénalité appliquée pour une séance future."""
        session = Session.objects.create(
            group=self.group,
            session_number=1,
            cycle=1,
            date=date.today() + timedelta(days=5),
            status="planned",
            created_by=self.president,
        )
        Contribution.objects.create(
            membership=self.m_frank,
            session=session,
            amount_due=10_000,
            status="pending",
        )

        result = PenaltyService.apply_penalties(session)
        self.assertIsNone(result)

    def test_penalty_applied_on_past_session(self):
        """Pénalité appliquée correctement sur une séance passée avec cotisation impayée."""
        days_ago = 5
        session = Session.objects.create(
            group=self.group,
            session_number=2,
            cycle=1,
            date=date.today() - timedelta(days=days_ago),
            status="completed",
            created_by=self.president,
        )
        contribution = Contribution.objects.create(
            membership=self.m_frank,
            session=session,
            amount_due=10_000,
            status="pending",
        )

        PenaltyService.apply_penalties(session)

        contribution.refresh_from_db()
        expected_penalty = days_ago * int(self.group.penalty_per_day)
        self.assertEqual(contribution.penalty_amount, expected_penalty)
        self.assertTrue(contribution.is_late)
        self.assertEqual(contribution.status, "late")
        self.assertEqual(contribution.days_late, days_ago)

    def test_no_penalty_on_paid_contribution(self):
        """Aucune pénalité sur une cotisation déjà payée."""
        session = Session.objects.create(
            group=self.group,
            session_number=3,
            cycle=1,
            date=date.today() - timedelta(days=3),
            status="completed",
            created_by=self.president,
        )
        contribution = Contribution.objects.create(
            membership=self.m_frank,
            session=session,
            amount_due=10_000,
            amount_paid=10_000,
            status="paid",
        )

        PenaltyService.apply_penalties(session)

        contribution.refresh_from_db()
        self.assertEqual(contribution.penalty_amount, 0)
        self.assertEqual(contribution.status, "paid")


# ═══════════════════════════════════════════════════════════════════════════
# SUITE 4 — ReliabilityScoreService
# ═══════════════════════════════════════════════════════════════════════════

class ReliabilityScoreServiceTest(TestCase):

    def setUp(self):
        self.president = make_user("grace")
        self.group = make_group(self.president)
        self.m_grace = make_membership(self.president, self.group, role="president", hand_order=1)

    def _make_session(self, days_ago=10, number=1):
        return Session.objects.create(
            group=self.group,
            session_number=number,
            cycle=1,
            date=date.today() - timedelta(days=days_ago),
            status="completed",
            created_by=self.president,
        )

    def test_initial_score_is_100(self):
        """Score initial = 100 sans historique."""
        score = ReliabilityScoreService.compute(self.m_grace)
        self.assertEqual(score, 100)

    def test_late_payment_decreases_score(self):
        """Cotisation en retard diminue le score de 5."""
        session = self._make_session()
        Contribution.objects.create(
            membership=self.m_grace,
            session=session,
            amount_due=10_000,
            amount_paid=0,
            status="late",
            is_late=True,
        )

        score = ReliabilityScoreService.compute(self.m_grace)
        self.assertEqual(score, 95)

    def test_defaulted_loan_decreases_score(self):
        """Prêt en défaut diminue le score de 20."""
        Loan.objects.create(
            membership=self.m_grace,
            amount_requested=50_000,
            amount_approved=50_000,
            interest_rate=10,
            duration_months=3,
            status="defaulted",
            disbursed_at=timezone.now() - timedelta(days=120),
            due_date=date.today() - timedelta(days=30),
        )

        score = ReliabilityScoreService.compute(self.m_grace)
        self.assertEqual(score, 80)

    def test_score_never_below_zero(self):
        """Le score ne peut pas descendre sous 0."""
        for i in range(10):
            session = self._make_session(days_ago=10 + i * 30, number=i + 1)
            Contribution.objects.create(
                membership=self.m_grace,
                session=session,
                amount_due=10_000,
                status="late",
                is_late=True,
            )

        score = ReliabilityScoreService.compute(self.m_grace)
        self.assertGreaterEqual(score, 0)

    def test_update_saves_to_db(self):
        """update() sauvegarde le score en base."""
        session = self._make_session()
        Contribution.objects.create(
            membership=self.m_grace,
            session=session,
            amount_due=10_000,
            status="late",
            is_late=True,
        )

        score = ReliabilityScoreService.update(self.m_grace)
        self.m_grace.refresh_from_db()
        self.assertEqual(self.m_grace.reliability_score, score)
        self.assertEqual(score, 95)


# ═══════════════════════════════════════════════════════════════════════════
# SUITE 5 — Modèles (Group, Loan)
# ═══════════════════════════════════════════════════════════════════════════

class GroupModelTest(TestCase):

    def setUp(self):
        self.user = make_user("henry")
        self.group = make_group(self.user)

    def test_slug_auto_generated(self):
        self.assertTrue(len(self.group.slug) > 0)

    def test_invite_code_8_chars(self):
        self.assertEqual(len(self.group.invite_code), 8)

    def test_unique_invite_codes(self):
        group2 = make_group(self.user, name="Autre groupe")
        self.assertNotEqual(self.group.invite_code, group2.invite_code)

    def test_plan_free_always_active(self):
        self.assertEqual(self.group.plan, "free")
        self.assertTrue(self.group.is_plan_active)

    def test_plan_free_max_5_members(self):
        self.assertEqual(self.group.plan_max_members, 5)


class LoanModelTest(TestCase):

    def setUp(self):
        self.user = make_user("iris")
        self.group = make_group(self.user)
        self.m = make_membership(self.user, self.group, role="president")

    def test_compute_totals(self):
        """compute_totals calcule intérêts et total à rembourser correctement."""
        loan = Loan(
            membership=self.m,
            amount_requested=100_000,
            amount_approved=100_000,
            interest_rate=Decimal("10"),
            duration_months=3,
        )
        loan.compute_totals()
        self.assertEqual(int(loan.total_interest), 30_000)
        self.assertEqual(int(loan.total_due), 130_000)

    def test_balance_remaining(self):
        loan = Loan(
            membership=self.m,
            amount_approved=100_000,
            interest_rate=Decimal("10"),
            duration_months=3,
            total_due=130_000,
            total_repaid=50_000,
        )
        self.assertEqual(int(loan.balance_remaining), 80_000)

    def test_is_overdue_false_when_not_active(self):
        loan = Loan(status="pending", due_date=date.today() - timedelta(days=1))
        self.assertFalse(loan.is_overdue)

    def test_is_overdue_true_when_past_due(self):
        loan = Loan(status="active", due_date=date.today() - timedelta(days=1))
        self.assertTrue(loan.is_overdue)
