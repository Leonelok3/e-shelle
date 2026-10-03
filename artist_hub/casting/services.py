"""
artist_hub/casting/services.py
Services métier du module casting :
- Numérotation automatique des candidatures (CAST-YYYY-XXXX)
- Génération des codes d'accès sécurisés (OPUS-XXXX-X)
- Traitement, redimensionnement et sécurisation des photos via Pillow
- Génération de la Fiche Officielle & Reçu PDF avec QR Code (ReportLab)
- Envoi d'email de confirmation avec pièce jointe
"""
import io
import os
import uuid
import string
import random
import logging
import datetime
from PIL import Image, ImageOps

from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from artist_hub.casting.models import (
    Candidate,
    CandidatePhoto,
    CandidateStatus,
    PhotoType,
)
from artist_hub.conf import hub_settings

logger = logging.getLogger("artist_hub.casting")


def generate_candidate_number(session) -> str:
    """
    Génère un numéro unique de candidature séquentiel : CAST-YYYY-0001
    """
    year = timezone.now().year
    count = Candidate.objects.filter(session=session).count() + 1
    number = f"CAST-{year}-{count:04d}"
    # Éviter toute collision
    while Candidate.objects.filter(candidate_number=number).exists():
        count += 1
        number = f"CAST-{year}-{count:04d}"
    return number


def generate_access_code() -> str:
    """
    Génère un code d'accès sécurisé et lisible : OPUS-XXXX-X
    """
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    part1 = "".join(random.choices(chars, k=4))
    part2 = "".join(random.choices(chars, k=1))
    code = f"OPUS-{part1}-{part2}"
    while Candidate.objects.filter(access_code=code).exists():
        part1 = "".join(random.choices(chars, k=4))
        code = f"OPUS-{part1}-{part2}"
    return code


def process_uploaded_image(uploaded_file, max_dimension=1600, quality=85) -> ContentFile:
    """
    Valide l'image avec Pillow, applique la rotation EXIF,
    redimensionne si nécessaire et compresse au format JPEG.
    Renvoie un ContentFile prêt à enregistrer avec un nom aléatoire.
    """
    try:
        img = Image.open(uploaded_file)
        img.verify()
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
    except Exception as exc:
        raise ValueError("Le fichier téléversé n'est pas une image valide.") from exc

    # Corriger l'orientation issue des smartphones (EXIF)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Conversion en RGB si image transparente (PNG/WEBP/RGBA)
    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Redimensionnement proportionnel si plus grand que max_dimension
    if img.width > max_dimension or img.height > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)

    filename = f"{uuid.uuid4().hex}.jpg"
    return ContentFile(output.getvalue(), name=filename)


def generate_qr_code_image(data_text: str) -> io.BytesIO:
    """
    Génère un QR Code haute définition en mémoire.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0B0C10", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_candidate_pdf(candidate: Candidate) -> bytes:
    """
    Génère la Fiche Officielle & Reçu de Candidature au format PDF (ReportLab).
    Comprend un QR code de vérification, le récapitulatif du candidat et le reçu de paiement.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Couleurs du thème
    primary_color = colors.HexColor("#D4AF37")   # Or
    dark_bg = colors.HexColor("#0B0C10")         # Noir
    text_dark = colors.HexColor("#1F2937")
    gray_muted = colors.HexColor("#6B7280")
    light_box = colors.HexColor("#F9FAFB")
    accent_green = colors.HexColor("#10B981")

    # 1. En-tête noir & or
    p.setFillColor(dark_bg)
    p.rect(0, height - 3.2 * cm, width, 3.2 * cm, fill=1, stroke=0)

    # Ligne dorée décorative
    p.setFillColor(primary_color)
    p.rect(0, height - 3.35 * cm, width, 0.15 * cm, fill=1, stroke=0)

    # Titres En-tête
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(1.5 * cm, height - 1.4 * cm, f"{hub_settings.BRAND_NAME} — {hub_settings.ARTIST_NAME}")

    p.setFont("Helvetica", 10)
    p.setFillColor(primary_color)
    p.drawString(1.5 * cm, height - 2.1 * cm, "FICHE OFFICIELLE DE CANDIDATURE & REÇU DE CASTING")

    p.setFillColor(colors.HexColor("#D1D5DB"))
    p.setFont("Helvetica", 9)
    p.drawString(1.5 * cm, height - 2.7 * cm, f"{candidate.session.title} • {candidate.session.subtitle}")

    # Numéro officiel en haut à droite
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(width - 1.5 * cm, height - 1.4 * cm, candidate.candidate_number)
    p.setFont("Helvetica", 9)
    p.setFillColor(primary_color)
    p.drawRightString(width - 1.5 * cm, height - 2.1 * cm, f"Code d'accès : {candidate.access_code}")

    # 2. Bandeau Statut
    y = height - 4.4 * cm
    p.setFillColor(light_box)
    p.roundRect(1.5 * cm, y - 0.9 * cm, width - 3 * cm, 1.1 * cm, 6, fill=1, stroke=0)

    p.setFillColor(accent_green if candidate.status == CandidateStatus.INSCRIT else primary_color)
    p.setFont("Helvetica-Bold", 11)
    status_label = "STATUT : INSCRIPTION OFFICIELLE CONFIRMÉE" if candidate.status == CandidateStatus.INSCRIT else f"STATUT : {candidate.get_status_display().upper()}"
    p.drawString(2 * cm, y - 0.45 * cm, status_label)

    p.setFillColor(gray_muted)
    p.setFont("Helvetica", 9)
    p.drawRightString(width - 2 * cm, y - 0.45 * cm, f"Émis le {timezone.localdate().strftime('%d/%m/%Y')}")

    # 3. Informations du Candidat
    y -= 1.8 * cm
    p.setFillColor(dark_bg)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1.5 * cm, y, "1. IDENTITÉ DU CANDIDAT")
    p.setStrokeColor(primary_color)
    p.setLineWidth(1)
    p.line(1.5 * cm, y - 0.15 * cm, width - 1.5 * cm, y - 0.15 * cm)

    y -= 0.8 * cm
    fields_left = [
        ("Nom complet", candidate.full_name),
        ("Âge / Né(e) le", f"{candidate.age} ans ({candidate.birth_date.strftime('%d/%m/%Y')})"),
        ("Sexe", candidate.get_gender_display()),
        ("Taille / Poids", f"{candidate.height_cm} cm" + (f" / {candidate.weight_kg} kg" if candidate.weight_kg else "")),
        ("Mensurations", candidate.measurements or "Non renseignées"),
    ]
    fields_right = [
        ("Ville & Pays", f"{candidate.city}, {candidate.country}"),
        ("Téléphone / WhatsApp", candidate.phone),
        ("Adresse Email", candidate.email),
        ("Réseaux Sociaux", candidate.social_links or "-"),
        ("Profil Mineur", f"Tuteur : {candidate.guardian_name} ({candidate.guardian_phone})" if candidate.is_minor else "Majeur(e)"),
    ]

    p.setFont("Helvetica", 9)
    for label, val in fields_left:
        p.setFillColor(gray_muted)
        p.drawString(1.8 * cm, y, f"{label} :")
        p.setFillColor(text_dark)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(5.5 * cm, y, str(val))
        p.setFont("Helvetica", 9)
        y -= 0.65 * cm

    y_right = height - 6.2 * cm - 0.8 * cm
    for label, val in fields_right:
        p.setFillColor(gray_muted)
        p.drawString(11 * cm, y_right, f"{label} :")
        p.setFillColor(text_dark)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(14.8 * cm, y_right, str(val)[:28])
        p.setFont("Helvetica", 9)
        y_right -= 0.65 * cm

    # Confirmation de participation gratuite
    y -= 1.2 * cm
    p.setFillColor(text_dark)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(2 * cm, y, "CASTING GRATUIT - FICHE DE CANDIDATURE")
    p.setFont("Helvetica", 9)
    p.drawString(2 * cm, y - 0.7 * cm, "Inscription enregistrée. La sélection finale appartient au jury.")
    p.drawString(2 * cm, y - 1.25 * cm, f"Casting : {candidate.session.casting_date.strftime('%d/%m/%Y') if candidate.session.casting_date else 'À préciser'}")
    p.drawString(2 * cm, y - 1.8 * cm, f"Défilé : {candidate.session.event_date.strftime('%d/%m/%Y') if candidate.session.event_date else 'À préciser'}")
    # QR Code incrusté dans le reçu
    qr_data = f"https://e-shelle.com/artist-hub/suivi/?code={candidate.access_code}&num={candidate.candidate_number}"
    qr_buf = generate_qr_code_image(qr_data)
    from reportlab.lib.utils import ImageReader
    qr_img = ImageReader(qr_buf)
    p.drawImage(qr_img, width - 4.6 * cm, y - 2.6 * cm, 2.4 * cm, 2.4 * cm)
    p.setFont("Helvetica", 7)
    p.setFillColor(gray_muted)
    p.drawRightString(width - 2.1 * cm, y - 2.8 * cm, "Scanner pour vérifier")

    # 5. Avertissement & Conditions
    y -= 3.8 * cm
    p.setFillColor(colors.HexColor("#FEF2F2"))
    p.roundRect(1.5 * cm, y - 1.6 * cm, width - 3 * cm, 1.8 * cm, 6, fill=1, stroke=0)

    p.setFillColor(colors.HexColor("#991B1B"))
    p.setFont("Helvetica-Bold", 8)
    p.drawString(2 * cm, y - 0.4 * cm, "MENTION LÉGALE OBLIGATOIRE :")
    p.setFont("Helvetica", 7.5)
    disclaimer_text = (
        "Le casting est gratuit. L’inscription est ouverte aux candidats admissibles. "
        "Elle ne garantit en aucun cas la sélection finale du candidat pour le défilé de la Fashion Week Douala. "
        "Le jury est souverain et se réserve le droit d'admettre ou de refuser toute candidature selon les critères artistiques."
    )
    # Affichage sur 2 lignes
    p.drawString(2 * cm, y - 0.8 * cm, disclaimer_text[:115])
    p.drawString(2 * cm, y - 1.15 * cm, disclaimer_text[115:230])
    p.drawString(2 * cm, y - 1.5 * cm, disclaimer_text[230:])

    # 6. Signature / Cachet officiel
    y -= 2.8 * cm
    p.setFillColor(dark_bg)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(2 * cm, y, "Comité d'Organisation")
    p.setFont("Helvetica", 8)
    p.drawString(2 * cm, y - 0.45 * cm, f"{hub_settings.BRAND_NAME} / {hub_settings.ARTIST_NAME}")
    p.drawString(2 * cm, y - 0.85 * cm, "Douala, Cameroun")

    p.setFont("Helvetica-Bold", 9)
    p.drawRightString(width - 2 * cm, y, "Signature du Candidat")
    p.setFont("Helvetica", 8)
    p.drawRightString(width - 2 * cm, y - 0.45 * cm, "« Bon pour accord des conditions »")

    # Bas de page
    p.setFont("Helvetica", 7)
    p.setFillColor(gray_muted)
    p.drawCentredString(width / 2.0, 1.0 * cm, f"Document officiel émis par {hub_settings.BRAND_NAME} • Contact WhatsApp : {hub_settings.CONTACT_WHATSAPP} • Email : {hub_settings.CONTACT_EMAIL}")

    p.showPage()
    p.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def finalize_candidate_registration(candidate: Candidate, verified_by_user=None) -> bool:
    """
    Finalise l'inscription : passe le statut à INSCRIT,
    génère la fiche PDF et envoie l'email de confirmation au candidat.
    """
    if candidate.status in (CandidateStatus.INSCRIT, CandidateStatus.PRESELECTIONNE, CandidateStatus.RETENU, CandidateStatus.REFUSE):
        logger.info("CANDIDATE_ALREADY_INSCRIT: %s", candidate.candidate_number)
        return False

    candidate.status = CandidateStatus.INSCRIT
    candidate.save(update_fields=["status", "updated_at"])

    from django.db import transaction
    transaction.on_commit(lambda: _send_registration_confirmation(candidate))
    return True


def _send_registration_confirmation(candidate):
    # Generate and send only after the payment and registration have committed.
    try:
        pdf_bytes = generate_candidate_pdf(candidate)
    except Exception as exc:
        logger.exception("Erreur génération PDF pour %s : %s", candidate.candidate_number, exc)
        pdf_bytes = None

    # Envoi de l'email
    if candidate.email and pdf_bytes:
        try:
            subject = f"Confirmation de votre inscription — {hub_settings.BRAND_NAME} ({candidate.candidate_number})"
            body = (
                f"Bonjour {candidate.first_name},\n\n"
                f"Nous avons le plaisir de vous confirmer votre inscription gratuite "
                f"pour le casting de la {hub_settings.EVENT_TITLE}.\n\n"
                f"Casting : {candidate.session.casting_date.strftime('%d/%m/%Y') if candidate.session.casting_date else 'À préciser'}.\n"
                f"Défilé : {candidate.session.event_date.strftime('%d/%m/%Y') if candidate.session.event_date else 'À préciser'}, pour les profils retenus.\n\n"
                f"Vos identifiants officiels :\n"
                f"• Numéro de candidature : {candidate.candidate_number}\n"
                f"• Code d'accès : {candidate.access_code}\n\n"
                f"Vous trouverez ci-joint votre Fiche Officielle de Candidature (PDF).\n"
                f"Vous pouvez également suivre l'avancement de votre sélection en ligne à tout moment.\n\n"
                f"Cordialement,\n"
                f"L'équipe {hub_settings.BRAND_NAME} / {hub_settings.ARTIST_NAME}\n"
                f"WhatsApp : {hub_settings.CONTACT_WHATSAPP}\n"
            )
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=hub_settings.CONTACT_EMAIL or settings.DEFAULT_FROM_EMAIL,
                to=[candidate.email],
            )
            email.attach(
                filename=f"Fiche_Casting_{candidate.candidate_number}.pdf",
                content=pdf_bytes,
                mimetype="application/pdf",
            )
            email.send(fail_silently=True)
            logger.info("EMAIL_CONFIRMATION_SENT: Candidat=%s", candidate.candidate_number)
        except Exception as exc:
            logger.exception("Échec envoi email pour %s : %s", candidate.candidate_number, exc)

    return True
