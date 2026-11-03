from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
PDF_OUTPUT = ROOT / "proposition_commerciale_tech_provider_eshelle_pricing_final.pdf"
GREEN = colors.HexColor("#087f5b")
INK = colors.HexColor("#172b3a")
MUTED = colors.HexColor("#526574")
PALE_GREEN = colors.HexColor("#e8f5ef")
PALE_BLUE = colors.HexColor("#eef5fb")
GRID = colors.HexColor("#d6e0e7")


def register_fonts():
    fonts = Path(r"C:\Windows\Fonts")
    regular = fonts / "arial.ttf"
    bold = fonts / "arialbd.ttf"
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("E-Shelle", str(regular)))
        pdfmetrics.registerFont(TTFont("E-Shelle-Bold", str(bold)))
        return "E-Shelle", "E-Shelle-Bold"
    return "Helvetica", "Helvetica-Bold"


def make_styles():
    regular, bold = register_fonts()
    base = getSampleStyleSheet()
    return {
        "cover": ParagraphStyle(
            "Cover",
            parent=base["Title"],
            fontName=bold,
            fontSize=28,
            leading=34,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=13,
            leading=19,
            textColor=MUTED,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading1"],
            fontName=bold,
            fontSize=19,
            leading=24,
            textColor=INK,
            spaceBefore=2,
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "Subheading",
            parent=base["Heading2"],
            fontName=bold,
            fontSize=12,
            leading=16,
            textColor=GREEN,
            spaceBefore=9,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=9.4,
            leading=14,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=8,
            leading=11,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName=bold,
            fontSize=10,
            leading=15,
            textColor=INK,
            backColor=PALE_GREEN,
            borderColor=GREEN,
            borderWidth=0.8,
            borderPadding=9,
            spaceBefore=5,
            spaceAfter=10,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=8,
            leading=10.5,
            textColor=INK,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=base["BodyText"],
            fontName=bold,
            fontSize=8,
            leading=10.5,
            textColor=colors.white,
        ),
        "script": ParagraphStyle(
            "Script",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=9.2,
            leading=14,
            textColor=INK,
            backColor=PALE_BLUE,
            borderColor=GRID,
            borderWidth=0.6,
            borderPadding=8,
            spaceBefore=3,
            spaceAfter=9,
        ),
    }


def para(text, style):
    return Paragraph(text, style)


def bullet(text, styles):
    return para(f'<font color="#087f5b"><b>•</b></font>  {text}', styles["body"])


def make_table(rows, widths, styles, header=True):
    formatted = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if header and row_index == 0 else styles["table"]
        formatted.append([para(str(value), style) for value in row])
    table = Table(formatted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), GREEN))
        if len(rows) > 1:
            commands.append(
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f9fb")])
            )
    table.setStyle(TableStyle(commands))
    return table


def footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(GRID)
    canvas.line(1.7 * cm, 1.25 * cm, width - 1.7 * cm, 1.25 * cm)
    canvas.setFont("E-Shelle", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(1.7 * cm, 0.85 * cm, "E-Shelle | Proposition commerciale Tech Provider")
    canvas.drawRightString(width - 1.7 * cm, 0.85 * cm, f"{doc.page}")
    canvas.restoreState()


def build_pdf():
    styles = make_styles()
    regular, _ = register_fonts()
    if regular == "Helvetica":
        pdfmetrics.registerFont(TTFont("E-Shelle", r"C:\Windows\Fonts\arial.ttf"))
    doc = SimpleDocTemplate(
        str(PDF_OUTPUT),
        pagesize=A4,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
        topMargin=1.65 * cm,
        bottomMargin=1.65 * cm,
        title="E-Shelle - Proposition commerciale Tech Provider Meta",
        author="E-Shelle",
        subject="Offres, agents IA, WhatsApp Business et plan de commercialisation",
    )
    story = []

    story.extend(
        [
            Spacer(1, 1.4 * cm),
            para("E-SHELLE", ParagraphStyle(
                "Brand", fontName="E-Shelle-Bold", fontSize=14, leading=18,
                textColor=GREEN, spaceAfter=18,
            )),
            para("Proposition commerciale<br/>Tech Provider Meta", styles["cover"]),
            para(
                "Transformer l’infrastructure WhatsApp Business, les agents IA et les vitrines "
                "métiers d’E-Shelle en offres concrètes pour les entreprises africaines.",
                styles["subtitle"],
            ),
            Spacer(1, 0.25 * cm),
            para(
                "<b>Point de départ :</b> la capture Meta fournie par le dirigeant affiche "
                "« Congratulations! You are now a Tech Provider » et « 2 of 2 steps complete ». "
                "Cette proposition prend ce statut comme annoncé par le dirigeant; elle ne "
                "constitue pas une vérification indépendante des permissions, de l’App Review "
                "ou de la configuration de production.",
                styles["callout"],
            ),
            Spacer(1, 0.2 * cm),
            make_table(
                [
                    ["Actif différenciant", "Ce que le dépôt contient"],
                    ["WhatsApp Business", "Onboarding Meta intégré, inbox par entreprise, CRM et catalogue"],
                    ["Vente assistée par IA", "Agent vendeur ancré sur la fiche, le catalogue et les échanges"],
                    ["Marchés adressés", "Commerce local, restauration, immobilier, auto, services et éducation"],
                    ["Modèle de revenus", "Abonnement logiciel, installation/accompagnement et services partenaires"],
                ],
                [4.1 * cm, 12.5 * cm],
                styles,
            ),
            Spacer(1, 0.6 * cm),
            para("Document de décision et de vente | 3 novembre 2026", styles["small"]),
            para(
                "Proposition construite à partir du dépôt E-Shelle et de sa documentation locale. "
                "Les capacités de code, les tarifs seedés et la disponibilité sur le serveur sont "
                "distingués dans tout le document.",
                styles["small"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("1. Recommandation exécutive", styles["h1"]),
            para(
                "<b>Vendre un résultat complet :</b> « nous aidons votre entreprise à être mieux "
                "présentée sur Google et les moteurs de réponse IA, à recevoir des demandes "
                "WhatsApp mieux organisées et à suivre ses prospects ».",
                styles["callout"],
            ),
            para("Pourquoi E-Shelle a une proposition crédible", styles["h2"]),
            bullet("L’intégration WhatsApp Business est rattachée à une fiche entreprise, plutôt qu’à un simple compte WhatsApp global.", styles),
            bullet("Le dépôt associe vitrine/catalogue, conversations, contacts CRM, statuts de messages et parcours de commande assistée.", styles),
            bullet("L’agent vendeur exploite les informations du commerce et est conçu pour ne pas inventer prix, disponibilité, livraison ou paiement.", styles),
            bullet("E-Shelle possède aussi un socle SEO local et GEO/AEO : pages ville + métier, sitemap, robots.txt, llms.txt et données structurées.", styles),
            bullet("La plateforme possède déjà des modules verticaux utiles pour adapter l’offre à des métiers locaux plutôt que de vendre un chatbot générique.", styles),
            para("Positionnement recommandé", styles["h2"]),
            para(
                "<b>E-Shelle est une plateforme de visibilité et de vente conversationnelle pour "
                "les petites entreprises :</b> des pages métier travaillées pour la recherche "
                "Google et les assistants IA, une vitrine partageable, WhatsApp Business, un "
                "carnet de prospects et des agents IA métier. Le statut Tech Provider facilite "
                "l’intégration et l’onboarding; il ne garantit ni classement, ni citation par "
                "une IA, ni ventes.",
                styles["body"],
            ),
            make_table(
                [
                    ["Cible prioritaire", "Besoin que l’on vend", "Démonstration courte"],
                    ["Commerce avec catalogue", "Présenter les produits et répondre aux demandes", "Fiche → article → conversation WhatsApp"],
                    ["Restaurant / services", "Transformer les demandes répétitives en contacts suivis", "Menu ou service → inbox → CRM"],
                    ["Prestataire déjà actif sur WhatsApp", "Organiser la relation et les relances autorisées", "Connexion de sa propre entreprise par Embedded Signup"],
                    ["Réseau de partenaires", "Déployer des vitrines métier et accompagner les vendeurs", "Business Key, formation et outils de prospection"],
                ],
                [3.4 * cm, 6.4 * cm, 6.8 * cm],
                styles,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("2. Ce que le projet a déjà", styles["h1"]),
            para("Socle produit et applications métier", styles["h2"]),
            make_table(
                [
                    ["Ensemble", "Éléments présents dans le dépôt", "Comment le vendre"],
                    ["Vitrines et marketplace", "Fiches Business, pages publiques, produits/services, zones et liens de contact.", "« Une page professionnelle prête à être partagée et trouvée. »"],
                    ["WhatsApp Business", "Onboarding Embedded Signup, connexion WABA par fiche, inbox, contacts et statuts webhook.", "« Votre canal WhatsApp relié à vos outils de vente. »"],
                    ["Commerce conversationnel", "Catalogue synchronisable; brouillon de commande, récapitulatif et confirmation explicite.", "« L’agent prépare la demande; vous gardez la validation finale. »"],
                    ["Agents IA", "Agent central, génération de contenu/marketing et agent vendeur WhatsApp ancré sur la fiche.", "« Une assistance adaptée à votre activité, supervisée par votre équipe. »"],
                    ["Référencement Google & moteurs IA", "Agent SEO, pages locales ville + métier, sitemap.xml, robots.txt, llms.txt, canonicals et schémas JSON-LD.", "« Structurer votre présence pour être mieux compris par Google et les assistants IA; sans garantir classement ni citation. »"],
                    ["Marketing et visibilité", "AdGen, création de contenus, pages sectorielles et partage Facebook.", "« Produire des contenus et améliorer votre présence locale. »"],
                    ["Réseau partenaire", "Business Key, CRM prospects, lien partenaire, scripts, academy et logique de commission.", "« Un canal d’accompagnement et de distribution de proximité. »"],
                ],
                [3.1 * cm, 7.3 * cm, 6.2 * cm],
                styles,
            ),
            para("Familles de marchés visibles dans le code", styles["h2"]),
            para(
                "Restauration et commerces; immobilier; automobile et transport; agriculture; "
                "artisans et services locaux; beauté/salons; pharmacie/santé; éducation, "
                "formations et préparation aux examens; emploi et mobilité internationale; "
                "boutique et paiements. Cela permet de constituer des démonstrations par secteur "
                "et des offres adaptées. La présence d’un module ne garantit pas à elle seule "
                "son niveau de finition ou sa disponibilité commerciale.",
                styles["body"],
            ),
            para(
                "<b>Sources principales :</b> dossiers business/, whatsapp_commerce/, "
                "e_shelle_ai/, commercial_agent/, adgen/, seo_agent/, business/, "
                "immobilier_cameroun/, resto/, auto_cameroun/, agro/, artisans/, "
                "salonhub/, edu_cm/, formations/, jobs/, sante/ et transport_core/.",
                styles["small"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("3. Offre WhatsApp + Tech Provider", styles["h1"]),
            para("Parcours déjà matérialisés dans le code", styles["h2"]),
            bullet("Connexion d’une entreprise à son propre WABA via Embedded Signup; stockage de la connexion associé à sa fiche.", styles),
            bullet("Inbox privée, contacts et messages rattachés à l’entreprise; réponses libres dans la fenêtre de service applicable.", styles),
            bullet("Catalogue Business synchronisable vers le catalogue WhatsApp de l’entreprise lorsque le plan/droit le permet.", styles),
            bullet("CRM de contacts avec étapes, notes, tags et informations de consentement.", styles),
            bullet("Agent IA vendeur s’appuyant sur la fiche, les articles, les avis et un historique récent; commande créée en brouillon puis confirmée par le client.", styles),
            bullet("Relances individuelles possibles dans le code avec modèle approuvé et consentement explicite; mécanisme protégé par des réglages serveur.", styles),
            para("Ce que Tech Provider change dans le discours", styles["h2"]),
            para(
                "Le client peut connecter ses actifs WhatsApp dans un parcours intégré à E-Shelle. "
                "E-Shelle fournit le logiciel et l’accompagnement; le client conserve la "
                "propriété de son compte et numéro WhatsApp Business et doit disposer des "
                "autorisations, actifs, modèles et moyens de paiement Meta nécessaires.",
                styles["body"],
            ),
            para("Garde-fous commerciaux essentiels", styles["h2"]),
            make_table(
                [
                    ["Dire", "Ne pas promettre"],
                    ["« Connexion WhatsApp Business intégrée, selon votre éligibilité et la configuration Meta. »", "« Toutes les permissions Meta sont automatiquement garanties. »"],
                    ["« L’agent prépare une commande pour validation. »", "« L’IA encaisse et confirme toute commande automatiquement. »"],
                    ["« Les relances exigent les consentements et modèles approuvés requis. »", "« Envois illimités / campagnes de masse déjà actives pour tous. »"],
                    ["« Les frais de messagerie Meta sont à la charge du client. »", "« Votre abonnement E-Shelle inclut les frais Meta. »"],
                ],
                [8.2 * cm, 8.4 * cm],
                styles,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("4. Agents IA : valeur à vendre", styles["h1"]),
            make_table(
                [
                    ["Agent / outil", "Valeur métier", "Preuve et limites"],
                    ["Agent vendeur WhatsApp", "Répondre aux questions, qualifier le besoin, orienter vers un article et préparer un brouillon.", "whatsapp_commerce/brain.py; appui sur données métier; validation/confirmation nécessaire."],
                    ["Agent central E-Shelle", "Point d’entrée IA et outils de génération/assistance.", "e_shelle_ai/services/central_agent.py et services associés; dépend des clés et réglages d’exécution."],
                    ["Agent commercial", "Structurer prospects et prospection, générer des aides à la vente.", "commercial_agent/; qualifier l’exécution réelle et les droits en démo."],
                    ["AdGen / contenu", "Produire des briefs et ressources marketing, dont création de contenus.", "adgen/ et e_shelle_ai/services/tools/; coûts et quotas API à mesurer."],
                    ["SEO, GEO et AEO", "Travailler la visibilité locale et la compréhension des pages par les moteurs de recherche et assistants IA.", "seo_agent/ et business/seo_geo.py; inclut robots.txt, sitemap.xml, llms.txt, pages locales et schémas; ne garantit ni position Google ni citation par un LLM."],
                    ["Phone OCR", "Extraire des numéros depuis une image/import pour faciliter le travail commercial.", "phone_ocr_agent/; ne pas vendre comme consentement à contacter."],
                ],
                [3.6 * cm, 6.0 * cm, 7.0 * cm],
                styles,
            ),
            para("Promesse de confiance", styles["h2"]),
            para(
                "« L’IA prépare et aide; l’entreprise décide. » Les prix, disponibilités, "
                "conditions de livraison, paiements et commandes ne doivent pas être inventés. "
                "Le parcours documenté demande une confirmation explicite et laisse la "
                "validation du paiement au prestataire.",
                styles["callout"],
            ),
            para("Démonstration en cinq minutes", styles["h2"]),
            bullet("Créer/ouvrir une fiche d’un commerce pilote et vérifier ses informations publiques.", styles),
            bullet("Montrer son catalogue et l’onboarding WhatsApp avec un actif de démonstration autorisé.", styles),
            bullet("Simuler une question client sur un produit; vérifier que l’agent reste fidèle au prix/catalogue.", styles),
            bullet("Montrer l’inbox, le contact CRM et le brouillon de commande; expliquer la confirmation humaine.", styles),
            bullet("Présenter les indicateurs qu’on mesurera au pilote : demandes, réponses, clics et commandes confirmées.", styles),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("5. Quoi vendre et comment facturer", styles["h1"]),
            para("Quatre offres faciles à expliquer", styles["h2"]),
            make_table(
                [
                    ["Offre", "Contenu", "Facturation proposée"],
                    ["1. Mise en route WhatsApp", "Diagnostic des actifs, préparation de la fiche/catalogue, assistance à la connexion, vérifications et formation.", "Frais de mise en service à définir après mesure du temps d’accompagnement; devis pilote avant généralisation."],
                    ["2. Abonnement E-Shelle Business", "Vitrine, catalogue, CRM WhatsApp selon formule, assistance IA et outils correspondant aux droits actifs.", "Utiliser les plans présents dans le seeder comme base de proposition; vérifier les prix actifs en production."],
                    ["3. Pack Référencement Google + IA", "Audit de visibilité, pages locales ville + métier, contenus/FAQ utiles, données structurées et accompagnement de la fiche Google Business Profile.", "Prestation ponctuelle ou mensuelle à chiffrer après audit; commencer par 3 à 5 pilotes."],
                    ["4. Pack visibilité & vente", "Catalogue, contenus, SEO local, intégration WhatsApp, atelier équipe et suivi des demandes.", "Prestation forfaitaire récurrente ou ponctuelle; prix à tester avec les pilotes."],
                ],
                [3.5 * cm, 7.0 * cm, 6.1 * cm],
                styles,
            ),
            para("Grille commerciale approuvée — à synchroniser en production", styles["h2"]),
            make_table(
                [
                    ["Plan", "Prix / 30 jours", "Droits/éléments décrits dans le code"],
                    ["Gratuit", "0 XAF", "Fiche basique; pas de CRM WhatsApp selon description du plan."],
                    ["Pro", "5 000 XAF", "5 crédits IA; connexion WhatsApp et CRM avec réponses dans la fenêtre de service."],
                    ["Business", "15 000 XAF", "20 crédits IA, boost 7 jours; catalogue et relances individuelles approuvées sous conditions."],
                    ["Premium", "30 000 XAF", "50 crédits IA, boost 15 jours; catalogue sans plafond déclaré et outils de visibilité SEO/IA."],
                ],
                [3.0 * cm, 3.2 * cm, 10.4 * cm],
                styles,
            ),
            para(
                "<b>Important :</b> ces tarifs constituent la grille commerciale approuvée "
                "pour publication après déploiement. Ils ne prouvent pas que les montants sont "
                "déjà chargés sur le VPS. Vérifier la page et la base de production avant "
                "d'accepter des paiements.",
                styles["callout"],
            ),
            para(
                "Les outils logiciels SEO/IA sont inclus selon le niveau du plan; aucun "
                "accompagnement humain mensuel n’est compris dans Premium. Toute prestation "
                "humaine de référencement ou de création est proposée séparément sur devis. "
                "Autres revenus possibles : Business Key à 9 900 XAF et commissions partenaires "
                "50 % / 30 % sont documentés dans docs/etat-projet-business-key.md. Confirmer "
                "les règles de paiement et de commission en production avant de les annoncer "
                "comme acquis. Ne pas inclure les frais Meta, les coûts LLM, ni un quota de "
                "messages illimité sans chiffrage et règles explicites.",
                styles["body"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("6. Scripts de vente prêts à adapter", styles["h1"]),
            para("Pitch de 30 secondes", styles["h2"]),
            para(
                "« E-Shelle vous aide à mieux présenter votre activité pour Google et les "
                "assistants IA, à recevoir les demandes sur WhatsApp et à suivre vos prospects. "
                "Notre site structure vos pages locales et vos informations; un agent IA peut "
                "assister vos échanges, mais vous gardez la main sur les prix et les confirmations. "
                "On peut commencer par un pilote mesuré. »",
                styles["script"],
            ),
            para("Message de prospection avec demande de permission", styles["h2"]),
            para(
                "« Bonjour [Nom], je vous contacte parce que [raison réelle liée à son activité]. "
                "Nous aidons les entreprises à organiser leur vitrine et leurs demandes WhatsApp "
                "avec E-Shelle. Seriez-vous d’accord pour une démonstration de 10 minutes ? Si ce "
                "n’est pas le bon moment, dites-le-moi et je ne vous relance pas. »",
                styles["script"],
            ),
            para("Restaurant / commerce", styles["h2"]),
            para(
                "« Vos clients peuvent consulter vos plats/produits sur une fiche partageable, "
                "puis vous contacter sur WhatsApp. Nous configurons le catalogue avec vous et "
                "vous montrons comment suivre les demandes. L’agent ne confirme pas une "
                "disponibilité ou un paiement sans votre validation. »",
                styles["script"],
            ),
            para("Référencement Google et assistants IA", styles["h2"]),
            para(
                "« On vous aide à structurer une page claire sur votre activité, votre ville, "
                "vos services et vos réponses fréquentes, avec des éléments techniques pour que "
                "les moteurs puissent mieux comprendre le site. Cela prépare votre visibilité "
                "sur Google et les assistants IA; personne ne peut garantir une position ou une "
                "citation précise. »",
                styles["script"],
            ),
            para("Immobilier / automobile / services", styles["h2"]),
            para(
                "« Nous pouvons structurer vos offres avec photos, détails et moyen de contact, "
                "puis centraliser les demandes entrantes pour mieux les qualifier. Vous pouvez "
                "tester le parcours sur une annonce réelle et mesurer les demandes reçues. »",
                styles["script"],
            ),
            para("Objections", styles["h2"]),
            make_table(
                [
                    ["Objection", "Réponse"],
                    ["« J’ai déjà WhatsApp. »", "« E-Shelle ne remplace pas votre numéro; il relie vos demandes, votre catalogue et votre suivi au canal que vous utilisez déjà. »"],
                    ["« L’IA va répondre n’importe quoi. »", "« Elle est guidée par votre fiche et vos articles. On teste les réponses, et vous validez les commandes et informations sensibles. »"],
                    ["« Ça garantit des ventes ? »", "« Non. Nous fournissons des outils et un accompagnement; nous mesurons demandes et conversions pendant un pilote, sans promettre un chiffre de ventes. »"],
                    ["« Le prix couvre WhatsApp ? »", "« L’abonnement couvre le service E-Shelle selon la formule. Les frais Meta et les coûts variables éventuels sont séparés et expliqués avant activation. »"],
                ],
                [4.0 * cm, 12.6 * cm],
                styles,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("7. Plan de lancement commercial", styles["h1"]),
            make_table(
                [
                    ["Étape", "Action", "Résultat attendu / contrôle"],
                    ["Semaine 1 — préparer", "Confirmer le statut Meta, permissions, app review, actifs, domaines, webhook et parcours Embedded Signup.", "Dossier de preuves interne; checklist d’éligibilité; aucun secret dans le dépôt."],
                    ["Semaine 2 — pilote", "Sélectionner 3 à 5 entreprises consentantes dans 2 secteurs; onboarding individuel et catalogue propre.", "Connexion testée, consentements documentés, équipe formée; support identifié."],
                    ["Semaine 3 — mesurer", "Observer conversations, temps de réponse, demandes qualifiées, erreurs webhook et commandes en brouillon.", "Rapport pilote séparant simulation, acceptation Meta et livraison réelle."],
                    ["Semaine 4 — vendre", "Publier offres et tarifs vérifiés; proposer démonstration, frais d’installation si validés et abonnement.", "Premiers contrats et retours; prix révisé selon coût et charge réelle."],
                    ["Après le pilote", "Activer progressivement modèles approuvés/relances et étendre les verticales qui convertissent.", "Contrôles de consentement, qualité et support réévalués avant chaque extension."],
                ],
                [3.1 * cm, 7.4 * cm, 6.1 * cm],
                styles,
            ),
            para("Indicateurs à suivre dès le pilote", styles["h2"]),
            bullet("Entreprises contactées avec permission, démonstrations tenues et taux de conversion en pilote.", styles),
            bullet("Taux d’onboarding terminé, connexions actives, modèles autorisés et incidents de configuration.", styles),
            bullet("Conversations reçues, délai de première réponse, contacts qualifiés, clics vers WhatsApp et commandes confirmées.", styles),
            bullet("Statuts remis par webhook, erreurs, désinscriptions/STOP et plaintes; distinguer accepté, envoyé et livré.", styles),
            bullet("Revenu par entreprise, temps d’installation/support, coûts API/IA et frais de paiement pour calculer la marge.", styles),
            para("Responsabilités", styles["h2"]),
            para(
                "<b>E-Shelle :</b> logiciel, sécurité des accès, documentation, assistance et suivi des incidents. "
                "<b>Entreprise cliente :</b> propriété de ses actifs, exactitude du catalogue, consentements, "
                "respect des règles applicables et paiement de ses frais Meta. "
                "<b>Partenaire commercial :</b> prospection non abusive, démonstration honnête, pas de promesse "
                "de revenus ni d’envoi sans permission.",
                styles["body"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            para("8. Limites, preuves et décision", styles["h1"]),
            para("À contrôler avant de signer un client", styles["h2"]),
            bullet("Vérifier sur le Meta Business/App Dashboard les permissions, App Review, actifs et fonctionnalités réellement disponibles pour l’application.", styles),
            bullet("Vérifier sur le serveur les variables d’environnement sans exposer de secrets, les migrations, le webhook, les workers Celery/Redis et les drapeaux WhatsApp.", styles),
            bullet("Tester une entreprise de démonstration de bout en bout et confirmer les statuts de livraison par webhook; ne pas confondre réponse HTTP avec livraison.", styles),
            bullet("Confirmer dans la base de production les tarifs actifs, droits des plans et processus de paiement/activation.", styles),
            bullet("Définir contrat, politique de confidentialité, durée de conservation, consentement, retrait et procédure d’assistance.", styles),
            para("Éléments non prouvés par le dépôt local", styles["h2"]),
            make_table(
                [
                    ["Sujet", "État dans cette proposition"],
                    ["Statut Tech Provider", "La capture Meta remise par le dirigeant l’affiche comme obtenu; non vérifié indépendamment dans le compte Meta."],
                    ["Disponibilité en production", "Configuration VPS, permissions Meta, workers, migrations et envois réels non certifiés par la lecture locale."],
                    ["Paiements / ventes / clients actifs", "Non déduits de la présence du code; vérifier les transactions et contrats réels."],
                    ["Tarifs", "Seeder consulté localement; tarifs de la base de production à confirmer."],
                    ["Conformité de chaque campagne", "Dépend du cas d’usage, du consentement, du modèle, des autorisations et des règles Meta en vigueur."],
                ],
                [4.2 * cm, 12.4 * cm],
                styles,
            ),
            para("Sources principales du dépôt", styles["h2"]),
            para(
                "whatsapp_commerce/ (models.py, brain.py, onboarding.py, inbox.py, "
                "orchestrator.py, automations.py, entitlements.py); whatsapp_agent/; "
                "e_shelle_ai/services/; commercial_agent/; business/ et "
                "business/management/commands/seed_business_plans.py; docs/INVENTAIRE_REEL_16_OCT_2026.md; "
                "docs/packs-produits-2026.md; docs/whatsapp-business-mvp.md; "
                "docs/etat-projet-business-key.md; docs/whatsapp-production.md.",
                styles["small"],
            ),
            Spacer(1, 0.25 * cm),
            para(
                "<b>Décision proposée :</b> lancer un pilote encadré de 3 à 5 entreprises, "
                "vendre d’abord la mise en route et l’abonnement dont les droits sont vérifiés, "
                "puis développer les offres gérées après mesure des coûts, des résultats et de "
                "la charge de support.",
                styles["callout"],
            ),
        ]
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF généré : {PDF_OUTPUT}")


if __name__ == "__main__":
    build_pdf()
