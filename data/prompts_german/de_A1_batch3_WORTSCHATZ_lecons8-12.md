# PROMPT CHATGPT — A1 WORTSCHATZ — Batch 3 (Leçons 8 à 12)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe A1** pour immigrer en Allemagne.

Génère exactement **5 leçons de vocabulaire (Wortschatz) niveau A1** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Exemples bilingues dans `content`
7. Prénoms africains dans les exemples (Mamadou, Fatou, Kofi, Amina, Ibrahima, Moussa, Aïssatou)
8. Situations pratiques liées à l'immigration en Allemagne
9. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"A1","skill":"WORTSCHATZ","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

## LEÇONS À GÉNÉRER

### Leçon 8 : Begrüßungen und Verabschiedungen (Saluer et dire au revoir)
**Vocabulaire à enseigner :**
- Formules formelles : Guten Morgen / Guten Tag / Guten Abend / Gute Nacht
- Formules informelles : Hallo / Hi / Tschüss / Bis später / Bis morgen
- Formules de politesse : Bitte / Danke / Bitte sehr / Vielen Dank / Entschuldigung / Es tut mir leid
- Dialogue typique : À la Ausländerbehörde (office des étrangers)
- Réponses à "Wie geht es Ihnen ?" → Gut, danke. / Es geht. / Nicht so gut.

**5 exercices basés sur des dialogues à l'ambassade ou à l'office des étrangers**

---

### Leçon 9 : Familie und persönliche Daten (La famille et les données personnelles)
**Vocabulaire à enseigner :**
- Famille : der Mann, die Frau, der Vater, die Mutter, der Sohn, die Tochter, der Bruder, die Schwester, die Großeltern, das Kind
- Formulaire visa : der Name, der Vorname, das Geburtsdatum, der Geburtsort, die Staatsangehörigkeit, die Adresse, die Telefonnummer, verheiratet/ledig/geschieden
- Phrases : Ich bin verheiratet. Ich habe zwei Kinder. Mein Mann heißt Ibrahima.
- Nationalités : Ich bin Senegalese/Senegalesierin. Ich komme aus Kamerun.

**5 exercices :**
1. Comment dit-on "épouse" (femme mariée) en allemand ?
2. Quel mot correspond à "date de naissance" sur un formulaire ?
3. "Je suis marié(e)" → traduction correcte
4. "Nationalité" sur un formulaire = ?
5. "J'ai 3 enfants" → traduction

---

### Leçon 10 : Zahlen, Uhrzeit und Datum (Chiffres, heure et date)
**Vocabulaire à enseigner :**
- Chiffres 0–100 (avec les irréguliers : eins, zwei, drei... zwanzig, dreißig, hundert)
- Nombres pour les dates : der erste, der zweite... (1., 2., 3...)
- Mois : Januar, Februar, März, April, Mai, Juni, Juli, August, September, Oktober, November, Dezember
- Jours : Montag bis Sonntag
- Heure : Es ist 9 Uhr. Um 10 Uhr 30. Viertel nach / vor. Halb.
- Formules : Mein Termin ist am Dienstag, den 15. März um 9 Uhr.

**5 exercices :**
1. Comment dit-on "14h30" en allemand ?
2. Quel mois suit "Oktober" ?
3. Comment écrire la date "15 mars" ?
4. "Mon rendez-vous est lundi à 10h" → traduction
5. Quel chiffre est "vierzig" ?

---

### Leçon 11 : Berufe und Nationalitäten (Métiers et nationalités)
**Vocabulaire à enseigner :**
- Métiers fréquents : der Arzt/die Ärztin, der Lehrer/die Lehrerin, der Elektriker, der Koch/die Köchin, der Fahrer, der Verkäufer, der Pfleger/die Pflegerin, der Handwerker, der Ingenieur, der Schüler/die Schülerin
- Nationalités africaines : Senegalese/Senegalesierin, Kameruner/Kamerunerin, Kongolese/Kongolesin, Ghanaer/Ghanaerin, Ivorer/Ivorerin
- Phrase : Ich bin Elektriker von Beruf. Was sind Sie von Beruf?
- Importance du métier pour le visa de travail

**5 exercices :**
1. Comment dit-on "infirmier/infirmière" ?
2. "Je suis chauffeur de métier" → traduction
3. Féminin de "Lehrer" ?
4. "Was sind Sie von Beruf?" → que veut dire cette question ?
5. Nationalité féminine pour quelqu'un du Sénégal

---

### Leçon 12 : Essen, Trinken und Einkaufen (Manger, boire et faire des courses)
**Vocabulaire à enseigner :**
- Aliments basiques : das Brot, die Milch, das Wasser, der Kaffee, der Tee, das Fleisch, das Gemüse, das Obst, der Reis, die Nudeln
- Au restaurant / supermarché : Ich möchte... / Was kostet das? / Wie viel kostet...? / Das macht... Euro.
- Quantités : ein Kilo, eine Flasche, ein Liter, eine Packung, ein Stück
- Dialogue typique : commande au restaurant, payer à la caisse

**5 exercices :**
1. "Je voudrais un café" → traduction avec "möchten"
2. Comment demander le prix ?
3. "Un kilo de riz" → traduction
4. Que signifie "Das macht 5 Euro" ?
5. "Das Fleisch" est de quel genre ?

---

Génère maintenant le JSON. Commence directement par `[` et termine par `]`.
