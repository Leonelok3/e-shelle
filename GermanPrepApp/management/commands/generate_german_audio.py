"""
Commande Django : génération audio TTS pour les leçons HÖREN de GermanPrepApp.

Utilise le service TTS existant (edge-tts DE KatjaNeural en priorité).
Génère un fichier MP3 par leçon HÖREN et sauvegarde le chemin dans GermanLesson.audio_url.

Usage :
    python manage.py generate_german_audio
    python manage.py generate_german_audio --level A1
    python manage.py generate_german_audio --exam_type GOETHE --level B1
    python manage.py generate_german_audio --force   # re-génère même si audio existe déjà
"""
import logging
import re

from django.core.management.base import BaseCommand

from GermanPrepApp.models import GermanLesson
from ai_engine.services.tts_service import generate_audio

logger = logging.getLogger(__name__)

# Répertoire de sortie relatif à MEDIA_ROOT
AUDIO_OUTPUT_DIR = "audio/german"


FRENCH_WORDS = {
    'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'en', 'et', 'pour', 'avec', 
    'dans', 'sur', 'par', 'pas', 'vous', 'nous', 'je', 'tu', 'il', 'elle', 'on', 
    'ils', 'elles', 'est', 'sont', 'ont', 'avez', 'votre', 'notre', 'ce', 'cette', 
    'ces', 'mais', 'ou', 'donc', 'car', 'qui', 'que', 'quoi', 'dont', 'où', 'comme',
    'se', 'sa', 'son', 'ses', 'mes', 'tes', 'nos', 'vos', 'leurs', 'leur', 'aux', 'au'
}

def is_french(text: str) -> bool:
    # 1. Vérifier la présence d'accents typiquement français
    if re.search(r'[éèàçùâêîôûëïœæ]', text, re.IGNORECASE):
        return True
    # 2. Vérifier la présence de mots-outils français
    words = re.findall(r'\b\w+\b', text.lower())
    if any(w in FRENCH_WORDS for w in words):
        return True
    return False

def _extract_audio_text(lesson: GermanLesson) -> str:
    """
    Extrait uniquement le contenu allemand du texte de la leçon,
    en excluant les explications et traductions en français.
    """
    html = lesson.content or ""
    # Séparer les listes en repérant <li> et </li>
    items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE)
    german_parts = []
    
    for item in items:
        # 1. Si présence de "Traduction" ou "traduction", on exclut ce qui suit
        if re.search(r'traduction', item, re.IGNORECASE):
            item = re.split(r'traduction', item, flags=re.IGNORECASE)[0]
            
        # 2. Chercher du texte entre guillemets doubles (typique des répliques de dialogue allemand)
        quotes = re.findall(r'"([^"]+)"', item)
        if quotes:
            for q in quotes:
                cleaned_q = q.strip().strip('"').strip()
                if cleaned_q and not is_french(cleaned_q):
                    german_parts.append(cleaned_q)
            continue
            
        # 3. Chercher le texte dans les balises strong (vocabulaire)
        strongs = re.findall(r'<strong[^>]*>(.*?)</strong>', item, re.DOTALL | re.IGNORECASE)
        if strongs:
            for s in strongs:
                s_clean = re.sub(r'<[^>]+>', ' ', s)
                s_clean = re.sub(r'\.\.\.$', '', s_clean.strip()).strip()
                if s_clean and not is_french(s_clean):
                    german_parts.append(s_clean)
            continue
            
        # 4. Fallback : prendre le texte brut avant parenthèse ou tiret
        clean_text = re.sub(r'<[^>]+>', ' ', item)
        clean_text = re.split(r'[\(\-\:]', clean_text)[0].strip()
        if clean_text and not is_french(clean_text):
            german_parts.append(clean_text)

    # Si aucune liste trouvée, fallback sur les paragraphes p
    if not german_parts:
        paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        for p in paras:
            p_clean = re.sub(r'<[^>]+>', ' ', p)
            p_clean = re.split(r'[\(\-\:]', p_clean)[0].strip()
            if p_clean and not is_french(p_clean):
                german_parts.append(p_clean)
            
    # Nettoyage final des doublons consécutifs et des lignes vides
    final_parts = []
    for part in german_parts:
        part = part.strip()
        if part and part not in final_parts:
            final_parts.append(part)
            
    return " ".join(final_parts)


class Command(BaseCommand):
    help = "Génère les fichiers audio TTS pour les leçons HÖREN de GermanPrepApp"

    def add_arguments(self, parser):
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Filtrer par niveau CECR (A1, A2, B1, B2, C1, C2)",
        )
        parser.add_argument(
            "--exam_type",
            type=str,
            default=None,
            help="Filtrer par type d'examen (GOETHE, TELC, TESTDAF, DSH, GENERAL, INTEGRATION)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-générer l'audio même si un fichier existe déjà",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continuer en cas d'erreur TTS",
        )

    def handle(self, *args, **options):
        level = options["level"].upper() if options["level"] else None
        exam_type = options["exam_type"].upper() if options["exam_type"] else None
        force = options["force"]
        continue_on_error = options["continue_on_error"]

        qs = GermanLesson.objects.filter(skill="HOREN").select_related("exam")

        if level:
            qs = qs.filter(exam__level=level)
        if exam_type:
            qs = qs.filter(exam__exam_type=exam_type)

        if not force:
            qs = qs.filter(audio_url="")

        total = qs.count()
        self.stdout.write(
            f"🎙️ {total} leçon(s) HÖREN à traiter"
            + (" (force=True, re-génération)" if force else "")
        )

        done = 0
        failed = 0

        for lesson in qs:
            text = _extract_audio_text(lesson)

            if not text:
                self.stdout.write(
                    self.style.WARNING(f"  [{lesson.id}] Texte vide, ignoré.")
                )
                continue

            self.stdout.write(
                f"  [{lesson.id}] {lesson.exam.level}/{lesson.title[:50]}…", ending=" "
            )
            self.stdout.flush()

            try:
                rel_path = generate_audio(
                    text=text,
                    language="de",
                    output_dir=AUDIO_OUTPUT_DIR,
                )
                lesson.audio_url = rel_path
                lesson.save(update_fields=["audio_url"])
                done += 1
                self.stdout.write(self.style.SUCCESS(f"OK → {rel_path}"))

            except Exception as exc:
                failed += 1
                logger.warning(
                    "generate_german_audio: échec leçon %d — %s", lesson.id, exc
                )
                if continue_on_error:
                    self.stdout.write(self.style.WARNING(f"ERREUR : {exc}"))
                else:
                    self.stderr.write(f"ERREUR leçon {lesson.id} : {exc}")
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Audio terminé : {done} généré(s), {failed} échec(s)."
            )
        )
