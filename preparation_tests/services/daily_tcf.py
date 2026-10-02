"""Original daily TCF Canada practice. Never generated during a page request."""
import copy
import hashlib
import random
import unicodedata
from datetime import date
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from .daily_tcf_bank import TOPICS

EPOCH = date(2026, 10, 1)
SKILLS = ("ce", "co", "ee", "eo")
LABELS = {"ce": "Compréhension écrite", "co": "Compréhension orale", "ee": "Expression écrite", "eo": "Expression orale"}
LESSONS = {
    "ce": ("Repérer la règle et son exception", ["Lis d'abord la question : cherche un fait, une intention ou une condition précise.", "Repère les marqueurs : sauf, uniquement, à condition que, cependant. Ils modifient la règle principale.", "Élimine chaque réponse qui ajoute une information absente ou transforme une possibilité en obligation."]),
    "co": ("Écouter ce qui change dans le dialogue", ["Avant l'écoute, lis les questions pour savoir quelles informations retenir.", "Distingue la première proposition de la décision finale. Une correction de date ou de lieu est souvent décisive.", "Ne choisis pas une réponse simplement parce que tu as entendu ses mots : vérifie leur rôle dans l'échange."]),
    "ee": ("Écrire pour un destinataire et un objectif", ["Avant d'écrire, identifie le destinataire, le type de texte et tous les éléments demandés.", "Pour un message, donne les informations utiles ; pour un récit, organise les événements ; pour comparer, reformule les deux points de vue avant ton avis.", "Garde du temps pour compter les mots et vérifier accords, temps, ponctuation et cohérence."]),
    "eo": ("Développer un point de vue sans préparation", ["Réponds directement à la question, puis annonce brièvement tes raisons.", "Développe une raison avec un exemple concret. Présente aussi une limite ou une objection.", "Termine par une conclusion claire. Parle naturellement : un vocabulaire précis vaut mieux que des expressions mémorisées sans lien avec le sujet."]),
}


def daily_audio_name(script):
    text = unicodedata.normalize("NFC", script.strip())
    digest = hashlib.sha256(("gtts-v2\0fr\0" + text).encode("utf-8")).hexdigest()
    return f"audio/fr/tcf_daily/tts_{digest}.mp3"


def daily_session(day=None):
    day = day or timezone.localdate()
    index = (day - EPOCH).days % (len(TOPICS) * len(SKILLS))
    skill = SKILLS[index % 4]
    topic = copy.deepcopy(TOPICS[index // 4])
    session = {"date": day, "key": day.isoformat(), "skill": skill, "skill_label": LABELS[skill],
               "topic": topic["title"], "lesson_title": topic["lessons"][skill][0],
               "lesson_steps": [topic["lessons"][skill][1], *LESSONS[skill][1]],
               "source": "https://www.france-education-international.fr/test/tcf-canada", "cycle_days": 28}
    if skill in ("ce", "co"):
        session.update(topic[skill])
        rng = random.Random("tcf-daily-v1:" + day.isoformat())
        for question in session["questions"]:
            choices = list(question["options"].items())
            rng.shuffle(choices)
            question["options"] = {letter: value for letter, (_, value) in zip("ABCD", choices)}
            question["answer"] = next(letter for letter, (old_letter, _) in zip("ABCD", choices) if old_letter == question["answer"])
        session.update(duration=300, duration_label="5 minutes", format_label="Mini-séquence · 3 QCM, 4 choix, une réponse correcte",
                       format_note="Durée d'entraînement conseillée. L'épreuve complète comprend 39 questions : 35 minutes à l'oral, 60 minutes à l'écrit.")
        if skill == "co":
            name = daily_audio_name(session["document"])
            session["audio_ready"] = (Path(settings.MEDIA_ROOT) / name).is_file() and (Path(settings.MEDIA_ROOT) / name).stat().st_size > 0
            session["audio_url"] = settings.MEDIA_URL.rstrip("/") + "/" + name if session["audio_ready"] else ""
    elif skill == "ee":
        task = index // 4 % 3 + 1
        limits = {1: (60, 120), 2: (120, 150), 3: (120, 180)}
        minimum, maximum = limits[task]
        session.update(duration=1200, duration_label="20 minutes", task_number=task, word_min=minimum, word_max=maximum,
                       question=topic["ee"][str(task)], document=topic["debate"] if task == 3 else "",
                       format_label=f"Expression écrite · tâche {task} · {minimum} à {maximum} mots",
                       format_note="Une tâche isolée ; 20 minutes est un objectif d'entraînement. L'épreuve complète comprend 3 tâches en 60 minutes.")
    else:
        session.update(duration=270, duration_label="4 minutes 30", task_number=3, question=topic["eo"], document="",
                       format_label="Expression orale · tâche 3 · point de vue sans préparation",
                       format_note="Durée de la tâche 3 du TCF Canada. L'épreuve orale complète comprend 3 tâches en 12 minutes. Ici, entraîne-toi seul à parler ; ce n'est pas un entretien avec un examinateur.")
    return session


def grade_questions(session, answers):
    rows = []
    for number, question in enumerate(session["questions"]):
        selected = answers.get(str(number), "")
        if selected not in ("A", "B", "C", "D"):
            selected = ""
        rows.append({**question, "selected": selected, "is_correct": selected == question["answer"]})
    return {"rows": rows, "correct": sum(row["is_correct"] for row in rows), "total": len(rows)}
