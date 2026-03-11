# PROMPT CHATGPT — C1 GRAMMATIK — Batch 1 (Leçons 1 à 5)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe C1** pour s'intégrer professionnellement en Allemagne.

Génère exactement **5 leçons de grammaire niveau C1** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon (options A/B/C/D)
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Grammaire C1 : structures complexes, style académique et journalistique, registre très soutenu
7. Exemples authentiques tirés de la presse allemande, textes académiques, documents officiels
8. Prénoms africains dans les exemples
9. Situations : vie universitaire, milieu professionnel avancé, textes complexes en Allemagne
10. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"C1","skill":"GRAMMATIK","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

---

### Leçon 1 : Modalpartikeln — Les particules modales (C1)
**Contenu :**
Les particules modales (Modalpartikeln) sont intraduisibles mot à mot mais essentielles au niveau C1 pour comprendre les nuances de l'oral et de l'écrit :
- **ja** : évidence partagée — "Das ist ja bekannt." (C'est bien connu, n'est-ce pas ?)
- **doch** : contradiction douce / rappel — "Das stimmt doch nicht." / "Komm doch mit!"
- **halt/eben** : résignation, fatalité — "Das ist halt so." / "Eben deshalb..." (c'est justement pour ça)
- **wohl** : probabilité / estimation — "Er ist wohl krank." (Il est probablement malade.)
- **eigentlich** : en réalité, à proprement parler — "Eigentlich wollte ich früher kommen."
- **mal** : atténuation d'une demande — "Kannst du mal kurz helfen?"
- **schon** : nuance de certitude ou concession — "Das wird schon klappen." / "Schon, aber..."
Dialogue modèle : Amina explique à son chef que son rapport est "eigentlich" prêt mais qu'elle voulait "noch mal" vérifier.

**5 exercices :**
1. "Das ist ja interessant" — que signifie "ja" ici ?
2. "Das stimmt doch" — quelle nuance exprime "doch" ?
3. "Das ist halt so" — quelle attitude exprime cette phrase ?
4. "Er ist wohl noch im Büro" — que signifie "wohl" dans ce contexte ?
5. "Kannst du mal kurz kommen?" — pourquoi utilise-t-on "mal" ici ?

---

### Leçon 2 : Erweiterte Infinitivkonstruktionen — Constructions infinitives avancées (C1)
**Contenu :**
Maîtrise avancée des constructions infinitives au niveau C1 :
- **um...zu + Infinitif** : but — "Ibrahima reiste nach Berlin, um eine Stelle zu finden."
- **ohne...zu + Infinitif** : sans que — "Er arbeitete, ohne eine Pause zu machen."
- **anstatt/statt...zu + Infinitif** : au lieu de — "Statt zu klagen, handelte er."
- **(an)statt dass** (subordonnée) vs. **(an)statt...zu** (même sujet)
- **scheinen + zu + Infinitif** : sembler — "Die Lage scheint sich zu verbessern."
- **drohen + zu + Infinitif** : menacer de / risquer de — "Das Projekt droht zu scheitern."
- **pflegen + zu + Infinitif** : avoir coutume de — "Er pflegte früh aufzustehen." (style soutenu)
Exemples issus de la presse : "Die Regierung droht, die Verhandlungen abzubrechen."

**5 exercices :**
1. "Er ging, ohne sich zu verabschieden" — quelle construction utilise-t-on ?
2. "Statt zu schlafen, arbeitete Kofi bis Mitternacht" — même sujet ou sujets différents ?
3. "Das Unternehmen scheint in Schwierigkeiten zu sein" — que signifie "scheinen + zu" ?
4. "Die Wirtschaft droht einzubrechen" — quelle nuance exprime "drohen + zu" ?
5. Quelle est la différence entre "statt...zu" et "statt dass" ?

---

### Leçon 3 : Genitivkonstruktionen und Genitivattribute — Style journalistique et académique (C1)
**Contenu :**
Le génitif est omniprésent dans le style soutenu, journalistique et académique :
- **Genitivattribut** (attribut génitif) : "die Entscheidung des Bundesverfassungsgerichts"
- **Doppelter Genitiv** : "Fatous Bericht des Jahres" → éviter (employer "von")
- **Genitivpräpositionen C1** : aufgrund (+ Génitif), trotz, wegen, infolge, anlässlich, hinsichtlich, angesichts, ungeachtet, kraft (+ Génitif), zwecks (très formel)
- **Genitiv vs. von + Datif** : style formel préfère le génitif
- Exemples journalistiques : "Angesichts der steigenden Arbeitslosigkeit..." / "Aufgrund des neuen Gesetzes..." / "Infolge der Pandemie..."
- Structures nominales denses typiques de la presse : "die im Koalitionsvertrag vorgesehene Reform der Rentenversicherung"

**5 exercices :**
1. "Aufgrund" régit quel cas grammatical ?
2. Traduire : "En raison de la nouvelle loi" → construction avec génitif ?
3. "Angesichts der Krise" — quelle préposition de génitif utilise-t-on ici ?
4. "Ungeachtet der Kritik" signifie → ?
5. Quel est l'équivalent génitif de "wegen" dans un registre très formel ?

---

### Leçon 4 : Komplexe Konnektoren C1 — Connecteurs complexes de niveau C1
**Contenu :**
Les connecteurs avancés C1 pour structurer un texte académique ou journalistique :
- **zumal** (d'autant plus que) : "Das ist schwierig, zumal die Zeit knapp ist."
- **geschweige denn** (encore moins / sans parler de) : "Er spricht kaum Deutsch, geschweige denn Englisch."
- **insofern (als)** (dans la mesure où) : "Das ist problematisch, insofern als..."
- **sofern** (à condition que / pour autant que) : "Sofern keine Einwände bestehen, gilt..."
- **indem** (en + gérondif / en faisant) : "Er verbesserte sein Deutsch, indem er täglich las."
- **wobei** (alors que / tout en) : "Er arbeitete, wobei er Musik hörte."
- **soweit** (pour autant que / dans la mesure où) : "Soweit ich informiert bin..."
- **wenngleich** (bien que — très soutenu) : "Wenngleich die Ergebnisse positiv sind..."

**5 exercices :**
1. "Er hat kein Deutsch, geschweige denn Fachkenntnisse" — que signifie "geschweige denn" ?
2. "Zumal" introduit quelle nuance ?
3. "Indem er regelmäßig übte, verbesserte er sein Deutsch" — que signifie "indem" ?
4. "Sofern Sie einverstanden sind" équivaut à quelle expression française ?
5. Quelle est la différence entre "insofern" et "sofern" ?

---

### Leçon 5 : Passivkonstruktionen erweitert — Constructions passives avancées (C1)
**Contenu :**
Maîtrise complète du passif au niveau C1 :
- **Vorgangspassiv** (passif d'action) : "Das Gesetz wird verabschiedet."
- **Zustandspassiv** (passif d'état) : "Das Gesetz ist verabschiedet." (résultat accompli)
- **Passiversatz** (substituts du passif) :
  - **sein + zu + Infinitif** (obligation/possibilité) : "Das Formular ist auszufüllen." = "Das Formular muss ausgefüllt werden."
  - **sich lassen + Infinitif** (possibilité) : "Das Problem lässt sich lösen." = "Das Problem kann gelöst werden."
  - **man + Aktiv** (on peut) : "Man kann das Problem lösen."
- **Passif avec Modalverb** : "Das muss sofort geprüft werden."
- **Passif du verbe sich** : rare mais existant dans certains textes officiels
Exemples officiels : "Die Unterlagen sind innerhalb von 4 Wochen einzureichen." / "Der Bescheid lässt sich anfechten."

**5 exercices :**
1. "Das Formular ist auszufüllen" — quelle obligation exprime cette structure ?
2. Différence entre Vorgangspassiv et Zustandspassiv avec "öffnen" ?
3. "Das lässt sich nicht ändern" — transformer en passif avec "können" ?
4. "Die Entscheidung muss überdacht werden" — quel temps de passif est-ce ?
5. Transformer : "Man muss das Visum beantragen" → passif avec "sein + zu" ?

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
