# PROMPT CHATGPT — C1 HÖREN + LESEN — Batch 3 (Leçons 11 à 18)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe C1** pour s'intégrer professionnellement en Allemagne.

Génère exactement **8 leçons** (4 HÖREN + 4 LESEN) niveau C1 au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement
2. Tableau de 8 objets
3. 5 exercices QCM par leçon
4. `content` = HTML avec blockquote pour dialogues/textes
5. `intro` + `explanation` en français
6. HÖREN C1 : transcriptions complexes ~20 répliques, implicite, humour, ironie, sous-entendu
7. LESEN C1 : textes authentiques ~250-300 mots (article de presse nationale, texte académique, texte littéraire exigeant)
8. Prénoms africains dans les exemples
9. Thèmes : politique, économie, société, culture, science, environnement, philosophie
10. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"C1","skill":"HOREN","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[...] }]
```

---

## LEÇONS HÖREN (4 leçons)

### Leçon 11 : Akademische Vorlesung — Extrait de conférence universitaire sur la migration
**Contenu :**
Transcription (~20 répliques) d'un extrait de conférence universitaire d'une professeure de sociologie sur les effets économiques de l'immigration qualifiée en Allemagne :
- Données statistiques sur la contribution des migrants au PIB
- Débat sur la fuite des cerveaux (Brain Drain) vs. gain de capital humain
- Témoignage de Kofi, doctorant ghanéen en économie
- Nuances implicites, ironie académique, références à des études
Vocabulaire sociologique et économique C1, structures complexes, nombreuses subordinations.

**5 exercices :**
1. Quelle est la position principale de la professeure sur l'immigration qualifiée ?
2. Quel concept économique est discuté en lien avec les pays d'origine ?
3. Quel argument Kofi apporte-t-il en tant que témoin ?
4. Quelle implication ironique la professeure formule-t-elle sur la politique migratoire ?
5. Sur quels points les participants s'accordent-ils finalement ?

---

### Leçon 12 : Politische Talkshow — Débat télévisé sur la réforme du système éducatif
**Contenu :**
Transcription (~20 répliques) d'une émission politique type "Anne Will" sur la réforme du Bildungssystem en Allemagne :
- Un ministre de l'Éducation défend la réforme du Abitur
- Une enseignante syndicale critique le manque de ressources
- Amina, chercheuse en pédagogie d'origine malienne, apporte une perspective comparative Afrique-Allemagne
- Échanges vifs, interruptions, insinuations, rhétorique politique
Vocabulaire politique et pédagogique C1 avancé.

**5 exercices :**
1. Quel est l'argument central du ministre en faveur de la réforme ?
2. Quelle critique principale l'enseignante syndicale formule-t-elle ?
3. Comment Amina nuance-t-elle le débat grâce à son expérience comparative ?
4. Quelle sous-entente (implicite) peut-on lire dans les propos du ministre ?
5. Quel accord partiel émerge-t-il en fin de discussion ?

---

### Leçon 13 : Literarisches Gespräch — Discussion radiophonique sur un roman afro-allemand
**Contenu :**
Transcription (~20 répliques) d'une émission culturelle type "Lesart" (Deutschlandfunk) sur un roman contemporain d'une autrice afro-allemande traitant d'identité, d'appartenance et de racisme ordinaire :
- La journaliste analyse le style narratif et les thèmes
- L'autrice explique ses choix esthétiques et autobiographiques
- Références littéraires (Chimamanda Ngozi Adichie, May Ayim)
- Langage littéraire C1, métaphores discutées, nuances stylistiques
Exemple de personnage : Fatou, héroïne franco-guinéenne du roman.

**5 exercices :**
1. Quel thème central le roman explore-t-il selon l'autrice ?
2. Quelle technique narrative est discutée dans l'émission ?
3. À quelle autre autrice l'autrice est-elle comparée et pourquoi ?
4. Quel passage du roman la journaliste cite-t-elle comme exemple de style ?
5. Comment l'autrice décrit-elle son rapport à l'identité afro-allemande ?

---

### Leçon 14 : Fachgespräch — Entretien médical spécialisé (C1)
**Contenu :**
Transcription (~20 répliques) d'un entretien entre un médecin spécialiste et Ibrahima, interne en médecine d'origine nigériane, lors d'une consultation en médecine interne :
- Discussion du tableau clinique d'un patient complexe (comorbidités)
- Termes médicaux spécialisés : anamnèse, diagnostic différentiel, pronostic
- Débat sur les options thérapeutiques avec argumentation clinique
- Implicites professionnels, questions rhétoriques, politesse médicale allemande
Vocabulaire médical et paramédical C1 très avancé.

**5 exercices :**
1. Quel est le principal défi diagnostique discuté dans cet entretien ?
2. Quelle option thérapeutique le médecin spécialiste privilégie-t-il et pourquoi ?
3. Quel terme médical Ibrahima utilise-t-il pour décrire les comorbidités ?
4. Quelle nuance implicite le médecin exprime-t-il sur la situation du patient ?
5. Comment Ibrahima argumente-t-il en faveur de son diagnostic différentiel ?

---

## LEÇONS LESEN (4 leçons)

### Leçon 15 : Feuilleton — Article d'opinion (FAZ/SZ niveau) sur l'identité européenne
**Contenu :**
Article de presse de niveau FAZ/Süddeutsche Zeitung (~280 mots) sur la question de l'identité européenne face aux mouvements migratoires :
- Argumentation complexe, ironie, références culturelles et historiques
- Vocabulaire : die Leitkultur, das Kulturerbe (patrimoine culturel), die Solidarität, die Abschottung (fermeture des frontières), das Zusammengehörigkeitsgefühl (sentiment d'appartenance)
- Point de vue d'un intellectuel afro-européen (Kofi Agyeman, philosophe)
- Implicites, allusions, citations d'auteurs classiques européens
Vocabulaire journalistique et philosophique C1.

**5 exercices :**
1. Quelle est la thèse principale de l'auteur sur l'identité européenne ?
2. Quel paradoxe l'auteur souligne-t-il dans la politique migratoire européenne ?
3. Que signifie "Leitkultur" dans le contexte de cet article ?
4. Comment l'auteur utilise-t-il l'ironie dans son argumentation ?
5. Quelle conclusion philosophique tire-t-il sur le "Zusammengehörigkeitsgefühl" européen ?

---

### Leçon 16 : Wissenschaftlicher Artikel — Texte académique sur l'intégration économique
**Contenu :**
Extrait d'article académique (~270 mots) d'une revue de sciences économiques sur les déterminants de l'intégration professionnelle des migrants qualifiés en Allemagne :
- Méthodologie (étude longitudinale, cohorte), résultats statistiques
- Variables : niveau de langue, reconnaissance des diplômes, réseau professionnel
- Conclusions et implications politiques
- Style académique dense : nominalisations, passif, citations en style indirect (Konjunktiv I)
Exemple de chercheur : Dr. Amina Coulibaly, économiste.

**5 exercices :**
1. Quelle variable s'avère la plus déterminante pour l'intégration professionnelle selon l'étude ?
2. Quelle méthodologie les auteurs utilisent-ils ?
3. Quelle est la principale limite de l'étude mentionnée dans l'extrait ?
4. Comment les auteurs formulent-ils leurs recommandations politiques ?
5. Que signifie l'usage du Konjunktiv I dans le passage "Die Ergebnisse zeigten, dass..." ?

---

### Leçon 17 : Gesetzestext — Extrait de texte législatif (Aufenthaltsgesetz)
**Contenu :**
Extrait (~260 mots) du Aufenthaltsgesetz (loi sur le séjour des étrangers) concernant les conditions de délivrance du titre de séjour permanent (Niederlassungserlaubnis) :
- Conditions : durée de séjour, niveau de langue, revenus, cotisations retraite
- Formulation juridique dense : Voraussetzungen, sofern, unbeschadet, vorbehaltlich
- Exceptions et cas particuliers pour les Fachkräfte
- Interprétation d'une clause complexe impliquant Mamadou, ingénieur ivoirien
Vocabulaire juridique et administratif C1 niveau avancé.

**5 exercices :**
1. Quelle est la condition principale pour obtenir la Niederlassungserlaubnis selon le texte ?
2. Que signifie "unbeschadet" dans ce contexte juridique ?
3. Quelle exception est prévue pour les Fachkräfte dans cet extrait ?
4. Comment interpréter la clause "sofern keine öffentlichen Belange entgegenstehen" ?
5. Mamadou remplit-il les conditions décrites ? Sur quelle base l'estimer ?

---

### Leçon 18 : Literarischer Text — Extrait littéraire (roman contemporain afro-allemand)
**Contenu :**
Extrait (~260 mots) d'un roman contemporain afro-allemand décrivant la double appartenance identitaire d'Ibrahima, ingénieur béninois à Berlin, lors d'un repas de famille en Allemagne où se mélangent langue, mémoire et présent :
- Style narratif C1 : focalisation interne, flux de conscience, analepses
- Thèmes : nostalgie, déracinement, reconstruction identitaire, altérité
- Langue : métaphores, images poétiques, ironie douce, registre introspectif
- Vocabulaire littéraire C1 : das Heimweh (nostalgie), die Zerrissenheit (déchirement), die Zugehörigkeit (appartenance), die Entfremdung (aliénation)
Vocabulaire littéraire C1.

**5 exercices :**
1. Quel procédé narratif domine cet extrait ?
2. Quel sentiment contradictoire Ibrahima éprouve-t-il lors du repas ?
3. Comment l'auteur utilise-t-il la langue pour exprimer la double appartenance ?
4. Que symbolise le repas de famille dans le contexte de cet extrait ?
5. Quel mot allemand correspond le mieux à "déchirement identitaire" dans le texte ?

---

Génère maintenant le JSON complet des 8 leçons. Commence par `[` et termine par `]`.
