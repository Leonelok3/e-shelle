from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "strategie_marketing_eshelle_business_key.pdf"


GREEN = colors.HexColor("#1f9d55")
DARK = colors.HexColor("#07130d")
GOLD = colors.HexColor("#d6a21c")
SOFT = colors.HexColor("#eaf7ed")
MUTED = colors.HexColor("#476653")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            alignment=TA_CENTER,
            textColor=DARK,
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontSize=12,
            leading=18,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=22,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=23,
            textColor=GREEN,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=GOLD,
            spaceBefore=9,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontSize=10.3,
            leading=15,
            textColor=DARK,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontSize=8.8,
            leading=12,
            textColor=MUTED,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontSize=10,
            leading=14,
            leftIndent=12,
            firstLineIndent=-8,
            textColor=DARK,
            spaceAfter=4,
        ),
        "script": ParagraphStyle(
            "Script",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            backColor=SOFT,
            borderColor=colors.HexColor("#b9e6c4"),
            borderWidth=0.6,
            borderPadding=7,
            textColor=DARK,
            spaceAfter=8,
        ),
    }


def p(text, style):
    return Paragraph(text, style)


def bullets(items, style):
    return [p(f"- {item}", style) for item in items]


def make_table(rows, widths=None):
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b8c9bd")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fbfffc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4fbf6")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK)
    canvas.rect(0, A4[1] - 1.1 * cm, A4[0], 1.1 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.4 * cm, A4[1] - 0.7 * cm, "E-Shelle Business Key")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 1.4 * cm, A4[1] - 0.7 * cm, "Strategie marketing terrain")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 0.75 * cm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    s = styles()
    story = []

    story.append(Spacer(1, 1.2 * cm))
    story.append(p("Plan Marketing Complet E-Shelle", s["title"]))
    story.append(
        p(
            "Strategie terrain pour obtenir les premiers prestataires, partenaires, clients payants et revenus avec E-Shelle Business Key.",
            s["subtitle"],
        )
    )
    story.append(
        make_table(
            [
                ["Objectif", "Faire rentrer les premiers revenus rapidement avec des services simples a vendre."],
                ["Cible", "Restaurants, pressings, gaz, immobilier, auto, formations, E-Shelle Love, services web et logiciels."],
                ["Methode", "Prospection WhatsApp + demo rapide + fiche gratuite + offre payante + suivi CRM partenaire."],
                ["Priorite", "Vendre ce qui resout un probleme immediat: visibilite, contacts WhatsApp, clients, presence Google."],
            ],
            [4.0 * cm, 12.4 * cm],
        )
    )

    story.append(p("1. Vision economique", s["h1"]))
    story.append(
        p(
            "E-Shelle ne doit pas etre presente comme une simple application. Il faut la vendre comme un ecosysteme qui aide les gens a gagner, vendre, apprendre, rencontrer, se rendre visibles et organiser leur activite.",
            s["body"],
        )
    )
    story.extend(
        bullets(
            [
                "Pour les prestataires: plus de clients, plus de demandes WhatsApp, meilleure presentation.",
                "Pour les partenaires: commissions, scripts, lien de parrainage, CRM, catalogue et missions.",
                "Pour E-Shelle: abonnements, packs, services web, formations, campagnes et logiciels personnalises.",
            ],
            s["bullet"],
        )
    )

    story.append(p("2. Offres a vendre en priorite", s["h1"]))
    story.append(
        make_table(
            [
                ["Offre", "Prix", "Client cible", "Argument de vente"],
                ["Fiche gratuite", "0 FCFA", "Tous commerces", "Demarrer sans risque, obtenir un lien partageable."],
                ["Cours de langue", "5 000/mois", "Etudiants, travailleurs", "Progresser en anglais, allemand, italien avec suivi."],
                ["Formation IA/Marketing", "5 000/mois", "Jeunes, entrepreneurs", "Apprendre a vendre en ligne et utiliser l'IA."],
                ["E-Shelle Love", "5 000/mois", "Celibataires serieux", "Rencontres plus organisees et respectueuses."],
                ["Business", "15 000/mois", "Restaurants, pressing, gaz", "Visibilite, leads WhatsApp, IA commerciale."],
                ["Premium", "30 000/mois", "Immobilier, auto, gros services", "Boost, contenu, priorite locale, campagnes."],
                ["Business Key", "5 000", "Partenaires", "Kit pour vendre E-Shelle et gagner par commission."],
                ["Site vitrine", "50 000+", "PME, pros", "Presence professionnelle, WhatsApp, SEO local."],
                ["Boutique web", "100 000+", "Vendeurs, grossistes", "Catalogue, commande WhatsApp, paiement."],
                ["Logiciel personnalise", "150 000+", "Ecoles, tontines, business", "Application metier adaptee au besoin reel."],
            ],
            [3.4 * cm, 2.5 * cm, 3.6 * cm, 6.9 * cm],
        )
    )

    story.append(PageBreak())
    story.append(p("3. Strategie pour avoir les 10 premiers prestataires", s["h1"]))
    story.append(p("La meilleure strategie est simple: ne pas vendre directement un abonnement. Vendre d'abord une preuve.", s["body"]))
    story.extend(
        bullets(
            [
                "Jour 1: choisir un secteur facile: restaurants, pressing, gaz, immobilier ou auto.",
                "Jour 2: collecter 50 contacts autorises ou publics.",
                "Jour 3: creer 10 fiches gratuites pour montrer la valeur.",
                "Jour 4: envoyer une demo WhatsApp personnalisee.",
                "Jour 5: proposer Business ou Premium aux plus interesses.",
                "Jour 6-7: relancer, proposer paiement Mobile Money et activation.",
            ],
            s["bullet"],
        )
    )
    story.append(p("Objectif numerique", s["h2"]))
    story.append(
        make_table(
            [
                ["Action", "Volume", "Resultat espere"],
                ["Messages envoyes", "100", "20 reponses"],
                ["Demos montrees", "20", "8 interesses"],
                ["Fiches gratuites creees", "10", "5 prospects chauds"],
                ["Ventes Business/Premium", "2 a 5", "30 000 a 150 000 FCFA/mois potentiel"],
            ],
            [5 * cm, 3 * cm, 8.4 * cm],
        )
    )

    story.append(p("4. Outils marketing a utiliser", s["h1"]))
    story.extend(
        bullets(
            [
                "Phone OCR: extraire les numeros depuis captures autorisees.",
                "Contacts WhatsApp: centraliser les prospects.",
                "Agent Commercial IA: generer messages, scripts, objections et propositions.",
                "WhatsApp Agent: creer campagnes, tester, suivre les envois.",
                "SEO Agent: creer des pages locales comme Restaurant a Douala ou Pressing a Yaounde.",
                "AdGen: creer posts, titres et messages publicitaires.",
                "Business Key CRM: suivre qui est interesse, qui doit etre relance, qui a paye.",
            ],
            s["bullet"],
        )
    )

    story.append(p("5. Tunnel de vente recommande", s["h1"]))
    story.append(
        make_table(
            [
                ["Etape", "Objectif", "Message"],
                ["Contact", "Obtenir une reponse", "Bonjour, je peux vous montrer comment recevoir plus de demandes WhatsApp avec E-Shelle ?"],
                ["Demo", "Montrer une preuve", "Voici une fiche simple de votre activite avec bouton WhatsApp."],
                ["Offre", "Convertir", "Le plan Business permet visibilite + campagne + suivi pour 15 000 FCFA/mois."],
                ["Paiement", "Encaisser", "Vous pouvez payer par Mobile Money, on active apres confirmation."],
                ["Relance", "Recuperer les hesitants", "Je peux vous laisser la fiche gratuite, puis activer le boost quand vous etes pret."],
            ],
            [3 * cm, 4.1 * cm, 9.3 * cm],
        )
    )

    story.append(PageBreak())
    story.append(p("6. Scripts WhatsApp prets a utiliser", s["h1"]))
    scripts = [
        ("Restaurant", "Bonjour, E-Shelle aide les restaurants a recevoir plus de commandes WhatsApp avec une fiche visible, un menu partageable et une campagne locale. Voulez-vous une demo rapide ?"),
        ("Pressing", "Bonjour, E-Shelle peut rendre votre pressing visible dans votre quartier et faciliter les demandes clients sur WhatsApp. Je peux vous montrer une fiche demo en 2 minutes ?"),
        ("Gaz", "Bonjour, plusieurs familles cherchent du gaz rapidement par quartier. E-Shelle peut afficher votre depot et envoyer les demandes directement vers WhatsApp. Voulez-vous tester ?"),
        ("Formation", "Bonjour, E-Shelle propose des cours de langue et formations IA/Marketing a partir de 5 000 FCFA/mois. Voulez-vous voir le programme ?"),
        ("E-Shelle Love", "Bonjour, E-Shelle Love aide les personnes serieuses a faire des rencontres plus organisees. L'abonnement commence a 5 000 FCFA/mois. Voulez-vous voir comment ca marche ?"),
        ("Site web", "Bonjour, E-Shelle peut creer un site web ou catalogue pour votre activite avec WhatsApp, SEO local et design professionnel. Voulez-vous une estimation ?"),
        ("Partenaire", "Tu peux gagner avec E-Shelle sans stock. Tu aides les commerces a trouver des clients, tu partages ton lien, et tu gagnes quand un client paie un service reel."),
    ]
    for title, text in scripts:
        story.append(p(title, s["h2"]))
        story.append(p(text, s["script"]))

    story.append(p("7. Objections et reponses", s["h1"]))
    story.append(
        make_table(
            [
                ["Objection", "Reponse"],
                ["Je n'ai pas d'argent.", "On peut commencer par une fiche gratuite. Quand vous voyez l'interet, vous activez Business."],
                ["Je vends deja sur WhatsApp.", "Justement, E-Shelle rend votre offre plus claire et plus facile a partager."],
                ["Je vais reflechir.", "Aucun probleme. Je vous envoie une demo et je vous relance demain."],
                ["Je ne comprends pas internet.", "Vous gardez WhatsApp. E-Shelle organise seulement la presentation et les demandes."],
                ["J'ai peur des arnaques.", "Le paiement est manuel et l'activation se fait apres confirmation. Vous gardez le controle."],
            ],
            [5.2 * cm, 11.2 * cm],
        )
    )

    story.append(PageBreak())
    story.append(p("8. Plan d'action 30 jours", s["h1"]))
    story.append(
        make_table(
            [
                ["Periode", "Objectif", "Actions"],
                ["Jours 1-3", "Preparation", "Choisir 2 secteurs, preparer scripts, tester CRM, creer 20 prospects."],
                ["Jours 4-7", "Premiers contacts", "Envoyer 100 messages propres, creer 10 fiches gratuites."],
                ["Semaine 2", "Conversion", "Relancer, montrer demos, encaisser 2 premiers clients."],
                ["Semaine 3", "Partenaires", "Recruter 5 partenaires Business Key et leur donner scripts."],
                ["Semaine 4", "Systeme", "Mesurer, garder ce qui marche, creer pages SEO locales et campagnes."],
            ],
            [3 * cm, 4 * cm, 9.4 * cm],
        )
    )

    story.append(p("9. Indicateurs a suivre", s["h1"]))
    story.extend(
        bullets(
            [
                "Nombre de prospects ajoutes dans le CRM.",
                "Nombre de messages envoyes et reponses recues.",
                "Nombre de demos montrees.",
                "Nombre de fiches gratuites creees.",
                "Nombre de paiements confirmes.",
                "Revenu mensuel recurrent cree.",
                "Commissions partenaires dues.",
            ],
            s["bullet"],
        )
    )

    story.append(p("10. Recommandation finale", s["h1"]))
    story.append(
        p(
            "La priorite n'est pas de tout vendre en meme temps. Il faut commencer par les offres les plus faciles a comprendre: fiche gratuite, Business a 15 000 FCFA, cours/formation a 5 000 FCFA, E-Shelle Love a 5 000 FCFA, puis sites web et logiciels pour les clients plus solides.",
            s["body"],
        )
    )
    story.append(
        p(
            "Le vrai pouvoir de E-Shelle Business Key est d'organiser une petite force commerciale africaine: chaque partenaire a un kit, un lien, des scripts, un CRM et des apps a vendre.",
            s["script"],
        )
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.3 * cm,
        title="Strategie Marketing E-Shelle Business Key",
        author="E-Shelle",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


if __name__ == "__main__":
    build()
    print(OUTPUT)
