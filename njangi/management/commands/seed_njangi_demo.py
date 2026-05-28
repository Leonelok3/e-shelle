from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from njangi.models import (
    Contribution,
    FundDeposit,
    FundTransaction,
    Group,
    Loan,
    LoanRepayment,
    Membership,
    Notification,
    Session,
)


User = get_user_model()


class Command(BaseCommand):
    help = "Cree un groupe Njangi demo rempli pour presentation commerciale."

    def handle(self, *args, **options):
        users_data = [
            ("demo_president", "Jean", "Président", "president"),
            ("demo_tresorier", "Clarisse", "Trésorière", "treasurer"),
            ("demo_secretaire", "Didier", "Secrétaire", "secretary"),
            ("demo_membre_1", "Esther", "Membre", "member"),
            ("demo_membre_2", "Marcel", "Membre", "member"),
            ("demo_membre_3", "Nadia", "Membre", "member"),
            ("demo_membre_4", "Olivier", "Membre", "member"),
            ("demo_membre_5", "Sandrine", "Membre", "member"),
        ]

        users = []
        for username, first_name, last_name, _role in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@demo.eshelle.cm",
                },
            )
            if created:
                user.set_password("demo2026")
                user.save()
            users.append(user)

        group, _created = Group.objects.update_or_create(
            slug="reunion-demo-e-shelle",
            defaults={
                "name": "Réunion Démo E-Shelle",
                "description": (
                    "Groupe exemple pour démontrer la gestion d'une réunion, tontine ou association : "
                    "membres, cotisations, séances, fonds communs, prêts et rapports."
                ),
                "frequency": "monthly",
                "contribution_amount": Decimal("25000"),
                "max_members": 30,
                "fund_loan_rate": Decimal("8"),
                "fund_deposit_rate": Decimal("4"),
                "penalty_per_day": Decimal("500"),
                "max_loan_multiplier": 3,
                "fund_reserve_pct": 20,
                "require_guarantor": True,
                "base_fund_required": Decimal("30000"),
                "start_date": date(2026, 1, 15),
                "next_session_date": date.today() + timedelta(days=10),
                "status": "active",
                "plan": "pro",
                "plan_expires_at": timezone.now() + timedelta(days=90),
                "plan_note": "Compte demo commercial E-Shelle",
                "created_by": users[0],
            },
        )

        Contribution.objects.filter(session__group=group).delete()
        LoanRepayment.objects.filter(loan__membership__group=group).delete()
        Loan.objects.filter(membership__group=group).delete()
        FundTransaction.objects.filter(group=group).delete()
        FundDeposit.objects.filter(membership__group=group).delete()
        Notification.objects.filter(membership__group=group).delete()
        Session.objects.filter(group=group).delete()
        Membership.objects.filter(group=group).delete()

        memberships = []
        for idx, (user, data) in enumerate(zip(users, users_data), start=1):
            membership = Membership.objects.create(
                user=user,
                group=group,
                role=data[3],
                hand_order=idx,
                is_active=True,
                reliability_score=96 if idx <= 3 else 88 + idx,
            )
            memberships.append(membership)

        start = date.today() - timedelta(days=90)
        contribution_amount = group.contribution_amount

        for session_number in range(1, 5):
            session_date = start + timedelta(days=30 * (session_number - 1))
            beneficiary = memberships[session_number - 1]
            session = Session.objects.create(
                group=group,
                session_number=session_number,
                cycle=1,
                date=session_date,
                beneficiary=beneficiary,
                status="completed" if session_number < 4 else "planned",
                notes=(
                    "Séance de démonstration : présence, cotisations, main et observations "
                    "sont centralisées dans Njangi Digital."
                ),
                opened_at=timezone.now() - timedelta(days=30 * (4 - session_number), hours=3)
                if session_number < 4
                else None,
                closed_at=timezone.now() - timedelta(days=30 * (4 - session_number))
                if session_number < 4
                else None,
                created_by=users[0],
            )

            total = Decimal("0")
            if session.status == "completed":
                for idx, membership in enumerate(memberships):
                    paid = not (session_number == 3 and idx in {5, 7})
                    amount_paid = contribution_amount if paid else Decimal("0")
                    Contribution.objects.create(
                        membership=membership,
                        session=session,
                        amount_due=contribution_amount,
                        amount_paid=amount_paid,
                        paid_at=timezone.now() - timedelta(days=30 * (4 - session_number))
                        if paid
                        else None,
                        payment_method="mtn_momo" if idx % 2 else "orange_money",
                        transaction_ref=f"DEMO-{session_number}-{idx + 1}",
                        status="paid" if paid else "late",
                        is_late=not paid,
                        days_late=2 if not paid else 0,
                        penalty_amount=Decimal("1000") if not paid else Decimal("0"),
                        recorded_by=users[1],
                    )
                    if paid:
                        total += amount_paid
                        membership.total_contributed += amount_paid
                        membership.save(update_fields=["total_contributed"])

                session.total_collected = total
                session.hand_amount = total
                session.penalties_collected = Decimal("2000") if session_number == 3 else Decimal("0")
                session.save(update_fields=["total_collected", "hand_amount", "penalties_collected"])
                beneficiary.total_received += total
                beneficiary.save(update_fields=["total_received"])
                FundTransaction.objects.create(
                    group=group,
                    type="hand_paid",
                    amount=total,
                    description=f"Main versée séance #{session_number} — {beneficiary.user.get_full_name()}",
                    reference_session=session,
                    created_by=users[1],
                )

        for membership, amount in zip(memberships[:4], [75000, 100000, 50000, 125000]):
            deposit = FundDeposit.objects.create(
                membership=membership,
                amount=Decimal(amount),
                interest_rate=group.fund_deposit_rate,
                payment_method="mtn_momo",
                transaction_ref=f"DEP-DEMO-{membership.hand_order}",
            )
            FundTransaction.objects.create(
                group=group,
                type="deposit_in",
                amount=deposit.amount,
                description=f"Dépôt fond commun — {membership.user.get_full_name()}",
                reference_deposit=deposit,
                created_by=membership.user,
            )

        loan = Loan.objects.create(
            membership=memberships[5],
            guarantor=memberships[1],
            amount_requested=Decimal("100000"),
            amount_approved=Decimal("100000"),
            interest_rate=group.fund_loan_rate,
            duration_months=3,
            purpose="Besoin de trésorerie pour une activité commerciale familiale.",
            status="active",
            approved_at=timezone.now() - timedelta(days=40),
            disbursed_at=timezone.now() - timedelta(days=39),
            due_date=date.today() + timedelta(days=50),
            total_interest=Decimal("24000"),
            total_due=Decimal("124000"),
            total_repaid=Decimal("0"),
            reviewed_by=users[1],
            payment_method="mtn_momo",
            transaction_ref="LOAN-DEMO-001",
        )
        FundTransaction.objects.create(
            group=group,
            type="loan_out",
            amount=loan.amount_approved,
            description=f"Prêt décaissé — {loan.membership.user.get_full_name()}",
            reference_loan=loan,
            created_by=users[1],
        )
        LoanRepayment.objects.create(
            loan=loan,
            amount_paid=Decimal("40000"),
            payment_method="mtn_momo",
            transaction_ref="REM-DEMO-001",
            recorded_by=users[1],
        )

        Notification.objects.create(
            membership=memberships[0],
            type="general",
            title="Démo prête",
            body="Votre groupe de démonstration Njangi Digital est prêt à être présenté.",
        )

        self.stdout.write(self.style.SUCCESS("Groupe demo Njangi pret."))
        self.stdout.write("Lien public : /njangi/groupe/reunion-demo-e-shelle/")
        self.stdout.write("Compte bureau : demo_president / demo2026")
