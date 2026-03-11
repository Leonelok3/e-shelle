# PROMPT CHATGPT — B1 WORTSCHATZ — Batch 3 (Leçons 11 à 15)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe B1** pour obtenir leur titre de séjour permanent en Allemagne.

Génère exactement **5 leçons de vocabulaire (Wortschatz) niveau B1** au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement — rien avant ni après
2. Tableau de 5 objets
3. 5 exercices QCM par leçon
4. `content` = HTML (h3, p, ul/li, table, strong)
5. `intro` + `explanation` en français
6. Exemples bilingues dans `content`
7. Prénoms africains dans les exemples
8. Situations : vie professionnelle, droits, intégration sociale en Allemagne
9. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"B1","skill":"WORTSCHATZ","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[{"question_text":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_option":"A","explanation":"..."}] }]
```

---

### Leçon 11 : Rechte und Pflichten — Droits et obligations en Allemagne
**Vocabulaire à enseigner :**
- Droits fondamentaux : das Recht (droit), die Meinungsfreiheit (liberté d'expression), die Religionsfreiheit, das Wahlrecht (droit de vote), das Asylrecht, das Aufenthaltsrecht
- Obligations civiques : die Steuern zahlen (payer les impôts), die Schulpflicht (obligation scolaire), die Meldepflicht (obligation d'inscription à la mairie), die Versicherungspflicht
- Institutions : das Grundgesetz (Loi fondamentale), das Bundesverfassungsgericht, der Bürger/die Bürgerin (citoyen/ne), der Ausländer/die Ausländerin
- Phrases : Ich habe das Recht auf... / Ich bin verpflichtet, ... zu tun. / Als Einwohner muss ich mich anmelden.

**5 exercices :**
1. "Meldepflicht" signifie → ?
2. "Das Grundgesetz" est → ?
3. "Schulpflicht" s'applique à → ?
4. "Steuern zahlen" est → un droit ou une obligation ?
5. "Aufenthaltsrecht" signifie → ?

---

### Leçon 12 : Berufsleben und Arbeitsrecht (Vie professionnelle et droit du travail)
**Vocabulaire à enseigner :**
- Contrat et conditions : der unbefristete/befristete Vertrag (CDI/CDD), die Probezeit (période d'essai), die Überstunden (heures supplémentaires), die Lohnerhöhung (augmentation), die Kündigung (licenciement/démission), die Abfindung (indemnité de départ)
- Droits des travailleurs : der Betriebsrat (comité d'entreprise), der Gewerkschaft (syndicat), der Mindestlohn (salaire minimum), der Mutterschutz (congé maternité), das Elterngeld (allocation parentale)
- Phrases : Ich habe einen unbefristeten Vertrag. / Mein Arbeitgeber hat mich ohne Grund gekündigt. / Ich möchte meinen Lohn verhandeln.

**5 exercices :**
1. "CDI" en allemand → unbefristeter ou befristeter Vertrag ?
2. "Mindestlohn" est → ?
3. "Probezeit" dure généralement combien de temps en Allemagne ?
4. "Betriebsrat" représente → ?
5. "Elterngeld" est → ?

---

### Leçon 13 : Gesellschaft und Integration (Société et intégration)
**Vocabulaire à enseigner :**
- Intégration : die Integration, der Integrationskurs, die Einbürgerung (naturalisation), die doppelte Staatsbürgerschaft (double nationalité), das Zusammenleben (vie en commun)
- Société allemande : das Ehrenamt (bénévolat), der Verein (association/club), die Nachbarschaft (voisinage), die Gemeinschaft (communauté), das Miteinander (vivre ensemble)
- Discrimination : die Diskriminierung, das Vorurteil (préjugé), der Rassismus, die Gleichberechtigung (égalité des droits), die Toleranz
- Phrases : Ich möchte die deutsche Staatsangehörigkeit beantragen. / Ich engagiere mich ehrenamtlich. / Wir leben gut zusammen.

**5 exercices :**
1. "Einbürgerung" signifie → ?
2. "Ehrenamt" est → travail bénévole ou emploi à temps partiel ?
3. "Vorurteil" signifie → ?
4. Condition principale pour la naturalisation en Allemagne → ?
5. "Gleichberechtigung" signifie → ?

---

### Leçon 14 : Umwelt und Alltag (Environnement et quotidien allemand)
**Vocabulaire à enseigner :**
- Tri des déchets : der Müll (déchets), die Mülltrennung (tri sélectif), die Biotonne (poubelle verts), die Gelbe Tonne/der Gelbe Sack (emballages), das Altpapier (vieux papiers), das Pfand (consigne)
- Énergie et environnement : die Energiesparen (économies d'énergie), die Heizung (chauffage), der Strom (électricité), die Solarenergie, die Nachhaltigkeit (durabilité)
- Quotidien pratique : die Hausordnung (règlement intérieur), der Hausmeister (gardien), der Lärm (bruit), die Ruhezeiten (heures de silence), der Nachbar/die Nachbarin

**5 exercices :**
1. Où jette-t-on les emballages en Allemagne ?
2. "Pfand" sur une bouteille signifie → ?
3. "Ruhezeiten" sont généralement → de 13h à 15h et après 22h ou 24h/24 ?
4. "Hausmeister" est → ?
5. "Mülltrennung" est → obligatoire ou facultatif en Allemagne ?

---

### Leçon 15 : Medien und Kommunikation (Médias et communication)
**Vocabulaire à enseigner :**
- Médias : die Zeitung (journal), die Zeitschrift (magazine), die Nachrichten (informations), die Sendung (émission), der Rundfunk (radio/audiovisuel public), die ARD/ZDF (chaînes publiques), das Internet
- GEZ/Rundfunkbeitrag : la redevance audiovisuelle obligatoire en Allemagne (~18€/mois)
- Communication formelle : der Brief (courrier), das Fax, die E-Mail, die Kündigung schriftlich (résiliation par écrit), die Einschreiben (recommandé), der Datenschutz (protection des données)
- DSGVO : Datenschutz-Grundverordnung (RGPD) — droits sur les données personnelles
- Phrases : Ich möchte meinen Vertrag kündigen. / Ich widerrufe meine Einwilligung.

**5 exercices :**
1. "Rundfunkbeitrag" est → ?
2. "Einschreiben" est → ?
3. "DSGVO" protège → ?
4. Pour résilier un contrat, quelle forme est obligatoire en Allemagne ?
5. "ARD und ZDF" sont → chaînes publiques ou privées ?

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
