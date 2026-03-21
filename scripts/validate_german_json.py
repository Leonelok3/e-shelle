"""
Valide un fichier JSON généré par ChatGPT avant import dans GermanPrepApp.
Usage : python -X utf8 scripts/validate_german_json.py --file data/lessons_json/de_A1_batch1.json
"""
import json
import sys
import argparse

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

VALID_LEVELS   = {"A1", "A2", "B1", "B2", "C1", "C2"}
VALID_SKILLS   = {"GRAMMATIK", "WORTSCHATZ", "HOREN", "LESEN", "SPRECHEN", "SCHREIBEN"}
VALID_EXAMS    = {"GOETHE", "TELC", "TESTDAF", "DSH", "GENERAL", "INTEGRATION"}
VALID_CORRECT  = {"A", "B", "C", "D"}

def validate(filepath: str) -> bool:
    print(f"\n Validation de : {filepath}")
    print("=" * 60)

    try:
        with open(filepath, encoding="utf-8") as f:
            raw = f.read().strip()

        # Nettoyage si ChatGPT a ajouté ```json ... ```
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(
                l for l in lines
                if not l.strip().startswith("```")
            )

        data = json.loads(raw)
    except FileNotFoundError:
        print(f"  ERREUR : Fichier introuvable.")
        return False
    except json.JSONDecodeError as e:
        print(f"  ERREUR JSON : {e}")
        print("  Conseil : vérifie que ChatGPT n'a pas ajouté de texte avant/après le JSON.")
        return False

    if not isinstance(data, list):
        print("  ERREUR : Le JSON doit être un tableau [ ... ]")
        return False

    print(f"  {len(data)} leçon(s) trouvée(s)\n")

    errors = []
    warnings = []

    for idx, lesson in enumerate(data):
        prefix = f"  Leçon {idx+1}"

        # Champs obligatoires
        for field in ("level", "skill", "title", "content", "exercises"):
            if field not in lesson:
                errors.append(f"{prefix} : champ manquant '{field}'")

        level = str(lesson.get("level", "")).upper()
        skill = str(lesson.get("skill", "")).upper()
        exam  = str(lesson.get("exam_type", "GOETHE")).upper()
        title = lesson.get("title", "")

        if level not in VALID_LEVELS:
            errors.append(f"{prefix} '{title}' : level='{level}' invalide. Valides: {VALID_LEVELS}")
        if skill not in VALID_SKILLS:
            errors.append(f"{prefix} '{title}' : skill='{skill}' invalide. Valides: {VALID_SKILLS}")
        if exam not in VALID_EXAMS:
            errors.append(f"{prefix} '{title}' : exam_type='{exam}' invalide. Valides: {VALID_EXAMS}")

        exercises = lesson.get("exercises", [])
        if not isinstance(exercises, list):
            errors.append(f"{prefix} '{title}' : 'exercises' doit être une liste")
            continue

        if len(exercises) < 3:
            warnings.append(f"{prefix} '{title}' : seulement {len(exercises)} exercice(s) (recommandé: 5)")
        if len(exercises) == 0:
            errors.append(f"{prefix} '{title}' : aucun exercice !")

        for j, ex in enumerate(exercises):
            ex_prefix = f"{prefix} ex{j+1}"

            for field in ("question_text", "option_a", "option_b", "correct_option"):
                if field not in ex:
                    errors.append(f"{ex_prefix} : champ manquant '{field}'")

            correct = str(ex.get("correct_option", "")).upper()
            if correct not in VALID_CORRECT:
                errors.append(
                    f"{ex_prefix} : correct_option='{correct}' invalide. Doit être A/B/C/D"
                )

            if not ex.get("explanation"):
                warnings.append(f"{ex_prefix} : 'explanation' manquante (recommandé)")

        # Affiche un résumé de la leçon
        status = "OK" if not any(e.startswith(prefix) for e in errors) else "ERREUR"
        icon = "" if status == "OK" else ""
        print(f"  {icon} [{idx+1}] {level}/{skill} — {title} ({len(exercises)} ex.)")

    print()

    if warnings:
        print(f"  AVERTISSEMENTS ({len(warnings)}) :")
        for w in warnings:
            print(f"    {w}")
        print()

    if errors:
        print(f"  ERREURS CRITIQUES ({len(errors)}) :")
        for e in errors:
            print(f"    {e}")
        print()
        print("  RÉSULTAT : INVALIDE — Corrige le JSON avant d'importer.")
        return False

    print(f"  RÉSULTAT : VALIDE — {len(data)} leçon(s) prête(s) à importer.")
    print(f"\n  Commande d'import :")
    print(f"  python manage.py import_german_lessons --file {filepath} --continue-on-error")
    return True


def main():
    parser = argparse.ArgumentParser(description="Valide un JSON de leçons allemandes")
    parser.add_argument("--file", required=True, help="Chemin vers le fichier JSON")
    args = parser.parse_args()

    ok = validate(args.file)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
