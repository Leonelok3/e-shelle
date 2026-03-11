# PROMPT CHATGPT — B2 GRAMMATIK — Batch 1 (Leçons 1 à 5)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe B2** pour s'intégrer professionnellement en Allemagne.

Génère exactement **5 leçons de grammaire niveau B2** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon (options A/B/C/D)
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Exemples authentiques en allemand soutenu (presse, administration, travail)
7. Prénoms africains dans les exemples
8. Situations : vie professionnelle avancée, écrits formels, textes complexes
9. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"B2","skill":"GRAMMATIK","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

---

### Leçon 1 : Erweiterte Partizipialkonstruktionen — Les groupes participiaux étendus
**Contenu :**
- Le participe présent (Partizip I) et passé (Partizip II) utilisés comme adjectifs étendus
- Struktur : Article + [complément + Partizip I/II] + Nomen
- Partizip I : action simultanée/active : der arbeitende Mann = l'homme qui travaille
- Partizip II : action accomplie/passive : der geprüfte Antrag = la demande vérifiée
- Expansion : Das von der Behörde abgelehnte Visum wurde erneut beantragt.
- Équivalent de propositions relatives comprimées
- Fréquent dans les textes juridiques, officiels, journalistiques
- Exemples : die bereits eingereichten Unterlagen / der noch ausstehende Bescheid / die kürzlich eingeführten Regelungen

**5 exercices :**
1. Transformer la relative en groupe participial : "der Antrag, der abgelehnt wurde"
2. Identifier le Partizip I dans : "die zunehmende Zahl der Fachkräfte"
3. Groupes participiaux étendus — lequel est grammaticalement correct ?
4. "Das von der Ausländerbehörde ausgestellte Dokument" — que signifie cette structure ?
5. Transformer en groupe participial : "die Regel, die seit 2023 gilt"

---

### Leçon 2 : Nominalisierung — La nominalisation (style soutenu)
**Contenu :**
- La nominalisation : transformer des verbes ou adjectifs en substantifs
- Formation : Infinitif → das + Infinitif : arbeiten → das Arbeiten / beantragen → das Beantragen
- Suffixes courants : -ung (die Lösung, die Beantragung), -heit/-keit (die Freiheit, die Möglichkeit), -schaft (die Freundschaft), -nis (das Ergebnis)
- Style administratif et journalistique : préfère les nominalisations aux verbes
- Verbes → noms : entscheiden → die Entscheidung | zulassen → die Zulassung | genehmigen → die Genehmigung
- Exemples : Nach der Beantragung des Visums... / Trotz der Ablehnung seines Antrags... / Die Einführung neuer Regelungen...

**5 exercices :**
1. Nominalisation de "entscheiden" → ?
2. "Die Genehmigung" vient de quel verbe ?
3. Réécrire avec nominalisation : "Weil er den Antrag gestellt hat, konnte er..."
4. Suffixe -ung ou -heit ? → "die Freiheit" ou "die Freiung" pour "Freiheit" ?
5. Quel nom correspond à "sich bewerben" ?

---

### Leçon 3 : Konzessive und adversative Strukturen — Concession et opposition (niveau avancé)
**Contenu :**
- obwohl vs. obgleich vs. wenngleich (bien que — registres différents)
- trotz + Génitif (malgré) vs. trotzdem (quand même) vs. dennoch (néanmoins — soutenu)
- zwar...aber vs. einerseits...andererseits (d'un côté...de l'autre)
- während (tandis que — opposition) : Während Mamadou B2 spricht, sucht er noch Arbeit.
- wohingegen (alors que, en revanche — soutenu) : Er hat Arbeit gefunden, wohingegen viele andere noch suchen.
- im Gegensatz zu + Datif (contrairement à)

**5 exercices :**
1. Registre de "wenngleich" : formel, neutre ou familier ?
2. "Trotz" exige quel cas grammatical ?
3. "Dennoch" vs "trotzdem" — laquelle est plus soutenue ?
4. Relier avec "wohingegen" : "Amina hat die Prüfung bestanden. Kofi muss sie wiederholen."
5. "Im Gegensatz zu" + quel cas ?

---

### Leçon 4 : Konjunktiv I — Le subjonctif 1 (discours indirect formel)
**Contenu :**
- Konjunktiv I : rapporter des propos dans les médias, documents officiels, rapports
- Formation : radical de l'infinitif + terminaisons spéciales : -e/-est/-e/-en/-et/-en
- sein : sei/seiest/sei/seien/seiet/seien
- haben → habe | kommen → komme | arbeiten → arbeite | wissen → wisse
- Quand utiliser KI vs KII : si KI = indicatif → utiliser KII ou "würde"
- Emploi dans articles de presse : Der Minister sagte, die Lage sei ernst.
- Emploi dans procès-verbaux, rapports officiels, textes académiques

**5 exercices :**
1. Konjunktiv I de "sein" à la 3e personne singulier ?
2. Rapporter : "Ich habe keine Zeit." (er) → discours indirect Konjunktiv I
3. Pourquoi utilise-t-on KII quand KI = indicatif ? Exemple avec "arbeiten" (ich)
4. "Der Sprecher erklärte, das Projekt ___ erfolgreich." → KI de "sein"
5. Dans quel registre utilise-t-on principalement le Konjunktiv I ?

---

### Leçon 5 : Subjunktoren und Präpositionen — Correspondances subordonnants/prépositions
**Contenu :**
- Paires à maîtriser pour le style soutenu :
  - weil (subord.) ↔ wegen + Génitif (prép.) : Weil er krank ist / Wegen seiner Krankheit
  - obwohl (subord.) ↔ trotz + Génitif : Obwohl er müde war / Trotz seiner Müdigkeit
  - damit (subord.) ↔ zwecks + Génitif (très formel) / für + Akkusativ
  - wenn (subord.) ↔ bei + Datif : Wenn man Probleme hat / Bei Problemen
  - nachdem (subord.) ↔ nach + Datif : Nachdem er angekommen war / Nach seiner Ankunft
  - bevor (subord.) ↔ vor + Datif : Bevor er abreiste / Vor seiner Abreise
- Transformation de phrases complexes en style nominal compact (typique des textes officiels)

**5 exercices :**
1. Transformer avec préposition : "Weil er keine Arbeit hat, bekommt er Unterstützung."
2. Préposition correspondant à "obwohl" ?
3. "Nach seiner Ankunft in Berlin..." → subordonnant équivalent
4. "Bei Fragen wenden Sie sich an..." → subordonnant équivalent
5. Transformer : "Bevor Amina das Formular einreichte, prüfte sie alles."

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
