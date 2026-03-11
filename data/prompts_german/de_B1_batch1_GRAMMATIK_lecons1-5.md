# PROMPT CHATGPT — B1 GRAMMATIK — Batch 1 (Leçons 1 à 5)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe B1** pour obtenir leur titre de séjour permanent en Allemagne.

Génère exactement **5 leçons de grammaire niveau B1** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon (options A/B/C/D)
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Exemples bilingues (allemand — français)
7. Prénoms africains dans les exemples
8. Situations : vie professionnelle, administrative, sociale en Allemagne
9. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"B1","skill":"GRAMMATIK","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

---

### Leçon 1 : Relativsätze — Les propositions relatives
**Contenu :**
- Pronom relatif selon le genre et le cas : der/die/das/die (nominatif), den/die/das/die (accusatif), dem/der/dem/denen (datif)
- Structure : nom + pronom relatif + ... + verbe conjugué en fin
- Exemples : Das ist der Mann, der mir geholfen hat. / Ich suche eine Wohnung, die günstig ist. / Das ist das Formular, das ich ausfüllen muss.
- Cas particulier avec préposition : Das ist der Kollege, mit dem ich arbeite.
- Utilité B1 : décrire des personnes, objets, situations en détail

**5 exercices :**
1. "Das ist die Frau, ___ mir den Weg gezeigt hat." → pronom relatif correct
2. "Ich habe den Brief, ___ du geschrieben hast." → accusatif masculin
3. "Das ist der Kollege, mit ___ ich jeden Tag arbeite." → datif masculin
4. "Die Kinder, ___ hier spielen, kommen aus Senegal." → nominatif pluriel
5. Construire une relative : "Das ist das Amt. Ich habe dort meinen Antrag gestellt." → avec wo ou das

---

### Leçon 2 : Konjunktiv II — Le subjonctif 2 (politesse et hypothèses)
**Contenu :**
- Formation : würde + Infinitif (forme courante) / formes synthétiques : wäre, hätte, könnte, müsste, dürfte, sollte
- Usages principaux :
  1. Politesse : Könnten Sie mir helfen? / Ich hätte gern... / Würden Sie bitte...?
  2. Hypothèse irréelle : Wenn ich mehr Geld hätte, würde ich eine größere Wohnung mieten.
  3. Conseil : An deiner Stelle würde ich sofort einen Anwalt anrufen.
- Exemples pratiques : demandes polies à l'administration, hypothèses sur le visa

**5 exercices :**
1. Forme polie de "Helfen Sie mir" → avec Konjunktiv II
2. "Wenn ich Zeit ___, würde ich mehr lernen." → hätte ou wäre ?
3. "An deiner Stelle ___ ich das nicht machen." → würde ou wäre ?
4. Forme Konjunktiv II de "können" à la 1ère personne singulier
5. Laquelle est une demande polie correcte ?

---

### Leçon 3 : Passiv — La voix passive
**Contenu :**
- Formation Passiv Präsens : werden + Partizip II
  Das Formular wird ausgefüllt. / Der Antrag wird bearbeitet.
- Formation Passiv Präteritum : wurde + Partizip II
  Der Antrag wurde abgelehnt. / Das Visum wurde verlängert.
- Agent avec "von" : Das Dokument wurde vom Sachbearbeiter geprüft.
- Passif dans les textes administratifs et officiels (très fréquent en allemand)
- Exemples : Ihr Antrag wird geprüft. / Sie werden informiert. / Der Termin wurde verschoben.

**5 exercices :**
1. Transformer en passif : "Der Beamte prüft den Antrag."
2. "Das Visum ___ letzte Woche verlängert." → Passiv Präteritum → wurde ou wird ?
3. "Sie ___ gebeten, die Dokumente mitzubringen." → werden ou werden
4. Comment dire "La décision a été prise" au passif Präteritum ?
5. Quel élément manque dans : "Der Brief ___ vom Chef unterschrieben."

---

### Leçon 4 : Infinitivkonstruktionen mit zu — Les constructions infinitives avec zu
**Contenu :**
- Structure : es ist + adjektif + zu + infinitif : Es ist wichtig, pünktlich zu sein.
- Après certains verbes : versuchen, vergessen, anfangen, aufhören, hoffen, empfehlen, bitten, erlauben
  Ich versuche, jeden Tag Deutsch zu lernen.
  Er hat vergessen, den Pass mitzunehmen.
- Avec um...zu (but) : Ich lerne Deutsch, um in Deutschland zu arbeiten.
- Avec ohne...zu et anstatt...zu
- Verbes à particule : Partizip mit zu zwischen particule et radical : aufzufüllen, mitzunehmen

**5 exercices :**
1. "Ich versuche ___ pünktlich zu sein." → virgule ou pas ?
2. "Er ist nach Deutschland gekommen, ___ arbeiten." → um...zu ou damit ?
3. Infinitif avec zu de "mitnehmen" →  ?
4. "Es ist wichtig, alle Dokumente ___." → mitbringen avec zu
5. "Anstatt ___ warten, hat er einen Termin genommen." → zu + infinitif correct

---

### Leçon 5 : Zweiteilige Konnektoren — Les connecteurs doubles
**Contenu :**
- sowohl...als auch (et...et / aussi bien...que) : Er spricht sowohl Deutsch als auch Französisch.
- entweder...oder (soit...soit) : Entweder nimmst du den Bus oder du gehst zu Fuß.
- weder...noch (ni...ni) : Er hat weder Zeit noch Geld.
- nicht nur...sondern auch (non seulement...mais aussi) : Sie ist nicht nur klug, sondern auch fleißig.
- zwar...aber (certes...mais) : Das ist zwar schwierig, aber möglich.
- Ordre des mots selon la position du connecteur
- Exemples : situations professionnelles et administratives

**5 exercices :**
1. "Er spricht ___ Deutsch ___ Englisch." → sowohl...als auch
2. "___ kommt er heute, ___ kommt er morgen." → entweder...oder
3. "Sie hat ___ Zeit ___ Lust." → weder...noch
4. "Das ist ___ teuer, ___ qualitativ hochwertig." → zwar...aber
5. Choisir le connecteur correct pour : "Il ne travaille pas seulement en Allemagne, mais aussi en Autriche."

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
