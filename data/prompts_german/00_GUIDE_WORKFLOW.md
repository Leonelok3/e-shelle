# GUIDE COMPLET — Génération du contenu allemand via ChatGPT

## Audience cible
Africains francophones qui veulent immigrer en Allemagne.
- Visa regroupement familial → Goethe A1
- Titre de séjour permanent → B1
- Visa travail qualifié → B2/C1
- Test d'intégration → A2/B1

---

## STRUCTURE DES FICHIERS JSON

### Nom de fichier
```
data/lessons_json/de_A1_goethe.json   ← niveau A1, type Goethe
data/lessons_json/de_A2_goethe.json
data/lessons_json/de_B1_goethe.json
...
```

### Format JSON exact attendu
```json
[
  {
    "level": "A1",
    "skill": "GRAMMATIK",
    "exam_type": "GOETHE",
    "title": "Personalpronomen und das Verb sein",
    "intro": "Dans cette leçon, tu vas apprendre à te présenter en allemand avec le verbe être.",
    "content": "<h3>Die Personalpronomen</h3><p>En allemand, les pronoms personnels sont...</p><table><tr><th>Pronom</th><th>sein</th></tr><tr><td>ich</td><td>bin</td></tr></table>",
    "exercises": [
      {
        "question_text": "Wie heißt 'je suis' auf Deutsch?",
        "option_a": "ich bin",
        "option_b": "ich ist",
        "option_c": "ich sind",
        "option_d": "ich bist",
        "correct_option": "A",
        "explanation": "'Ich bin' est la forme correcte. 'Sein' se conjugue irrégulièrement : ich bin, du bist, er/sie/es ist."
      }
    ]
  }
]
```

### Valeurs autorisées
- **level** : "A1", "A2", "B1", "B2", "C1", "C2"
- **skill** : "GRAMMATIK", "WORTSCHATZ", "HOREN", "LESEN", "SPRECHEN", "SCHREIBEN"
- **exam_type** : "GOETHE", "TELC", "TESTDAF", "DSH", "GENERAL", "INTEGRATION"
- **correct_option** : "A", "B", "C" ou "D" (TOUJOURS majuscule)

---

## PLAN COMPLET A1 (25 leçons × 5 exercices = 125 exercices)

### GRAMMATIK — 7 leçons
| # | Titre | Batch |
|---|-------|-------|
| 1 | Das Alphabet und die Aussprache | Batch 1 |
| 2 | Personalpronomen und das Verb "sein" | Batch 1 |
| 3 | Das Verb "haben" und Possessivpronomen | Batch 1 |
| 4 | Nomen und bestimmte Artikel (der/die/das) | Batch 2 |
| 5 | Unbestimmte Artikel und Negation (kein/nicht) | Batch 2 |
| 6 | Regelmäßige Verben im Präsens | Batch 2 |
| 7 | Satzstellung — Verbe en 2e position | Batch 2 |

### WORTSCHATZ — 5 leçons
| # | Titre | Batch |
|---|-------|-------|
| 8 | Begrüßungen und Verabschiedungen | Batch 3 |
| 9 | Familie und persönliche Daten | Batch 3 |
| 10 | Zahlen, Uhrzeit und Datum | Batch 3 |
| 11 | Berufe und Nationalitäten | Batch 4 |
| 12 | Essen, Trinken und Einkaufen | Batch 4 |

### HÖREN — 4 leçons
| # | Titre | Batch |
|---|-------|-------|
| 13 | Sich vorstellen — Dialoge einfach | Batch 5 |
| 14 | Im Alltag — Kurze Dialoge | Batch 5 |
| 15 | Zahlen und Informationen hören | Batch 5 |
| 16 | Einfache Ansagen und Bekanntmachungen | Batch 5 |

### LESEN — 4 leçons
| # | Titre | Batch |
|---|-------|-------|
| 17 | Formulare und persönliche Daten lesen | Batch 6 |
| 18 | Schilder, Hinweise und kurze Texte | Batch 6 |
| 19 | Kurze Mitteilungen und SMS lesen | Batch 6 |
| 20 | Fahrpläne, Speisekarten und Adressen | Batch 6 |

### SPRECHEN — 3 leçons
| # | Titre | Batch |
|---|-------|-------|
| 21 | Sich vorstellen auf Deutsch | Batch 7 |
| 22 | Nach dem Weg fragen und beschreiben | Batch 7 |
| 23 | Im Geschäft und im Restaurant | Batch 7 |

### SCHREIBEN — 2 leçons
| # | Titre | Batch |
|---|-------|-------|
| 24 | Einfache Formulare ausfüllen | Batch 8 |
| 25 | Eine kurze Nachricht oder SMS schreiben | Batch 8 |

---

## WORKFLOW (étapes à suivre)

```
1. Ouvre le fichier de prompt correspondant au batch
2. Copie TOUT le prompt
3. Colle dans ChatGPT (GPT-4 ou GPT-4o recommandé)
4. Copie la réponse JSON complète
5. Crée le fichier : data/lessons_json/de_A1_goethe_batch1.json
6. Valide le JSON : python -X utf8 scripts/validate_german_json.py --file data/lessons_json/de_A1_goethe_batch1.json
7. Importe : python manage.py import_german_lessons --file data/lessons_json/de_A1_goethe_batch1.json --continue-on-error
8. Répète pour les batches 2→8
9. Une fois tous les batches importés : python manage.py flush_and_merge_german_a1.sh (optionnel)
```

---

## COMMANDES D'IMPORT

```bash
# Import d'un batch
python manage.py import_german_lessons --file data/lessons_json/de_A1_goethe_batch1.json --continue-on-error

# Flush + re-import complet niveau A1
python manage.py import_german_lessons --file data/lessons_json/de_A1_goethe_COMPLET.json --flush --level A1 --exam_type GOETHE

# Vérification en base
python manage.py shell -c "from GermanPrepApp.models import GermanLesson; print(GermanLesson.objects.filter(exam__level='A1').count(), 'leçons A1')"
```
