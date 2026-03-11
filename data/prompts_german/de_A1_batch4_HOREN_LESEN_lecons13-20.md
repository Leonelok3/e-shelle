# PROMPT CHATGPT — A1 HÖREN + LESEN — Batch 4 (Leçons 13 à 20)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe A1** pour immigrer en Allemagne.

Génère exactement **8 leçons** (4 HÖREN + 4 LESEN) niveau A1 au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement
2. Tableau de 8 objets
3. 5 exercices QCM par leçon
4. `content` = HTML (h3, p, ul/li, strong, blockquote pour les textes/dialogues)
5. `intro` + `explanation` en français
6. Pour HÖREN : inclure dans `content` une **transcription d'un dialogue court** en allemand (entre guillemets dans un blockquote)
7. Pour LESEN : inclure dans `content` un **texte court à lire** (annonce, SMS, panneau, formulaire)
8. Prénoms africains dans tous les exemples
9. Situations immigration / vie quotidienne en Allemagne
10. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"A1","skill":"HOREN","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[...] }]
```
(remplacer HOREN par LESEN pour les leçons de lecture)

---

## LEÇONS HÖREN (4 leçons)

### Leçon 13 : sich vorstellen — Sich vorstellen in einem Dialog (Se présenter — dialogue)
**Contenu :**
Transcription d'un dialogue A1 entre Mamadou et une employée de l'Ausländerbehörde :
- Mamadou se présente (nom, prénom, nationalité, âge, situation familiale)
- L'employée pose des questions basiques
Le dialogue doit faire ~8-10 répliques, vocabulaire A1 uniquement.

**5 exercices basés sur la compréhension du dialogue :**
1. Comment s'appelle l'homme dans le dialogue ?
2. De quel pays vient-il ?
3. Quel âge a-t-il ?
4. Est-il marié ?
5. Quelle est sa profession ?

---

### Leçon 14 : Im Alltag — Kurze Dialoge verstehen (Dialogues du quotidien)
**Contenu :**
2 mini-dialogues A1 :
1. À la boulangerie (Bäckerei) — commander quelque chose, payer
2. Dans le bus — demander si le bus va à une destination

**5 exercices de compréhension basés sur les 2 dialogues**

---

### Leçon 15 : Zahlen und Informationen hören (Écouter des chiffres et informations)
**Contenu :**
Situations typiques où on entend des chiffres :
- Numéro de dossier, numéro de ticket
- Adresse avec numéro
- Heure d'un rendez-vous
- Prix

Dialogue : un agent donne des informations à Kofi à l'office des étrangers (numéro dossier, date RDV, heure)

**5 exercices sur la compréhension de chiffres dans le dialogue**

---

### Leçon 16 : Ansagen und Bekanntmachungen (Annonces publiques)
**Contenu :**
3 annonces courtes typiques en Allemagne :
1. Annonce dans un train (gare)
2. Annonce dans une salle d'attente (Warteraum) administrative
3. Message vocal sur répondeur

**5 exercices de compréhension**

---

## LEÇONS LESEN (4 leçons)

### Leçon 17 : Formulare lesen — Formulaires et données personnelles
**Contenu :**
Un formulaire de demande de visa Goethe A1 (fictif) avec les champs :
- Name, Vorname, Geburtsdatum, Geburtsort, Staatsangehörigkeit, Adresse, Telefon, E-Mail, Familienstand, Beruf
Explication de chaque champ en français.
Exemple rempli pour "Mamadou Diallo, né le 03.05.1990, Dakar, Sénégalese, marié, Elektriker"

**5 exercices basés sur la lecture du formulaire :**
1. Quel champ correspond à "lieu de naissance" ?
2. "Familienstand: verheiratet" signifie ?
3. Comment s'écrit la date "3 mai 1990" sur un formulaire ?
4. Quel champ demande le métier ?
5. "Staatsangehörigkeit: senegalesisch" signifie ?

---

### Leçon 18 : Schilder und kurze Texte (Panneaux et textes courts)
**Contenu :**
8 panneaux/affiches typiques en Allemagne avec traduction :
- Eingang/Ausgang (entrée/sortie)
- Notausgang (sortie de secours)
- Geöffnet/Geschlossen (ouvert/fermé)
- Bitte warten (veuillez patienter)
- Kein Zutritt (accès interdit)
- Öffnungszeiten (horaires d'ouverture)
- Bitte Ticket entwerten (composter votre ticket)
- WC / Damen / Herren

**5 exercices basés sur la lecture de ces panneaux**

---

### Leçon 19 : SMS und kurze Mitteilungen lesen (Lire des SMS et messages courts)
**Contenu :**
3 SMS/messages courts authentiques niveau A1 :
1. SMS de confirmation de rendez-vous (Ausländerbehörde)
2. SMS d'un ami invitant à une réunion
3. Note laissée par un voisin

**5 exercices de compréhension**

---

### Leçon 20 : Fahrpläne und praktische Informationen (Horaires et informations pratiques)
**Contenu :**
Un extrait de tableau d'horaires de bus/S-Bahn (fictif mais réaliste) avec les destinations et horaires.
Explication : comment lire un plan de transport en Allemagne.

**5 exercices sur la lecture de l'horaire :**
1. À quelle heure part le prochain train pour X ?
2. Quel est le quai de départ ?
3. Combien de minutes dure le trajet ?
4. Est-ce que le train du dimanche est différent ?
5. Où descend Amina pour aller à l'Ausländerbehörde ?

---

Génère maintenant le JSON complet des 8 leçons. Commence par `[` et termine par `]`.
