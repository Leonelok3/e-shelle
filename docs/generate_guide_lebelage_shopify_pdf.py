from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
PDF_OUTPUT = ROOT / "guide_utilisation_lebelage_shopify.pdf"


def p(text, style):
    return Paragraph(text.replace("\n", "<br/>"), style)


def build_pdf():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4c1d95"),
        spaceAfter=18,
    )
    h2 = ParagraphStyle(
        "H2Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#111827"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=7,
    )
    note = ParagraphStyle(
        "NoteCustom",
        parent=body,
        backColor=colors.HexColor("#eef2ff"),
        borderColor=colors.HexColor("#c7d2fe"),
        borderWidth=1,
        borderPadding=8,
        leading=14,
    )

    doc = SimpleDocTemplate(
        str(PDF_OUTPUT),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title="Guide LEBELAGE Shopify",
    )

    story = [
        p("Guide d'utilisation - LEBELAGE vers Shopify", title),
        p(
            "Ce guide explique comment exporter les produits LEBELAGE en local, exporter une boutique Shopify, comparer les deux sources, calculer un prix final avec marge, generer des descriptions vendeuses et importer en brouillon sans publier directement.",
            note,
        ),
        p("1. Lien local", h2),
        p("Ouvrir l'interface dans le navigateur: http://127.0.0.1:8000/lebelage-importer/", body),
        p("2. Exporter LEBELAGE en local", h2),
        p(
            "Renseigner l'URL de depart, la limite produits, les pages max, puis cliquer sur Exporter LEBELAGE en local. Les fichiers crees sont tmp/lebelage_products.json et tmp/lebelage_products.csv.",
            body,
        ),
        p("3. Calcul automatique de marge", h2),
        p(
            "Renseigner Livraison par produit et Marge par produit avant l'export. Le systeme calcule: prix final = prix source + livraison + marge. Le prix final est sauvegarde dans les fichiers locaux.",
            body,
        ),
        p("4. Descriptions vendeuses", h2),
        p(
            "A chaque export LEBELAGE, le systeme ajoute une description vendeuse locale: presentation du produit, points forts, conseil boutique et rappel de verification cosmetique. Cela fonctionne sans credit API.",
            body,
        ),
        p("5. Exporter Shopify en local", h2),
        p(
            "Configurer SHOPIFY_SHOP_DOMAIN et SHOPIFY_ADMIN_ACCESS_TOKEN, puis cliquer sur Exporter ma boutique Shopify. Les fichiers crees sont tmp/shopify_products.json et tmp/shopify_products.csv.",
            body,
        ),
        p("6. Comparateur LEBELAGE vs Shopify", h2),
        p(
            "Apres les deux exports, cliquer sur Comparer LEBELAGE vs Shopify. Le systeme affiche les nouveaux produits, les doublons possibles et les prix differents. Les fichiers crees sont tmp/lebelage_shopify_comparison.json et tmp/lebelage_shopify_comparison.csv.",
            body,
        ),
        p("7. Import en brouillon", h2),
        p(
            "Pour importer, taper BROUILLON dans le champ de confirmation, puis cliquer sur Importer en brouillon. Les produits sont envoyes dans Shopify avec le statut draft. Ils ne sont pas publies directement.",
            body,
        ),
        p("8. Permissions Shopify", h2),
        p(
            "Pour exporter Shopify: read_products. Pour importer en brouillon: write_products. Le token doit venir d'une app Shopify autorisee pour la boutique concernee.",
            body,
        ),
    ]

    table_data = [
        ["Action", "Fichier local produit"],
        ["Export LEBELAGE", "tmp/lebelage_products.json / tmp/lebelage_products.csv"],
        ["Export Shopify", "tmp/shopify_products.json / tmp/shopify_products.csv"],
        ["Comparaison", "tmp/lebelage_shopify_comparison.json / tmp/lebelage_shopify_comparison.csv"],
        ["Guide PDF", "docs/guide_utilisation_lebelage_shopify.pdf"],
    ]
    table = Table(table_data, colWidths=[4.2 * cm, 12 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4c1d95")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([Spacer(1, 8), table])

    story.extend(
        [
            p("9. Utilisation avec plusieurs boutiques", h2),
            p(
                "Changer SHOPIFY_SHOP_DOMAIN et SHOPIFY_ADMIN_ACCESS_TOKEN pour chaque boutique. Utiliser des fichiers d'export separes par client pour eviter les melanges.",
                body,
            ),
            p("10. Regles de securite", h2),
            p(
                "Ne jamais mettre les tokens Shopify, le fichier .env reel, les mots de passe ou les exports clients sensibles sur une cle USB partagee. Donner plutot un .env.example et demander au partenaire de configurer ses propres identifiants.",
                note,
            ),
        ]
    )

    doc.build(story)
    print(f"PDF genere: {PDF_OUTPUT}")


if __name__ == "__main__":
    build_pdf()
