# PROMPT CHATGPT — C2 GRAMMATIK — Batch 1 (Leçons 1 à 5)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe C2** pour atteindre un niveau quasi natif en allemand professionnel et académique.

Génère exactement **5 leçons de grammaire niveau C2** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon (options A/B/C/D)
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Grammaire C2 : maîtrise quasi native, stylistique avancée, histoire de la langue, subtilités rhétoriques
7. Exemples issus de textes authentiques (Bundesverfassungsgericht, Goethe, Habermas, Die Zeit)
8. Prénoms africains dans les exemples
9. Niveau : enseignement supérieur avancé, textes constitutionnels, littérature classique et contemporaine
10. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"C2","skill":"GRAMMATIK","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

---

### Leçon 1 : Stilistik — Stilmittel und rhetorische Figuren (C2)
**Contenu :**
Maîtrise des figures de style et procédés rhétoriques de la langue allemande au niveau C2 :
- **Chiasmus** : "Man soll essen, um zu leben, nicht leben, um zu essen."
- **Anapher** : répétition en début de phrase — "Wir fordern Gerechtigkeit. Wir fordern Teilhabe. Wir fordern Würde."
- **Litotes** : atténuation par la négation du contraire — "Das ist nicht uninteressant."
- **Euphémismus** : "entlassen" au lieu de "feuern", "Kollateralschäden" pour les victimes civiles
- **Hyperbel** : exagération stylistique — "Das haben wir tausendmal besprochen."
- **Ironie** / **Sarkasmus** : nuance entre l'ironie douce et le sarcasme acide
- **Ellipse** : suppression d'éléments grammaticaux pour l'effet — "Je eher, desto besser."
- Identifier ces figures dans des textes politiques, littéraires, journalistiques
Modèle : Amina analyse un discours du Bundestag et identifie les procédés rhétoriques utilisés.

**5 exercices :**
1. "Das ist nicht uninteressant" — quel procédé stylistique est utilisé ?
2. "Wir kämpfen für Freiheit. Wir kämpfen für Gleichheit." — quelle figure de style ?
3. Quelle est la nuance entre ironie et sarkasme en allemand ?
4. "Je eher, desto besser" est un exemple de → ?
5. Dans un texte officiel, quel euphémisme remplace souvent "Entlassung" (licenciement massif) ?

---

### Leçon 2 : Syntaktische Variation — Variantes syntaxiques avancées (C2)
**Contenu :**
Au niveau C2, la maîtrise de la syntaxe implique de varier les structures pour créer des effets stylistiques :
- **Ausklammerung** (extraposition) : placer un élément hors du cadre verbal pour le mettre en relief — "Er hat das Problem gelöst, trotz aller Widerstände."
- **Herausstellung** (dislocation) : "Der Bericht, den habe ich gelesen." (familier → rare à l'écrit formel)
- **Topikalisierung** (topicalisation) : mettre en première position ce qui est thématiquement important — "Dieses Problem hat die Kommission bereits 2019 erkannt."
- **Parenthesen** (parenthèses incises) : "Der Minister — und das ist neu — hat gestern zugegeben, dass..."
- **Hypotaxe vs. Parataxe** : Cicéron vs. César — style périodique vs. style court (effet stylistique)
- Exemples issus de Die Zeit, FAZ, Bundesgerichtshofurteile
Modèle : Kofi analyse le style syntaxique de Habermas vs. celui d'un article de la BILD.

**5 exercices :**
1. "Dieses Problem hat die Regierung erkannt" vs. "Die Regierung hat dieses Problem erkannt" — quelle différence stylistique ?
2. "Ausklammerung" consiste à → ?
3. Dans quel style préfère-t-on la parataxe (phrases courtes) et pourquoi ?
4. "Der Minister — und das ist bemerkenswert — hat zugegeben, dass..." — quel procédé syntaxique est utilisé ?
5. Qu'est-ce que la "Topikalisierung" et quel effet produit-elle ?

---

### Leçon 3 : Historische Grammatik — Archaïsmes et évolution de l'allemand (C2)
**Contenu :**
Compréhension des structures grammaticales archaïques présentes dans les textes classiques et juridiques :
- **Genitiv verbal archaïque** : "Ich bin des Lebens müde." / "Er bedarf der Hilfe." (verbes à génitif)
- **Konjunktiv I archaïque** : "Es lebe die Freiheit!" / "Gott sei Dank!" / "Sei dem wie es wolle..."
- **Ancien ordre des mots** : dans les textes du XVIIIe-XIXe siècle (Goethe, Schiller)
- **Präteritum als Erzähltempus** : l'usage du prétérit comme temps narratif en allemand (vs. passé composé en français)
- **Genitivus subjectivus / objectivus** : "die Liebe des Vaters" (le père aime ou on aime le père ?)
- **Textes modèles** : extraits de la Constitution allemande (Grundgesetz), Goethe (Faust), Hegel
Modèle : Ibrahima lit un arrêt du Bundesverfassungsgericht de 1958 et doit en comprendre les structures grammaticales.

**5 exercices :**
1. "Ich bin des Lebens müde" — quel cas régit le verbe "müde sein" dans ce contexte archaïque ?
2. "Es lebe die Demokratie!" — quel mode et quel usage représente cette phrase ?
3. "Die Liebe des Vaters" — est-ce un génitif subjectif ou objectif ? Comment le déterminer ?
4. "Sei dem wie es wolle" — que signifie cette expression archaïque ?
5. Pourquoi l'allemand préfère-t-il le Präteritum dans les textes littéraires narratifs ?

---

### Leçon 4 : Präzision und Ambiguität — Précision du langage et ambiguïté sémantique (C2)
**Contenu :**
Au niveau C2, maîtriser les subtilités sémantiques qui distinguent le locuteur natif cultivé :
- **Synonymes à nuances fines** : fragen / befragen / verhören / erkundigen / beantragen (gradation de formalité et de contrainte)
- **Faux amis internes** (mots allemands à double sens) : "der Bescheid" (décision administrative ET connaissance populaire "Bescheid wissen")
- **Ambiguïté référentielle** : "Er sah den Mann mit dem Fernglas" (qui porte le télescope ?)
- **Polysémie avancée** : "die Bank" (banque financière / banc), "der Strauß" (bouquet / autruche / nom propre), "der Hahn" (coq / robinet)
- **Lexikalische Lücken** : mots allemands intraduisibles — Schadenfreude, Weltanschauung, Fingerspitzengefühl, Verschlimmbessern
- **Registervariation** : un même concept exprimé différemment selon le registre (oral spontané → soutenu → juridique → académique)
Modèle : Fatou, traductrice juridique, doit choisir précisément entre "beantragen", "anfragen" et "ersuchen" dans un document officiel.

**5 exercices :**
1. Quelle différence précise entre "befragen" et "verhören" ?
2. "Er sah den Mann mit dem Fernglas" — pourquoi cette phrase est-elle ambiguë ?
3. "Schadenfreude" — pourquoi ce mot allemand est-il adopté en anglais ?
4. "Verschlimmbessern" décrit quelle situation ironique ?
5. Dans un document officiel, "beantragen", "anfragen" ou "ersuchen" — lequel est le plus formel ?

---

### Leçon 5 : Idiomatik und Phraseologie — Expressions idiomatiques et phrases figées (C2)
**Contenu :**
Maîtrise des expressions idiomatiques (Redewendungen) et phrases figées (Phraseologismen) au niveau C2 :
- **Idiomes courants mais mal connus** : "jemandem auf den Zahn fühlen" (sonder qqn), "etwas auf die lange Bank schieben" (remettre à plus tard), "den Nagel auf den Kopf treffen" (mettre le doigt dessus)
- **Idiomes professionnels** : "die Fäden in der Hand halten" (tenir les rênes), "auf dem Laufenden bleiben" (rester informé), "den Ball flach halten" (ne pas s'emballer)
- **Idiomes politiques et journalistiques** : "das Ruder herumreißen" (renverser la tendance), "Öl ins Feuer gießen" (jeter de l'huile sur le feu), "auf der Hut sein" (être sur ses gardes)
- **Proverbes** : "Übung macht den Meister" / "Aller Anfang ist schwer" / "Morgenstund hat Gold im Mund"
- **Collocations avancées** : einen Antrag stellen (PAS machen) / eine Entscheidung treffen (PAS tun) / ein Gespräch führen (PAS haben)
Modèle : Ibrahima doit comprendre les expressions idiomatiques utilisées par ses collègues allemands lors d'une réunion de direction.

**5 exercices :**
1. "Etwas auf die lange Bank schieben" signifie → ?
2. "Den Nagel auf den Kopf treffen" équivaut à quelle expression française ?
3. "Die Fäden in der Hand halten" — dans quel contexte professionnel utilise-t-on cet idiome ?
4. "Öl ins Feuer gießen" — quelle collocation correcte pour "prendre une décision" ?
5. Quelle est la différence de sens entre "Übung macht den Meister" et "Aller Anfang ist schwer" ?

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
