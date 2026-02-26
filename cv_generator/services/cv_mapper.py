import re
from datetime import date
from cv_generator.models import Experience


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
