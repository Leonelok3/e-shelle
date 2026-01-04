import re

KEYWORDS_BY_JOB = {
    "default": [
        "experience", "skills", "responsible", "team", "project",
        "maintenance", "analysis", "management", "support"
    ]
}

def calculate_ats_score(cv, language="fr"):
    score = 0
    feedback = []
    keywords_found = set()

    # SUMMARY
    if cv.summary and len(cv.summary.split()) >= 30:
        score += 20
    else:
        feedback.append("Résumé trop court ou manquant")

    # EXPERIENCE
    exp_count = cv.experiences.count()
    if exp_count >= 1:
        score += 15
    if exp_count >= 2:
        score += 10

    # SKILLS
    skills_count = cv.skills.count()
    if skills_count >= 5:
        score += 20
    else:
        feedback.append("Ajoutez au moins 5 compétences")

    # LANGUAGES
    if cv.languages.exists():
        score += 10
    else:
        feedback.append("Ajoutez vos langues")

    # EDUCATION
    if cv.educations.exists():
        score += 15
    else:
        feedback.append("Ajoutez une formation")

    # KEYWORDS
    text_blob = " ".join([
        cv.summary or "",
        " ".join(e.description_raw or "" for e in cv.experiences.all())
    ]).lower()

    for kw in KEYWORDS_BY_JOB["default"]:
        if re.search(rf"\b{kw}\b", text_blob):
            keywords_found.add(kw)

    if len(keywords_found) >= 3:
        score += 10
    else:
        feedback.append("Ajoutez plus de mots-clés métier")

    return {
        "score": min(score, 100),
        "keywords_found": list(keywords_found),
        "feedback": feedback,
    }
