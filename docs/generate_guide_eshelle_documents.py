from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "guide_complet_eshelle_vision_utilisation_investisseurs.md"
PDF_OUTPUT = ROOT / "guide_complet_eshelle_vision_utilisation_investisseurs.pdf"
RTF_OUTPUT = ROOT / "guide_complet_eshelle_vision_utilisation_investisseurs.rtf"


GREEN = colors.HexColor("#1f9d55")
DARK = colors.HexColor("#07130d")
GOLD = colors.HexColor("#d6a21c")
MUTED = colors.HexColor("#4b6153")


def clean_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text


def pdf_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "EshelleTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=31,
            alignment=TA_CENTER,
            textColor=DARK,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "EshelleSubtitle",
            parent=base["BodyText"],
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "EshelleH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=21,
            textColor=GREEN,
            spaceBefore=12,
            spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "EshelleH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=GOLD,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "EshelleBody",
            parent=base["BodyText"],
            fontSize=9.7,
            leading=14,
            textColor=DARK,
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "EshelleBullet",
            parent=base["BodyText"],
            fontSize=9.5,
            leading=13.5,
            leftIndent=14,
            firstLineIndent=-8,
            textColor=DARK,
            spaceAfter=3,
        ),
        "quote": ParagraphStyle(
            "EshelleQuote",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=14,
            leftIndent=12,
            borderColor=GREEN,
            borderWidth=0.8,
            borderPadding=7,
            backColor=colors.HexColor("#eef8f0"),
            textColor=DARK,
            spaceAfter=7,
        ),
    }


def markdown_to_pdf():
    styles = pdf_styles()
    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    first_title = True
    in_code = False
    code_lines = []

    for line in lines:
        raw = line.rstrip()

        if raw.startswith("```"):
            if in_code:
                if code_lines:
                    story.append(Paragraph(clean_inline("<br/>".join(code_lines)), styles["quote"]))
                    code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw)
            continue

        if not raw:
            story.append(Spacer(1, 0.08 * cm))
            continue

        if raw == "---":
            story.append(Spacer(1, 0.2 * cm))
            continue

        if raw.startswith("# "):
            if first_title:
                story.append(Paragraph(clean_inline(raw[2:]), styles["title"]))
                story.append(Paragraph("Document de reference pour presentation, formation, partenaires et investisseurs.", styles["subtitle"]))
                first_title = False
            else:
                story.append(PageBreak())
                story.append(Paragraph(clean_inline(raw[2:]), styles["title"]))
            continue

        if raw.startswith("## "):
            story.append(Paragraph(clean_inline(raw[3:]), styles["h1"]))
            continue

        if raw.startswith("### "):
            story.append(Paragraph(clean_inline(raw[4:]), styles["h2"]))
            continue

        if raw.startswith("- "):
            story.append(Paragraph(f"- {clean_inline(raw[2:])}", styles["bullet"]))
            continue

        if raw.startswith("> "):
            story.append(Paragraph(clean_inline(raw[2:]), styles["quote"]))
            continue

        story.append(Paragraph(clean_inline(raw), styles["body"]))

    doc = SimpleDocTemplate(
        str(PDF_OUTPUT),
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.25 * cm,
        bottomMargin=1.25 * cm,
        title="Guide complet E-Shelle",
        author="E-Shelle",
    )
    doc.build(story)


def rtf_escape(text: str) -> str:
    replacements = {
        "\\": "\\\\",
        "{": "\\{",
        "}": "\\}",
        "\n": "\\par\n",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def markdown_to_rtf():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    out = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Arial;}{\f1 Arial Black;}{\f2 Courier New;}}",
        r"{\colortbl;\red7\green19\blue13;\red31\green157\blue85;\red214\green162\blue28;\red75\green97\blue83;}",
        r"\viewkind4\uc1",
    ]
    in_code = False

    for line in lines:
        raw = line.rstrip()
        if raw.startswith("```"):
            in_code = not in_code
            continue
        if not raw or raw == "---":
            out.append(r"\par")
            continue
        if in_code:
            out.append(r"\f2\fs19 " + rtf_escape(raw) + r"\par")
            continue
        if raw.startswith("# "):
            out.append(r"\page\pard\qc\b\f1\fs42\cf1 " + rtf_escape(raw[2:]) + r"\b0\f0\fs22\cf0\par")
            continue
        if raw.startswith("## "):
            out.append(r"\pard\sa160\b\f0\fs30\cf2 " + rtf_escape(raw[3:]) + r"\b0\fs22\cf0\par")
            continue
        if raw.startswith("### "):
            out.append(r"\pard\sa100\b\f0\fs24\cf3 " + rtf_escape(raw[4:]) + r"\b0\fs22\cf0\par")
            continue
        if raw.startswith("- "):
            out.append(r"\pard\li360\fi-180\fs21 \bullet\tab " + rtf_escape(raw[2:]) + r"\par")
            continue
        if raw.startswith("> "):
            out.append(r"\pard\li360\i\fs22\cf4 " + rtf_escape(raw[2:]) + r"\i0\cf0\par")
            continue
        text = re.sub(r"\*\*(.*?)\*\*", r"\b \1\b0 ", raw)
        text = re.sub(r"`([^`]+)`", r"\f2 \1\f0 ", text)
        out.append(r"\pard\fs22\cf1 " + rtf_escape(text) + r"\cf0\par")

    out.append("}")
    RTF_OUTPUT.write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    markdown_to_pdf()
    markdown_to_rtf()
    print(f"PDF genere: {PDF_OUTPUT}")
    print(f"Word modifiable genere: {RTF_OUTPUT}")
