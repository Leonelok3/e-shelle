"""Audit the daily TCF content bank and its required local audio assets."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from preparation_tests.services.daily_tcf import daily_session, daily_audio_name
from preparation_tests.services.daily_tcf_bank import TOPICS


class Command(BaseCommand):
    help = "Contrôle les contenus quotidiens TCF, les trois tâches et les fichiers audio."

    def handle(self, *args, **options):
        errors = []
        titles = [topic.get("title", "") for topic in TOPICS]
        if len(set(titles)) != len(titles):
            errors.append("Titres de thèmes dupliqués.")
        events = [topic.get("event", "") for topic in TOPICS]
        if len(set(events)) != len(events):
            errors.append("Événements de mise en situation dupliqués.")
        if len(TOPICS) < 7:
            errors.append(f"Banque trop courte : {len(TOPICS)} thèmes, minimum 7.")
        audio_missing = []
        for number, topic in enumerate(TOPICS, 1):
            if not topic.get("title") or not topic.get("event"):
                errors.append(f"Thème {number} : titre ou événement absent.")
            if not topic.get("lessons", {}).get("eo"):
                errors.append(f"Thème {number} : leçon EO absente.")
            for skill in ("ce", "co"):
                section = topic.get(skill, {})
                document = section.get("document", "")
                questions = section.get("questions", [])
                if len(document.split()) < 50 or len(questions) != 3:
                    errors.append(f"Thème {number}/{skill.upper()} : document trop court ou nombre de QCM incorrect.")
                for qno, question in enumerate(questions, 1):
                    if set(question.get("options", {})) != set("ABCD") or question.get("answer") not in question.get("options", {}):
                        errors.append(f"Thème {number}/{skill.upper()}/Q{qno} : options ou clé incorrectes.")
                    if question.get("evidence", "") not in document:
                        errors.append(f"Thème {number}/{skill.upper()}/Q{qno} : preuve absente du document.")
            if set(topic.get("ee", {})) != {"1", "2", "3"}:
                errors.append(f"Thème {number}/EE : les trois tâches ne sont pas définies.")
            audio_path = Path(settings.MEDIA_ROOT) / daily_audio_name(topic.get("co", {}).get("document", ""))
            if not audio_path.is_file() or audio_path.stat().st_size == 0:
                audio_missing.append(topic.get("title", f"thème {number}"))

        task_sessions = {daily_session_from_index(i)["task_number"] for i in range(28)
                         if daily_session_from_index(i)["skill"] == "eo"}
        if task_sessions != {1, 2, 3}:
            errors.append("Le cycle quotidien ne couvre pas les trois tâches d'expression orale.")
        if audio_missing:
            errors.append(f"Audios CO absents ou vides : {len(audio_missing)}/{len(TOPICS)} ({'; '.join(audio_missing)}).")

        self.stdout.write(f"Banque : {len(TOPICS)} thèmes · cycle 28 jours · tâches EO {', '.join(map(str, sorted(task_sessions)))}")
        self.stdout.write(f"Audios CO prêts : {len(TOPICS) - len(audio_missing)}/{len(TOPICS)}")
        for error in errors:
            self.stderr.write(self.style.ERROR("ERREUR : " + error))
        if errors:
            raise CommandError(f"Audit en échec : {len(errors)} erreur(s).")
        self.stdout.write(self.style.SUCCESS("Audit TCF quotidien valide."))


def daily_session_from_index(index):
    """Use the real deterministic schedule while avoiding a hardcoded epoch."""
    from datetime import date, timedelta
    from preparation_tests.services.daily_tcf import EPOCH
    return daily_session(EPOCH + timedelta(days=index))
