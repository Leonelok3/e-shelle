# PROMPT CHATGPT — A2 HÖREN + LESEN — Batch 4 (Leçons 16 à 22)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe A2** pour immigrer en Allemagne.

Génère exactement **7 leçons** (4 HÖREN + 3 LESEN) niveau A2 au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement
2. Tableau de 7 objets
3. 5 exercices QCM par leçon
4. `content` = HTML (h3, p, ul/li, blockquote pour dialogues/textes)
5. `intro` + `explanation` en français
6. Pour HÖREN : transcription d'un dialogue A2 dans un blockquote
7. Pour LESEN : texte court réaliste (email, annonce, article simple, formulaire)
8. Prénoms africains dans tous les exemples
9. Situations immigration / vie quotidienne en Allemagne
10. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"A2","skill":"HOREN","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[...] }]
```
(remplacer HOREN par LESEN pour les leçons de lecture)

---

## LEÇONS HÖREN (4 leçons)

### Leçon 16 : Beim Arzt — Dialogue chez le médecin
**Contenu :**
Transcription d'un dialogue A2 entre Amina et son médecin généraliste :
- Le médecin demande les symptômes
- Amina décrit sa douleur et depuis quand
- Le médecin prescrit un médicament et donne des conseils
Dialogue ~10 répliques, vocabulaire A2 (Schmerzen, Fieber, Rezept, Tabletten, drei Mal täglich).

**5 exercices basés sur le dialogue :**
1. Quelle est la raison de la consultation d'Amina ?
2. Depuis quand a-t-elle ces symptômes ?
3. Qu'est-ce que le médecin prescrit ?
4. Combien de fois par jour doit-elle prendre le médicament ?
5. Que lui conseille le médecin en plus du médicament ?

---

### Leçon 17 : Wohnungssuche — Appel téléphonique pour un appartement
**Contenu :**
Transcription d'un appel téléphonique entre Mamadou et un propriétaire :
- Mamadou appelle pour une annonce d'appartement
- Il demande le loyer, la superficie, le quartier, les charges
- Il prend rendez-vous pour visiter
Dialogue ~10 répliques, niveau A2.

**5 exercices :**
1. Combien coûte le loyer mensuel ?
2. Quelle est la superficie de l'appartement ?
3. Les charges sont-elles incluses dans le loyer ?
4. Dans quel quartier se trouve l'appartement ?
5. Quand est prévu le rendez-vous pour la visite ?

---

### Leçon 18 : Am Telefon — Conversation téléphonique administrative
**Contenu :**
Transcription d'un appel téléphonique entre Kofi et la réception de l'Ausländerbehörde :
- Kofi demande un rendez-vous
- La réceptionniste demande son numéro de dossier et son nom
- Elle lui propose des créneaux
- Kofi confirme et reçoit une information importante
Dialogue ~12 répliques.

**5 exercices :**
1. Pourquoi Kofi appelle-t-il ?
2. Quelle information personnelle lui demande-t-on ?
3. Quel est le premier créneau proposé ?
4. Quel document Kofi doit-il apporter absolument ?
5. Comment Kofi doit-il confirmer son rendez-vous ?

---

### Leçon 19 : Im Jobcenter — Entretien au centre pour l'emploi
**Contenu :**
Transcription d'un entretien entre Ibrahima et une conseillère au Jobcenter :
- La conseillère demande la situation actuelle d'Ibrahima (sans emploi depuis quand, formation, expérience)
- Elle lui présente des options : Ausbildung, Weiterbildung, offres d'emploi
- Elle lui explique les aides disponibles
Dialogue ~10 répliques.

**5 exercices :**
1. Depuis combien de temps Ibrahima est-il sans emploi ?
2. Quelle est sa formation ?
3. Quelle option la conseillère recommande-t-elle en premier ?
4. Quelle aide financière est mentionnée ?
5. Quelle est la prochaine étape pour Ibrahima ?

---

## LEÇONS LESEN (3 leçons)

### Leçon 20 : Eine Wohnungsanzeige lesen — Lire une annonce immobilière
**Contenu :**
Une annonce immobilière réaliste (style ImmoScout24) :
- Titre, localisation, superficie, nombre de pièces, loyer, charges, étage, disponibilité, contact
- Abréviations courantes : KM = Kaltmiete, WM = Warmmiete, NK = Nebenkosten, EG = Erdgeschoss, OG = Obergeschoss, qm = m²
- Explication des abréviations en français

**5 exercices basés sur la lecture de l'annonce :**
1. Quel est le loyer charges comprises ?
2. À quel étage se trouve l'appartement ?
3. Combien de pièces a l'appartement ?
4. Quand l'appartement est-il disponible ?
5. "NK" dans l'annonce signifie → ?

---

### Leçon 21 : Eine E-Mail lesen und schreiben — Email formel niveau A2
**Contenu :**
Un email formel d'Amina à son propriétaire signalant une panne :
- Objet, formule de salutation, description du problème, demande d'intervention, formule de politesse
Puis un email de réponse du propriétaire.
Structure et vocabulaire d'un email formel A2.

**5 exercices :**
1. Quel est le problème signalé dans l'email ?
2. Quelle est la formule de salutation formelle utilisée ?
3. Que demande Amina précisément ?
4. Comment signe-t-elle l'email ?
5. Quelle est la réponse du propriétaire ?

---

### Leçon 22 : Informationen aus einem Text entnehmen — Extraire des informations d'un texte
**Contenu :**
Un article court de journal local (~150 mots) sur un cours d'intégration gratuit proposé par la ville :
- Date, lieu, public cible, contenu du cours, inscription, contact
Texte réaliste niveau A2 avec vocabulaire administratif simple.

**5 exercices :**
1. Quel type de cours est proposé ?
2. Pour qui est ce cours destiné ?
3. Où a lieu le cours ?
4. Comment s'inscrire ?
5. Le cours est-il payant ?

---

Génère maintenant le JSON complet des 7 leçons. Commence par `[` et termine par `]`.
