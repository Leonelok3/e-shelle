from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.conf import settings
from pathlib import Path

def generate_coach_ai_pdf(report):
    output_dir = Path(settings.MEDIA_ROOT) / "coach_reports"
    output_dir.mkdir(exist_ok=True)

    file_path = output_dir / f"coach_ai_{report.id}.pdf"

    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 50, "Rapport Coach IA – Immigration97")

    c.setFont("Helvetica", 12)
    y = height - 100

    c.drawString(50, y, f"Examen : {report.exam_code}")
    y -= 20
    c.drawString(50, y, f"Section : {report.scope.upper()}")
    y -= 20
    c.drawString(50, y, f"Date : {report.created_at.strftime('%d/%m/%Y')}")

    y -= 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Analyse IA :")

    c.setFont("Helvetica", 11)
    y -= 25

    for k, v in report.data.items():
        c.drawString(60, y, f"- {k} : {v}")
        y -= 18
        if y < 80:
            c.showPage()
            y = height - 80

    c.save()
    return file_path
