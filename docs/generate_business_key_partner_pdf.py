from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
PDF_OUTPUT = ROOT / "guide_business_key_partenaire.pdf"


def para(text, style):
    return Paragraph(text.replace("\n", "<br/>"), style)


def build_pdf():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleBK",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#14532d"),
        spaceAfter=16,
    )
    h2 = ParagraphStyle(
        "H2BK",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceBefore=12,
        spaceAfter=7,
    )
    body = ParagraphStyle(
        "BodyBK",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=7,
    )
    note = ParagraphStyle(
        "NoteBK",
        parent=body,
        backColor=colors.HexColor("#ecfdf5"),
        borderColor=colors.HexColor("#86efac"),
        borderWidth=1,
        borderPadding=8,
    )

    doc = SimpleDocTemplate(
        str(PDF_OUTPUT),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title="Guide Business Key Partenaire",
    )

    story = [
        para("E-Shelle Business Key - Guide Partenaire", title),
        para(
            "Business Key est une cle commerciale a 9 900 XAF donnant acces aux outils marketing E-Shelle. Le partenaire gagne 50% quand il recrute un autre partenaire et 30% sur les frais valides d'un prestataire qu'il fait enregistrer.",
            note,
        ),
        para("1. Offre simple a presenter", h2),
        para("Prix unique: 9 900 XAF. Acces complet: CRM, scripts, creation de fiches, agents IA, SEO, AdGen, WhatsApp, formation quotidienne et dashboard commissions.", body),
        para("2. Commissions", h2),
    ]

    table = Table(
        [
            ["Action", "Commission", "Exemple"],
            ["Faire souscrire un partenaire", "50%", "9 900 XAF x 50% = 4 950 XAF"],
            ["Faire enregistrer un prestataire", "30%", "15 000 XAF x 30% = 4 500 XAF"],
        ],
        colWidths=[6 * cm, 3.2 * cm, 7 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14532d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([table, Spacer(1, 8)])

    sections = [
        ("3. Script pour recruter un partenaire", "Tu peux rejoindre E-Shelle Business Key a 9 900 XAF, utiliser les outils marketing et gagner quand tu aides des prestataires ou recrutes un partenaire. Je peux te montrer le dashboard."),
        ("4. Script pour un prestataire", "Bonjour, je peux vous creer une fiche E-Shelle propre avec WhatsApp, services, photos et lien partageable. Vous voyez d'abord une demo, ensuite vous decidez."),
        ("5. Routine quotidienne", "Chaque jour: 1 lecon, 1 script, 1 mission terrain et 1 preuve. Ouvrir /business/partner/academy/daily/ pour suivre la formation."),
        ("6. Regles de qualite", "Ne pas promettre de revenus garantis. Ne pas spammer. Montrer une preuve avant paiement. Les commissions sont payees uniquement apres validation."),
        ("7. Objectif hebdomadaire", "10 prospects ajoutes, 3 fiches creees, 1 demo prestataire, 1 relance propre, 1 partenaire potentiel contacte."),
    ]
    for heading, text in sections:
        story.append(para(heading, h2))
        story.append(para(text, body))

    doc.build(story)
    print(f"PDF genere: {PDF_OUTPUT}")


if __name__ == "__main__":
    build_pdf()
