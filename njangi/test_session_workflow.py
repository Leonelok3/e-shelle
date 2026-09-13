from datetime import date, timedelta
from io import BytesIO
import os
from pathlib import Path

from django.test import TestCase
from django.urls import reverse
from pypdf import PdfReader

from .models import Session, Contribution, Loan, LoanRepayment, FundTransaction
from .models.session import SessionBeneficiary
from .tests import make_user, make_group, make_membership


class SessionWorkflowTests(TestCase):
    def setUp(self):
        self.user = make_user("president")
        self.group = make_group(self.user, name="Réunion Étoile & Famille")
        self.member = make_membership(self.user, self.group, role="president")
        self.other = make_membership(make_user("membre"), self.group)
        self.session = Session.objects.create(group=self.group, session_number=1, date=date.today(), status="in_progress")
        self.client.force_login(self.user)

    def post(self, route, data, **kwargs):
        return self.client.post(reverse("njangi:" + route, kwargs={"slug": self.group.slug, **kwargs}), data)

    def operation(self, route, data):
        return self.post(route, data, session_pk=self.session.pk)

    def deposit(self, amount=100000):
        return self.operation("session_direct_deposit", {"membership_pk": self.member.pk, "amount": amount})

    def loan(self, amount=40000):
        return self.operation("session_direct_loan", {"membership_pk": self.other.pk, "amount": amount,
            "total_due": amount + 4000, "due_date": str(date.today() + timedelta(days=30))})

    def test_complete_workflow_and_pdf(self):
        page = self.client.get(reverse("njangi:session_detail", kwargs={"slug": self.group.slug, "pk": self.session.pk}))
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        headings = ["1. Présences et cotisations", "2. Bénéficiaires du jour", "3. Remboursements", "4. Dépôts pour prêt", "5. Prêts aux membres", "6. Fond de caisse", "7. Propositions et divers", "8. Bref rapport écrit"]
        positions = [html.index(h) for h in headings]
        self.assertEqual(positions, sorted(positions))
        c = self.session.contributions.get(membership=self.member)
        self.post("htmx_bureau_contribution_presence", {"presence": "absent"}, session_pk=self.session.pk, contribution_pk=c.pk)
        self.post("htmx_bureau_contribution_toggle", {}, session_pk=self.session.pk, contribution_pk=c.pk)
        c.refresh_from_db()
        self.assertEqual((c.presence, c.status), ("absent", "paid"))
        for member, amount in [(self.member, 4000), (self.other, 5000)]:
            self.operation("session_add_beneficiary", {"membership_pk": member.pk, "amount": amount})
        self.deposit()
        self.loan()
        loan = Loan.objects.get()
        self.operation("bureau_loan_repay_quick", {"loan_pk": loan.pk, "amount": 5000})
        self.operation("session_add_base_fund", {"membership_pk": self.other.pk, "amount": 2500})
        self.post("session_financial_update", {"proposals": "Prévoir une aide & voter <demain>.", "notes": "Séance tenue dans le calme.\nDécision approuvée.", "loan_fund_available": 0, "cash_returned_manual": 1000}, pk=self.session.pk)
        self.post("session_close", {}, pk=self.session.pk)
        self.session.refresh_from_db()
        self.assertEqual(self.session.hand_amount, 9000)
        self.session.close(self.user)
        self.member.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.member.total_received, 4000)
        self.assertEqual(self.other.total_received, 5000)
        self.assertEqual(self.session.total_repayments, 5000)
        result = self.client.get(reverse("njangi:session_report_pdf", kwargs={"slug": self.group.slug, "pk": self.session.pk}))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result["Content-Type"], "application/pdf")
        pdf = PdfReader(BytesIO(result.content))
        text = "\n".join(p.extract_text() for p in pdf.pages)
        for heading in headings:
            self.assertIn(heading, text)
        for value in ["Prévoir une aide & voter <demain>.", "Décision approuvée.", "9 000 FCFA", "2 500 FCFA", "Absent", "Page 1 sur"]:
            self.assertIn(value, text)
        if os.environ.get("NJANGI_QA_OUTPUT"):
            out = Path(os.environ["NJANGI_QA_OUTPUT"])
            out.mkdir(parents=True, exist_ok=True)
            (out / "seance_complete.pdf").write_bytes(result.content)
            (out / "seance.html").write_bytes(page.content)

    def test_loan_cannot_exceed_cash_and_base_fund_is_separate(self):
        self.operation("session_add_base_fund", {"membership_pk": self.other.pk, "amount": 100000})
        self.loan()
        self.assertFalse(Loan.objects.exists())
        self.deposit()
        self.assertEqual(self.group.session_lending_available, 80000)
        self.loan(80001)
        self.assertFalse(Loan.objects.exists())
        self.loan(80000)
        self.assertEqual(Loan.objects.count(), 1)
        self.assertEqual(self.group.session_lending_available, 16000)

    def test_repayment_interest_counted_once_and_overpayment_rejected(self):
        self.deposit()
        self.loan()
        loan = Loan.objects.get()
        self.operation("bureau_loan_repay_quick", {"loan_pk": loan.pk, "amount": 45000})
        self.assertFalse(LoanRepayment.objects.exists())
        self.operation("bureau_loan_repay_quick", {"loan_pk": loan.pk, "amount": 5000})
        self.assertEqual(self.group.session_lending_available, 52000)

    def test_disbursement_is_not_duplicated_or_assigned_to_another_session(self):
        Session.objects.create(group=self.group, session_number=2, date=date.today() + timedelta(days=2), status="in_progress")
        self.deposit()
        self.loan()
        loan = Loan.objects.get()
        self.assertEqual(loan.session_id, self.session.pk)
        with self.assertRaises(ValueError):
            loan.disburse(self.user)
        self.assertEqual(FundTransaction.objects.filter(type="loan_out").count(), 1)

    def test_invalid_amounts_do_not_create_operations(self):
        for amount in ["-1", "0", "NaN", "Infinity", "1.5", "100000000000000"]:
            self.deposit(amount)
            self.operation("session_add_beneficiary", {"membership_pk": self.member.pk, "amount": amount})
            self.operation("session_add_base_fund", {"membership_pk": self.member.pk, "amount": amount})
        self.assertFalse(self.session.deposits.exists())
        self.assertFalse(self.session.session_beneficiaries.exists())
        self.assertFalse(self.session.base_fund_deposits.exists())

    def test_member_cannot_write_before_permission_check(self):
        self.client.force_login(self.other.user)
        self.deposit()
        self.post("session_financial_update", {"notes": "forbidden", "proposals": "forbidden", "loan_fund_available": 0, "cash_returned_manual": 0}, pk=self.session.pk)
        self.assertFalse(self.session.deposits.exists())
        self.session.refresh_from_db()
        self.assertEqual(self.session.notes, "")

    def test_repayments_belong_to_the_selected_session(self):
        self.deposit()
        self.loan()
        second = Session.objects.create(group=self.group, session_number=2, date=date.today())
        loan = Loan.objects.get()
        LoanRepayment.objects.create(loan=loan, session=self.session, amount_paid=1000)
        LoanRepayment.objects.create(loan=loan, session=second, amount_paid=2000)
        self.assertEqual(self.session.total_repayments, 1000)
        self.assertEqual(second.total_repayments, 2000)

    def test_long_pdf_keeps_all_rows_and_text(self):
        from .session_report import build_session_report
        self.session.proposals = ("Proposition très détaillée, avec accents et décisions. " * 10 + "\n") * 12
        self.session.notes = "Rapport final & validation <accord>.\n" * 30
        self.session.save()
        for n in range(30):
            u = make_user(f"participant{n}")
            u.first_name = f"Participant {n} au nom composé particulièrement long"
            u.save()
            member = make_membership(u, self.group)
            Contribution.objects.create(session=self.session, membership=member, amount_due=10000)
            SessionBeneficiary.objects.create(session=self.session, membership=member, amount=100)
        content = build_session_report(self.session)
        reader = PdfReader(BytesIO(content))
        self.assertGreater(len(reader.pages), 3)
        text = "\n".join(p.extract_text() for p in reader.pages)
        self.assertIn("Participant 29", text)
        self.assertIn("Rapport final & validation <accord>.", text)
        self.assertIn(f"Page 1 sur {len(reader.pages)}", text)
        if os.environ.get("NJANGI_QA_OUTPUT"):
            (Path(os.environ["NJANGI_QA_OUTPUT"]) / "seance_longue.pdf").write_bytes(content)

    def test_invalid_report_preserves_written_text(self):
        response = self.post("session_financial_update", {"notes": "Ne pas perdre ce rapport", "proposals": "Sujet conservé", "loan_fund_available": "invalide", "cash_returned_manual": 0}, pk=self.session.pk)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Ne pas perdre ce rapport", status_code=400)
        self.assertContains(response, "Sujet conservé", status_code=400)

    def test_closed_session_rejects_new_financial_operations(self):
        c = Contribution.objects.create(session=self.session, membership=self.member, amount_due=10000)
        self.session.close(self.user)
        self.assertEqual(self.deposit().status_code, 404)
        self.assertFalse(self.session.deposits.exists())
        self.assertEqual(self.operation("session_add_beneficiary", {"membership_pk": self.member.pk, "amount": 1000}).status_code, 404)
        self.assertEqual(self.operation("session_direct_loan", {"membership_pk": self.other.pk, "amount": 1000, "total_due": 1100, "due_date": str(date.today())}).status_code, 404)
        self.assertEqual(self.operation("session_add_base_fund", {"membership_pk": self.member.pk, "amount": 1000}).status_code, 404)
        self.assertEqual(self.post("htmx_bureau_contribution_toggle", {}, session_pk=self.session.pk, contribution_pk=c.pk).status_code, 404)
        self.assertEqual(self.post("htmx_bureau_contribution_presence", {"presence": "absent"}, session_pk=self.session.pk, contribution_pk=c.pk).status_code, 404)
        self.assertEqual(self.post("htmx_bureau_contribution_method", {"payment_method": "transfer"}, session_pk=self.session.pk, contribution_pk=c.pk).status_code, 404)
