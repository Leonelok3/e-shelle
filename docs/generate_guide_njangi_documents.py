from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "guide_njangi_digital_utilisation_investisseurs.md"
PDF_OUTPUT = ROOT / "guide_njangi_digital_utilisation_investisseurs.pdf"
RTF_OUTPUT = ROOT / "guide_njangi_digital_utilisation_investisseurs.rtf"


BLUE = colors.HexColor("#1B6CA8")
DARK = colors.HexColor("#0D2438")
GOLD = colors.HexColor("#F5A623")
MUTED = colors.HexColor("#4B6375")
LIGHT = colors.HexColor("#EBF4FB")


def clean_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    return text


def pdf_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "NjangiTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            alignment=TA_CENTER,
            textColor=DARK,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "NjangiSubtitle",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=15,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "NjangiH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15.5,
            leading=20,
            textColor=BLUE,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "NjangiH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=GOLD,
            spaceBefore=7,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "NjangiBody",
            parent=base["BodyText"],
            fontSize=9.5,
            leading=13.5,
            textColor=DARK,
            spaceAfter=4.5,
        ),
        "bullet": ParagraphStyle(
            "NjangiBullet",
            parent=base["BodyText"],
            fontSize=9.3,
            leading=13,
            leftIndent=14,
            firstLineIndent=-8,
            textColor=DARK,
            spaceAfter=3,
        ),
        "quote": ParagraphStyle(
            "NjangiQuote",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            leading=13.5,
            leftIndent=10,
            borderColor=BLUE,
            borderWidth=0.8,
            borderPadding=7,
            backColor=LIGHT,
            textColor=DARK,
            spaceAfter=6,
        ),
        "table": ParagraphStyle(
            "NjangiTableLine",
            parent=base["BodyText"],
            fontSize=8.8,
            leading=12.2,
            textColor=DARK,
            leftIndent=8,
            spaceAfter=2,
        ),
    }


def markdown_to_pdf():
    styles = pdf_styles()
    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    first_title = True
    in_code = False
    code_lines = []
    in_table = False

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
            in_table = False
            story.append(Spacer(1, 0.07 * cm))
            continue

        if raw == "---":
            in_table = False
            story.append(Spacer(1, 0.18 * cm))
            continue

        if raw.startswith("# "):
            in_table = False
            if first_title:
                story.append(Paragraph(clean_inline(raw[2:]), styles["title"]))
                story.append(Paragraph("Guide de reference pour formation, usage terrain, partenaires et investisseurs.", styles["subtitle"]))
                first_title = False
            else:
                story.append(PageBreak())
                story.append(Paragraph(clean_inline(raw[2:]), styles["title"]))
            continue

        if raw.startswith("## "):
            in_table = False
            story.append(Paragraph(clean_inline(raw[3:]), styles["h1"]))
            continue

        if raw.startswith("### "):
            in_table = False
            story.append(Paragraph(clean_inline(raw[4:]), styles["h2"]))
            continue

        if raw.startswith("- "):
            in_table = False
            story.append(Paragraph(f"- {clean_inline(raw[2:])}", styles["bullet"]))
            continue

        if raw.startswith("|"):
            if "---" in raw:
                continue
            cells = [cell.strip() for cell in raw.strip("|").split("|")]
            prefix = " | " if in_table else ""
            in_table = True
            story.append(Paragraph(prefix + clean_inline("  |  ".join(cells)), styles["table"]))
            continue

        if raw.startswith("> "):
            in_table = False
            story.append(Paragraph(clean_inline(raw[2:]), styles["quote"]))
            continue

        in_table = False
        story.append(Paragraph(clean_inline(raw), styles["body"]))

    doc = SimpleDocTemplate(
        str(PDF_OUTPUT),
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.25 * cm,
        bottomMargin=1.25 * cm,
        title="Guide Njangi Digital",
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
        r"{\colortbl;\red13\green36\blue56;\red27\green108\blue168;\red245\green166\blue35;\red75\green99\blue117;}",
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
            out.append(r"\page\pard\qc\b\f1\fs40\cf1 " + rtf_escape(raw[2:]) + r"\b0\f0\fs22\cf0\par")
            continue
        if raw.startswith("## "):
            out.append(r"\pard\sa150\b\f0\fs29\cf2 " + rtf_escape(raw[3:]) + r"\b0\fs22\cf0\par")
            continue
        if raw.startswith("### "):
            out.append(r"\pard\sa95\b\f0\fs24\cf3 " + rtf_escape(raw[4:]) + r"\b0\fs22\cf0\par")
            continue
        if raw.startswith("- "):
            out.append(r"\pard\li360\fi-180\fs21 \bullet\tab " + rtf_escape(raw[2:]) + r"\par")
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
