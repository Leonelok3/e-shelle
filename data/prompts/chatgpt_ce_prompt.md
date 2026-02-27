# Prompt ChatGPT — Génération leçons CE (Compréhension Écrite)
# Immigration97 — Format JSON d'import direct

---

## INSTRUCTIONS POUR CHATGPT

Tu es un expert en didactique du FLE (Français Langue Étrangère) et en préparation aux examens TEF Canada et TCF.

Génère **50 leçons de Compréhension Écrite (CE)** de niveau **[NIVEAU]** selon le CECR.

---

## FORMAT JSON OBLIGATOIRE

Réponds UNIQUEMENT avec le JSON ci-dessous, sans texte avant ni après.
Respecte exactement les noms de champs. Le JSON doit être valide (pas de virgule finale).

```json
{
  "skill": "ce",
  "exam_id": [EXAM_ID],
  "level": "[NIVEAU]",
  "language": "fr",
  "lessons": [
    {
      "title": "Titre court de la leçon (max 60 caractères)",
      "reading_text": "<p>Texte de lecture HTML complet ici. Utilise des balises <p>, <strong>, <br> si nécessaire.</p>",
      "questions": [
        {
          "question_text": "Question portant sur le texte ?",
          "option_a": "Réponse A",
          "option_b": "Réponse B",
          "option_c": "Réponse C",
          "option_d": "Réponse D",
          "correct_option": "B",
          "summary": "Explication courte : pourquoi B est correct (1 phrase)."
        }
      ]
    }
  ]
}
```

---

## TABLEAU DES NIVEAUX ET EXAM_IDS

| Niveau | exam_id | Longueur texte | Nb questions | Types de documents |
|--------|---------|---------------|--------------|-------------------|
| A1     | 19      | 60-120 mots   | 4 questions  | Message, annonce simple, horaire, menu |
| A2     | 20      | 100-180 mots  | 5 questions  | Email, publicité, programme, notice courte |
| B1     | 21      | 180-280 mots  | 6 questions  | Article simple, offre d'emploi, lettre, blog |
| B2     | 22      | 280-400 mots  | 7 questions  | Article de presse, rapport, lettre formelle |
| C1     | 23      | 400-550 mots  | 8 questions  | Article spécialisé, éditorial, essai court |
| C2     | 24      | 500-700 mots  | 8 questions  | Texte littéraire, rapport académique, critique |

---

## RÈGLES DE QUALITÉ (OBLIGATOIRES)

### Pour le texte de lecture (reading_text)
- Contexte : immigration au Canada (Québec prioritairement), vie quotidienne, travail, logement, santé, services publics, culture québécoise
- Le texte doit être **autonome** : compréhensible sans contexte extérieur
- **Formater en HTML** : utilise `<p>` pour les paragraphes, `<strong>` pour les parties importantes, `<br>` pour les sauts de ligne dans les listes ou adresses
- Le texte doit ressembler à un **vrai document** du quotidien : email professionnel, annonce de colocation, article de journal local, publicité de commerce, programme de cours de français, lettre de la mairie, horaire d'une garderie, etc.

### Pour les questions
- Chaque question doit porter **directement sur le texte** (pas de culture générale)
- Types de questions à varier :
  1. **Idée principale** : "De quoi parle ce texte ?"
  2. **Détail précis** : prix, date, heure, lieu, nom
  3. **Vocabulaire en contexte** : "Que signifie X dans ce texte ?"
  4. **Inférence simple** : "Que peut-on déduire de... ?"
  5. **Vrai/Faux reformulé** : "Quelle affirmation est vraie ?"
- Les **mauvaises réponses** doivent être plausibles (pas clairement absurdes), basées sur des informations proches dans le texte ou des confusions courantes

### Diversité des types de documents (à alterner)
Pour A1/A2 : message personnel, annonce de colocation, publicité de supermarché, menu de restaurant, horaire de bus, programme d'activités, email entre collègues, affiche d'événement
Pour B1/B2 : article de blog, offre d'emploi, lettre de réclamation, communiqué de presse, reportage court, guide pratique
Pour C1/C2 : article de fond, éditorial, lettre ouverte, critique culturelle, extrait de rapport officiel

### Pour le summary (explication)
- 1 phrase explicative indiquant POURQUOI la réponse est correcte
- Référence au texte : "Le texte indique que..." ou "À la ligne 3, on lit..."

---

## EXEMPLES DE BONNE QUALITÉ

### Exemple A1
```json
{
  "title": "Annonce de colocation — Montréal",
  "reading_text": "<p>Bonjour ! Je cherche un(e) colocataire pour partager mon appartement au centre-ville de Montréal.</p><p>L'appartement est au 3e étage. Il y a 2 chambres, une cuisine et une salle de bain. Le loyer est de <strong>600 dollars par mois</strong>, charges comprises.</p><p>Je cherche quelqu'un de calme et de propre. Pas d'animaux, s'il vous plaît.</p><p>Contact : Marie — 514-555-0123</p>",
  "questions": [
    {
      "question_text": "Où se trouve l'appartement ?",
      "option_a": "En banlieue de Montréal",
      "option_b": "Au centre-ville de Montréal",
      "option_c": "À Québec",
      "option_d": "Dans un quartier résidentiel calme",
      "correct_option": "B",
      "summary": "Le texte indique clairement : 'au centre-ville de Montréal'."
    },
    {
      "question_text": "Quel est le prix du loyer par mois ?",
      "option_a": "400 dollars",
      "option_b": "500 dollars",
      "option_c": "600 dollars",
      "option_d": "800 dollars",
      "correct_option": "C",
      "summary": "Le texte précise : 'Le loyer est de 600 dollars par mois, charges comprises'."
    },
    {
      "question_text": "Qu'est-ce que Marie n'accepte pas dans son appartement ?",
      "option_a": "Les enfants",
      "option_b": "Les fumeurs",
      "option_c": "Les animaux",
      "option_d": "Les étudiants",
      "correct_option": "C",
      "summary": "Marie écrit explicitement : 'Pas d'animaux, s'il vous plaît'."
    },
    {
      "question_text": "Comment peut-on contacter Marie ?",
      "option_a": "Par email",
      "option_b": "Par courrier",
      "option_c": "En personne",
      "option_d": "Par téléphone",
      "correct_option": "D",
      "summary": "L'annonce donne un numéro de téléphone (514-555-0123), pas d'email ni d'adresse."
    }
  ]
}
```

---

## CE QU'IL NE FAUT PAS FAIRE

❌ Textes génériques sans rapport avec la vie au Canada
❌ Questions dont la réponse n'est pas dans le texte
❌ Mauvaises réponses clairement absurdes ("Le loyer est de 1 million de dollars")
❌ Toutes les bonnes réponses sur la même lettre (A, A, A, A...)
❌ Questions trop similaires entre elles
❌ Texte sans HTML (utilisez au minimum les balises `<p>`)
❌ "reading_text" vide ou trop court pour le niveau demandé

---

## COMMANDE POUR IMPORTER APRÈS GÉNÉRATION

Sur le serveur :
```bash
# Vider les anciennes leçons CE du niveau concerné
python manage.py flush_skill_lessons --skill ce --level A1

# Importer les nouvelles
python manage.py import_json_lessons --file data/lessons_json/ce_A1.json
```
