import os
import uuid
from django.conf import settings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import qrcode


def generate_cefr_certificate(*, user, exam_code, level, public_id):
    """
    🎓 Génère un certificat CECR premium avec QR code vérifiable
    """

    output_dir = os.path.join(settings.MEDIA_ROOT, "certificates")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{exam_code}_{level}_{public_id}.pdf"
    file_path = os.path.join(output_dir, filename)

    c = canvas.Canvas(file_path, pagesize=landscape(A4))
    width, height = landscape(A4)

    # 🎨 FOND
    bg_path = os.path.join(
        settings.BASE_DIR,
        "static/certificates/background.png"
    )
    if os.path.exists(bg_path):
        c.drawImage(bg_path, 0, 0, width, height)

    # 🏷️ TITRE
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(
        width / 2,
        height - 3 * cm,
        "CERTIFICAT CECR"
    )

    # 👤 NOM UTILISATEUR
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(
        width / 2,
        height - 6 * cm,
        user.get_full_name() or user.username
    )

    # 📘 TEXTE
    c.setFont("Helvetica", 16)
    c.drawCentredString(
        width / 2,
        height - 8 * cm,
        f"a validé le niveau {level} du Cadre Européen Commun de Référence"
    )

    c.drawCentredString(
        width / 2,
        height - 9.5 * cm,
        f"Examen : {exam_code.upper()}"
    )

    # ✍️ SIGNATURE
    signature_path = os.path.join(
        settings.BASE_DIR,
        "static/certificates/signature.png"
    )
    if os.path.exists(signature_path):
        c.drawImage(
            signature_path,
            width - 7 * cm,
            3 * cm,
            width=4 * cm,
            preserveAspectRatio=True,
            mask="auto",
        )

    c.setFont("Helvetica", 10)
    c.drawString(width - 7 * cm, 2.5 * cm, "Signature officielle")

    # 🔐 QR CODE (LIEN PUBLIC)
    verify_url = f"https://immigration97.com/certificates/verify/{public_id}"
    qr = qrcode.make(verify_url)

    qr_path = os.path.join(output_dir, f"{public_id}.png")
    qr.save(qr_path)

    c.drawImage(qr_path, 2 * cm, 2 * cm, 4 * cm, 4 * cm)

    # 🆔 ID PUBLIC
    c.setFont("Helvetica", 9)
    c.drawString(
        2 * cm,
        1.5 * cm,
        f"Certificat ID : {public_id}"
    )

    c.save()

    return {
        "file": f"certificates/{filename}",
        "public_id": public_id,
    }
