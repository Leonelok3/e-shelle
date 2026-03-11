"""
Corrige les guillemets ASCII non échappés à l'intérieur des strings JSON.
Utilisé quand ChatGPT place des "citations" directement dans des champs JSON.
"""
import re, json, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

filepath = sys.argv[1] if len(sys.argv) > 1 else "data/lessons_json/de_C1_batch4.json"

with open(filepath, encoding="utf-8") as f:
    raw = f.read()

# Fix 1: guillemets typographiques allemands „...`` → «...»
fixed = re.sub(r'\u201e([^"\n]*?)"', r'«\1»', raw)

# Fix 2: guillemets ASCII dans les balises HTML (<strong>"text"</strong>)
fixed = re.sub(r'(<(?:strong|em|b|i)>)"', r'\1«', fixed)
fixed = re.sub(r'"(</(?:strong|em|b|i)>)', r'»\1', fixed)

# Fix 3: state machine — échapper les guillemets internes dans les strings JSON
def escape_inner_quotes(text):
    result = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        # Caractère échappé
        if c == '\\' and in_string:
            result.append(c)
            i += 1
            if i < len(text):
                result.append(text[i])
                i += 1
            continue
        if c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                # Lookahead: prochain caractère non-espace
                j = i + 1
                while j < len(text) and text[j] in ' \t\n\r':
                    j += 1
                if j >= len(text) or text[j] in ',:]}':
                    # Fin légitime de la string
                    in_string = False
                    result.append(c)
                else:
                    # Guillemet interne — on l'échappe
                    result.append('\\')
                    result.append(c)
        else:
            result.append(c)
        i += 1
    return ''.join(result)

fixed = escape_inner_quotes(fixed)

try:
    data = json.loads(fixed)
    print(f"JSON valide — {len(data)} leçon(s)")
except json.JSONDecodeError as e:
    print(f"Toujours invalide : ligne {e.lineno}, col {e.colno}: {e.msg}")
    lines = fixed.split('\n')
    if e.lineno <= len(lines):
        print("Contexte :", repr(lines[e.lineno-1][max(0, e.colno-80):e.colno+80]))
    sys.exit(1)

# Normaliser la structure des exercices (format alternatif ChatGPT)
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

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Fichier corrigé : {filepath}")
