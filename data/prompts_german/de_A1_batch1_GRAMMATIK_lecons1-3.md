# PROMPT CHATGPT — A1 GRAMMATIK — Batch 1 (Leçons 1 à 3)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu structuré pour une application web d'apprentissage de l'allemand destinée à des **Africains francophones** qui veulent **immigrer en Allemagne** (visa, regroupement familial, travail). Le niveau ciblé est **A1 — débutant absolu**.

Génère exactement **3 leçons** de grammaire allemande niveau A1, au format JSON strict.

## RÈGLES ABSOLUES
1. La réponse doit être **uniquement du JSON valide** — aucun texte avant ou après
2. Le tableau JSON contient exactement 3 objets
3. Chaque leçon a exactement **5 exercices QCM** (4 options A/B/C/D)
4. Le champ `content` est en **HTML simple** (h3, p, ul/li, table, strong, em)
5. `intro` et `explanation` sont en **français** (l'app est pour francophones)
6. Les phrases d'exemple dans `content` sont **bilingues** (allemand + traduction française)
7. `correct_option` est TOUJOURS une lettre majuscule : "A", "B", "C" ou "D"
8. Les exercices testent DIRECTEMENT ce qui est enseigné dans la leçon

## CONTEXTE IMMIGRATION (très important)
- Les utilisateurs sont des Africains francophones (Sénégal, Côte d'Ivoire, Cameroun, Mali, Congo, etc.)
- Objectif : passer le Goethe-Zertifikat A1 pour le visa de regroupement familial
- Les exemples doivent inclure des prénoms africains (Mamadou, Fatou, Kofi, Amina, etc.)
- Les situations doivent refléter l'immigration : ambassade, formulaire visa, se présenter à l'administration

## FORMAT JSON EXACT

```json
[
  {
    "level": "A1",
    "skill": "GRAMMATIK",
    "exam_type": "GOETHE",
    "title": "Titre de la leçon",
    "intro": "Phrase d'introduction en français expliquant ce que l'apprenant va apprendre.",
    "content": "<h3>Titre section</h3><p>Explication...</p>",
    "exercises": [
      {
        "question_text": "Question en allemand ou français",
        "option_a": "Option A",
        "option_b": "Option B",
        "option_c": "Option C",
        "option_d": "Option D",
        "correct_option": "A",
        "explanation": "Explication de la bonne réponse en français."
      }
    ]
  }
]
```

## LEÇONS À GÉNÉRER

### Leçon 1 : Das Alphabet und die Aussprache (L'alphabet et la prononciation)
**Contenu à couvrir :**
- Les 26 lettres + Ä Ö Ü ß
- La prononciation des lettres difficiles (W=V, V=F, Z=TS, J=Y, IE=î, EI=aï, EU=oi, CH, SCH, SP, ST)
- L'épellation dans un contexte administratif (nom, prénom, ville)
- Exercice : épeler son nom à l'ambassade allemande

**5 exercices sur :**
1. Comment se prononce "W" en allemand ?
2. Comment épelle-t-on "Visum" ?
3. Quelle est la prononciation du son "Z" en allemand ?
4. Comment se prononce "ie" dans "Wien" ?
5. Un dialogue : "Können Sie Ihren Namen buchstabieren?" — réponse correcte

---

### Leçon 2 : Personalpronomen und das Verb "sein" (Pronoms personnels et le verbe être)
**Contenu à couvrir :**
- Tableau complet : ich bin / du bist / er ist / sie ist / es ist / wir sind / ihr seid / sie sind / Sie sind
- Différence Sie (formel) vs du (informel) — crucial pour l'administration allemande
- Phrases de présentation : Ich bin Mamadou. Ich bin aus Senegal. Ich bin 32 Jahre alt.
- Négation avec "nicht" : Ich bin nicht müde.

**5 exercices sur :**
1. "Je suis étudiant" → quelle traduction ?
2. "Vous êtes Madame Koné ?" (formel) → forme correcte ?
3. Conjugaison de "sein" à la 3e personne (er/sie)
4. "Nous sommes de Côte d'Ivoire" → traduction
5. Choisir la bonne forme pour compléter : "Fatou ___ Lehrerin."

---

### Leçon 3 : Das Verb "haben" und Possessivpronomen (Avoir + pronoms possessifs)
**Contenu à couvrir :**
- Conjugaison complète : ich habe / du hast / er hat / sie hat / wir haben / ihr habt / sie haben
- Possessifs : mein/meine, dein/deine, sein/seine, ihr/ihre, unser/unsere
- Accord avec der/die/das : mein Pass (masc.) / meine Karte (fém.) / mein Visum (neutre)
- Phrases pratiques : Ich habe einen Pass. Hast du ein Visum? Er hat eine Aufenthaltserlaubnis.

**5 exercices sur :**
1. "J'ai un passeport" → traduction correcte
2. Compléter : "Das ist ___ Pass." (son passeport à lui)
3. "Avez-vous un visa ?" (formel) → bonne formulation
4. Conjugaison de "haben" à "wir"
5. "Ma carte de séjour" → mein/meine/meinen ?

---

Génère maintenant le JSON complet. Commence directement par `[` et termine par `]`. Aucun texte autour.
