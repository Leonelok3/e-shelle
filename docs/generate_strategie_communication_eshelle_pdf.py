from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
PDF_OUTPUT = ROOT / "strategie_communication_eshelle.pdf"

DARK = colors.HexColor("#03130c")
GREEN = colors.HexColor("#35b257")
GOLD = colors.HexColor("#d49618")
LIGHT = colors.HexColor("#f6fff6")
MUTED = colors.HexColor("#47604f")


def styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            alignment=TA_CENTER,
            textColor=LIGHT,
            spaceAfter=16,
        )
    )
    base.add(
        ParagraphStyle(
            name="CoverSub",
            parent=base["BodyText"],
            fontSize=12,
            leading=17,
            alignment=TA_CENTER,
            textColor=LIGHT,
        )
    )
    base.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=DARK,
            spaceBefore=12,
            spaceAfter=8,
        )
    )
    base.add(
        ParagraphStyle(
            name="SubTitle",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=GREEN,
            spaceBefore=7,
            spaceAfter=5,
        )
    )
    base.add(
        ParagraphStyle(
            name="Text",
            parent=base["BodyText"],
            fontSize=9.6,
            leading=14,
            textColor=colors.HexColor("#172017"),
            spaceAfter=5,
        )
    )
    base.add(
        ParagraphStyle(
            name="BulletText",
            parent=base["BodyText"],
            fontSize=9.4,
            leading=13,
            leftIndent=12,
            firstLineIndent=-8,
            textColor=colors.HexColor("#172017"),
        )
    )
    base.add(
        ParagraphStyle(
            name="Quote",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=DARK,
            backColor=colors.HexColor("#eaf9ec"),
            borderColor=GREEN,
            borderWidth=1,
            borderPadding=8,
            spaceBefore=6,
            spaceAfter=10,
        )
    )
    return base


def p(text, style):
    return Paragraph(text.replace("&", "&amp;"), style)


def bullet(text, style):
    return Paragraph(f"- {text}".replace("&", "&amp;"), style)


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK)
    canvas.rect(0, A4[1] - 1.05 * cm, A4[0], 1.05 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.4 * cm, A4[1] - 0.68 * cm, "E-Shelle")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 1.4 * cm, A4[1] - 0.68 * cm, "Strategie de communication")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 0.72 * cm, f"Page {doc.page}")
    canvas.restoreState()


def cover(story, s):
    table = Table(
        [[
            p("Strategie de communication E-Shelle", s["CoverTitle"]),
            p("Faire connaitre E-Shelle aux prestataires, aux clients et aux partenaires terrain.", s["CoverSub"]),
        ]],
        colWidths=[17 * cm],
        rowHeights=[9.8 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK),
                ("BOX", (0, 0), (-1, -1), 1.2, GREEN),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.7 * cm))
    story.append(p("Phrase centrale", s["SubTitle"]))
    story.append(p("Vous cherchez quelque chose au Cameroun ? E-Shelle trouve ou demande au reseau pour vous.", s["Quote"]))
    story.append(p("Document operationnel pour lancer E-Shelle sur le terrain, recruter les prestataires, attirer les clients et piloter les partenaires.", s["Text"]))
    story.append(PageBreak())


def add_table(story, rows, widths):
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9eadc")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fbfffb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.3 * cm))


def build_pdf():
    s = styles()
    story = []
    cover(story, s)

    story.append(p("1. Positionnement", s["SectionTitle"]))
    story.append(p("E-Shelle doit etre presente comme un moteur local assiste par IA. Le client cherche un produit, un service, un bien ou une opportunite. Si le resultat existe, il contacte directement. Sinon, E-Shelle enregistre la demande et active le reseau local.", s["Text"]))

    story.append(p("2. Objectifs sur 90 jours", s["SectionTitle"]))
    for item in [
        "Faire comprendre E-Shelle en une phrase simple.",
        "Enregistrer les prestataires utiles par ville et quartier.",
        "Faire utiliser la recherche E-Shelle par les clients.",
        "Transformer les recherches sans resultat en demandes exploitables.",
        "Former les partenaires a vendre la Business Key et les fiches prestataires.",
        "Mesurer chaque semaine recherches, demandes, contacts et conversions.",
    ]:
        story.append(bullet(item, s["BulletText"]))

    story.append(p("3. Cibles et messages", s["SectionTitle"]))
    add_table(
        story,
        [
            ["Cible", "Message principal", "Objectif"],
            ["Prestataires", "Les clients cherchent deja vos services. E-Shelle vous rend visible.", "Creer fiches, collecter WhatsApp, photos, services et zones."],
            ["Clients", "Tapez votre besoin. E-Shelle trouve, propose des pistes ou demande au reseau.", "Faire adopter la recherche E-Shelle."],
            ["Partenaires", "Avec la Business Key, vous gagnez en aidant les business locaux.", "Former une force commerciale terrain."],
        ],
        [3.2 * cm, 8.2 * cm, 5.2 * cm],
    )

    story.append(p("4. Strategie de lancement", s["SectionTitle"]))
    add_table(
        story,
        [
            ["Phase", "Duree", "Actions"],
            ["Preuve locale", "7 jours", "Choisir 1 ou 2 niches, creer 50 fiches, faire 100 recherches test, identifier les manques."],
            ["Communication terrain", "14 jours", "20 prestataires contactes/jour, 5 demos/jour, statuts WhatsApp, posts Facebook, videos courtes."],
            ["Acceleration", "30 a 90 jours", "Former partenaires, suivre Command Center, lancer campagnes par quartier, publier pages SEO locales."],
        ],
        [4 * cm, 3 * cm, 9.6 * cm],
    )

    story.append(p("5. Niches recommandees", s["SectionTitle"]))
    for item in ["Studios et chambres a Yaounde.", "Restaurants a Douala.", "Gaz et livraison par quartier.", "Artisans et services urgents."]:
        story.append(bullet(item, s["BulletText"]))

    story.append(PageBreak())
    story.append(p("6. Scripts prets a utiliser", s["SectionTitle"]))
    scripts = [
        ("Statut WhatsApp client", "Vous cherchez quelque chose au Cameroun ? E-Shelle trouve ou demande au reseau pour vous. Testez une recherche : resto, gaz, studio, formation, service, produit."),
        ("Message prestataire", "Bonjour, E-Shelle aide les clients a trouver des prestataires locaux par ville et quartier. Nous pouvons creer votre fiche avec vos services, photos, WhatsApp et zone. Voulez-vous voir une demo ?"),
        ("Message partenaire", "E-Shelle Business Key vous donne les outils pour vendre des services digitaux locaux : fiches, IA marketing, campagnes WhatsApp, prospection et demandes clients. La cle est a 9 900 XAF."),
        ("Post Facebook", "E-Shelle simplifie la recherche locale au Cameroun. Vous cherchez un produit, un service, un studio, un restaurant ou une formation ? E-Shelle trouve ou demande au reseau local."),
        ("TikTok/Reel", "0-5s : Vous cherchez un service ? 5-12s : Tapez votre besoin sur E-Shelle. 12-20s : E-Shelle trouve ou demande au reseau. 20-25s : E-Shelle, le moteur local assiste par IA."),
    ]
    for title, text in scripts:
        story.append(p(title, s["SubTitle"]))
        story.append(p(text, s["Text"]))

    story.append(p("7. Plan hebdomadaire", s["SectionTitle"]))
    add_table(
        story,
        [
            ["Jour", "Mission"],
            ["Lundi", "Choisir la niche, verifier les demandes non satisfaites, fixer objectifs."],
            ["Mardi", "Prospection prestataires, creation de fiches, contenus AdGen."],
            ["Mercredi", "Campagne WhatsApp, publication Facebook, relances partenaires."],
            ["Jeudi", "Demos terrain, collecte photos/prix/zones/WhatsApp."],
            ["Vendredi", "Videos courtes, statuts WhatsApp, mise en avant premium."],
            ["Samedi", "Test client public, demandes sans resultat, contact prestataires capables."],
            ["Dimanche", "Bilan Command Center, top recherches, categories manquantes, plan suivant."],
        ],
        [3 * cm, 13.6 * cm],
    )

    story.append(PageBreak())
    story.append(p("8. Indicateurs a suivre", s["SectionTitle"]))
    indicators = [
        "Nombre de recherches.",
        "Nombre de demandes sans resultat.",
        "Nombre de fiches creees.",
        "Nombre de prestataires actifs.",
        "Nombre de clics WhatsApp.",
        "Nombre de campagnes creees.",
        "Nombre de partenaires formes.",
        "Nombre de paiements Business Key.",
        "Nombre de categories sans prestataire.",
    ]
    for item in indicators:
        story.append(bullet(item, s["BulletText"]))

    story.append(p("9. Methode partenaire", s["SectionTitle"]))
    for item in [
        "Trouver des prestataires dans sa zone.",
        "Montrer E-Shelle en 2 minutes.",
        "Creer ou ameliorer leur fiche.",
        "Generer un contenu AdGen.",
        "Noter le prospect dans le CRM.",
        "Relancer proprement.",
        "Suivre les commissions.",
    ]:
        story.append(bullet(item, s["BulletText"]))

    story.append(p("10. Regles de qualite fiche", s["SectionTitle"]))
    story.append(p("Une fiche prestataire doit contenir : nom clair, ville, quartier, WhatsApp, description utile, photo reelle si possible, services ou prix, appel a l'action.", s["Text"]))

    story.append(p("11. Utilisation des outils E-Shelle", s["SectionTitle"]))
    add_table(
        story,
        [
            ["Outil", "Usage"],
            ["Arsenal IA", "Voir les agents et declencher actions."],
            ["Command Center", "Suivre recherches, demandes et opportunites."],
            ["Agent Prospection", "Scorer et relancer les prospects."],
            ["AdGen", "Creer contenus, scripts video et messages."],
            ["WhatsApp Agent", "Creer campagnes et relances."],
            ["SEO Agent", "Construire la visibilite locale."],
            ["Audio Studio", "Preparer voix-off et musiques de videos."],
        ],
        [4.2 * cm, 12.4 * cm],
    )

    story.append(p("Message final", s["SectionTitle"]))
    story.append(p("E-Shelle n'est pas seulement un site d'annonces. E-Shelle est un reseau local assiste par IA. Le client cherche, E-Shelle trouve ou demande au reseau. Le prestataire gagne en visibilite. Le partenaire gagne en aidant les business locaux.", s["Quote"]))

    doc = SimpleDocTemplate(
        str(PDF_OUTPUT),
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.2 * cm,
        title="Strategie de communication E-Shelle",
        author="E-Shelle",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(PDF_OUTPUT)


if __name__ == "__main__":
    build_pdf()
