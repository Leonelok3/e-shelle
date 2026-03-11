# PROMPT CHATGPT — A1 GRAMMATIK — Batch 2 (Leçons 4 à 7)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app web destinée à des **Africains francophones** qui préparent le **Goethe-Zertifikat A1** pour immigrer en Allemagne.

Génère exactement **4 leçons** de grammaire niveau A1 au format JSON strict.

## RÈGLES ABSOLUES
1. Réponse = **JSON valide uniquement** — rien avant, rien après
2. Tableau de 4 objets leçon
3. Chaque leçon a exactement **5 exercices QCM** (options A/B/C/D)
4. `content` en **HTML** (h3, p, ul/li, table, strong)
5. `intro` et `explanation` en **français**
6. Exemples bilingues dans `content` (allemand — français)
7. Prénoms africains dans les exemples (Mamadou, Fatou, Kofi, Amina, Ibrahima, Awa)
8. Situations liées à l'immigration, à l'administration, à la vie quotidienne en Allemagne
9. `correct_option` : lettre majuscule "A", "B", "C" ou "D"

## FORMAT JSON
```json
[
  {
    "level": "A1",
    "skill": "GRAMMATIK",
    "exam_type": "GOETHE",
    "title": "...",
    "intro": "... (français)",
    "content": "<h3>...</h3><p>...</p>...",
    "exercises": [
      {
        "question_text": "...",
        "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...",
        "correct_option": "A",
        "explanation": "... (français)"
      }
    ]
  }
]
```

## LEÇONS À GÉNÉRER

### Leçon 4 : Nomen und bestimmte Artikel — der, die, das (Les noms et l'article défini)
**Contenu :**
- Règle des 3 genres en allemand (masculin=der, féminin=die, neutre=das) — différent du français
- Quelques indices : -ung → die, -er/-ling → der, -chen/-lein → das
- Vocabulaire immigration : der Pass (passeport), die Karte (carte), das Visum (visa), die Botschaft (ambassade), das Formular (formulaire), der Termin (rendez-vous), die Adresse, das Land
- Pluriel : die (pour tous les genres au pluriel)
- Tableau avec 10 mots essentiels + leur article

**5 exercices :**
1. Article correct pour "Pass" (passeport)
2. Article correct pour "Botschaft" (ambassade)
3. Article correct pour "Formular" (formulaire)
4. Au pluriel, quel article utilise-t-on ?
5. Choisir le bon article pour "Aufenthaltserlaubnis"

---

### Leçon 5 : Unbestimmte Artikel und Negation — ein/eine, kein/keine, nicht
**Contenu :**
- Article indéfini : ein (masc./neutre), eine (féminin)
- Négation de l'article : kein/keine/kein (pas de...)
- Négation d'un verbe/adjectif : nicht (ne... pas)
- Règle de placement de "nicht" (en fin de phrase pour le verbe)
- Exemples : Ich habe ein Visum. — Ich habe kein Visum. / Ich bin nicht müde.

**5 exercices :**
1. "Je n'ai pas de passeport" → Ich habe ___ Pass
2. "Je ne suis pas allemand" → Ich bin ___ Deutsch
3. Article indéfini pour "Termin" (masculin)
4. "Elle n'a pas de rendez-vous" → Sie hat ___ Termin
5. Choisir entre "nicht" et "kein" dans la phrase correcte

---

### Leçon 6 : Regelmäßige Verben im Präsens (Verbes réguliers au présent)
**Contenu :**
- Terminaisons régulières : -e / -st / -t / -en / -t / -en
- Verbes essentiels pour l'immigration : wohnen (habiter), arbeiten (travailler), lernen (apprendre), kommen (venir), heißen (s'appeler), sprechen (parler — irrégulier : du sprichst / er spricht)
- Conjugaison complète de "wohnen" et "arbeiten"
- Exemples : Ich wohne in Berlin. Mamadou arbeitet als Elektriker. Wir lernen Deutsch.

**5 exercices :**
1. Conjuguer "wohnen" à la 2e personne singulier (du)
2. "Mamadou arbeite___ als Fahrer" — quelle terminaison ?
3. "Wir lern___ Deutsch für das Visum" — compléter
4. "Elle parle allemand" — traduction avec "sprechen" irrégulier
5. Conjuguer "kommen" à la 3e personne pluriel

---

### Leçon 7 : Satzstellung — L'ordre des mots dans la phrase allemande
**Contenu :**
- Règle fondamentale : le verbe est TOUJOURS en 2e position
- Structure basique : Sujet + Verbe + Reste
- Inversion sujet-verbe si la phrase commence par autre chose (adverbe, complément)
- Question avec W-Wort : Wo wohnen Sie? Was machen Sie? Woher kommen Sie? Wie heißen Sie?
- Question Oui/Non : Verbe en 1re position : Haben Sie ein Visum?
- Exemples pratiques : dialogues à la Botschaft (ambassade)

**5 exercices :**
1. Remettre dans le bon ordre : "Berlin / ich / in / wohne"
2. Quelle est la question correcte pour "Wo" ?
3. "Heute / Mamadou / zur Botschaft / geht" — bonne construction ?
4. Formuler "Avez-vous un rendez-vous ?" en question oui/non
5. "Woher kommen Sie?" — quelle est la bonne réponse pour quelqu'un du Sénégal ?

---

Génère maintenant le JSON. Commence directement par `[` et termine par `]`.
