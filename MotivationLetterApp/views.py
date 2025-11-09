import os, re
from io import BytesIO
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import cm

from .forms import FullCoverForm, CVUploadForm
from .models import Letter
from .services.parsing.pdf_parser import parse_pdf
from .services.parsing.docx_parser import parse_docx
from .services.generation.template_engine import render_letter, compute_ats_score

# --- Pages de base ---

from django.views.generic import TemplateView
class HomeView(TemplateView):
    template_name = 'motivation_letter/home.html'

class GeneratorView(View):
    template_name = "motivation_letter/generator.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": FullCoverForm(),
            "cv_form": CVUploadForm(),
            "result": None
        })

    def post(self, request):
        # 1) Via Formulaire
        if "generate_from_form" in request.POST:
            form = FullCoverForm(request.POST)
            cv_form = CVUploadForm()
            if form.is_valid():
                data = form.cleaned_data
                ctx = {
                    "full_name": data.get("full_name"),
                    "email": data.get("email"),
                    "phone": data.get("phone"),
                    "target_role": data.get("target_role"),
                    "company": data.get("company"),
                    "experiences": data.get("experiences"),
                    "skills": data.get("skills"),
                }
                lang = data.get("language", "fr")
                tone = data.get("tone", "pro")
                letter = render_letter(ctx, language=lang, tone=tone)
                ats = compute_ats_score(letter, data.get("keywords", ""))

                # Si clic “Enregistrer”
                if "save_letter" in request.POST:
                    obj = Letter.objects.create(
                        full_name=data.get("full_name"),
                        email=data.get("email") or "",
                        phone=data.get("phone") or "",
                        target_role=data.get("target_role") or "",
                        company=data.get("company") or "",
                        keywords=data.get("keywords") or "",
                        language=lang, tone=tone, source="form",
                        content=letter, ats_score=ats["score"]
                    )
                    return redirect("motivation_letter:letter_detail", pk=obj.pk)

                return render(request, self.template_name, {
                    "form": form, "cv_form": cv_form,
                    "result": {"letter": letter, "ats": ats, "source": "form"},
                })

        # 2) Via CV Upload
        if "generate_from_cv" in request.POST:
            form = FullCoverForm()
            cv_form = CVUploadForm(request.POST, request.FILES)
            if cv_form.is_valid():
                file = request.FILES["cv_file"]
                fs = FileSystemStorage(location=settings.MEDIA_ROOT)
                filename = fs.save(file.name, file)
                filepath = os.path.join(settings.MEDIA_ROOT, filename)

                if filename.lower().endswith(".pdf"):
                    parsed = parse_pdf(filepath)
                elif filename.lower().endswith(".docx"):
                    parsed = parse_docx(filepath)
                else:
                    parsed = {"error": "Format non supporté (PDF/DOCX uniquement)."}

                ctx = {
                    "full_name": (parsed.get("profile") or ["Candidat"])[0]
                                if isinstance(parsed.get("profile"), list) else "Candidat",
                    "target_role": "",
                    "company": "",
                    "experiences": parsed.get("experiences"),
                    "skills": parsed.get("skills"),
                    "achievements": parsed.get("achievements"),
                }
                letter = render_letter(ctx, language="fr", tone="pro")
                ats = compute_ats_score(letter, "")

                if "save_letter" in request.POST:
                    obj = Letter.objects.create(
                        full_name=ctx["full_name"], language="fr", tone="pro",
                        source="cv", content=letter, ats_score=ats["score"],
                        target_role="", company="", keywords=""
                    )
                    return redirect("motivation_letter:letter_detail", pk=obj.pk)

                return render(request, self.template_name, {
                    "form": form, "cv_form": CVUploadForm(),
                    "result": {"letter": letter, "ats": ats, "source": "cv", "parsed": parsed},
                })

        # fallback
        return render(request, self.template_name, {
            "form": FullCoverForm(),
            "cv_form": CVUploadForm(),
            "result": None
        })

# --- PDF ---
class PdfDownloadView(View):
    def post(self, request):
        letter = (request.POST.get("letter") or "").strip()
        filename = (request.POST.get("filename") or "lettre_de_motivation.pdf").strip()
        if not letter:
            return HttpResponseBadRequest("Lettre vide.")
        if len(letter) > 20000:
            return HttpResponseBadRequest("Lettre trop longue (>20000).")
        letter = re.sub(r"<[^>]+>", "", letter)

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.2*cm, bottomMargin=2.0*cm
        )
        styles = getSampleStyleSheet()
        base = ParagraphStyle("Base", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=16, alignment=TA_LEFT)
        header = ParagraphStyle("Header", parent=base, fontName="Helvetica-Bold", fontSize=13, leading=18)
        date_st = ParagraphStyle("Date", parent=base, spaceAfter=12)

        story, blocks = [], [b for b in letter.split("\n\n") if b.strip()]
        if blocks:
            story.append(Paragraph(blocks[0].replace("\n", "<br/>"), header)); story.append(Spacer(1, 0.2*cm)); blocks = blocks[1:]
        if blocks:
            story.append(Paragraph(blocks[0].replace("\n", "<br/>"), date_st)); blocks = blocks[1:]
        for b in blocks:
            story.append(Paragraph(b.replace("\n", "<br/>"), base)); story.append(Spacer(1, 0.35*cm))
        doc.build(story)

        pdf = buffer.getvalue(); buffer.close()
        if not filename.lower().endswith(".pdf"): filename += ".pdf"
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

# --- Historique ---
class LetterListView(View):
    template_name = "motivation_letter/letter_list.html"
    def get(self, request):
        letters = Letter.objects.all()
        return render(request, self.template_name, {"letters": letters})

class LetterDetailView(View):
    template_name = "motivation_letter/letter_detail.html"
    def get(self, request, pk: int):
        obj = get_object_or_404(Letter, pk=pk)
        return render(request, self.template_name, {"letter": obj})
