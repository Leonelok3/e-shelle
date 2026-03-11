# PROMPT CHATGPT — B1 GRAMMATIK — Batch 2 (Leçons 6 à 10)
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

### Leçon 6 : Genitivkasus — Le génitif (possession et style soutenu)
**Contenu :**
- Formation : des/eines (masc./neutre) + -s/-es au nom | der/einer (fém.) | der/- (pluriel)
- Génitif de possession : das Büro des Chefs, die Meinung der Mitarbeiterin, der Antrag des Kunden
- Prépositions avec génitif : wegen (à cause de), trotz (malgré), während (pendant), aufgrund (en raison de), innerhalb (à l'intérieur de), außerhalb (en dehors de)
- wegen + Génitif : Wegen des schlechten Wetters... / Wegen meiner Arbeit...
- Usage courant dans les textes officiels et administratifs

**5 exercices :**
1. "Das Büro ___ Chef" → article génitif masculin
2. "Wegen ___ Regen" → masculin génitif → des ou dem ?
3. "Trotz ___ Schwierigkeiten" → pluriel génitif → der ou die ?
4. "Das ist das Auto ___ Mitarbeiterin." → féminin génitif
5. Laquelle utilise correctement le génitif dans une phrase formelle ?

---

### Leçon 7 : Temporale Konnektoren — Les connecteurs temporels
**Contenu :**
- als (quand, une fois — passé) : Als Mamadou in Deutschland ankam, war er sehr nervös.
- wenn (quand, chaque fois — présent/futur/répétition) : Wenn ich Zeit habe, lerne ich Deutsch.
- bevor (avant que) : Bevor du gehst, füll das Formular aus.
- nachdem (après que) + Plusquamperfekt : Nachdem er den Antrag eingereicht hatte, wartete er.
- während (pendant que) : Während er wartete, las er ein Buch.
- seitdem (depuis que) : Seitdem er in Deutschland ist, spricht er jeden Tag Deutsch.
- solange (tant que) : Solange du hier lebst, musst du die Regeln einhalten.

**5 exercices :**
1. "Als" ou "wenn" pour une action passée unique ?
2. "___ er den Brief erhalten hatte, rief er sofort an." → Nachdem ou Bevor ?
3. "___ ich in Deutschland wohne, habe ich viel gelernt." → Seitdem ou Während ?
4. "Bevor" exige-t-il un temps particulier dans la subordonnée ?
5. Relier : "Er hat den Antrag gestellt. Danach hat er gewartet." → avec nachdem

---

### Leçon 8 : Konzessive und kausale Konnektoren — Cause, concession, conséquence
**Contenu :**
- Cause : weil (subord.) / denn (coord., même ordre) / da (subord., début de phrase souvent)
  Ich lerne Deutsch, weil ich in Deutschland bleiben möchte.
  Er geht zum Arzt, denn er ist krank.
- Concession : obwohl (bien que) + verbe en fin
  Obwohl er müde war, hat er weitergearbeitet.
- Conséquence : deshalb / daher / deswegen (c'est pourquoi) — position variable
  Er hat keine Aufenthaltserlaubnis, deshalb muss er das Land verlassen.
- also (donc, dans le sens logique)
- trotzdem (quand même, malgré tout)

**5 exercices :**
1. "Er war krank, ___ er nicht zur Arbeit gegangen ist." → deshalb ou obwohl ?
2. Différence entre "weil" et "denn" dans la structure de phrase ?
3. "___ er kein Visum hatte, konnte er nicht einreisen." → Obwohl ou Da ?
4. "Er hat den Test nicht bestanden, ___ hat er es noch mal versucht." → trotzdem ou deshalb
5. Construire avec obwohl : "Er hat wenig Geld. Er geht jeden Tag essen."

---

### Leçon 9 : Indirekte Rede — Le discours indirect
**Contenu :**
- Rapporter les paroles de quelqu'un en allemand
- Avec dass : Er sagt, dass er einen Termin hat.
- Konjunktiv I pour le style journalistique/soutenu : Er sagt, er habe einen Termin.
- Konjunktiv I des verbes courants : haben → habe | sein → sei | kommen → komme
- Quand utiliser Konjunktiv II si Konjunktiv I = forme indicative : er arbeite (OK) / ich arbeite → ich würde arbeiten
- Usages pratiques : rapporter une conversation avec l'administration, une information officielle

**5 exercices :**
1. Rapporter en discours indirect : "Ich habe keinen Pass." → Er sagt, dass...
2. Konjunktiv I de "sein" à la 3e personne singulier ?
3. "Die Beamtin sagt, ___ Antrag ___ bereits bearbeitet." → dass + sein (Konj. I)
4. Quelle forme utiliser quand Konjunktiv I = indicatif ?
5. Rapporter : "Wir kommen morgen." → Sie sagen, dass...

---

### Leçon 10 : Modalpartikeln — Les particules modales (nuances expressives)
**Contenu :**
- Les particules modales donnent une nuance émotionnelle — intraduisibles littéralement
- doch : contradiction douce, rappel : Du weißt doch, dass... / Komm doch mal vorbei!
- mal : suggestion douce, atténuation : Kannst du mal helfen? / Warte mal kurz.
- ja : évidence partagée : Das ist ja interessant. / Er ist ja noch neu hier.
- eigentlich : en fait, à proprement parler : Ich wollte eigentlich früher kommen.
- halt/eben : c'est comme ça, résignation : Das ist halt so. / Das musst du eben akzeptieren.
- schon : renforcement, concession : Das stimmt schon, aber... / Er kommt schon.
- Exemples dans des situations de travail et de vie quotidienne

**5 exercices :**
1. "Du bist ___ Arzt, oder?" → particule pour rappel d'évidence → doch ou mal ?
2. "Kannst du ___ kurz warten?" → atténuation → mal ou ja ?
3. "Das ist ___ interessant!" → surprise positive → ja ou halt ?
4. "Ich wollte ___ früher kommen." → en fait → eigentlich ou schon ?
5. "Das ist ___ so in Deutschland." → résignation → halt ou doch ?

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
