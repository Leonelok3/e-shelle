import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

class NumberedCanvas(canvas.Canvas):
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
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Draw beautiful blue background on cover page
            self.saveState()
            self.setFillColor(colors.HexColor("#0D3B6E"))
            self.rect(0, 0, 21*cm, 29.7*cm, fill=1, stroke=0)
            
            # Gold stripe
            self.setFillColor(colors.HexColor("#F5A623"))
            self.rect(0, 8*cm, 21*cm, 0.4*cm, fill=1, stroke=0)
            
            # White and Gold text styling
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 36)
            self.drawString(2*cm, 18*cm, "NJANGI+")
            
            self.setFont("Helvetica", 18)
            self.drawString(2*cm, 16.5*cm, "La tontine numérique révolutionnaire")
            
            self.setFillColor(colors.HexColor("#93C5FD"))
            self.setFont("Helvetica", 13)
            self.drawString(2*cm, 15*cm, "Dossier de Présentation & Synthèse Fonctionnelle")
            
            self.setFillColor(colors.white)
            self.setFont("Helvetica", 11)
            self.drawString(2*cm, 4.2*cm, "Préparé par l'équipe E-Shelle")
            self.drawString(2*cm, 3.6*cm, "À l'attention des investisseurs et gestionnaires de tontines")
            self.drawString(2*cm, 3.0*cm, "Date : Juillet 2026")
            
            # Draw tiny e-shelle logo text
            self.setFont("Helvetica-Bold", 14)
            self.drawString(2*cm, 25*cm, "E-Shelle App Suite")
            
            self.restoreState()
            return
        
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(2*cm, 27.5*cm, 19*cm, 27.5*cm)
        self.drawString(2*cm, 27.8*cm, "Njangi+ by E-Shelle — Dossier de Présentation")
        
        # Footer
        self.line(2*cm, 2.5*cm, 19*cm, 2.5*cm)
        page_str = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(19*cm, 2*cm, page_str)
        self.drawString(2*cm, 2*cm, "© 2026 E-Shelle. Tous droits réservés.")
        self.restoreState()


def generate_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=3*cm,
        bottomMargin=3*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    primary_color = colors.HexColor("#0D3B6E")
    text_color = colors.HexColor("#1E293B")
    
    h1_style = ParagraphStyle(
        "H1_Custom",
        parent=styles["Heading1"],
        textColor=primary_color,
        fontSize=20,
        spaceAfter=15,
        spaceBefore=10
    )
    
    h2_style = ParagraphStyle(
        "H2_Custom",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#1B6CA8"),
        fontSize=14,
        spaceAfter=10,
        spaceBefore=12
    )
    
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        textColor=text_color,
        fontSize=10,
        leading=14,
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        textColor=text_color,
        fontSize=10,
        leading=14,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=5
    )
    
    story = []
    
    # Page 1 is the cover page (handled by canvas)
    story.append(Spacer(1, 10*cm)) # spacer to push content on page 1 below cover text if needed, but since cover is only in canvas, we just put PageBreak
    story.append(PageBreak())
    
    # Page 2: Executive Summary & Table of Contents
    story.append(Paragraph("1. Synthèse Exécutive", h1_style))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<b>Njangi+</b> est une solution fintech de digitalisation des tontines, associations et mutuelles au Cameroun et dans sa diaspora. "
        "Intégrée à la suite d'applications <b>E-Shelle</b>, Njangi+ modernise la gestion financière communautaire traditionnelle "
        "en y injectant de la transparence, de la sécurité et de la traçabilité complète.",
        body_style
    ))
    story.append(Paragraph(
        "L'application résout les trois principaux défis des tontines physiques :<br/>"
        "• <b>Manque de transparence :</b> Registres papier perdus ou falsifiés.<br/>"
        "• <b>Risques de vol/perte :</b> Manipulation de fortes sommes de cash physique.<br/>"
        "• <b>Lenteur administrative :</b> Calculs manuels des taux d'intérêts et des parts de répartition complexes.",
        body_style
    ))
    story.append(Spacer(1, 0.4*cm))
    
    story.append(Paragraph("Sommaire des Sections", h2_style))
    story.append(Paragraph("<b>Section 1 :</b> Synthèse Exécutive & Introduction", bullet_style))
    story.append(Paragraph("<b>Section 2 :</b> Fonctionnalités clés de l'Espace Membre", bullet_style))
    story.append(Paragraph("<b>Section 3 :</b> Fonctionnalités du Bureau d'Administration (Président, Trésorier)", bullet_style))
    story.append(Paragraph("<b>Section 4 :</b> Modèle Premium & Fonctionnalités Avancées", bullet_style))
    story.append(Paragraph("<b>Section 5 :</b> Garanties de Sécurité & Piste d'Audit", bullet_style))
    
    story.append(PageBreak())
    
    # Page 3: Espace Membre
    story.append(Paragraph("2. Fonctionnalités de l'Espace Membre", h1_style))
    story.append(Paragraph(
        "Chaque membre de tontine dispose d'un tableau de bord personnalisé sécurisé lui offrant une autonomie totale et une visibilité en temps réel sur ses avoirs :",
        body_style
    ))
    
    member_feats = [
        ["Fonctionnalité", "Description & Valeur Ajoutée"],
        ["💵 Cotisations en ligne", "Suivi et paiement direct des cotisations associées aux séances de réunion. Plus besoin de se déplacer avec des espèces."],
        ["💰 Épargne & Dépôts", "Possibilité de déposer des fonds dans le fond de réserve de la tontine et de suivre les intérêts capitalisés mensuellement."],
        ["📝 Demande de Prêt", "Soumission de demandes de prêts directement depuis l'espace membre, avec choix du garant et calcul automatique de l'échéancier et des mensualités."],
        ["💼 Portefeuille digital", "Suivi des transactions de crédit/débit, solde disponible, et retraits faciles."],
        ["📄 Relevés PDF", "Génération en un clic du relevé mensuel détaillant les dépôts actifs, la part du membre dans le pool d'intérêts, et le cumul de ses avoirs."]
    ]
    
    t_member = Table(member_feats, colWidths=[5*cm, 12*cm])
    t_member.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    
    story.append(t_member)
    story.append(PageBreak())
    
    # Page 4: Espace Bureau
    story.append(Paragraph("3. Fonctionnalités de l'Espace Bureau", h1_style))
    story.append(Paragraph(
        "Pour les administrateurs (Président, Secrétaire, Trésorier), Njangi+ automatise les tâches complexes de gestion et élimine toute erreur humaine :",
        body_style
    ))
    
    bureau_feats = [
        ["Fonctionnalité", "Description & Usage pour le Bureau"],
        ["📅 Gestion des séances", "Planification, ouverture et clôture des séances de réunion. Le système génère automatiquement les fiches de présence et de cotisation."],
        ["🔍 Suivi des prêts", "Interface d'approbation/rejet des demandes de prêts. Suivi en temps réel des remboursements et alertes en cas de défaut ou de retard."],
        ["🧮 Calculateur d'intérêts", "Distribution mensuelle automatique des intérêts générés par les prêts vers le portefeuille des membres au prorata de leur épargne."],
        ["🤝 Gestion des membres", "Invitation de nouveaux membres via code unique, définition des rôles (Président, Trésorier, Secrétaire, Membre simple)."],
        ["📊 Réconciliation financière", "Module de réconciliation pour comparer la balance théorique de la tontine avec les liquidités réelles en banque ou caisse mobile."]
    ]
    
    t_bureau = Table(bureau_feats, colWidths=[5*cm, 12*cm])
    t_bureau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    
    story.append(t_bureau)
    story.append(PageBreak())
    
    # Page 5: Premium, Sécurité & Conclusion
    story.append(Paragraph("4. Modèle Premium et Monétisation", h1_style))
    story.append(Paragraph(
        "Njangi+ est proposé en modèle Freemium adapté à la taille de chaque association :<br/>"
        "• <b>Plan Gratuit (Free) :</b> Limité à 5 membres maximum, fonctionnalités de base.<br/>"
        "• <b>Plan Standard :</b> Membres illimités, frais mensuels fixes de 3 000 FCFA par groupe.<br/>"
        "• <b>Plan Pro :</b> 7 000 FCFA par mois. Ajoute la piste d'audit avancée et les exports PDF.<br/>"
        "• <b>Plan Association :</b> 15 000 FCFA par mois. Conçu pour les grandes fédérations avec multi-tontines et gestion multi-bureau.",
        body_style
    ))
    
    story.append(Paragraph("5. Sécurité, Piste d'Audit & Conclusion", h1_style))
    story.append(Paragraph(
        "<b>La Piste d'Audit (Audit Trail) :</b><br/>"
        "Chaque action administrative (ouverture de séance, versement de cotisation, modification de taux, décaissement de prêt) "
        "génère un log immuable et horodaté décrivant l'auteur, l'adresse IP et l'impact financier. "
        "Cette transparence totale évite tout litige ou suspicion de favoritisme.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Intégration Mobile Money :</b><br/>"
        "La plateforme est conçue pour s'interfacer avec MTN MoMo et Orange Money, "
        "permettant des transferts instantanés vers le coffre-fort numérique de la tontine.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Conclusion :</b><br/>"
        "Njangi+ n'est pas seulement un outil de gestion, c'est un créateur de confiance numérique. "
        "Il permet aux membres résidant à l'étranger ou localement de participer à leurs réunions familiales "
        "et professionnelles en toute sérénité, tout en offrant aux institutions financières partenaires un historique de crédit fiable "
        "pour octroyer des financements.",
        body_style
    ))
    
    doc.build(story, canvasmaker=NumberedCanvas)


if __name__ == "__main__":
    output_pdf = "Njangi_Presentation_Recap.pdf"
    if len(sys.argv) > 1:
        output_pdf = sys.argv[1]
    
    generate_pdf(output_pdf)
    print(f"Presentation generated at {output_pdf}")
