import io
import os
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


# Palette de couleurs officielles E-Shelle & OCD Live
COLOR_DARK_BG = HexColor("#0A0E0C")
COLOR_SURFACE = HexColor("#111714")
COLOR_CARD_BG = HexColor("#F8FAFC")
COLOR_CARD_BORDER = HexColor("#E2E8F0")
COLOR_GREEN = HexColor("#16A34A")
COLOR_GREEN_LIGHT = HexColor("#DCFCE7")
COLOR_ORANGE = HexColor("#E65100")
COLOR_AMBER = HexColor("#D97706")
COLOR_RED = HexColor("#DC2626")
COLOR_TEXT_PRIMARY = HexColor("#0F172A")
COLOR_TEXT_SECONDARY = HexColor("#475569")
COLOR_TEXT_MUTED = HexColor("#64748B")
COLOR_WHITE = HexColor("#FFFFFF")


def _truncate(text: str, max_len: int = 80) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text


def _split_text_lines(text: str, max_chars_per_line: int = 80) -> list[str]:
    if not text:
        return []
    words = text.strip().split()
    lines, current_line = [], ""
    for w in words:
        test_line = (current_line + " " + w).strip()
        if len(test_line) > max_chars_per_line:
            if current_line:
                lines.append(current_line)
            current_line = w
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def generate_live_booking_pdf(booking) -> bytes:
    """
    Génère la fiche officielle de réservation OCD Live au format PDF A4.
    Utilise ReportLab pour un rendu vectoriel haute précision, propre, aux couleurs E-Shelle.
    """
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4  # 595.27 x 841.89 points

    pdf.setTitle(f"Fiche_Reservation_OCD_Live_{booking.code_reservation}")
    pdf.setAuthor("E-Shelle OCD Live")
    pdf.setSubject("Fiche officielle de passage en direct OCD Live")

    # ──────────────────────────────────────────────────────────────────────────
    # 1. EN-TÊTE SUPÉRIEUR (BANDEAU NOIR ÉLÉGANT & ACCENTS COULEURS)
    # ──────────────────────────────────────────────────────────────────────────
    header_height = 88
    header_y = page_height - header_height

    # Fond noir
    pdf.setFillColor(COLOR_DARK_BG)
    pdf.rect(0, header_y, page_width, header_height, fill=True, stroke=False)

    # Ligne d'accent supérieure double (Vert E-Shelle & Orange OCD)
    pdf.setFillColor(COLOR_GREEN)
    pdf.rect(0, page_height - 4, page_width * 0.45, 4, fill=True, stroke=False)
    pdf.setFillColor(COLOR_ORANGE)
    pdf.rect(page_width * 0.45, page_height - 4, page_width * 0.55, 4, fill=True, stroke=False)

    # Logo OCD Live
    logo_drawn = False
    logo_path = os.path.join(settings.BASE_DIR, "ocd_live", "static", "ocd_live", "img", "ocd_live_logo.png")
    if os.path.exists(logo_path):
        try:
            pdf.drawImage(logo_path, 32, header_y + 14, width=130, height=56, mask='auto', preserveAspectRatio=True)
            logo_drawn = True
        except Exception:
            pass

    if not logo_drawn:
        # Fallback typographique soigné si l'image ne charge pas
        pdf.setFillColor(COLOR_WHITE)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(32, header_y + 44, "OCD ")
        pdf.setFillColor(COLOR_ORANGE)
        pdf.drawString(82, header_y + 44, "LIVE")
        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColor(COLOR_WHITE)
        pdf.drawString(32, header_y + 26, "E-SHELLE.COM")

    # Titre du document
    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawRightString(page_width - 32, header_y + 50, "FICHE DE RÉSERVATION OCD LIVE")

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.drawRightString(page_width - 32, header_y + 34, "Passage en Direct • Pitch Produits & Services • E-Shelle")

    pdf.setFont("Helvetica-Bold", 9)
    pdf.setFillColor(HexColor("#FBBF24"))
    pdf.drawRightString(page_width - 32, header_y + 18, f"Code dossier : {booking.code_reservation}")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. BANDEAU DE STATUT & INFORMATIONS RAPIDES
    # ──────────────────────────────────────────────────────────────────────────
    status_bar_y = header_y - 36
    pdf.setFillColor(HexColor("#F1F5F9"))
    pdf.roundRect(32, status_bar_y, page_width - 64, 28, 4, fill=True, stroke=False)

    # Statut
    statut_val = booking.statut
    if statut_val in ["validee_admin", "confirmee"]:
        badge_bg = COLOR_GREEN
        badge_text = "STATUT : RÉSERVATION VALIDÉE & CONFIRMÉE"
    elif statut_val == "en_attente_validation_admin":
        badge_bg = COLOR_AMBER
        badge_text = "STATUT : EN ATTENTE DE VALIDATION ADMIN"
    elif statut_val == "en_attente_paiement":
        badge_bg = COLOR_ORANGE
        badge_text = "STATUT : EN ATTENTE DE PAIEMENT"
    elif statut_val in ["refusee", "annulee"]:
        badge_bg = COLOR_RED
        badge_text = f"STATUT : DEMANDE {statut_val.upper()}"
    else:
        badge_bg = HexColor("#64748B")
        badge_text = f"STATUT : {booking.get_statut_display().upper()}"

    # Badge visuel
    pdf.setFillColor(badge_bg)
    pdf.roundRect(40, status_bar_y + 5, 230, 18, 3, fill=True, stroke=False)
    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(48, status_bar_y + 10, badge_text)

    # Date d'émission
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.setFont("Helvetica", 8)
    date_demande_str = booking.date_creation.strftime("%d/%m/%Y à %H:%M") if booking.date_creation else timezone.now().strftime("%d/%m/%Y")
    pdf.drawRightString(page_width - 40, status_bar_y + 10, f"Demande enregistrée le : {date_demande_str}")

    y_pos = status_bar_y - 14

    # Fonction utilitaire pour dessiner une boîte de section
    def draw_section_box(title: str, height: int, icon: str = "") -> tuple[float, float, float]:
        nonlocal y_pos
        box_y = y_pos - height
        box_x = 32
        box_w = page_width - 64

        # Cadre blanc avec bordure subtile
        pdf.setFillColor(COLOR_WHITE)
        pdf.setStrokeColor(COLOR_CARD_BORDER)
        pdf.setLineWidth(0.8)
        pdf.roundRect(box_x, box_y, box_w, height, 4, fill=True, stroke=True)

        # En-tête de section
        pdf.setFillColor(HexColor("#F8FAFC"))
        pdf.roundRect(box_x, box_y + height - 20, box_w, 20, 3, fill=True, stroke=False)
        pdf.setFillColor(COLOR_ORANGE)
        pdf.rect(box_x, box_y + height - 20, 3, 20, fill=True, stroke=False)

        pdf.setFillColor(COLOR_DARK_BG)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(box_x + 10, box_y + height - 14, f"{title}")

        y_pos = box_y - 8
        return box_x, box_y, box_w

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 1 : DEMANDEUR & ENTREPRISE
    # ──────────────────────────────────────────────────────────────────────────
    s1_x, s1_y, s1_w = draw_section_box("1. INFORMATIONS DU CANDIDAT & DE L'ENTREPRISE", 84)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(s1_x + 12, s1_y + 50, "Nom complet :")
    pdf.drawString(s1_x + 12, s1_y + 35, "Entreprise / Marque :")
    pdf.drawString(s1_x + 12, s1_y + 20, "Secteur d'activité :")

    pdf.setFont("Helvetica", 8.5)
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.drawString(s1_x + 110, s1_y + 50, booking.nom_complet or "—")
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(s1_x + 110, s1_y + 35, booking.nom_entreprise or "—")
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(s1_x + 110, s1_y + 20, booking.secteur_activite or "—")

    # Colonne droite
    col2_x = s1_x + s1_w * 0.52
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(col2_x, s1_y + 50, "WhatsApp :")
    pdf.drawString(col2_x, s1_y + 35, "Email :")
    pdf.drawString(col2_x, s1_y + 20, "Page web / Liens :")

    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillColor(COLOR_GREEN)
    pdf.drawString(col2_x + 85, s1_y + 50, booking.telephone_whatsapp or "—")
    pdf.setFont("Helvetica", 8.5)
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.drawString(col2_x + 85, s1_y + 35, _truncate(booking.email, 30))
    link_disp = booking.lien_site_ou_page or booking.lien_whatsapp or "Non renseigné"
    pdf.drawString(col2_x + 85, s1_y + 20, _truncate(link_disp, 32))

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2 : CONTENU DU DIRECT LIVE (PITCH & PRODUITS)
    # ──────────────────────────────────────────────────────────────────────────
    s2_x, s2_y, s2_w = draw_section_box("2. CONTENU DU DIRECT LIVE & OFFRE PRÉSENTÉE", 96)

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(s2_x + 12, s2_y + 62, "Titre du Live :")
    pdf.setFont("Helvetica-Bold", 9)
    pdf.setFillColor(COLOR_ORANGE)
    pdf.drawString(s2_x + 110, s2_y + 62, _truncate(booking.titre_du_live, 65))

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(s2_x + 12, s2_y + 44, "Pitch / Présentation :")
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    desc_lines = _split_text_lines(booking.description_activite, max_chars_per_line=85)[:2]
    line_y = s2_y + 44
    for dl in desc_lines:
        pdf.drawString(s2_x + 110, line_y, dl)
        line_y -= 10

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(s2_x + 12, s2_y + 16, "Produits / Services :")
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.setFillColor(HexColor("#334155"))
    prod_lines = _split_text_lines(booking.produits_services, max_chars_per_line=85)[:1]
    if prod_lines:
        pdf.drawString(s2_x + 110, s2_y + 16, prod_lines[0])

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 3 : FORMULE, CRÉNEAU & PAIEMENT
    # ──────────────────────────────────────────────────────────────────────────
    s3_x, s3_y, s3_w = draw_section_box("3. FORMULE CHOISIE, CRÉNEAU HORAIRE & RÈGLEMENT", 86)

    # Col 1
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(s3_x + 12, s3_y + 50, "Package :")
    pdf.drawString(s3_x + 12, s3_y + 35, "Date de passage :")
    pdf.drawString(s3_x + 12, s3_y + 20, "Heure & Durée :")

    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.drawString(s3_x + 95, s3_y + 50, booking.package.nom if booking.package else "Pass Standard")
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillColor(COLOR_ORANGE)
    date_str = booking.date_choisie.strftime("%A %d %B %Y").capitalize() if booking.date_choisie else "—"
    pdf.drawString(s3_x + 95, s3_y + 35, date_str)
    pdf.setFont("Helvetica", 8.5)
    heure_deb_str = booking.heure_choisie.strftime("%H:%M") if booking.heure_choisie else "—"
    heure_fin_str = booking.heure_fin_calculee.strftime("%H:%M") if booking.heure_choisie else "—"
    pdf.drawString(s3_x + 95, s3_y + 20, f"{heure_deb_str} à {heure_fin_str} ({booking.duree_minutes} minutes)")

    # Col 2
    col3_2_x = s3_x + s3_w * 0.52
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(COLOR_TEXT_MUTED)
    pdf.drawString(col3_2_x, s3_y + 50, "Montant Total :")
    pdf.drawString(col3_2_x, s3_y + 35, "Mode de paiement :")
    pdf.drawString(col3_2_x, s3_y + 20, "Réf. Transaction :")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(COLOR_GREEN)
    pdf.drawString(col3_2_x + 90, s3_y + 50, f"{booking.prix_formate}")
    pdf.setFont("Helvetica", 8.5)
    pdf.setFillColor(COLOR_TEXT_PRIMARY)
    pdf.drawString(col3_2_x + 90, s3_y + 35, booking.mode_paiement or "Mobile Money")
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(HexColor("#1E293B"))
    pdf.drawString(col3_2_x + 90, s3_y + 20, booking.reference_paiement or "En cours de vérification")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 4 : DÉROULÉ TECHNIQUE DE PASSAGE
    # ──────────────────────────────────────────────────────────────────────────
    s4_x, s4_y, s4_w = draw_section_box("4. PROGRAMME DE PASSAGE EN DIRECT (PLANNING TECHNIQUE)", 76)

    step_w = (s4_w - 24) / 4
    steps_data = [
        ("1. ARRIVÉE RÉGIE", f"{booking.heure_arrivee_technique.strftime('%H:%M')}", "H - 30 min : Accueil & briefing"),
        ("2. INSTALLATION", "H - 15 min", "Tests micro, caméra, éclairage"),
        ("3. DÉBUT DU LIVE", f"{heure_deb_str}", "Prise d'antenne devant l'audience"),
        ("4. FIN & CLÔTURE", f"{heure_fin_str}", "Débriefing & leads acheteurs"),
    ]

    for i, (stitle, stime, sdesc) in enumerate(steps_data):
        bx = s4_x + 12 + i * step_w
        by = s4_y + 8
        pdf.setFillColor(HexColor("#F8FAFC"))
        pdf.roundRect(bx, by, step_w - 6, 46, 3, fill=True, stroke=False)

        pdf.setFillColor(COLOR_TEXT_MUTED)
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(bx + 6, by + 34, stitle)

        pdf.setFillColor(COLOR_ORANGE)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(bx + 6, by + 21, stime)

        pdf.setFillColor(COLOR_TEXT_SECONDARY)
        pdf.setFont("Helvetica", 6.5)
        pdf.drawString(bx + 6, by + 8, sdesc)

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 5 : RÈGLES D'OR OCD LIVE (CHARTE DU PRÉSENTATEUR)
    # ──────────────────────────────────────────────────────────────────────────
    s5_x, s5_y, s5_w = draw_section_box("5. RÈGLES D'OR OCD LIVE (ENGAGEMENT DU PRÉSENTATEUR)", 96)

    regles = [
        ("Ponctualité stricte :", "Être connecté obligatoirement 30 minutes avant le début pour le calage technique."),
        ("Connexion & Cadre :", "Disposer d'une connexion Internet stable (fibre ou 4.5G) et d'un endroit calme et bien éclairé."),
        ("Produits prêts :", "Tous les produits physiques, démos et supports doivent être prêts à portée de main."),
        ("Transparence & Vérité :", "Tolérance zéro pour les promesses mensongères ou allégations non fondées."),
        ("Respect de l'audience :", "Courtoisie, bienveillance et interaction active avec les spectateurs dans le chat."),
    ]

    ry = s5_y + 58
    for r_title, r_desc in regles:
        pdf.setFillColor(COLOR_GREEN)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(s5_x + 12, ry, "✓ " + r_title)
        pdf.setFillColor(COLOR_TEXT_PRIMARY)
        pdf.setFont("Helvetica", 7.5)
        pdf.drawString(s5_x + 115, ry, r_desc)
        ry -= 12.5

    # ──────────────────────────────────────────────────────────────────────────
    # PIED DE PAGE : CONTACTS & AUTHENTIFICATION E-SHELLE
    # ──────────────────────────────────────────────────────────────────────────
    footer_height = 42
    pdf.setFillColor(COLOR_DARK_BG)
    pdf.rect(0, 0, page_width, footer_height, fill=True, stroke=False)

    # Ligne verte subtile
    pdf.setFillColor(COLOR_GREEN)
    pdf.rect(0, footer_height - 2, page_width, 2, fill=True, stroke=False)

    pdf.setFillColor(COLOR_WHITE)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(32, 22, "PLATEFORME OFFICIELLE E-SHELLE • OCD LIVE")
    pdf.setFont("Helvetica", 7.5)
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.drawString(32, 10, "Site web : https://e-shelle.com  •  Email assistance : e.shelleltd@gmail.com")

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(HexColor("#FBBF24"))
    pdf.drawRightString(page_width - 32, 22, "RÉGIE WHATSAPP DIRECT : +237 680 625 082")
    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(HexColor("#94A3B8"))
    pdf.drawRightString(page_width - 32, 10, "Présentez vos produits et services devant l'audience E-Shelle")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer.getvalue()

