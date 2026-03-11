# PROMPT CHATGPT — A2 GRAMMATIK — Batch 1 (Leçons 1 à 5)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe A2** pour immigrer en Allemagne.

Génère exactement **5 leçons de grammaire niveau A2** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon (options A/B/C/D)
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Exemples bilingues dans `content` (allemand — français)
7. Prénoms africains dans les exemples (Mamadou, Fatou, Kofi, Amina, Ibrahima, Awa)
8. Situations liées à l'immigration, à l'administration, à la vie quotidienne en Allemagne
9. `correct_option` = lettre majuscule "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"A2","skill":"GRAMMATIK","exam_type":"GOETHE","title":"...","intro":"...","content":"<h3>...</h3><p>...</p>","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

---

### Leçon 1 : Der Akkusativ — L'accusatif (complément d'objet direct)
**Contenu :**
- Cas nominatif vs accusatif : changement de l'article masculin (der → den, ein → einen, kein → keinen)
- Féminin et neutre : pas de changement
- Verbes qui exigent l'accusatif : haben, brauchen, suchen, finden, beantragen, ausfüllen
- Tableau : der/ein/kein → den/einen/keinen (masc.) + exemples
- Exemples immigration : Ich brauche einen Reisepass. Ich beantrage einen Aufenthaltstitel. Mamadou sucht einen Job.

**5 exercices :**
1. "Ich brauche ___ Termin" (masculin) → article correct à l'accusatif
2. "Sie beantragen ___ Visum" (neutre) → article correct
3. "Kofi sucht ___ Wohnung" (féminin) → article correct
4. Identifier l'accusatif dans la phrase : "Der Mann beantragt den Aufenthaltstitel."
5. Transformer : "Das ist ein Pass" → "Ich habe ___"

---

### Leçon 2 : Der Dativ — Le datif (complément d'objet indirect)
**Contenu :**
- Le datif : après les verbes helfen, geben, zeigen, schreiben, erklären + prépositions mit, bei, von, seit, nach, aus, zu, gegenüber
- Changements d'articles : dem (masc./neutre), der (fém.), den+n (pluriel)
- Tableau complet : der/die/das/die → dem/der/dem/den
- Exemples : Ich helfe dem Mann. Sie schreibt der Mitarbeiterin. Mamadou wohnt bei einem Freund.
- Formules pratiques : seit + Dativ (seit einem Jahr), mit + Dativ (mit dem Bus), nach + Dativ (nach dem Termin)

**5 exercices :**
1. "Ich helfe ___ Frau" (féminin, datif) → article correct
2. "Er fährt mit ___ Bus" (masculin) → article au datif
3. "Amina wohnt seit ___ Jahr" (neutre) → article au datif
4. "Ich gebe ___ Kind das Buch" (neutre) → article au datif
5. Préposition qui exige toujours le datif parmi : durch / mit / für / ohne

---

### Leçon 3 : Modalverben — Les verbes modaux (können, müssen, dürfen, sollen, wollen)
**Contenu :**
- Les 5 modaux essentiels avec conjugaison au présent
- können : capacité / possibilité — Ich kann Deutsch sprechen.
- müssen : obligation — Ich muss zum Amt gehen.
- dürfen : permission / interdiction — Hier darf man nicht parken.
- sollen : injonction — Du sollst den Antrag ausfüllen.
- wollen : volonté — Mamadou will in Deutschland arbeiten.
- Infinitif rejeté en fin de phrase : Er muss morgen zum Ausländeramt gehen.
- Exemples liés aux démarches administratives

**5 exercices :**
1. "Fatou ___ kein Deutsch, sie lernt noch." → modal correct (können)
2. "Du ___ dieses Formular unterschreiben." → obligation → müssen
3. "Hier ___ man nicht rauchen." → interdiction → dürfen
4. Conjuguer "können" à la 2e personne singulier
5. Mettre dans le bon ordre : "arbeiten / Mamadou / in Berlin / will"

---

### Leçon 4 : Perfekt — Le passé composé (sein et haben)
**Contenu :**
- Formation du Perfekt : haben/sein + Partizip II
- Règle haben : la plupart des verbes transitifs et réfléchis
- Règle sein : verbes de mouvement (fahren, gehen, kommen, fliegen, reisen) + Zustandsveränderung (werden, bleiben)
- Formation du Partizip II : ge- + radical + -(e)t (réguliers) / ge- + radical + -en (irréguliers)
- Tableau des irréguliers essentiels : gehen → gegangen, kommen → gekommen, fahren → gefahren, sein → gewesen, haben → gehabt, sprechen → gesprochen, schreiben → geschrieben
- Exemples : Mamadou ist nach Deutschland geflogen. Er hat den Antrag ausgefüllt.

**5 exercices :**
1. Auxiliaire de "fahren" au Perfekt → haben ou sein ?
2. Partizip II de "schreiben" (irrégulier) ?
3. "Amina ___ gestern zum Amt gegangen." → auxiliaire correct
4. Partizip II de "ausfüllen" (verbe à particule) ?
5. Former le Perfekt : "Kofi / fliegen / nach Frankfurt"

---

### Leçon 5 : Trennbare Verben — Les verbes à particule séparable
**Contenu :**
- Principe : la particule se sépare du verbe et se place en fin de phrase
- Particules courantes : an-, auf-, aus-, ein-, mit-, vor-, zu-, ab-, zurück-
- Verbes essentiels pour l'immigration :
  - anrufen (appeler) → Ich rufe das Amt an.
  - ausfüllen (remplir) → Er füllt das Formular aus.
  - einreichen (soumettre) → Sie reicht die Dokumente ein.
  - mitnehmen (apporter) → Nimm deinen Pass mit!
  - abgeben (déposer) → Mamadou gibt die Unterlagen ab.
  - zurückkommen (revenir) → Wann kommst du zurück?
- Au Perfekt : ge- entre la particule et le radical : angerufen, ausgefüllt, eingereicht

**5 exercices :**
1. "Ich ___ das Formular ___." → anrufen ou ausfüllen ? Placer la particule.
2. Position de la particule dans : "Mamadou ruft das Amt an." → correcte ou non ?
3. Partizip II de "einreichen" ?
4. "Bitte ___ Ihren Reisepass ___!" → mitbringen → forme correcte
5. Traduire : "Il dépose les documents à l'office des étrangers." avec "abgeben"

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
