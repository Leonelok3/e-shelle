# billing/utils/receipt_pdf.py
from __future__ import annotations

from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


WHATSAPP_NUMBER = "+237 680625082"
WEBSITE = "www.e-shelle.com"
SUPPORT_EMAIL = "e.shelleltd@gmail.com"
BRAND_GREEN = HexColor("#16a34a")
BRAND_GREEN_LIGHT = HexColor("#e8f8ee")
BRAND_DARK = HexColor("#0f172a")
GREY_TEXT = HexColor("#475569")
STATUS_COLORS = {
    "paid": HexColor("#16a34a"),
    "pending": HexColor("#d97706"),
    "failed": HexColor("#dc2626"),
}


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

    # ====== Bandeau de marque (haut de page)
    p.setFillColor(BRAND_GREEN)
    p.rect(0, height - 6 * mm, width, 6 * mm, stroke=0, fill=1)

    # ====== Marges
    left = 20 * mm
    right = width - 20 * mm
    top = height - 20 * mm

    # ====== HEADER (bandeau letterhead avec fond teinte)
    header_h = 38 * mm
    header_bottom = top - header_h
    p.setFillColor(BRAND_GREEN_LIGHT)
    p.rect(0, header_bottom, width, (height - 6 * mm) - header_bottom, stroke=0, fill=1)

    # ====== LOGO (gauche)
    logo_w = 26 * mm
    logo_h = 26 * mm
    logo_x = left
    logo_y = top - logo_h - 2 * mm

    logo_path = None
    try:
        logo_path = settings.BASE_DIR / "static" / "img" / "logo.png"
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
        p.setFillColor(BRAND_GREEN)
        p.setFont("Helvetica-Bold", 9)
        p.rect(logo_x, logo_y, logo_w, logo_h, stroke=1, fill=0)
        p.setFillColor(BRAND_DARK)
        p.drawString(logo_x + 4, logo_y + (logo_h / 2), "LOGO")

    # ====== Nom + infos entreprise (droite du logo)
    text_x = logo_x + logo_w + 10
    title_y = top - 5 * mm

    p.setFont("Helvetica-Bold", 18)
    p.setFillColor(BRAND_GREEN)
    p.drawString(text_x, title_y, "E-SHELLE")

    p.setFont("Helvetica", 10)
    p.setFillColor(GREY_TEXT)
    p.drawString(text_x, title_y - 6.5 * mm, f"Plateforme digitale et IA — {WEBSITE}")
    p.drawString(text_x, title_y - 12.5 * mm, f"WhatsApp : {WHATSAPP_NUMBER}")

    # Bande de séparation sous header (trait vert plein)
    p.setFillColor(BRAND_GREEN)
    p.rect(0, header_bottom - 1.2 * mm, width, 1.2 * mm, stroke=0, fill=1)

    # ====== TITRE DOCUMENT (sous le header)
    y = header_bottom - 14 * mm
    p.setFont("Helvetica-Bold", 20)
    p.setFillColor(BRAND_DARK)
    p.drawString(left, y, "REÇU")
    p.setFont("Helvetica", 11)
    p.setFillColor(GREY_TEXT)
    p.drawString(left + 32 * mm, y + 0.5 * mm, "/ Facture de paiement")

    # ====== Boîte infos (droite, fond teinte + bordure verte)
    box_w = 82 * mm
    box_h = 30 * mm
    box_x = right - box_w
    box_y = y - 5 * mm - box_h

    p.setFillColor(BRAND_GREEN_LIGHT)
    p.setStrokeColor(BRAND_GREEN)
    p.setLineWidth(1)
    p.roundRect(box_x, box_y, box_w, box_h, 3 * mm, stroke=1, fill=1)

    issued = timezone.localtime(receipt.issued_at)
    status_color = STATUS_COLORS.get(receipt.status, BRAND_DARK)
    info_y = box_y + box_h - 7 * mm

    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(BRAND_DARK)
    p.drawString(box_x + 6 * mm, info_y, f"N° : {receipt.receipt_number}")
    p.setFont("Helvetica", 10)
    p.drawString(box_x + 6 * mm, info_y - 6 * mm, f"Date : {issued.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(box_x + 6 * mm, info_y - 12 * mm, f"Méthode : {receipt.payment_method or '-'}")
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(status_color)
    p.drawString(box_x + 6 * mm, info_y - 18 * mm, f"Statut : {receipt.get_status_display()}")

    # ====== Bloc gauche : CLIENT + SERVICE
    y2 = box_y - 12 * mm

    def _section_title(label, y_pos):
        p.setFillColor(BRAND_GREEN)
        p.rect(left, y_pos - 1 * mm, 3.2 * mm, 4.2 * mm, stroke=0, fill=1)
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(BRAND_DARK)
        p.drawString(left + 6 * mm, y_pos, label)

    # Client
    _section_title("Client", y2)
    y2 -= 7 * mm

    p.setFont("Helvetica", 10)
    p.setFillColor(BRAND_DARK)
    p.drawString(left, y2, receipt.client_full_name)
    y2 -= 5 * mm

    p.setFillColor(GREY_TEXT)
    if getattr(receipt, "client_email", None):
        p.drawString(left, y2, f"Email : {receipt.client_email}")
        y2 -= 5 * mm
    if getattr(receipt, "client_phone", None):
        p.drawString(left, y2, f"Tél : {receipt.client_phone}")
        y2 -= 5 * mm

    # Service
    y2 -= 7 * mm
    _section_title("Service", y2)
    y2 -= 7 * mm

    p.setFont("Helvetica", 10)
    p.setFillColor(BRAND_DARK)
    p.drawString(left, y2, f"Nom : {receipt.service_name}")
    y2 -= 5 * mm

    if getattr(receipt, "service_description", None):
        p.setFillColor(GREY_TEXT)
        p.drawString(left, y2, "Description :")
        y2 -= 5 * mm
        for ln in _wrap_text(receipt.service_description, max_chars=96)[:8]:
            p.drawString(left + 6 * mm, y2, f"• {ln}")
            y2 -= 4.8 * mm

    # ====== Bandeau TOTAL (bas, mis en avant)
    total_h = 16 * mm
    total_y = 68 * mm
    p.setFillColor(BRAND_DARK)
    p.roundRect(left, total_y, right - left, total_h, 2.5 * mm, stroke=0, fill=1)

    p.setFont("Helvetica-Bold", 13)
    p.setFillColor(HexColor("#ffffff"))
    p.drawString(left + 6 * mm, total_y + total_h / 2 - 2 * mm, "TOTAL PAYÉ")

    p.setFont("Helvetica-Bold", 16)
    p.setFillColor(HexColor("#7cf66c"))
    total_str = f"{_money(receipt.amount)} {receipt.currency}"
    p.drawRightString(right - 6 * mm, total_y + total_h / 2 - 2.3 * mm, total_str)

    # ====== Footer
    p.setFont("Helvetica", 9)
    p.setFillColor(GREY_TEXT)
    p.drawString(left, 18 * mm, "Ce reçu est généré automatiquement par E-Shelle.")
    p.drawString(left, 12 * mm, f"Support : {SUPPORT_EMAIL}  |  WhatsApp : {WHATSAPP_NUMBER}")

    p.setFillColor(BRAND_GREEN)
    p.rect(0, 0, width, 6 * mm, stroke=0, fill=1)

    p.showPage()
    p.save()

