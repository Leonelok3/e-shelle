"""Fix de_C2_batch3.json — newline literal inside JSON string"""
import re, json, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

filepath = "data/lessons_json/de_C2_batch3.json"

with open(filepath, encoding="utf-8") as f:
    raw = f.read()

print(f"Nb lignes: {raw.count(chr(10))}")

# Fix 1: guillemets typographiques
fixed = re.sub('\u201e([^"\n]*?)"', r'«\1»', raw)
# Fix 2: guillemets HTML
fixed = re.sub(r'(<(?:strong|em|b|i)>)"', r'\1«', fixed)
fixed = re.sub(r'"(</(?:strong|em|b|i)>)', r'»\1', fixed)

# Fix 3: newlines literaux DANS les strings JSON
# Remplace les \n qui sont a l'interieur d'une string JSON par un espace
def fix_newlines_in_strings(text):
    result = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
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
                # Lookahead
                j = i + 1
                while j < len(text) and text[j] in ' \t\r\n':
                    j += 1
                if j >= len(text) or text[j] in ',:]}':
                    in_string = False
                    result.append(c)
                else:
                    # Guillemet interne — echapper
                    result.append('\\')
                    result.append(c)
        elif c == '\n' and in_string:
            # Newline dans une string: remplacer par espace
            result.append(' ')
        elif c == '\r' and in_string:
            pass  # Supprimer
        else:
            result.append(c)
        i += 1
    return ''.join(result)

fixed = fix_newlines_in_strings(fixed)

try:
    data = json.loads(fixed)
    print(f"JSON valide — {len(data)} leçons")
except json.JSONDecodeError as e:
    print(f"Invalide : ligne {e.lineno}, col {e.colno}: {e.msg}")
    lines = fixed.split('\n')
    if e.lineno <= len(lines):
        print("Contexte :", repr(lines[e.lineno-1][max(0, e.colno-80):e.colno+80]))
    sys.exit(1)

# Normaliser exercices
converted = 0
for lesson in data:
    new_ex = []
    for ex in lesson.get('exercises', []):
        if 'question' in ex and 'options' in ex and 'question_text' not in ex:
            opts = ex['options'] if isinstance(ex['options'], dict) else {}
            new_ex.append({
                'question_text': ex.get('question', ''),
                'option_a': opts.get('A', ''),
                'option_b': opts.get('B', ''),
                'option_c': opts.get('C', ''),
                'option_d': opts.get('D', ''),
                'correct_option': ex.get('correct_option', 'A'),
                'explanation': ex.get('explanation', '')
            })
            converted += 1
        else:
            new_ex.append(ex)
    lesson['exercises'] = new_ex

if converted:
    print(f"Normalisation : {converted} exercice(s)")

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Fichier corrigé : {filepath}")
