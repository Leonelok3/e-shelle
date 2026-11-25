import io
import os
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from django.conf import settings


# Palette E-Shelle & OCD Live
COLOR_DARK_BG = HexColor("#080E0B")
COLOR_HEADER_BG = HexColor("#0B132B")
COLOR_CARD_BG = HexColor("#FFFFFF")
COLOR_CARD_BORDER = HexColor("#E2E8F0")
COLOR_GREEN = HexColor("#10B981")
COLOR_GREEN_DARK = HexColor("#047857")
COLOR_GREEN_LIGHT = HexColor("#ECFDF5")
COLOR_ORANGE = HexColor("#FF7A00")
COLOR_ORANGE_DARK = HexColor("#C2410C")
COLOR_ORANGE_LIGHT = HexColor("#FFF7ED")
COLOR_AMBER = HexColor("#F59E0B")
COLOR_AMBER_LIGHT = HexColor("#FEF3C7")
COLOR_BLUE = HexColor("#2563EB")
COLOR_BLUE_LIGHT = HexColor("#EFF6FF")
COLOR_PURPLE = HexColor("#7C3AED")
COLOR_PURPLE_LIGHT = HexColor("#F5F3FF")
COLOR_TEXT_PRIMARY = HexColor("#0F172A")
COLOR_TEXT_SECONDARY = HexColor("#334155")
COLOR_TEXT_MUTED = HexColor("#64748B")
COLOR_LIGHT_BG = HexColor("#F8FAFC")
COLOR_WHITE = HexColor("#FFFFFF")


def _draw_header(pdf, page_num, total_pages, title="GUIDE OFFICIEL D'UTILISATION • OCD LIVE"):
    width, height = A4
    header_h = 58

    # Fond d'en-tête sombre
    pdf.setFillColor(COLOR_HEADER_BG)
    pdf.rect(0, height - header_h, width, header_h, fill=True, stroke=False)

    # Ligne d'accent bicolore
    pdf.setFillColor(COLOR_GREEN)
    pdf.rect(0, height - 3, width * 0.45, 3, fill=True, stroke=False)
    pdf.setFillColor(COLOR_ORANGE)
    pdf.rect(width * 0.45, height - 3, width * 0.55, 3, fill=True, stroke=False)

    # Logo ou titre de marque
    logo_path = os.path.join(settings.BASE_DIR, "static", "img", "ocd_live_logo.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(settings.BASE_DIR, "ocd_live", "static", "ocd_live", "img", "ocd_live_logo.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(settings.BASE_DIR, "static", "img", "logo.png")

    drawn_logo = False
    if os.path.exists(logo_path):
        try:
            pdf.drawImage(logo_path, 32, height - header_h + 10, width=95, height=38, mask='auto', preserveAspectRatio=True)
            drawn_logo = True
        except Exception:
            drawn_logo = False

    if not drawn_logo:
        pdf.setFillColor(COLOR_WHITE)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(32, height - 34, "OCD")
        pdf.setFillColor(COLOR_ORANGE)
        pdf.drawString(75, height - 34, "LIVE")
        pdf.setFillColor(COLOR_GREEN)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(32, height - 46, "E-SHELLE.COM")

    # Titre du document à droite
    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(width - 32, height - 26, title)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.drawRightString(width - 32, height - 39, "La Scène Commerciale en Direct d'E-Shelle • Édition Officielle")


def _draw_footer(pdf, page_num, total_pages):
    width, _ = A4
    footer_h = 36

    pdf.setFillColor(COLOR_DARK_BG)
    pdf.rect(0, 0, width, footer_h, fill=True, stroke=False)

    pdf.setFillColor(COLOR_GREEN)
    pdf.rect(0, footer_h - 2, width, 2, fill=True, stroke=False)

    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(32, 20, "OCD LIVE • E-SHELLE LTD")
    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.drawString(32, 9, "Plateforme web : https://e-shelle.com/ocd-live/ • Assistance : contact@e-shelle.com")

    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.setFillColor(HexColor("#FBBF24"))
    pdf.drawString(270, 15, "HOTLINE WHATSAPP RÉGIE : +237 680 625 082")

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_WHITE)
    pdf.drawRightString(width - 32, 14, f"Page {page_num} / {total_pages}")


def _draw_card(pdf, x, y, w, h, bg=COLOR_WHITE, border=COLOR_CARD_BORDER, radius=6):
    pdf.setFillColor(bg)
    pdf.setStrokeColor(border)
    pdf.setLineWidth(0.8)
    pdf.roundRect(x, y, w, h, radius, fill=True, stroke=True)


def _draw_section_header(pdf, x, y, title, subtitle="", badge="", badge_color=COLOR_GREEN):
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x, y, title)

    if badge:
        title_w = pdf.stringWidth(title, "Helvetica-Bold", 13)
        bx = x + title_w + 12
        by = y - 2
        bw = pdf.stringWidth(badge, "Helvetica-Bold", 7.5) + 14
        pdf.setFillColor(badge_color)
        pdf.roundRect(bx, by, bw, 14, 3, fill=True, stroke=False)
        pdf.setFillColor(COLOR_WHITE)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(bx + 7, by + 4, badge)

    if subtitle:
        pdf.setFont("Helvetica", 8.5)
        pdf.setFillColor(COLOR_TEXT_MUTED)
        pdf.drawString(x, y - 13, subtitle)


def generate_guide_pdf() -> bytes:
    """Génère le Guide Officiel Complet OCD Live au format PDF A4 (5 pages)."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    total_pages = 5

    # =========================================================================
    # PAGE 1 : COUVERTURE & MANIFESTE OFFICIEL
    # =========================================================================
    _draw_header(pdf, 1, total_pages, "GUIDE OFFICIEL • ÉDITION 2026")
    _draw_footer(pdf, 1, total_pages)

    # Hero Banner
    hero_y = height - 215
    hero_h = 145
    _draw_card(pdf, 32, hero_y, width - 64, hero_h, bg=HexColor("#060A08"), border=COLOR_GREEN, radius=8)

    # Lueur décorative latérale
    pdf.setFillColor(COLOR_ORANGE)
    pdf.rect(32, hero_y, 4, hero_h, fill=True, stroke=False)

    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(48, hero_y + 112, "PASSEZ EN DIRECT. CONVAINQUEZ.")
    pdf.setFillColor(COLOR_ORANGE)
    pdf.drawString(48, hero_y + 88, "VENDEZ SUR OCD LIVE !")

    pdf.setFillColor(HexColor("#CBD5E1"))
    pdf.setFont("Helvetica", 9)
    intro_lines = [
        "OCD Live est la scène commerciale en direct d'E-Shelle (e-shelle.com), conçue pour permettre",
        "aux entrepreneurs, commerçants, artisans, prestataires de services et créateurs de présenter",
        "leurs produits en direct et de conclure des ventes immédiates devant une large audience ciblée.",
    ]
    cur_y = hero_y + 64
    for line in intro_lines:
        pdf.drawString(48, cur_y, line)
        cur_y -= 13

    # Badges clés
    badges = [
        ("✦ Live Shopping Interactif", COLOR_GREEN),
        ("✦ Audience Cameroun & Diaspora", COLOR_ORANGE),
        ("✦ Commandes WhatsApp en Direct", COLOR_BLUE),
    ]
    bx = 48
    for b_text, b_col in badges:
        bw = pdf.stringWidth(b_text, "Helvetica-Bold", 7.5) + 12
        pdf.setFillColor(b_col)
        pdf.roundRect(bx, hero_y + 14, bw, 16, 3, fill=True, stroke=False)
        pdf.setFillColor(COLOR_WHITE)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(bx + 6, hero_y + 19, b_text)
        bx += bw + 8

    # Bloc 1 : Pourquoi OCD Live ?
    b1_y = hero_y - 145
    b1_h = 132
    _draw_card(pdf, 32, b1_y, width - 64, b1_h)
    _draw_section_header(pdf, 48, b1_y + 108, "1. Pourquoi Choisir le Direct OCD Live ?", "L'alternative aux publications passives qui ne convertissent pas", "RÉVOLUTION VENTE", COLOR_GREEN)

    avantages = [
        ("Visibilité Immédiate :", "Vous ne parlez pas dans le vide. Vous touchez des centaines d'acheteurs attentifs et qualifiés."),
        ("Taux de Conversion x5 à x10 :", "Voir un produit en direct, en action, répondant aux objections, lève 90% des freins à l'achat."),
        ("Prise de Commande Instantanée :", "Lien direct vers votre Boutique Live et votre WhatsApp pour finaliser les ventes sans friction."),
        ("Crédibilité & Confiance :", "Monter sur la scène officielle E-Shelle certifie votre sérieux aux yeux du public et de la diaspora."),
    ]
    cur_y = b1_y + 75
    for a_titre, a_desc in avantages:
        pdf.setFillColor(COLOR_GREEN)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(50, cur_y, "✓ " + a_titre)
        tw = pdf.stringWidth("✓ " + a_titre, "Helvetica-Bold", 8.5)
        pdf.setFillColor(COLOR_TEXT_SECONDARY)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(50 + tw + 6, cur_y, a_desc)
        cur_y -= 17

    # Bloc 2 : À qui s'adresse OCD Live ?
    b2_y = b1_y - 128
    b2_h = 118
    _draw_card(pdf, 32, b2_y, width - 64, b2_h, bg=HexColor("#F8FAFC"))
    _draw_section_header(pdf, 48, b2_y + 94, "2. À Qui S'adresse Cette Plateforme ?", "Tous les secteurs marchands et de services", "TOUS PROFILS", COLOR_ORANGE)

    secteurs = [
        ("🛍️ Commerçants & Boutiques :", "Mode, prêt-à-porter, cosmétiques, chaussures, bijoux, accessoires."),
        ("🌾 Agroalimentaire & Élevage :", "Aliments locaux, produits transformés, fermes avicoles, semences bio."),
        ("📱 Électronique & Solaire :", "Smartphones, ordinateurs, panneaux solaires, kits d'énergie autonome."),
        ("🏢 Immobilier & Services :", "Terrains titrés, villas, formations professionnelles, prestations B2B."),
    ]
    cur_y = b2_y + 64
    for s_titre, s_desc in secteurs:
        pdf.setFillColor(COLOR_ORANGE_DARK)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(50, cur_y, s_titre)
        tw = pdf.stringWidth(s_titre, "Helvetica-Bold", 8.5)
        pdf.setFillColor(COLOR_TEXT_PRIMARY)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(50 + tw + 6, cur_y, s_desc)
        cur_y -= 16

    # Bloc 3 : Sommaire Exécutif du Guide
    b3_y = b2_y - 88
    b3_h = 78
    _draw_card(pdf, 32, b3_y, width - 64, b3_h, bg=COLOR_GREEN_LIGHT, border=COLOR_GREEN)
    pdf.setFillColor(COLOR_GREEN_DARK)
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(48, b3_y + 58, "📖 SOMMAIRE DU GUIDE PRATIQUE")

    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.drawString(48, b3_y + 40, "• Page 2 : Les 4 Formules & Tarifs détaillés (Découverte, Business, Premium, Marathon)")
    pdf.drawString(48, b3_y + 26, "• Page 3 : Le Parcours de Réservation pas-à-pas & La Fiche Officielle PDF")
    pdf.drawString(290, b3_y + 40, "• Page 4 : Vos Outils de Vente : Boutique Live, Vente Flash & WhatsApp WABA")
    pdf.drawString(290, b3_y + 26, "• Page 5 : Les 10 Règles d'Or pour réussir votre direct & Contacts Régie")

    pdf.showPage()

    # =========================================================================
    # PAGE 2 : LES 4 PACKAGES & FORMULES DE DIRECT
    # =========================================================================
    _draw_header(pdf, 2, total_pages, "LES 4 PACKAGES OFFICIELS OCD LIVE")
    _draw_footer(pdf, 2, total_pages)

    p2_top_y = height - 100
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(32, p2_top_y, "Choisissez Votre Durée & Niveau d'Impact Commercial")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(32, p2_top_y - 15, "Des formules adaptées au test de marché jusqu'à l'événement marathon d'envergure nationale.")

    # 4 Cartes Packages
    card_w = width - 64
    card_h = 142
    start_y = p2_top_y - 30

    packages_data = [
        {
            "nom": "Pass Découverte",
            "duree": "60 minutes (1 heure)",
            "prix": "10 000 XAF",
            "desc": "Idéal pour tester le live shopping et pitcher 1 à 3 produits spécifiques.",
            "points": [
                "1 heure de direct sur la scène OCD Live avec assistance régie.",
                "Présentation simple de produits et réponse aux questions de base du chat.",
                "Fiche de réservation officielle PDF avec programme de passage.",
                "Lien de votre boutique ou WhatsApp diffusé pendant la session.",
            ],
            "accent": COLOR_TEXT_SECONDARY,
            "badge": "STARTER",
            "bg": COLOR_WHITE,
            "vip": False,
        },
        {
            "nom": "Pass Business",
            "duree": "120 minutes (2 heures)",
            "prix": "20 000 XAF",
            "desc": "La formule préférée des commerçants : temps optimal pour convaincre et vendre.",
            "points": [
                "2 heures complètes de direct avec démo produits approfondie en situation réelle.",
                "Gestion interactive des questions-réponses en direct et négociation des offres.",
                "Activation de la Boutique Live dédiée avec lien court et QR Code de commande.",
                "Replay accessible sur la plateforme pour les acheteurs ayant manqué le direct.",
            ],
            "accent": COLOR_GREEN,
            "badge": "FORMULE RECOMMANDÉE ★",
            "bg": COLOR_GREEN_LIGHT,
            "vip": False,
        },
        {
            "nom": "Pass Premium",
            "duree": "180 minutes (3 heures)",
            "prix": "30 000 XAF",
            "desc": "Pour les lancements de produits d'envergure, promotions massives et marques établies.",
            "points": [
                "3 heures de diffusion intensive avec format dynamique (Pitch + Démo + Interview).",
                "Mise en avant prioritaire sur la page d'accueil d'OCD Live et d'E-Shelle.",
                "Support technique dédié régie pour basculer entre caméras ou écrans partagés.",
                "Système d'Offre Flash avec compte à rebours interactif activé sur votre vitrine.",
            ],
            "accent": COLOR_BLUE,
            "badge": "HAUTE VISIBILITÉ",
            "bg": COLOR_BLUE_LIGHT,
            "vip": False,
        },
        {
            "nom": "Pass Marathon (Événement VIP)",
            "duree": "300 minutes (5 heures)",
            "prix": "50 000 XAF",
            "desc": "La consécration : journée portes ouvertes, méga-vente et écosystème commercial complet.",
            "points": [
                "5 heures de direct non-stop : invitez des partenaires, clients témoins et experts.",
                "Badge VIP Or permanent et Replay prioritaire en tête de la médiathèque.",
                "Boutique Live Permanente sans expiration avec gestion complète du catalogue.",
                "Passerelle WhatsApp WABA & intégration complète dans le CRM et l'annuaire E-Shelle.",
            ],
            "accent": COLOR_ORANGE,
            "badge": "LE PACK SUPRÊME • VIP OR",
            "bg": COLOR_ORANGE_LIGHT,
            "vip": True,
        },
    ]

    cy = start_y
    for pkg in packages_data:
        box_y = cy - card_h
        _draw_card(pdf, 32, box_y, card_w, card_h, bg=pkg["bg"], border=pkg["accent"])

        # Bandeau de gauche
        pdf.setFillColor(pkg["accent"])
        pdf.rect(32, box_y, 5, card_h, fill=True, stroke=False)

        # En-tête de carte
        pdf.setFillColor(COLOR_TEXT_PRIMARY)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(48, box_y + card_h - 22, pkg["nom"])

        # Badge
        bw = pdf.stringWidth(pkg["badge"], "Helvetica-Bold", 7.5) + 12
        pdf.setFillColor(pkg["accent"])
        pdf.roundRect(165, box_y + card_h - 25, bw, 15, 3, fill=True, stroke=False)
        pdf.setFillColor(COLOR_WHITE)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(171, box_y + card_h - 20, pkg["badge"])

        # Prix et durée
        pdf.setFillColor(pkg["accent"])
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawRightString(width - 48, box_y + card_h - 22, pkg["prix"])
        pdf.setFillColor(COLOR_TEXT_MUTED)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawRightString(width - 48, box_y + card_h - 35, pkg["duree"])

        # Pitch
        pdf.setFillColor(COLOR_TEXT_SECONDARY)
        pdf.setFont("Helvetica-Oblique", 8.5)
        pdf.drawString(48, box_y + card_h - 40, pkg["desc"])

        # Puces
        bullet_y = box_y + card_h - 58
        for pt in pkg["points"]:
            pdf.setFillColor(pkg["accent"])
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(48, bullet_y, "✓")
            pdf.setFillColor(COLOR_TEXT_PRIMARY)
            pdf.setFont("Helvetica", 8)
            pdf.drawString(60, bullet_y, pt)
            bullet_y -= 18

        cy -= (card_h + 10)

    pdf.showPage()

    # =========================================================================
    # PAGE 3 : LE PARCOURS UTILISATEUR PAS-À-PAS
    # =========================================================================
    _draw_header(pdf, 3, total_pages, "PARCOURS RÉSERVATION & PRÉPARATION")
    _draw_footer(pdf, 3, total_pages)

    p3_top_y = height - 95
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(32, p3_top_y, "Le Parcours Simple en 5 Étapes pour Réussir Votre Direct")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(32, p3_top_y - 14, "De l'inscription sur la plateforme jusqu'au passage en régie.")

    steps = [
        {
            "num": "ÉTAPE 1",
            "title": "Réservation du Créneau en Ligne",
            "url": "https://e-shelle.com/ocd-live/reserver/",
            "desc": "Accédez au formulaire public simplifié. Renseignez votre activité, le titre de votre passage et ce que vous allez vendre. Choisissez votre date sur le calendrier (créneaux garantis 1 live à la fois sans double réservation) et sélectionnez votre formule.",
            "tag": "100% Mobile & Rapide",
        },
        {
            "num": "ÉTAPE 2",
            "title": "Paiement Sécurisé & Envoi de la Preuve",
            "url": "MTN Mobile Money • Orange Money • Virement",
            "desc": "Réglez les frais correspondant à votre package. Renseignez votre référence de transaction et uploadez la capture d'écran du paiement. Le statut passe automatiquement à 'En attente de validation régie'.",
            "tag": "Aucune Réservation Sans Paiement",
        },
        {
            "num": "ÉTAPE 3",
            "title": "Attribution du Code Unique & Fiche PDF",
            "url": "Exemple : OCD-2026-A8F2",
            "desc": "Dès l'envoi, vous obtenez votre code de réservation unique et pouvez télécharger immédiatement votre Fiche Officielle de Passage PDF aux couleurs E-Shelle avec les horaires d'installation et règles de régie.",
            "tag": "Fiche de Passage Normée A4",
        },
        {
            "num": "ÉTAPE 4",
            "title": "Génération de l'Affiche Promo HD",
            "url": "https://e-shelle.com/ocd-live/affiche/<code>/",
            "desc": "Ouvrez le studio d'affiches intégré. En 1 clic, générez votre affiche promotionnelle officielle aux formats Story WhatsApp (9:16) et Carré Réseaux Sociaux (1:1), intégrant votre QR Code direct vers votre boutique et votre pitch.",
            "tag": "PNG Haute Définition Exportable",
        },
        {
            "num": "ÉTAPE 5",
            "title": "Configuration Produits & Vente Flash",
            "url": "https://e-shelle.com/ocd-live/suivi/<code>/",
            "desc": "Sur votre tableau de bord de suivi, ajoutez la liste des articles que vous allez présenter avec leurs prix réguliers. Activez votre Vente Flash (-10%, -15%, -20%) pour déclencher le compte à rebours d'urgence d'achat.",
            "tag": "Boutique Live Personnalisée",
        },
    ]

    sy = p3_top_y - 30
    step_h = 104
    for st in steps:
        box_y = sy - step_h
        _draw_card(pdf, 32, box_y, width - 64, step_h)

        # Encart Étape Numéro
        pdf.setFillColor(COLOR_HEADER_BG)
        pdf.roundRect(44, box_y + step_h - 32, 68, 22, 4, fill=True, stroke=False)
        pdf.setFillColor(COLOR_WHITE)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(52, box_y + step_h - 22, st["num"])

        # Titre
        pdf.setFillColor(COLOR_TEXT_PRIMARY)
        pdf.setFont("Helvetica-Bold", 11.5)
        pdf.drawString(122, box_y + step_h - 22, st["title"])

        # Tag
        tw = pdf.stringWidth(st["tag"], "Helvetica-Bold", 7) + 12
        pdf.setFillColor(COLOR_GREEN_LIGHT)
        pdf.roundRect(width - 48 - tw, box_y + step_h - 26, tw, 14, 3, fill=True, stroke=False)
        pdf.setFillColor(COLOR_GREEN_DARK)
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawRightString(width - 54, box_y + step_h - 21, st["tag"])

        # URL / info
        pdf.setFillColor(COLOR_ORANGE_DARK)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(122, box_y + step_h - 38, "Accès / Méthode : " + st["url"])

        # Description sur plusieurs lignes
        pdf.setFillColor(COLOR_TEXT_SECONDARY)
        pdf.setFont("Helvetica", 8)
        words = st["desc"].split()
        lines = []
        cur_l = ""
        for w in words:
            if len((cur_l + " " + w).strip()) > 95:
                lines.append(cur_l)
                cur_l = w
            else:
                cur_l = (cur_l + " " + w).strip()
        if cur_l:
            lines.append(cur_l)

        ly = box_y + step_h - 54
        for l in lines:
            pdf.drawString(48, ly, l)
            ly -= 12

        sy -= (step_h + 12)

    pdf.showPage()

    # =========================================================================
    # PAGE 4 : LES SUPER-POUVOIRS COMMERCIAUX INTÉGRÉS
    # =========================================================================
    _draw_header(pdf, 4, total_pages, "LES SUPER-POUVOIRS COMMERCIAUX")
    _draw_footer(pdf, 4, total_pages)

    p4_top_y = height - 95
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(32, p4_top_y, "Les Outils Qui Transforment les Spectateurs en Acheteurs")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(32, p4_top_y - 14, "OCD Live n'est pas une simple vidéo : c'est un entonnoir de vente complet et automatisé.")

    # Pouvoir 1 : La Boutique Live Dédiée
    pow1_y = p4_top_y - 180
    _draw_card(pdf, 32, pow1_y, width - 64, 155, bg=COLOR_WHITE)
    _draw_section_header(pdf, 48, pow1_y + 130, "A. La Boutique Live Dédiée (/ocd-live/boutique/<code>/)", "Votre vitrine e-commerce accessible avant, pendant et après le direct", "CONVERSION DIRECTE", COLOR_GREEN)

    p1_items = [
        ("Catalogue Visuel & Prix Transparents :", "Tous vos produits présentés en direct s'affichent sous forme de cartes élégantes avec description et disponibilité."),
        ("Commande WhatsApp en 1 Clic :", "Chaque article possède un bouton 'Commander sur WhatsApp' qui ouvre directement la conversation avec le message pré-rempli."),
        ("Accessible Partout :", "Lien court facile à dicter à l'antenne et scannable instantanément via le QR Code intégré sur vos affiches."),
        ("Durabilité Commerciale :", "Vos ventes continuent même après la fin du live. Les personnes visionnant le replay commandent toujours sur votre boutique."),
    ]
    cur_y = pow1_y + 92
    for tit, dsc in p1_items:
        pdf.setFillColor(COLOR_GREEN)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(50, cur_y, "✓ " + tit)
        tw = pdf.stringWidth("✓ " + tit, "Helvetica-Bold", 8.5)
        pdf.setFillColor(COLOR_TEXT_SECONDARY)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(50 + tw + 6, cur_y, dsc)
        cur_y -= 19

    # Pouvoir 2 : Vente Flash & Compte à Rebours
    pow2_y = pow1_y - 170
    _draw_card(pdf, 32, pow2_y, width - 64, 155, bg=COLOR_ORANGE_LIGHT, border=COLOR_ORANGE)
    _draw_section_header(pdf, 48, pow2_y + 130, "B. Le Système de Vente Flash avec Compte à Rebours", "La puissance de l'urgence psychologique pour déclencher le passage à l'action", "EFFET D'URGENCE", COLOR_ORANGE)

    p2_items = [
        ("Chronomètre Interactif en Temps Réel :", "Une bannière lumineuse avec compte à rebours (Heures : Minutes : Secondes) visible sur la boutique de l'intervenant."),
        ("Prix Barrés Automatiques :", "L'algorithme calcule immédiatement la réduction (ex: 15% ou 20%) et affiche le prix d'origine barré à côté du prix promo."),
        ("Message WhatsApp Pré-rempli avec la Remise :", "Le client qui clique sur 'Profiter de l'offre Flash' envoie un message avec le prix réduit officiel spécifié."),
        ("Durée d'Urgence Maîtrisée :", "La promotion flash reste active pendant toute la durée du live et jusqu'à 24h après pour clôturer les commandes indécises."),
    ]
    cur_y = pow2_y + 92
    for tit, dsc in p2_items:
        pdf.setFillColor(COLOR_ORANGE_DARK)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(50, cur_y, "⚡ " + tit)
        tw = pdf.stringWidth("⚡ " + tit, "Helvetica-Bold", 8.5)
        pdf.setFillColor(COLOR_TEXT_PRIMARY)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(50 + tw + 6, cur_y, dsc)
        cur_y -= 19

    # Pouvoir 3 : Écosystème E-Shelle & WABA WhatsApp
    pow3_y = pow2_y - 180
    _draw_card(pdf, 32, pow3_y, width - 64, 165, bg=COLOR_BLUE_LIGHT, border=COLOR_BLUE)
    _draw_section_header(pdf, 48, pow3_y + 140, "C. Intégration Écosystème E-Shelle & WhatsApp Business WABA", "Ne perdez aucun client : convertissez-les en acheteurs fidèles", "MULTI-CANAL E-SHELLE", COLOR_BLUE)

    p3_items = [
        ("Synchronisation Profil Vendeur :", "Chaque intervenant peut relier sa fiche à l'annuaire d'entreprises E-Shelle pour démultiplier son référencement web."),
        ("Connectivité WhatsApp Cloud API (WABA) :", "Possibilité de connecter son compte WABA officiel pour centraliser les messages et configurer des réponses automatiques."),
        ("Campagnes de Retargeting & Relance :", "Diffusez des offres exclusives par notification WhatsApp aux personnes ayant manifesté leur intérêt pendant le direct."),
        ("Visibilité Réseau National & International :", "Profitez de la notoriété de la marque E-Shelle auprès de la diaspora camerounaise et africaine."),
    ]
    cur_y = pow3_y + 102
    for tit, dsc in p3_items:
        pdf.setFillColor(COLOR_BLUE)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(50, cur_y, "◆ " + tit)
        tw = pdf.stringWidth("◆ " + tit, "Helvetica-Bold", 8.5)
        pdf.setFillColor(COLOR_TEXT_PRIMARY)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(50 + tw + 6, cur_y, dsc)
        cur_y -= 19

    pdf.showPage()

    # =========================================================================
    # PAGE 5 : LES 10 RÈGLES D'OR & CONTACTS RÉGIE
    # =========================================================================
    _draw_header(pdf, 5, total_pages, "CHECKLIST DU SUCCÈS & CONTACTS")
    _draw_footer(pdf, 5, total_pages)

    p5_top_y = height - 95
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(32, p5_top_y, "Les 10 Règles d'Or pour Réussir Votre Direct & Contacts Régie")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(32, p5_top_y - 14, "Conseils pratiques pour maximiser votre impact et vos ventes le Jour J.")

    # 10 Règles sous forme de 2 colonnes
    col_w = (width - 64 - 16) / 2
    col_h = 360
    col_y = p5_top_y - 390

    # Colonne 1 : Technique & Préparation
    _draw_card(pdf, 32, col_y, col_w, col_h, bg=COLOR_WHITE)
    _draw_section_header(pdf, 44, col_y + col_h - 24, "TECHNIQUE & SETUP", "Préparez votre studio", "CHECKLIST", COLOR_GREEN)

    c1_rules = [
        ("1. Éclairage Impeccable", "Placez-vous face à la lumière (fenêtre ou anneau LED). Évitez tout contre-jour sombre."),
        ("2. Son Clair & Net", "Utilisez un micro-cravate ou des écouteurs filaires. Un mauvais son fait fuir 80% des spectateurs."),
        ("3. Connexion 4G / Fibre Stable", "Assurez-vous d'avoir au moins 10 Mbps en upload. Gardez une connexion de secours (partage 4G)."),
        ("4. Arrivée 30 min Avant", "Connectez-vous impérativement 30 minutes avant l'heure du live pour le test technique avec la régie."),
        ("5. Produits Prêts à Portée", "Déballez et disposez tous les articles sur votre table pour éviter de quitter l'écran des yeux."),
    ]
    cur_y = col_y + col_h - 60
    for r_tit, r_txt in c1_rules:
        pdf.setFillColor(COLOR_GREEN)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(44, cur_y, r_tit)
        pdf.setFillColor(COLOR_TEXT_SECONDARY)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(44, cur_y - 13, r_txt)
        cur_y -= 48

    # Colonne 2 : Vente, Éthique & Conversion
    col2_x = 32 + col_w + 16
    _draw_card(pdf, col2_x, col_y, col_w, col_h, bg=COLOR_WHITE)
    _draw_section_header(pdf, col2_x + 12, col_y + col_h - 24, "VENTE & CONVERSION", "Captivez votre audience", "IMPACT", COLOR_ORANGE)

    c2_rules = [
        ("6. Offre Exclusivité Direct", "Proposez un prix ou un cadeau uniquement valable pendant le live pour forcer la décision."),
        ("7. Interaction Personnalisée", "Saluez les spectateurs par leur prénom, répondez avec enthousiasme et souriez à l'écran."),
        ("8. Démonstration Vivante", "Ne vous contentez pas de parler : montrez le produit, essayez-le, détaillez ses bénéfices concrets."),
        ("9. Transparence Totale", "Prix clairs, modalités de livraison précises. Pas de fausses promesses ni d'annonces mensongères."),
        ("10. Appel à l'Action Régulier", "Rappelez toutes les 10 minutes comment commander via le lien de la boutique ou WhatsApp."),
    ]
    cur_y = col_y + col_h - 60
    for r_tit, r_txt in c2_rules:
        pdf.setFillColor(COLOR_ORANGE_DARK)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(col2_x + 12, cur_y, r_tit)
        pdf.setFillColor(COLOR_TEXT_SECONDARY)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(col2_x + 12, cur_y - 13, r_txt)
        cur_y -= 48

    # Bloc Régie & Contacts Officiels
    reg_y = col_y - 170
    reg_h = 155
    _draw_card(pdf, 32, reg_y, width - 64, reg_h, bg=COLOR_HEADER_BG, border=COLOR_ORANGE)

    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(48, reg_y + reg_h - 28, "BESOIN D'ACCOMPAGNEMENT OU D'ASSISTANCE RÉGIE ?")

    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(48, reg_y + reg_h - 44, "L'équipe OCD Live et E-Shelle vous accompagne avant, pendant et après votre passage.")

    # 3 colonnes de contacts
    cw = (width - 64 - 32) / 3

    # Col 1 : WhatsApp
    pdf.setFillColor(HexColor("#1E293B"))
    pdf.roundRect(48, reg_y + 16, cw, 80, 4, fill=True, stroke=False)
    pdf.setFillColor(COLOR_GREEN)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(58, reg_y + 76, "💬 WHATSAPP RÉGIE")
    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(58, reg_y + 56, "+237 680 625 082")
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(58, reg_y + 38, "Assistance directe & tests")
    pdf.drawString(58, reg_y + 26, "Disponible 7j/7 de 8h à 21h")

    # Col 2 : Web & Réservation
    pdf.setFillColor(HexColor("#1E293B"))
    pdf.roundRect(48 + cw + 16, reg_y + 16, cw, 80, 4, fill=True, stroke=False)
    pdf.setFillColor(COLOR_ORANGE)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(48 + cw + 26, reg_y + 76, "🌐 SITE OFFICIEL")
    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(48 + cw + 26, reg_y + 56, "e-shelle.com/ocd-live/")
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(48 + cw + 26, reg_y + 38, "Réservation & Planning")
    pdf.drawString(48 + cw + 26, reg_y + 26, "Boutiques et replays")

    # Col 3 : Email & Siège
    pdf.setFillColor(HexColor("#1E293B"))
    pdf.roundRect(48 + (cw + 16) * 2, reg_y + 16, cw, 80, 4, fill=True, stroke=False)
    pdf.setFillColor(HexColor("#FBBF24"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(48 + (cw + 16) * 2 + 10, reg_y + 76, "🏢 SIÈGE & EMAIL")
    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(48 + (cw + 16) * 2 + 10, reg_y + 56, "contact@e-shelle.com")
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(48 + (cw + 16) * 2 + 10, reg_y + 38, "Douala / Yaoundé, Cameroun")
    pdf.drawString(48 + (cw + 16) * 2 + 10, reg_y + 26, "E-Shelle Ltd International")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer.getvalue()
