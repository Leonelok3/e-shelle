from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import cm
from pathlib import Path

OUTPUT = Path(__file__).with_name("njangi_guide_presentation_complete.pdf")

styles = getSampleStyleSheet()
PRIMARY = colors.HexColor("#1B6CA8")
ACCENT = colors.HexColor("#F5A623")
LIGHT = colors.HexColor("#EFF6FF")
DARK = colors.HexColor("#0F172A")

TITLE = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, textColor=PRIMARY, leading=30)
SUBTITLE = ParagraphStyle("Subtitle", parent=styles["Heading2"], fontName="Helvetica", fontSize=12, textColor=DARK, leading=16)
HEADING = ParagraphStyle("Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, textColor=PRIMARY, leading=18, spaceBefore=12, spaceAfter=8)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=11, leading=15, textColor=DARK)
BULLET = ParagraphStyle("Bullet", parent=styles["BodyText"], fontName="Helvetica", fontSize=11, leading=15, leftIndent=14, bulletIndent=4, textColor=DARK)
SMALL = ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.grey)

story = []
story.append(Paragraph("Guide de présentation complet — Njangi Digital", TITLE))
story.append(Spacer(1, 0.25 * cm))
story.append(Paragraph("Une brochure de présentation prête pour un public professionnel, des partenaires ou des investisseurs.", SUBTITLE))
story.append(Spacer(1, 0.6 * cm))
story.append(Paragraph("1. Vision et positionnement", HEADING))
story.append(Paragraph("Njangi Digital est une solution de gestion de tontine conçue pour digitaliser les cercles d’épargne informels, garantir la transparence financière, simplifier la gestion des séances et renforcer la confiance entre membres.", BODY))
story.append(Paragraph("Elle cible les groupes traditionnels, associations, comités de solidarité, et petits organismes qui souhaitent gérer facilement leurs cotisations, prêts et transactions sans papier.", BODY))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("2. Problématiques adressées", HEADING))
for item in [
    "Perte de traçabilité des cotisations et remboursements.",
    "Manque de transparence dans la gestion du fond commun.",
    "Difficulté à suivre les prêts, garanties et échéances.",
    "Absence de rapports fiables pour le bureau et les membres.",
    "Usage de papier et erreurs humaines lors des séances.",
]:
    story.append(Paragraph(f"• {item}", BULLET))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("3. Fonctions clés de Njangi", HEADING))
for item in [
    "Création de groupe avec paramètres de cotisation, fréquence et plan d’abonnement.",
    "Gestion des membres, rôles bureau, et ordre de passage pour les mains.",
    "Planification de séances, suivi des présences, paiements et pénalités.",
    "Gestion complète des prêts : demande, approbation, décaissement et remboursement.",
    "Fond commun auditée avec dépôts, retraits, transactions et réserves de sécurité.",
    "Calcul d’intérêts mensuels et relevés individuels pour les déposants.",
    "Exports PDF automatiques : relevés membres, fond commun et rapports de séance.",
    "Journal d’audit pour retracer toutes les actions du bureau.",
]:
    story.append(Paragraph(f"• {item}", BULLET))
story.append(PageBreak())
story.append(Paragraph("4. Parcours utilisateur stratégique", HEADING))
for i, item in enumerate([
    "Création du groupe et configuration des règles de la tontine.",
    "Enregistrement des membres et attribution des rôles (président, trésorier, secrétaire).",
    "Préparation et ouverture d’une séance de cotisation.",
    "Collecte et validation des paiements, déclaration des absences et pénalités.",
    "Clôture de la séance et génération du montant de la main ou du retour en caisse.",
    "Traitement des demandes de prêt, validation par le bureau et suivi du remboursement.",
    "Consultation des états financiers, des relevés et des rapports PDF pour la transparence.",
], start=1):
    story.append(Paragraph(f"{i}. {item}", BODY))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("5. Avantages pour le groupe", HEADING))
for item in [
    "Fiabilité : tout est tracé dans la base de données et horodaté.",
    "Transparence : chaque membre peut obtenir un relevé clair.",
    "Gain de temps : moins de saisie manuelle et de calculs papier.",
    "Sécurité : le fond commun est protégé par des règles de réserve et de garantie.",
    "Professionnel : rapports PDF prêts à être partagés avec les membres.",
]:
    story.append(Paragraph(f"• {item}", BULLET))
story.append(PageBreak())
story.append(Paragraph("6. Démonstration de maturité technique", HEADING))
story.append(Paragraph("Le projet Njangi a été vérifié avec l’outil Django et ses tests automatisés. Le module Njangi contient des tests unitaires qui passent avec succès, ce qui confirme la stabilité du cœur métier.", BODY))
story.append(Paragraph("Points vérifiés :", BODY))
for item in [
    "Vérification Django : aucun problème de configuration détecté.",
    "Tests du module Njangi : 40 tests exécutés, tous passés.",
    "Export PDF existant : relevés membres et état du fond commun.",
    "Modèles métiers établis : groupe, membre, séance, prêt, dépôt, transaction.",
]:
    story.append(Paragraph(f"• {item}", BULLET))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("7. Pourquoi présenter Njangi maintenant", HEADING))
story.append(Paragraph("Njangi est prêt à être présenté en tant que solution opérationnelle. Il est suffisamment abouti pour convaincre des groupes et des partenaires, tout en laissant la place à des améliorations futures sur l’UX et l’intégration mobile.", BODY))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("8. Recommandations de communication", HEADING))
for item in [
    "Mettre en avant le caractère local et adapté aux tontines camerounaises.",
    "Souligner la transparence financière et l’auditabilité.",
    "Préciser que les rapports PDF permettent des réunions claires et professionnelles.",
    "Insister sur la réduction des erreurs papier et le suivi automatisé.",
]:
    story.append(Paragraph(f"• {item}", BULLET))
story.append(PageBreak())
story.append(Paragraph("9. Structure du guide de présentation", HEADING))
story.append(Paragraph("Ce guide est conçu pour accompagner une présentation orale ou une démonstration au public. Il peut être utilisé comme support de communication, comme document de vente ou comme brochure informative.", BODY))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("10. Conclusion", HEADING))
story.append(Paragraph("Njangi Digital est un projet prêt à être présenté en public. Il allie logique métier solide, gestion documentaire, traçabilité financière et fonctionnalités utiles pour les groupes de tontine. Ce guide peut servir de document de référence pour expliquer le fonctionnement, les bénéfices et la valeur de Njangi.", BODY))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Document généré automatiquement — E-Shelle Njangi", SMALL))


doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=2.2 * cm, leftMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
doc.build(story)
print(f"PDF generated: {OUTPUT}")
