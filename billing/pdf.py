import io
from decimal import Decimal
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader


def _money(value: Decimal, currency: str) -> str:
    try:
        v = f"{value:,.2f}".replace(",", " ").replace(".00", "")
    except Exception:
        v = str(value)
    return f"{v} {currency}"


def build_receipt_pdf(receipt) -> bytes:
    """
    Retourne le PDF en bytes (streamable).
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ==== BRAND CONFIG ====
    brand_name = "Immigration97"
    site = "immigration97.com"
    email = "support@immigration97.com"
    phone = "+237 XXX XXX XXX"  # change
    address = "Plateforme d'immigration légale – Afrique francophone"

    # ==== HEADER ====
    top = height - 20 * mm

    # Logo (optionnel)
    # Mets ton logo ici: static/images/logo.png
    logo_path = None
    try:
        logo_path = settings.BASE_DIR / "static" / "images" / "logo.png"
        c.drawImage(ImageReader(str(logo_path)), 20 * mm, top - 18 * mm, width=35 * mm, height=18 * mm, mask="auto")
    except Exception:
        pass

    c.setFont("Helvetica-Bold", 16)
    c.drawString(60 * mm, top - 6 * mm, "REÇU DE PAIEMENT")

    c.setFont("Helvetica", 9)
    c.drawString(60 * mm, top - 12 * mm, f"{brand_name} • {site}")
    c.drawString(60 * mm, top - 16 * mm, f"{email} • {phone}")
    c.drawString(60 * mm, top - 20 * mm, address)

    # ==== RECEIPT META ====
    box_top = top - 30 * mm
    c.setLineWidth(1)
    c.rect(20 * mm, box_top - 28 * mm, width - 40 * mm, 28 * mm)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(24 * mm, box_top - 10 * mm, "N° Reçu :")
    c.setFont("Helvetica", 10)
    c.drawString(45 * mm, box_top - 10 * mm, receipt.receipt_number)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(24 * mm, box_top - 18 * mm, "Date :")
    c.setFont("Helvetica", 10)
    c.drawString(45 * mm, box_top - 18 * mm, receipt.issued_at.strftime("%d/%m/%Y %H:%M"))

    c.setFont("Helvetica-Bold", 10)
    c.drawString(120 * mm, box_top - 10 * mm, "Statut :")
    c.setFont("Helvetica", 10)
    c.drawString(140 * mm, box_top - 10 * mm, receipt.get_status_display())

    # ==== CLIENT ====
    y = box_top - 42 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Informations client")
    y -= 7 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Nom : {receipt.client_full_name}")
    y -= 6 * mm
    if receipt.client_email:
        c.drawString(20 * mm, y, f"Email : {receipt.client_email}")
        y -= 6 * mm
    if receipt.client_phone:
        c.drawString(20 * mm, y, f"Téléphone : {receipt.client_phone}")
        y -= 6 * mm

    # ==== SERVICE ====
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Service")
    y -= 7 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Prestation : {receipt.service_name}")
    y -= 6 * mm

    if receipt.service_description:
        # multi-line safe
        desc = receipt.service_description.strip()
        max_chars = 95
        lines = [desc[i:i+max_chars] for i in range(0, len(desc), max_chars)]
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, y, "Détails :")
        y -= 5 * mm
        for line in lines[:6]:
            c.drawString(28 * mm, y, line)
            y -= 4.5 * mm

    # ==== PAYMENT ====
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Paiement")
    y -= 7 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Montant : {_money(receipt.amount, receipt.currency)}")
    y -= 6 * mm

    if receipt.payment_method:
        c.drawString(20 * mm, y, f"Méthode : {receipt.payment_method}")
        y -= 6 * mm

    if receipt.transaction_id:
        c.drawString(20 * mm, y, f"Transaction ID : {receipt.transaction_id}")
        y -= 6 * mm

    # ==== FOOTER (Protection / Legal) ====
    c.setLineWidth(0.5)
    c.line(20 * mm, 28 * mm, width - 20 * mm, 28 * mm)

    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 22 * mm, "Ce reçu confirme un paiement lié à un service Immigration97.")
    c.drawString(20 * mm, 18 * mm, "Pour toute réclamation : support@immigration97.com • immigration97.com")

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
