"""Structured session report, shared with the session workflow."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle


from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to accurately calculate and print total page count."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#52657A"))
        self.drawString(36, 22, "E-Shelle • Njangi Digital")
        self.drawRightString(A4[0] - 36, 22, f"Page {self._pageNumber} sur {page_count}")
        self.restoreState()


def build_session_report(session):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36,
                            topMargin=38, bottomMargin=38,
                            title=f"Rapport de séance {session.session_number}")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, leading=12))
    styles.add(ParagraphStyle("HeaderCell", parent=styles["Cell"], textColor=colors.white))
    styles["Heading2"].textColor = colors.HexColor("#24639B")
    styles["Heading2"].keepWithNext = True
    story = []

    def paragraph(value, style="Cell"):
        return Paragraph(escape(str(value or "—")).replace("\n", "<br/>"), styles[style])

    def name(membership):
        return membership.user.get_full_name() or membership.user.username

    def money(value):
        return f"{int(value or 0):,} FCFA".replace(",", " ")

    def section(title, headers, rows, widths):
        story.append(paragraph(title, "Heading2"))
        rows = list(rows)
        if not rows:
            story.append(paragraph("Aucun enregistrement pour cette séance."))
        else:
            data = [[paragraph(h, "HeaderCell") for h in headers]]
            data.extend([[paragraph(cell) for cell in row] for row in rows])
            table = LongTable(data, colWidths=[doc.width * w for w in widths],
                              repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24639B")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F5FA")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#D5DFEA")),
            ]))
            story.append(table)
        story.append(Spacer(1, 10))

    contributions = list(session.contributions.select_related("membership__user", "recorded_by").order_by("membership__hand_order", "pk"))
    beneficiaries = list(session.session_beneficiaries.select_related("membership__user").order_by("pk"))
    repayments = list(session.repayments_made.order_by("paid_at", "pk"))
    deposits = list(session.deposits.select_related("membership__user").order_by("pk"))
    loans = list(session.loans_granted.select_related("membership__user").order_by("pk"))
    base_funds = list(session.base_fund_deposits.select_related("membership__user").order_by("pk"))
    story.append(paragraph(f"Rapport de séance #{session.session_number}", "Title"))
    story.append(paragraph(f"{session.group.name} | {session.date:%d/%m/%Y} | Cycle {session.cycle}", "Normal"))
    story.append(paragraph(f"Statut : {session.get_status_display()}", "Normal"))

    section("1. Présences et cotisations", ["Membre", "Présence", "Dû", "Payé", "Statut"],
            [(name(c.membership), c.get_presence_display(), money(c.amount_due), money(c.amount_paid), c.get_status_display()) for c in contributions],
            [.30, .16, .18, .18, .18])
    beneficiary_rows = [(name(b.membership), money(b.amount)) for b in beneficiaries]
    if not beneficiaries and session.beneficiary_id:
        beneficiary_rows.append((name(session.beneficiary), money(session.hand_amount)))
    section("2. Bénéficiaires du jour", ["Membre", "Montant reçu"], beneficiary_rows, [.65, .35])
    section("3. Remboursements", ["Membre / prêt", "Montant", "Capital", "Intérêts"],
            [(f"{name(r.loan.membership)} / prêt #{r.loan_id}\nEnregistré le {r.paid_at:%d/%m/%Y}", money(r.amount_paid), money(r.principal_part), money(r.interest_part)) for r in repayments],
            [.4, .2, .2, .2])
    section("4. Dépôts pour prêt", ["Membre", "Montant déposé", "Taux", "Statut"],
            [(name(d.membership), money(d.amount), f"{d.interest_rate} %", d.get_status_display()) for d in deposits],
            [.4, .25, .15, .2])
    section("5. Prêts aux membres", ["Membre / prêt", "Montant prêté", "Total à rembourser", "Échéance"],
            [(f"{name(l.membership)} / prêt #{l.pk}\nTaux : {l.interest_rate} %", money(l.amount_approved), money(l.total_due), l.due_date.strftime("%d/%m/%Y") if l.due_date else "—") for l in loans],
            [.34, .22, .24, .2])
    section("6. Fond de caisse", ["Membre", "Montant versé"],
            [(name(b.membership), money(b.amount)) for b in base_funds], [.65, .35])
    section("Récapitulatif de la séance", ["Opération", "Montant"], [
        ("Cotisations reçues", money(sum(c.amount_paid for c in contributions))),
        ("Montants remis aux bénéficiaires", money(sum(b.amount for b in beneficiaries) if beneficiaries else session.hand_amount)),
        ("Remboursements reçus", money(sum(r.amount_paid for r in repayments))),
        ("Dépôts pour prêt enregistrés", money(sum(d.amount for d in deposits))),
        ("Prêts accordés", money(sum(l.amount_approved or 0 for l in loans))),
        ("Versements au fond de caisse", money(sum(b.amount for b in base_funds))),
        ("Fond pour prêt déclaré (ancienne saisie)", money(session.loan_fund_available)),
        ("Retour en caisse déclaré", money(session.cash_returned_manual)),
    ], [.65, .35])
    section("Détails des paiements et pénalités", ["Membre", "Méthode / validation", "Pénalité", "Paiement pénalité"],
            [(name(c.membership), f"{c.get_payment_method_display() or '—'} / {(c.recorded_by.get_full_name() or c.recorded_by.username) if c.recorded_by else '—'}",
              money(c.penalty_amount), "Payée" if c.penalty_paid else "Non payée" if c.penalty_amount else "—") for c in contributions], [.30, .34, .18, .18])
    for title, value in [("7. Propositions et divers", session.proposals), ("8. Bref rapport écrit de la séance", session.notes)]:
        story.append(paragraph(title, "Heading2"))
        for line in (value or "Non renseigné.").splitlines():
            story.append(paragraph(line or " ", "BodyText"))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
