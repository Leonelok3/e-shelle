from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import cm
from pathlib import Path

OUTPUT = Path(__file__).with_name("njangi_guide_professionnel.pdf")

styles = getSampleStyleSheet()
PRIMARY = colors.HexColor("#1B6CA8")
ACCENT = colors.HexColor("#F5A623")
LIGHT = colors.HexColor("#EFF6FF")
DARK = colors.HexColor("#0F172A")

title_style = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, textColor=PRIMARY, leading=26)
subtitle_style = ParagraphStyle("Subtitle", parent=styles["Heading2"], fontName="Helvetica", fontSize=11, textColor=DARK, leading=14)
heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=PRIMARY, leading=16, spaceAfter=6)
body_style = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.2, leading=13.5, textColor=DARK)
bullet_style = ParagraphStyle("Bullet", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.1, leading=12.8, leftIndent=12, bulletIndent=0, textColor=DARK)
small_style = ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=10.5, textColor=colors.grey)

story = []
story.append(Paragraph("Njangi Digital — Solution de gestion de tontine", title_style))
story.append(Spacer(1, 0.25 * cm))
story.append(Paragraph("Une plateforme numérique pour moderniser les tontines, sécuriser les financements et améliorer la transparence au sein des groupes.", subtitle_style))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Pourquoi cette solution est utile", heading_style))
story.append(Paragraph("Les tontines traditionnelles sont efficaces, mais elles sont souvent confrontées à des difficultés de suivi, de traçabilité, de transparence et de gestion des remboursements. Njangi Digital répond à ces enjeux avec une approche numérique propre, accessible et structurée.", body_style))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("• Centraliser les cotisations et les paiements.\n• Automatiser les calculs et les rapports.\n• Assurer la transparence financière au sein du bureau.\n• Faciliter les prêts, remboursements et suivis de sessions.", bullet_style))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Fonctionnalités clés", heading_style))
features = [
    "Création et gestion de groupes avec paramètres personnalisés.",
    "Gestion des membres, rôles et ordre de rotation des mains.",
    "Création de séances, suivi des paiements et gestion des absences.",
    "Prêts, garanties, échéances et remboursements intégrés.",
    "Fond commun, dépôts, retraits, réserves et transactions auditées.",
    "Calcul mensuel des intérêts et relevés PDF pour chaque membre.",
    "Rapports de séance et état du fond commun exportables.",
]
for item in features:
    story.append(Paragraph(f"• {item}", bullet_style))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Valeur commerciale", heading_style))
story.append(Paragraph("Cette solution est déjà adaptée à un usage réel, avec une logique métier solide et prête à être présentée comme produit de gestion de tontine numérique. Elle peut servir aussi bien des associations, comités de solidarité, groupes familiaux, qu’organisations communautaires.", body_style))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("Conclusion", heading_style))
story.append(Paragraph("Njangi Digital est un logiciel opérationnel, crédible et déjà complet pour les usages essentiels de gestion de tontine. Il offre une base solide pour une présentation publique, un déploiement institutionnel ou une commercialisation auprès de groupes et organisations.", body_style))
story.append(Spacer(1, 1 * cm))
story.append(Paragraph("Document de présentation commerciale — E-Shelle", small_style))

doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=2.2 * cm, leftMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
doc.build(story)
print(f"PDF generated: {OUTPUT}")
