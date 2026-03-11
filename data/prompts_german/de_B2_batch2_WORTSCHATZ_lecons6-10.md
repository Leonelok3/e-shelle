# PROMPT CHATGPT — B2 WORTSCHATZ — Batch 2 (Leçons 6 à 10)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe B2** pour s'intégrer professionnellement en Allemagne.

Génère exactement **5 leçons de vocabulaire (Wortschatz) niveau B2** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Vocabulaire soutenu, registre formel/professionnel
7. Prénoms africains dans les exemples
8. Situations : carrière, droit, société, économie en Allemagne
9. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"B2","skill":"WORTSCHATZ","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

---

### Leçon 6 : Verwaltungs- und Rechtssprache (Vocabulaire administratif et juridique avancé)
**Vocabulaire à enseigner :**
- Procédures : das Widerspruchsverfahren (procédure de recours), die Klage (plainte/action en justice), der Bescheid (décision administrative), der Einspruch (opposition), die Frist (délai), die Zustellung (notification), rechtskräftig (ayant force de loi)
- Documents officiels : die Vollmacht (procuration), die eidesstattliche Erklärung (déclaration sur l'honneur), die Beglaubigung (légalisation), das Protokoll (procès-verbal), die Urkunde (acte officiel/diplôme)
- Verbes formels : beantragen, einlegen (Widerspruch einlegen), anfechten (contester), geltend machen (faire valoir), veranlassen (faire en sorte de), gewährleisten (garantir)
- Phrases : Gegen diesen Bescheid kann innerhalb von 4 Wochen Widerspruch eingelegt werden.

**5 exercices :**
1. "Widerspruch einlegen" signifie → ?
2. "Vollmacht" est → ?
3. "Die Frist beträgt 4 Wochen" → que signifie "Frist" ?
4. "Anfechten" signifie → ?
5. "Eidesstattliche Erklärung" est → ?

---

### Leçon 7 : Wirtschaft und Arbeitsmarkt (Économie et marché du travail)
**Vocabulaire à enseigner :**
- Marché du travail : der Fachkräftemangel (pénurie), die Qualifizierung (qualification), die Umschulung (reconversion), die Weiterbildung (formation continue), die Arbeitnehmerüberlassung (intérim), der Tarifvertrag (convention collective)
- Entreprise : die Geschäftsführung (direction), der Aufsichtsrat (conseil de surveillance), die Bilanz (bilan), der Umsatz (chiffre d'affaires), die Insolvenz (faillite), die Fusion (fusion)
- Économie nationale : das BIP (PIB), die Inflation, die Rezession, die Konjunktur (conjoncture), der Haushalt (budget), die Steuerpolitik
- Phrases : Die Konjunktur erholt sich langsam. / Der Fachkräftemangel betrifft alle Branchen.

**5 exercices :**
1. "Fachkräftemangel" signifie → ?
2. "Umschulung" est différent de "Weiterbildung" comment ?
3. "Tarifvertrag" est → ?
4. "BIP" est l'abréviation de → ?
5. "Insolvenz" signifie → ?

---

### Leçon 8 : Wissenschaft und Bildung (Sciences et enseignement supérieur)
**Vocabulaire à enseigner :**
- Système universitaire : das Studium, der Bachelor/Master/Doktor, die Dissertation, das Seminar, die Vorlesung, der Lehrplan (curriculum), die Zulassung (admission), der Numerus Clausus (NC)
- Reconnaissance des diplômes : die Anerkennung, die Nostrifikation, das anabin (base de données), die Äquivalenz, die Nachqualifizierung
- Recherche : die Forschung, das Labor, das Stipendium (bourse), die Publikation, peer-reviewed, die Forschungsförderung (financement de la recherche)
- Phrases : Ibrahima bewirbt sich um ein Stipendium der DAAD. Sein Abschluss wird durch anabin bewertet.

**5 exercices :**
1. "Numerus Clausus" est → ?
2. "DAAD" est → ?
3. "Nostrifikation" signifie → ?
4. "Die Dissertation" est → ?
5. "Stipendium" signifie → ?

---

### Leçon 9 : Gesellschaftliche und politische Themen (Thèmes de société et politique)
**Vocabulaire à enseigner :**
- Politique : der Bundestag, der Bundesrat, die Koalition, die Opposition, das Grundgesetz, die Demokratie, die Verfassung (constitution), das Wahlrecht, der Föderalismus
- Immigration et politique : das Aufenthaltsgesetz, das Asylrecht, die Abschiebung (expulsion), die Einbürgerung, die Residenzpflicht, der Integrationskurs, der Fachkräfteeinwanderungsgesetz
- Société : die Chancengleichheit (égalité des chances), die Inklusion, der soziale Aufstieg (ascension sociale), die Altersarmut (pauvreté des seniors), die Digitalisierung
- Phrases : Das Fachkräfteeinwanderungsgesetz erleichtert die Einwanderung qualifizierter Arbeitskräfte.

**5 exercices :**
1. "Föderalismus" en Allemagne signifie → ?
2. "Fachkräfteeinwanderungsgesetz" facilite → ?
3. "Residenzpflicht" concerne → ?
4. "Chancengleichheit" signifie → ?
5. "Abschiebung" signifie → ?

---

### Leçon 10 : Sprachregister und Stilebenen (Registres de langue et niveaux de style)
**Vocabulaire à enseigner :**
- Registres : umgangssprachlich (familier), neutral (neutre), formal/gehoben (soutenu/formel), wissenschaftlich (académique), amtlich (officiel/administratif)
- Synonymes selon le registre :
  - demander : fragen (neutre) / erkundigen (soutenu) / anfragen (formel) / beantragen (officiel)
  - donner : geben (neutre) / überreichen (solennel) / aushändigen (formel) / zukommen lassen (officiel)
  - habiter : wohnen (neutre) / seinen Wohnsitz haben (formel) / ansässig sein (officiel)
- Importance du registre dans les candidatures, lettres officielles, entretiens
- Comment adapter son registre selon le destinataire

**5 exercices :**
1. Registre de "erkundigen" vs "fragen" — lequel est plus soutenu ?
2. "Seinen Wohnsitz in Berlin haben" → équivalent familier ?
3. Dans une lettre à l'Ausländerbehörde, quel registre utiliser ?
4. "Aushändigen" est synonyme soutenu de → ?
5. Comment dire "J'habite à Frankfurt" dans un courrier officiel ?

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
