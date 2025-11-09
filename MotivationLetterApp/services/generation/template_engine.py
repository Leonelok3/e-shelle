from typing import Dict, List
from datetime import date
import re
import unicodedata

# ------------------ helpers texte/ATS ------------------

def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")

def _tokens(s: str) -> List[str]:
    s = _strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9\s\-\+\.]", " ", s)
    raw = re.split(r"[\s,;:/|]+", s)
    toks = [t for t in raw if t and len(t) > 1]
    # stemming léger : virer fins courantes FR/EN
    stemmed = []
    for t in toks:
        for suf in ("ment", "tion", "sion", "ment", "able", "ible", "ance", "ence", "ies", "ing", "ed", "es", "s"):
            if t.endswith(suf) and len(t) > len(suf) + 2:
                t = t[: -len(suf)]
                break
        stemmed.append(t)
    return stemmed

def _listize(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in re.split(r"[,;\n]+", str(value)) if p.strip()]

def compute_ats_score(letter_text: str, keywords) -> dict:
    """Score par couverture de mots-clés avec normalisation/“stemming” léger."""
    kws = [k for k in _listize(keywords)]
    if not kws:
        return {"score": 0, "matched": [], "missing": []}

    toks = set(_tokens(letter_text))
    matched, missing = [], []
    for k in kws:
        ktoks = set(_tokens(k))
        ok = any(kt in toks for kt in ktoks)
        (matched if ok else missing).append(k)
    score = int(round(100 * len(matched) / max(1, len(kws))))
    return {"score": score, "matched": matched, "missing": missing}

# ------------------ templates ------------------

TEMPLATES = {
    # FR
    ("fr", "pro"): """{header}

{city_date}

{greeting}

{intro}

{evidence}

{fit}

{closing}
{signature}
""",
    ("fr", "convaincant"): """{header}

{city_date}

{greeting}

{intro_conv}

{evidence}

{fit_conv}

{closing_strong}
{signature}
""",
    ("fr", "sobre"): """{header}

{city_date}

{greeting}

{intro_short}

{fit_short}

{closing_brief}
{signature}
""",
    # EN
    ("en", "pro"): """{header}

{city_date}

{greeting_en}

{intro_en}

{evidence_en}

{fit_en}

{closing_en}
{signature_en}
""",
}

SECTOR_SNIPPETS_FR = {
    "santé": "Respect strict des protocoles, sens aigu des priorités, confidentialité et empathie au cœur de ma pratique.",
    "informatique": "Culture DevOps, qualité de code, documentation, sécurité et performance orientées produit.",
    "finance": "Rigueur analytique, conformité et sens du risque au service d’indicateurs fiables.",
    "marketing": "Pilotage ROI, segmentation, A/B testing et activation multicanale centrée client.",
}

def _fmt_header(full_name: str, email: str = "", phone: str = "") -> str:
    line2 = " • ".join([x for x in [email, phone] if x])
    return f"{full_name}\n{line2}" if line2 else full_name

def _make_blocks(ctx: Dict) -> Dict:
    full_name = ctx.get("full_name") or "Candidat"
    email = ctx.get("email", "")
    phone = ctx.get("phone", "")
    role = ctx.get("target_role") or "Poste"
    company = ctx.get("company") or "Votre entreprise"
    city = ctx.get("city") or ""
    sector = (ctx.get("sector") or "").strip().lower()

    experiences = ctx.get("experiences") or []
    if isinstance(experiences, str):
        experiences = _listize(experiences)
    skills = ctx.get("skills") or []
    if isinstance(skills, str):
        skills = _listize(skills)
    achievements = ctx.get("achievements") or []

    header = _fmt_header(full_name, email, phone)
    city_date = f"{city}, le {date.today():%d/%m/%Y}" if city else f"{date.today():%d/%m/%Y}"

    greeting = "Madame, Monsieur,"
    intro = (
        f"Je vous propose ma candidature au poste de {role} chez {company}. "
        f"Mon expérience et mes compétences correspondent aux exigences du poste."
    )
    intro_conv = (
        f"Motivé(e) par l’impact du poste {role} chez {company}, je propose une approche orientée résultats, "
        f"avec un démarrage rapide et mesurable."
    )
    intro_short = f"Candidature au poste de {role} chez {company}."

    bullet_exp = "\n".join([f"• {e}" for e in experiences[:5]]) if experiences else ""
    line_skills = "Compétences : " + ", ".join(skills[:10]) + "." if skills else ""
    evidence = ("Expériences clés :\n" + bullet_exp + ("\n" if bullet_exp and line_skills else "") + line_skills) \
               if (bullet_exp or line_skills) else "Expérience pertinente et directement mobilisable."
    snippet = SECTOR_SNIPPETS_FR.get(sector, "")
    fit = (f"Ce poste me motive particulièrement : il combine mes acquis et l’impact recherché chez {company}. "
           f"{snippet} Je peux être rapidement opérationnel(le) et contribuer à des résultats mesurables.")
    fit_conv = (f"Je maximiserai la valeur du rôle {role} grâce à une exécution disciplinée, des priorités claires "
                f"et un suivi d’objectifs alignés {company}.")
    fit_short = f"Alignement fort avec le besoin de {company}."

    closing = "Je serais heureux(se) d’échanger pour détailler ma valeur ajoutée. Veuillez recevoir mes salutations distinguées."
    closing_strong = "Disponible rapidement pour un entretien, je serai ravi(e) de démontrer ma valeur. Cordialement."
    closing_brief = "Dans l’attente de votre retour, cordialement."
    signature = full_name

    # EN blocks
    greeting_en = "Dear Hiring Manager,"
    intro_en = f"I am applying for the {role} position at {company}."
    evidence_en = "Key experiences:\n" + ("\n".join([f"• {e}" for e in experiences[:5]]) if experiences else "Hands-on, relevant background.")
    if skills:
        evidence_en += ("\n" if experiences else "") + "Skills: " + ", ".join(skills[:10]) + "."
    fit_en = f"I am motivated by this role and can quickly contribute to measurable outcomes at {company}."
    closing_en = "I would welcome the opportunity to discuss how I can add value. Sincerely,"
    signature_en = full_name

    return {
        "header": header, "city_date": city_date,
        "greeting": greeting, "intro": intro, "intro_conv": intro_conv,
        "intro_short": intro_short, "evidence": evidence,
        "fit": fit, "fit_conv": fit_conv, "fit_short": fit_short,
        "closing": closing, "closing_strong": closing_strong, "closing_brief": closing_brief,
        "signature": signature,
        "greeting_en": greeting_en, "intro_en": intro_en,
        "evidence_en": evidence_en, "fit_en": fit_en,
        "closing_en": closing_en, "signature_en": signature_en,
    }

def render_letter(ctx: Dict, language: str = "fr", tone: str = "pro") -> str:
    blocks = _make_blocks(ctx)
    template = TEMPLATES.get((language, tone)) or TEMPLATES[("fr", "pro")]
    return template.format(**blocks)
