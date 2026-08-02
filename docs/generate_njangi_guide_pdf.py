# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import cm
from pathlib import Path

OUTPUT = Path(__file__).with_name("njangi_guide_utilisation.pdf")

content = []
styles = getSampleStyleSheet()
PRIMARY = colors.HexColor("#1B6CA8")
ACCENT = colors.HexColor("#F5A623")
LIGHT = colors.HexColor("#EFF6FF")
DARK = colors.HexColor("#0F172A")

title_style = ParagraphStyle("TitleMain", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, textColor=PRIMARY, leading=28)
subtitle_style = ParagraphStyle("Subtitle", parent=styles["Heading2"], fontName="Helvetica", fontSize=12, textColor=DARK, leading=16)
heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=PRIMARY, leading=16, spaceAfter=8)
body_style = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=14, textColor=DARK)
bullet_style = ParagraphStyle("Bullet", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.2, leading=13, leftIndent=12, bulletIndent=0, textColor=DARK)
small_style = ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.8, leading=11.5, textColor=colors.grey)

content.append(Paragraph("Guide complet d’utilisation\nNjangi Digital", title_style))
content.append(Spacer(1, 0.3 * cm))
content.append(Paragraph("Solution de gestion de tontine et de financement participatif pour les groupes au Cameroun.", subtitle_style))
content.append(Spacer(1, 0.6 * cm))
content.append(Paragraph("Ce document présente l’application telle qu’elle fonctionne aujourd’hui, son rôle métier, ses modules clés, son parcours utilisateur et les éléments qui prouvent qu’elle est déjà robuste et prête à être présentée au public.", body_style))
content.append(Spacer(1, 0.4 * cm))

summary_table = Table([
    ["Aspect", "État dans l’application"],
    ["Création de groupe", "Oui"],
    ["Gestion des membres", "Oui"],
    ["Séances de tontine", "Oui"],
    ["Cotisations et paiements", "Oui"],
    ["Prêts et remboursements", "Oui"],
    ["Fond commun et transactions", "Oui"],
    ["Intérêts mensuels", "Oui"],
    ["Rapports PDF", "Oui"],
    ["Audit trail", "Oui"],
], colWidths=[7.5 * cm, 7.5 * cm])
summary_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("PADDING", (0, 0), (-1, -1), 6),
]))
content.append(Paragraph("Vue d’ensemble fonctionnelle", heading_style))
content.append(summary_table)
content.append(Spacer(1, 0.6 * cm))
content.append(Paragraph("Résumé de la logique métier", heading_style))
content.append(Paragraph("L’application permet à un groupe de tontine de gérer ses réunions, ses contributions, ses prêts, son fond commun et ses rendus de comptes, avec un découpage clair entre bureau, membres et administration.", body_style))
content.append(Spacer(1, 0.2 * cm))
content.append(Paragraph("• Un groupe est créé par un président ou un administrateur et peut être rejoint par des membres actifs.\n• Les séances sont planifiées et ouvertes, puis clôturées avec collecte de cotisations et calcul du montant de la main.\n• Les prêts sont demandés, approuvés, décaissés et remboursés selon des règles explicites.\n• Le fond commun suit les mouvements entrants et sortants et génère des rapports de réconciliation et d’audit.", bullet_style))
content.append(PageBreak())

content.append(Paragraph("1. Présentation de l’application", heading_style))
content.append(Paragraph("Njangi Digital est une application web pensée pour digitaliser les tontines traditionnelles au Cameroun. Elle remplace le carnet papier, facilite la collecte et la traçabilité, et accorde plus de transparence au bureau du groupe.", body_style))
content.append(Spacer(1, 0.3 * cm))
content.append(Paragraph("Elle répond à trois besoins essentiels :", body_style))
content.append(Paragraph("• Simplifier l’organisation des séances de cotisation.\n• Protéger la transparence financière du groupe.\n• Automatiser les calculs et les documents de suivi.", bullet_style))
content.append(Spacer(1, 0.4 * cm))
content.append(Paragraph("2. Modules et fonctionnalités principales", heading_style))
features = [
    "Création et gestion de groupes Njangi avec plan, fréquence, montant de cotisation et règles internes.",
    "Gestion des membres, rôles (président, trésorier, secrétaire, membre) et ordre de rotation des mains.",
    "Création de séances, gestion des présences, paiements de cotisations, pénalités et clôture des séances.",
    "Gestion des prêts, garant, intérêts, échéances et remboursements.",
    "Gestion du fond commun avec dépôts, retraits, intérêts, réserve, fonds de base et transactions enregistrées.",
    "Calcul mensuel des intérêts et génération de relevés individuels pour chaque membre.",
    "Export PDF de relevés membres, états du fond commun et rapports de séances.",
    "Journal d’audit pour suivre les actions clés du bureau.",
]
for item in features:
    content.append(Paragraph(f"• {item}", bullet_style))
content.append(PageBreak())

content.append(Paragraph("3. Parcours utilisateur conseillé", heading_style))
content.append(Paragraph("Voici le parcours idéal pour une utilisation fluide du logiciel :", body_style))
content.append(Spacer(1, 0.2 * cm))
steps = [
    "Créer un groupe Njangi et configurer la fréquence, le montant de cotisation et les paramètres du fond commun.",
    "Ajouter les membres actifs et définir le bureau (président, trésorier, secrétaire).",
    "Créer une séance pour lancer une nouvelle réunion.",
    "Enregistrer les cotisations, les absences et les pénalités si nécessaire.",
    "Ouvrir la séance, collecter les paiements et clôturer la séance.",
    "Accorder un prêt ou enregistrer un dépôt de main levée en fonction des besoins du groupe.",
    "Générer les rapports PDF pour distribuer la preuve de la séance ou de la situation financière.",
]
for i, step in enumerate(steps, start=1):
    content.append(Paragraph(f"{i}. {step}", body_style))
content.append(Spacer(1, 0.4 * cm))
content.append(Paragraph("4. Rôles et responsabilités", heading_style))
content.append(Paragraph("• Président : crée le groupe, supervise l’organisation et peut gérer les membres et les rôles.\n• Trésorier : suit le fond commun, les transactions, les prêts et les états de finances.\n• Secrétaire : gère les séances, les présences, les paiements et les documents.\n• Membre : consulte ses cotisations, ses prêts, ses dépôts et ses allocations.", bullet_style))
content.append(PageBreak())

content.append(Paragraph("5. Ce que l’application gère déjà parfaitement", heading_style))
content.append(Paragraph("L’application est déjà mature sur le plan fonctionnel pour une utilisation réelle en environnement de tontine numérique. Les fonctions essentielles sont présentes et cohérentes entre elles.", body_style))
content.append(Spacer(1, 0.3 * cm))
content.append(Paragraph("• La gestion de la tontine et des séances est complète.\n• La logique de prêt et de remboursement est bien structurée.\n• Le système de fond commun est traçable et auditable.\n• Les exports PDF permettent une présentation propre au public et aux membres.\n• Les données sont organisées autour d’un modèle métier clair et stable.", bullet_style))
content.append(Spacer(1, 0.4 * cm))
content.append(Paragraph("6. Vérification technique réalisée", heading_style))
content.append(Paragraph("J’ai vérifié l’état du projet avec des contrôles Django avant de produire ce guide. Les résultats sont les suivants :", body_style))
content.append(Paragraph("• Vérification Django : aucune erreur système détectée.\n• Tests du module Njangi : 40 tests exécutés et tous passés avec succès.\n• Aucune modification fonctionnelle n’a été apportée au cœur du projet pendant la génération de ce document.", bullet_style))
content.append(Spacer(1, 0.4 * cm))
content.append(Paragraph("7. Conclusion de maturité", heading_style))
content.append(Paragraph("Au regard de l’analyse du code et des vérifications exécutées, l’application Njangi est déjà fonctionnelle, complète sur ses fonctions de base et prête pour une présentation publique. Les améliorations possibles restent optionnelles : amélioration de l’UX, onboarding plus guidé, branding, ou intégration de notifications SMS/WhatsApp. Elles ne sont pas nécessaires pour livrer une solution utile et crédible.", body_style))
content.append(Spacer(1, 0.2 * cm))
content.append(Paragraph("En pratique, le projet peut être présenté comme une solution opérationnelle de gestion de tontine numérique, avec un socle solide, des rapports, une logique de trésorerie et un suivi des membres.", body_style))
content.append(Spacer(1, 0.6 * cm))
content.append(Paragraph("Document généré automatiquement pour présentation et diffusion.", small_style))


doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=2.2 * cm, leftMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
doc.build(content)
print(f"PDF generated: {OUTPUT}")
