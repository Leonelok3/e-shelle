import re
from datetime import date
from cv_generator.models import Experience, Education, Skill, Language


import re
from cv_generator.models import Experience, Education


def map_cv_text_to_models(cv, text):
    """
    Mapping SIMPLE et PRÉVISIBLE du CV importé.
    Objectif : structure claire, pas perfection.
    """

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # ============================
    # EXPERIENCES (SIMPLE)
    # ============================
    current_exp = None
    buffer = []

    for line in lines:
        # Détection ligne poste / entreprise
        if re.search(r"(?:—|-| at )", line, re.IGNORECASE):
            if current_exp:
                current_exp.description_raw = "\n".join(buffer)
                current_exp.save()
                buffer = []

            parts = re.split(r"(?:—|-| at )", line, maxsplit=1)
            title = parts[0].strip()
            company = parts[1].strip() if len(parts) > 1 else ""

            current_exp = Experience.objects.create(
                cv=cv,
                title=title[:200],
                company=company[:200],
            )

        else:
            if current_exp:
                buffer.append(line)

    if current_exp:
        current_exp.description_raw = "\n".join(buffer)
        current_exp.save()

    # ============================
    # EDUCATION (BASIQUE)
    # ============================
    for line in lines:
        if "université" in line.lower() or "baccala" in line.lower():
            Education.objects.create(
                cv=cv,
                diploma=line[:200],
                institution="",
            )

   

def extract_summary(text):
    lines = text.split("\n")
    summary_lines = []
    for line in lines[:8]:
        if len(line.strip()) > 40:
            summary_lines.append(line.strip())
    return " ".join(summary_lines[:3])


def extract_experiences(text):
    results = []
    blocks = re.split(r"\n\n+", text)

    for block in blocks:
        if re.search(r"(experience|work|emploi)", block.lower()):
            lines = block.split("\n")
            title = lines[0][:120]
            results.append({
                "title": title,
                "description": block.strip()
            })
    return results[:5]


def extract_educations(text):
    results = []
    blocks = re.split(r"\n\n+", text)

    for block in blocks:
        if re.search(r"(education|formation|université|school)", block.lower()):
            results.append({
                "diploma": block.split("\n")[0][:120],
                "description": block.strip()
            })
    return results[:3]


def extract_skills(text):
    keywords = set()
    for word in re.findall(r"[A-Za-z\+#]{3,}", text):
        if word.lower() in [
            "python", "django", "excel", "sql", "management",
            "communication", "leadership", "marketing"
        ]:
            keywords.add(word.capitalize())
    return list(keywords)


def extract_languages(text):
    langs = []
    if "english" in text.lower():
        langs.append({"name": "English", "level": "Professional"})
    if "french" in text.lower() or "français" in text.lower():
        langs.append({"name": "Français", "level": "Native"})
    return langs


from datetime import date
from cv_generator.models import Experience


def map_cv_text_to_models(cv, text: str):
    """
    Création minimale d'expériences depuis un CV importé.
    Objectif : ne JAMAIS laisser Step 2 vide après upload.
    """

    # Sécurité : ne pas dupliquer
    if cv.experiences.exists():
        return

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Fallback ultra-sûr
    Experience.objects.create(
        cv=cv,
        title="Poste importé depuis le CV",
        company="Entreprise non précisée",
        start_date=date(2019, 1, 1),
        end_date=None,
        description_raw="\n".join(lines[:8])
    )
