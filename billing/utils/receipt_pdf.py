# billing/utils/receipt_pdf.py
from __future__ import annotations

from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


WHATSAPP_NUMBER = "+237 693649944"
WEBSITE = "www.immigration97.com"
SUPPORT_EMAIL = "support@immigration97.com"


def _money(amount) -> str:
    try:
        q = Decimal(str(amount))
        s = f"{q:,.2f}".replace(",", " ").replace("\xa0", " ")
        return s
    except Exception:
        return str(amount)


def _wrap_text(text: str, max_chars: int = 90) -> list[str]:
    if not text:
        return []
    words = text.strip().split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if len(test) > max_chars:
            if line:
                lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def render_receipt_pdf(receipt, response: HttpResponse) -> None:
    """
    PDF A4 pro (ReportLab) : pas de superposition, logo + en-tête propre.
    """
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # ====== Marges
    left = 20 * mm
    right = width - 20 * mm
    top = height - 18 * mm

    # ====== HEADER (zone réservée)
    header_h = 36 * mm
    header_bottom = top - header_h

    # ====== LOGO (gauche)
    logo_w = 28 * mm
    logo_h = 28 * mm
    logo_x = left
    logo_y = top - logo_h

    logo_path = None
    try:
        logo_path = settings.BASE_DIR / "static" / "img" / "LOGOIMM97.png"
    except Exception:
        logo_path = None

    if logo_path and logo_path.exists():
        p.drawImage(
            ImageReader(str(logo_path)),
            logo_x,
            logo_y,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask="auto",
        )
    else:
        # fallback si logo introuvable
        p.setFont("Helvetica-Bold", 9)
        p.rect(logo_x, logo_y, logo_w, logo_h, stroke=1, fill=0)
        p.drawString(logo_x + 4, logo_y + (logo_h / 2), "LOGO")

    # ====== Nom + infos entreprise (droite du logo)
    text_x = logo_x + logo_w + 10
    title_y = top - 7 * mm

    p.setFont("Helvetica-Bold", 16)
    p.drawString(text_x, title_y, "IMMIGRATION97")

    p.setFont("Helvetica", 10)
    p.drawString(text_x, title_y - 6 * mm, f"Plateforme d'immigration légale — {WEBSITE}")
    p.drawString(text_x, title_y - 12 * mm, f"WhatsApp : {WHATSAPP_NUMBER}")

    # Ligne de séparation sous header
    p.setLineWidth(0.8)
    p.line(left, header_bottom, right, header_bottom)

    # ====== TITRE DOCUMENT (sous le header)
    y = header_bottom - 12 * mm
    p.setFont("Helvetica-Bold", 18)
    p.drawString(left, y, "REÇU / FACTURE")

    # ====== Boîte infos (droite)
    box_w = 82 * mm
    box_h = 28 * mm
    box_x = right - box_w
    box_y = y - 5 * mm - box_h

    p.setLineWidth(0.8)
    p.rect(box_x, box_y, box_w, box_h, stroke=1, fill=0)

    issued = timezone.localtime(receipt.issued_at)
    p.setFont("Helvetica", 10)
    info_y = box_y + box_h - 7 * mm
    p.drawString(box_x + 6 * mm, info_y, f"N° : {receipt.receipt_number}")
    p.drawString(box_x + 6 * mm, info_y - 6 * mm, f"Date : {issued.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(box_x + 6 * mm, info_y - 12 * mm, f"Statut : {receipt.get_status_display()}")
    p.drawString(box_x + 6 * mm, info_y - 18 * mm, f"Méthode : {receipt.payment_method or '-'}")

    # ====== Bloc gauche : CLIENT + SERVICE
    y2 = box_y - 10 * mm

    # Client
    p.setFont("Helvetica-Bold", 12)
    p.drawString(left, y2, "Client")
    y2 -= 6 * mm

    p.setFont("Helvetica", 10)
    p.drawString(left, y2, receipt.client_full_name)
    y2 -= 5 * mm

    if getattr(receipt, "client_email", None):
        p.drawString(left, y2, f"Email : {receipt.client_email}")
        y2 -= 5 * mm
    if getattr(receipt, "client_phone", None):
        p.drawString(left, y2, f"Tél : {receipt.client_phone}")
        y2 -= 5 * mm

    # Service
    y2 -= 7 * mm
    p.setFont("Helvetica-Bold", 12)
    p.drawString(left, y2, "Service")
    y2 -= 6 * mm

    p.setFont("Helvetica", 10)
    p.drawString(left, y2, f"Nom : {receipt.service_name}")
    y2 -= 5 * mm

    if getattr(receipt, "service_description", None):
        p.drawString(left, y2, "Description :")
        y2 -= 5 * mm
        for ln in _wrap_text(receipt.service_description, max_chars=96)[:8]:
            p.drawString(left + 6 * mm, y2, f"• {ln}")
            y2 -= 4.8 * mm

    # ====== Ligne + TOTAL (bas)
    y_total_line = 70 * mm
    p.setLineWidth(0.8)
    p.line(left, y_total_line, right, y_total_line)

    p.setFont("Helvetica-Bold", 12)
    p.drawString(left, y_total_line - 10 * mm, "TOTAL")

    p.setFont("Helvetica-Bold", 14)
    total_str = f"{_money(receipt.amount)} {receipt.currency}"
    p.drawRightString(right, y_total_line - 10 * mm, total_str)

    # ====== Footer
    p.setFont("Helvetica", 9)
    p.setFillGray(0.35)
    p.drawString(left, 18 * mm, "Ce reçu est généré automatiquement par Immigration97.")
    p.drawString(left, 12 * mm, f"Support : {SUPPORT_EMAIL}  |  WhatsApp : {WHATSAPP_NUMBER}")
    p.setFillGray(0)

    p.showPage()
    p.save()

