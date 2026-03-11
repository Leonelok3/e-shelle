"""
Corrige les guillemets typographiques allemands „..." non échappés dans un fichier JSON
généré par ChatGPT. Remplace les paires „...\" par «...».
"""
import json
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

filepath = sys.argv[1] if len(sys.argv) > 1 else "data/lessons_json/de_A1_batch1.json"

with open(filepath, encoding="utf-8") as f:
    raw = f.read()

# Remplacer les paires de guillemets allemands „...\" par «...»
# U+201E = „ (guillemet bas double ouvrant), fermé par ASCII "
fixed = re.sub(r'\u201e([^"\n]*?)"', r'«\1»', raw)

remaining = fixed.count('\u201e')
if remaining:
    print(f"Attention : {remaining} guillemet(s) „ non corrigé(s) restant(s)")

try:
    data = json.loads(fixed)
except json.JSONDecodeError as e:
    print(f"Toujours invalide : ligne {e.lineno}, col {e.colno}: {e.msg}")
    lines = fixed.split('\n')
    if e.lineno <= len(lines):
        line = lines[e.lineno - 1]
        print("Contexte :", repr(line[max(0, e.colno-80):e.colno+80]))
    sys.exit(1)

# Normaliser la structure des exercices si ChatGPT a utilisé un format alternatif
# Format attendu : question_text, option_a/b/c/d, correct_option, explanation
# Format alternatif : question, options:{A,B,C,D}, correct_option
converted = 0
for lesson in data:
    new_exercises = []
    for ex in lesson.get('exercises', []):
        if 'question' in ex and 'options' in ex and 'question_text' not in ex:
            opts = ex['options'] if isinstance(ex['options'], dict) else {}
            new_exercises.append({
                'question_text': ex.get('question', ''),
                'option_a': opts.get('A', ''),
                'option_b': opts.get('B', ''),
                'option_c': opts.get('C', ''),
                'option_d': opts.get('D', ''),
                'correct_option': ex.get('correct_option', 'A'),
                'explanation': ex.get('explanation', ex.get('correct_answer_explanation', ''))
            })
            converted += 1
        else:
            new_exercises.append(ex)
    lesson['exercises'] = new_exercises

if converted:
    print(f"Normalisation : {converted} exercice(s) converti(s) au format standard")

print(f"JSON valide — {len(data)} leçon(s)")
with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Fichier corrigé : {filepath}")
