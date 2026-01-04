import re
from cv_generator.models import Experience, Skill

def prefill_cv_from_text(cv, text):
    # Exemple simple (on améliore après)
    if "EXPERIENCE" in text.upper():
        Experience.objects.create(
            cv=cv,
            title="Poste détecté",
            company="Entreprise détectée",
            start_date="2020-01-01",
        )

    # Détection compétences
    keywords = ["python", "excel", "management", "maintenance"]
    for k in keywords:
        if k.lower() in text.lower():
            Skill.objects.get_or_create(cv=cv, name=k)
