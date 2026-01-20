import os
import re
from io import BytesIO

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

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


def _strip_html(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\r\n?", "\n", s)
    return s.strip()


def _normalize_keywords(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s*,\s*", ", ", s)
    items = [i.strip() for i in s.split(",") if i.strip()]
    seen = set()
    out = []
    for i in items:
        key = i.lower()
        if key not in seen:
            seen.add(key)
            out.append(i)
    return ", ".join(out)


def _build_context_from_form(data: dict) -> dict:
    exps = _strip_html(data.get("experiences", ""))[:1200]
    skills = _strip_html(data.get("skills", ""))[:800]

    return {
        "full_name": (data.get("full_name") or "").strip(),
        "email": (data.get("email") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "target_role": (data.get("target_role") or "").strip(),
        "company": (data.get("company") or "").strip(),
        "experiences": exps,
        "skills": skills,
    }


def _build_context_from_parsed(parsed: dict) -> dict:
    profile = parsed.get("profile")
    if isinstance(profile, list) and profile:
        full_name = str(profile[0]).strip()
    elif isinstance(profile, str) and profile.strip():
        full_name = profile.strip()
    else:
        full_name = "Candidat"

    experiences = parsed.get("experiences")
    skills = parsed.get("skills")
    achievements = parsed.get("achievements")

    if isinstance(experiences, str):
        experiences = experiences[:1400]
    if isinstance(skills, str):
        skills = skills[:900]
    if isinstance(achievements, str):
        achievements = achievements[:900]

    return {
        "full_name": full_name,
        "email": "",
        "phone": "",
        "target_role": "",
        "company": "",
        "experiences": experiences or "",
        "skills": skills or "",
        "achievements": achievements or "",
    }


class HomeView(TemplateView):
    template_name = "motivation_letter/home.html"


class StartGeneratorView(View):
    """
    - si connecté -> generator
    - sinon -> login + next vers generator
    """
    def get(self, request):
        generator_url = reverse("motivation_letter:generator")
        if request.user.is_authenticated:
            return redirect(generator_url)

        login_url = reverse("authentification:login")
        return redirect(f"{login_url}?next={generator_url}")


class GeneratorView(LoginRequiredMixin, View):
    template_name = "motivation_letter/generator.html"
    login_url = "authentification:login"

    def get(self, request):
        return render(request, self.template_name, {
            "form": FullCoverForm(),
            "cv_form": CVUploadForm(),
            "result": None
        })

    def post(self, request):
        # 1) Génération depuis formulaire
        if "generate_from_form" in request.POST:
            form = FullCoverForm(request.POST)
            cv_form = CVUploadForm()

            if not form.is_valid():
                return render(request, self.template_name, {"form": form, "cv_form": cv_form, "result": None})

            data = form.cleaned_data
            lang = data.get("language", "fr")
            tone = data.get("tone", "pro")

            ctx = _build_context_from_form(data)

            letter_text = _strip_html(render_letter(ctx, language=lang, tone=tone))
            keywords = _normalize_keywords(data.get("keywords", ""))
            ats = compute_ats_score(letter_text, keywords)

            if "save_letter" in request.POST:
                obj = Letter.objects.create(
                    user=request.user,  # ✅
                    full_name=ctx["full_name"],
                    email=ctx["email"],
                    phone=ctx["phone"],
                    target_role=ctx["target_role"],
                    company=ctx["company"],
                    keywords=keywords,
                    language=lang,
                    tone=tone,
                    source="form",
                    content=letter_text,
                    ats_score=int(ats.get("score", 0) or 0),
                )
                return redirect("motivation_letter:letter_detail", pk=obj.pk)

            return render(request, self.template_name, {
                "form": form,
                "cv_form": cv_form,
                "result": {"letter": letter_text, "ats": ats, "source": "form"},
            })

        # 2) Génération depuis CV upload
        if "generate_from_cv" in request.POST:
            form = FullCoverForm()
            cv_form = CVUploadForm(request.POST, request.FILES)

            if not cv_form.is_valid():
                return render(request, self.template_name, {"form": form, "cv_form": cv_form, "result": None})

            f = request.FILES["cv_file"]
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            filename = fs.save(f"ml_{request.user.id}_{f.name}", f)
            filepath = os.path.join(settings.MEDIA_ROOT, filename)

            try:
                if filename.lower().endswith(".pdf"):
                    parsed = parse_pdf(filepath)
                elif filename.lower().endswith(".docx"):
                    parsed = parse_docx(filepath)
                else:
                    parsed = {"error": "Format non supporté (PDF/DOCX uniquement)."}
            finally:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception:
                    pass

            ctx = _build_context_from_parsed(parsed)

            letter_text = _strip_html(render_letter(ctx, language="fr", tone="pro"))
            ats = compute_ats_score(letter_text, "")

            if "save_letter" in request.POST:
                obj = Letter.objects.create(
                    user=request.user,  # ✅
                    full_name=ctx["full_name"],
                    email="",
                    phone="",
                    target_role=ctx.get("target_role", "") or "",
                    company=ctx.get("company", "") or "",
                    keywords="",
                    language="fr",
                    tone="pro",
                    source="cv",
                    content=letter_text,
                    ats_score=int(ats.get("score", 0) or 0),
                )
                return redirect("motivation_letter:letter_detail", pk=obj.pk)

            return render(request, self.template_name, {
                "form": form,
                "cv_form": CVUploadForm(),
                "result": {"letter": letter_text, "ats": ats, "source": "cv", "parsed": parsed},
            })

        return render(request, self.template_name, {
            "form": FullCoverForm(),
            "cv_form": CVUploadForm(),
            "result": None
        })


class PdfDownloadView(LoginRequiredMixin, View):
    def post(self, request):
        letter = _strip_html(request.POST.get("letter") or "")
        filename = (request.POST.get("filename") or "lettre_de_motivation.pdf").strip()

        if not letter:
            return HttpResponseBadRequest("Lettre vide.")
        if len(letter) > 25000:
            return HttpResponseBadRequest("Lettre trop longue (>25000).")

        filename = filename.replace('"', "").replace("'", "").strip()
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2.2 * cm,
            rightMargin=2.2 * cm,
            topMargin=2.1 * cm,
            bottomMargin=2.0 * cm,
        )

        styles = getSampleStyleSheet()
        base = ParagraphStyle(
            "Base",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_LEFT,
            spaceAfter=10,
        )
        header = ParagraphStyle(
            "Header",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=18,
            spaceAfter=10,
        )

        blocks = [b.strip() for b in letter.split("\n\n") if b.strip()]
        story = []

        if blocks:
            first = blocks[0]
            if first.lower().startswith("objet") or len(first) < 70:
                story.append(Paragraph(first.replace("\n", "<br/>"), header))
                story.append(Spacer(1, 0.15 * cm))
                blocks = blocks[1:]

        for b in blocks:
            story.append(Paragraph(b.replace("\n", "<br/>"), base))

        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()

        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


class LetterListView(LoginRequiredMixin, View):
    template_name = "motivation_letter/letter_list.html"

    def get(self, request):
        letters = Letter.objects.filter(user=request.user)  # ✅
        return render(request, self.template_name, {"letters": letters})


class LetterDetailView(LoginRequiredMixin, View):
    template_name = "motivation_letter/letter_detail.html"

    def get(self, request, pk: int):
        obj = get_object_or_404(Letter, pk=pk, user=request.user)  # ✅
        return render(request, self.template_name, {"letter": obj})
