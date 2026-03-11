# PROMPT CHATGPT — A1 SPRECHEN + SCHREIBEN — Batch 5 (Leçons 21 à 25)
# Copie TOUT ce qui suit la ligne de tirets dans ChatGPT

---

Tu es un expert pédagogue en langue allemande. Tu crées du contenu pour une app destinée à des **Africains francophones** préparant le **Goethe A1** pour immigrer en Allemagne.

Génère exactement **5 leçons** (3 SPRECHEN + 2 SCHREIBEN) niveau A1 au format JSON strict.

## RÈGLES ABSOLUES
1. JSON valide uniquement
2. Tableau de 5 objets
3. 5 exercices QCM par leçon
4. `content` = HTML (h3, p, ul/li, strong, blockquote)
5. `intro` + `explanation` en français
6. SPRECHEN : dialogues modèles + phrases types à mémoriser
7. SCHREIBEN : textes modèles à compléter/imiter (formulaires, SMS, petite annonce)
8. Prénoms africains dans tous les exemples
9. Situations immigration/quotidien en Allemagne
10. `correct_option` = "A", "B", "C" ou "D"

## FORMAT
```json
[{ "level":"A1","skill":"SPRECHEN","exam_type":"GOETHE","title":"...","intro":"...","content":"...","exercises":[...] }]
```

---

## LEÇONS SPRECHEN (3 leçons)

### Leçon 21 : Sich vorstellen auf Deutsch (Se présenter en allemand)
**Contenu :**
Le dialogue de présentation complet pour le Goethe A1 :
Wie heißen Sie? — Wo wohnen Sie? — Woher kommen Sie? — Wie alt sind Sie? — Was machen Sie beruflich? — Sind Sie verheiratet?

Modèle complet de présentation pour Mamadou :
"Guten Tag! Ich heiße Mamadou Diallo. Ich komme aus dem Senegal, aus Dakar. Ich wohne jetzt in Frankfurt. Ich bin 32 Jahre alt. Ich bin Elektriker von Beruf. Ich bin verheiratet und habe zwei Kinder."

Conseils Goethe A1 : ce qui est évalué à l'oral, les erreurs à éviter.

**5 exercices :**
1. Quelle question demande le lieu d'origine ?
2. Comment répondre à "Wie alt sind Sie ?" si on a 28 ans ?
3. "Je suis marié et j'ai un enfant" → traduction
4. Quelle formule utiliser pour saluer formellement ?
5. "Was machen Sie beruflich?" veut dire ?

---

### Leçon 22 : Nach dem Weg fragen (Demander son chemin)
**Contenu :**
Vocabulaire de direction : geradeaus, links, rechts, die erste/zweite Straße, die Kreuzung, die Ampel, der Bahnhof, das Rathaus, die Ausländerbehörde, die U-Bahn, der Bus
Dialogue : Kofi demande comment aller à l'Ausländerbehörde depuis le S-Bahnhof
Phrases clés : Entschuldigung, wie komme ich zur...? / Wo ist die...? / Ist es weit? / Wie weit ist es?

**5 exercices de compréhension et production**

---

### Leçon 23 : Im Geschäft und im Restaurant (Dans un magasin/restaurant)
**Contenu :**
2 situations pratiques :
1. Au supermarché : demander où est quelque chose, payer
2. Au restaurant : commander, demander la carte, payer l'addition
Phrases : Was kostet das? / Haben Sie...? / Ich hätte gern... / Die Speisekarte bitte. / Zahlen bitte. / Zusammen oder getrennt?

**5 exercices de dialogue**

---

## LEÇONS SCHREIBEN (2 leçons)

### Leçon 24 : Formulare ausfüllen (Remplir des formulaires)
**Contenu :**
Guide complet pour remplir un formulaire administratif allemand :
- Abréviations courantes : Str. = Straße, Nr. = Nummer, Jh. = Jahrhundert, Geb.-Datum = Geburtsdatum
- Champs obligatoires sur un formulaire visa
- Exemple : formulaire de demande d'inscription à un cours de langue (Anmeldeformular)

Modèle rempli pour Amina Touré, née le 12.08.1995, Abidjan, ivorienne, célibataire, serveuse, habitant Berlin.

**5 exercices basés sur la lecture et compréhension du formulaire**

---

### Leçon 25 : Eine kurze Nachricht schreiben (Écrire un message court)
**Contenu :**
3 modèles de messages courts à écrire :
1. SMS pour confirmer un rendez-vous : "Guten Tag, ich bestätige meinen Termin am Montag, den 10. März um 9 Uhr. Mit freundlichen Grüßen, Mamadou Diallo."
2. Note pour son voisin : horaires, clé, problème
3. Demande de renseignement par email (très simple)

Formules utiles : Sehr geehrte Damen und Herren / Mit freundlichen Grüßen / Ich schreibe wegen... / Könnten Sie mir sagen...?

**5 exercices :**
1. Quelle formule utiliser pour terminer un email formel ?
2. Comment confirmer un rendez-vous par SMS ?
3. "Je vous écris au sujet de ma demande de visa" → traduction
4. Quelle est la formule de politesse formelle en début d'email ?
5. Compléter le message : "Sehr geehrte Damen und Herren, ich ___ Mamadou Diallo..."

---

Génère maintenant le JSON des 5 leçons. Commence par `[` et termine par `]`.
[
  {
    "level": "A1",
    "skill": "SPRECHEN",
    "exam_type": "GOETHE",
    "title": "Sich vorstellen auf Deutsch — Se présenter en allemand",
    "intro": "La présentation de soi est l'exercice central de l'examen oral du Goethe-Zertifikat A1. L'examinateur vous posera des questions simples sur votre identité, votre famille et votre profession. Cette leçon vous donne un modèle complet à mémoriser et à adapter à votre situation personnelle.",
    "content": "<h3>Les questions clés et leurs réponses</h3><table border='1' cellpadding='8' style='border-collapse:collapse;width:100%;'><tr><th>Question</th><th>Traduction</th><th>Réponse modèle</th></tr><tr><td><strong>Wie heißen Sie?</strong></td><td>Comment vous appelez-vous ?</td><td>Ich heiße Mamadou Diallo.</td></tr><tr><td><strong>Woher kommen Sie?</strong></td><td>D'où venez-vous ?</td><td>Ich komme aus dem Senegal, aus Dakar.</td></tr><tr><td><strong>Wo wohnen Sie?</strong></td><td>Où habitez-vous ?</td><td>Ich wohne jetzt in Frankfurt.</td></tr><tr><td><strong>Wie alt sind Sie?</strong></td><td>Quel âge avez-vous ?</td><td>Ich bin 32 Jahre alt.</td></tr><tr><td><strong>Was machen Sie beruflich?</strong></td><td>Que faites-vous comme métier ?</td><td>Ich bin Elektriker von Beruf.</td></tr><tr><td><strong>Sind Sie verheiratet?</strong></td><td>Êtes-vous marié(e) ?</td><td>Ja, ich bin verheiratet und habe zwei Kinder.</td></tr></table><h3>Modèle complet de présentation — Mamadou</h3><blockquote><p><em>« Guten Tag! Ich heiße Mamadou Diallo. Ich komme aus dem Senegal, aus Dakar. Ich wohne jetzt in Frankfurt. Ich bin 32 Jahre alt. Ich bin Elektriker von Beruf. Ich bin verheiratet und habe zwei Kinder. »</em></p><p><strong>Traduction :</strong> Bonjour ! Je m'appelle Mamadou Diallo. Je viens du Sénégal, de Dakar. J'habite maintenant à Francfort. J'ai 32 ans. Je suis électricien de métier. Je suis marié et j'ai deux enfants.</p></blockquote><h3>Adaptez la présentation à votre situation</h3><ul><li><em>Ich heiße <strong>Fatou Camara</strong>. Ich komme aus <strong>Guinea</strong>. Ich wohne in <strong>München</strong>.</em></li><li><em>Ich bin <strong>25</strong> Jahre alt. Ich bin <strong>Krankenpflegerin</strong> von Beruf.</em></li><li><em>Ich bin <strong>ledig</strong> und habe <strong>keine Kinder</strong>.</em></li></ul><h3>Conseils pour l'examen oral Goethe A1</h3><ul><li>Parlez lentement et clairement — la vitesse n'est pas évaluée</li><li>Utilisez toujours <strong>Sie</strong> (vouvoiement) avec l'examinateur</li><li>Si vous ne comprenez pas, dites : <strong>Können Sie das bitte wiederholen?</strong> (Pouvez-vous répéter ?)</li><li>Erreur fréquente : ne dites PAS « <em>Ich habe 32 Jahre</em> » mais « <em>Ich bin 32 Jahre alt</em> »</li><li>Ne dites PAS « <em>Ich komme von Senegal</em> » mais « <em>Ich komme aus dem Senegal</em> »</li></ul>",
    "exercises": [
      {
        "question_text": "Quelle question pose l'examinateur pour savoir d'où vous venez ?",
        "option_a": "Wo wohnen Sie?",
        "option_b": "Wie heißen Sie?",
        "option_c": "Woher kommen Sie?",
        "option_d": "Was machen Sie beruflich?",
        "correct_option": "C",
        "explanation": "« Woher kommen Sie? » signifie « D'où venez-vous ? ». « Woher » = d'où. La réponse type est : « Ich komme aus [pays/ville]. » Exemple : Ich komme aus Kamerun, aus Yaoundé. À ne pas confondre avec « Wo wohnen Sie? » (Où habitez-vous ?) qui demande l'adresse actuelle."
      },
      {
        "question_text": "Comment répondre correctement à « Wie alt sind Sie? » si on a 28 ans ?",
        "option_a": "Ich habe 28 Jahre.",
        "option_b": "Ich bin 28 Jahre alt.",
        "option_c": "Ich bin alt 28 Jahre.",
        "option_d": "Mein Alter ist 28.",
        "correct_option": "B",
        "explanation": "La formule correcte est « Ich bin 28 Jahre alt. » — J'ai 28 ans (littéralement : Je suis âgé de 28 ans). C'est une erreur très fréquente des francophones de dire « Ich habe 28 Jahre » sur le modèle du français « j'ai 28 ans ». En allemand, on utilise le verbe « sein » (être), pas « haben » (avoir)."
      },
      {
        "question_text": "Comment traduire « Je suis marié(e) et j'ai un enfant » en allemand ?",
        "option_a": "Ich bin verheiratet und habe ein Kind.",
        "option_b": "Ich bin verheiratet und bin ein Kind.",
        "option_c": "Ich habe verheiratet und habe ein Kind.",
        "option_d": "Ich bin ledig und habe ein Kind.",
        "correct_option": "A",
        "explanation": "« Ich bin verheiratet und habe ein Kind. » est la traduction correcte. « verheiratet » = marié(e) avec le verbe « sein » (être). « ein Kind haben » = avoir un enfant avec le verbe « haben ». « ledig » = célibataire, donc la réponse D est incorrecte sur le plan du sens."
      },
      {
        "question_text": "Quelle formule utiliser pour saluer formellement un examinateur ou un agent administratif ?",
        "option_a": "Hallo!",
        "option_b": "Tschüss!",
        "option_c": "Hi!",
        "option_d": "Guten Tag!",
        "correct_option": "D",
        "explanation": "« Guten Tag! » est la formule de salutation formelle de la journée, appropriée pour un examen, un bureau administratif ou toute situation professionnelle. « Hallo » et « Hi » sont informels (entre amis). « Tschüss » signifie « Au revoir » et ne s'utilise pas pour saluer."
      },
      {
        "question_text": "Que signifie la question « Was machen Sie beruflich? » ?",
        "option_a": "Qu'est-ce que vous aimez faire ?",
        "option_b": "Quel est votre pays d'origine ?",
        "option_c": "Où travaillez-vous ?",
        "option_d": "Que faites-vous comme métier ?",
        "correct_option": "D",
        "explanation": "« Was machen Sie beruflich? » signifie « Que faites-vous comme métier / profession ? ». « beruflich » = professionnellement, « der Beruf » = le métier. La réponse type est : « Ich bin [métier] von Beruf. » Exemple : Ich bin Elektriker von Beruf — Je suis électricien de métier."
      }
    ]
  },
  {
    "level": "A1",
    "skill": "SPRECHEN",
    "exam_type": "GOETHE",
    "title": "Nach dem Weg fragen — Demander son chemin",
    "intro": "Savoir demander et comprendre des indications de chemin est une compétence orale essentielle pour votre vie quotidienne en Allemagne. Que ce soit pour trouver l'Ausländerbehörde, la gare ou votre lieu de travail, cette leçon vous donne tous les outils pour vous orienter et communiquer.",
    "content": "<h3>Vocabulaire de direction — Richtungswörter</h3><table border='1' cellpadding='8' style='border-collapse:collapse;width:100%;'><tr><th>Allemand</th><th>Français</th></tr><tr><td><strong>geradeaus</strong></td><td>tout droit</td></tr><tr><td><strong>links</strong></td><td>à gauche</td></tr><tr><td><strong>rechts</strong></td><td>à droite</td></tr><tr><td><strong>die erste Straße links</strong></td><td>la première rue à gauche</td></tr><tr><td><strong>die zweite Straße rechts</strong></td><td>la deuxième rue à droite</td></tr><tr><td><strong>die Kreuzung</strong></td><td>le carrefour</td></tr><tr><td><strong>die Ampel</strong></td><td>le feu (tricolore)</td></tr><tr><td><strong>der Bahnhof</strong></td><td>la gare</td></tr><tr><td><strong>das Rathaus</strong></td><td>la mairie</td></tr><tr><td><strong>die U-Bahn</strong></td><td>le métro</td></tr></table><h3>Phrases clés pour demander son chemin</h3><ul><li><em><strong>Entschuldigung, wie komme ich zur Ausländerbehörde?</strong></em> — Excusez-moi, comment aller à l'office des étrangers ?</li><li><em><strong>Wo ist die Ausländerbehörde, bitte?</strong></em> — Où est l'office des étrangers, s'il vous plaît ?</li><li><em><strong>Ist es weit?</strong></em> — Est-ce loin ?</li><li><em><strong>Wie weit ist es?</strong></em> — C'est à quelle distance ?</li><li><em><strong>Kann ich zu Fuß gehen?</strong></em> — Puis-je y aller à pied ?</li></ul><h3>Dialogue modèle — Kofi demande son chemin</h3><blockquote><p><strong>Kofi:</strong> Entschuldigung! Wie komme ich zur Ausländerbehörde?</p><p><strong>Passantin:</strong> Gehen Sie hier geradeaus bis zur Ampel. Dann biegen Sie links ab. Die Ausländerbehörde ist die zweite Straße rechts. Sie sehen ein großes Gebäude.</p><p><strong>Kofi:</strong> Ist es weit?</p><p><strong>Passantin:</strong> Nein, ungefähr fünf Minuten zu Fuß.</p><p><strong>Kofi:</strong> Vielen Dank!</p><p><strong>Passantin:</strong> Bitte sehr. Guten Erfolg!</p></blockquote><h3>Traduction du dialogue</h3><blockquote><p><em>Kofi : Excusez-moi ! Comment puis-je aller à l'Ausländerbehörde ?<br>Passante : Allez tout droit jusqu'au feu. Ensuite tournez à gauche. L'Ausländerbehörde est la deuxième rue à droite. Vous verrez un grand bâtiment.<br>Kofi : Est-ce loin ?<br>Passante : Non, environ cinq minutes à pied.<br>Kofi : Merci beaucoup !<br>Passante : Je vous en prie. Bonne chance !</em></p></blockquote><h3>Répondre à une indication de direction</h3><ul><li>Pour confirmer : <strong>Verstanden, danke!</strong> — Compris, merci !</li><li>Pour demander de répéter : <strong>Können Sie das bitte wiederholen?</strong> — Pouvez-vous répéter, s'il vous plaît ?</li><li>Pour remercier : <strong>Vielen Dank für Ihre Hilfe!</strong> — Merci beaucoup pour votre aide !</li></ul>",
    "exercises": [
      {
        "question_text": "Kofi veut demander poliment où est la gare. Quelle phrase utilise-t-il ?",
        "option_a": "Bahnhof wo?",
        "option_b": "Ich möchte Bahnhof.",
        "option_c": "Entschuldigung, wo ist der Bahnhof?",
        "option_d": "Wie heißt der Bahnhof?",
        "correct_option": "C",
        "explanation": "La formule correcte est « Entschuldigung, wo ist der Bahnhof? » — Excusez-moi, où est la gare ? « Entschuldigung » sert à aborder poliment un inconnu. « der Bahnhof » = la gare (masculin). On peut aussi dire « Wie komme ich zum Bahnhof? » (Comment puis-je aller à la gare ?)."
      },
      {
        "question_text": "La passante dit à Ibrahima : « Gehen Sie geradeaus. » Que doit-il faire ?",
        "option_a": "Tourner à gauche",
        "option_b": "S'arrêter",
        "option_c": "Tourner à droite",
        "option_d": "Aller tout droit",
        "correct_option": "D",
        "explanation": "« Gehen Sie geradeaus » signifie « Allez tout droit ». « geradeaus » = tout droit. C'est l'une des indications les plus fréquentes. Les autres directions : « links » = à gauche, « rechts » = à droite, « zurück » = en arrière."
      },
      {
        "question_text": "Comment demande-t-on « Est-ce loin ? » en allemand ?",
        "option_a": "Wie lange dauert das?",
        "option_b": "Wo ist das?",
        "option_c": "Ist es weit?",
        "option_d": "Wie viel kostet das?",
        "correct_option": "C",
        "explanation": "« Ist es weit? » signifie « Est-ce loin ? ». « weit » = loin. C'est une question très utile pour savoir si on peut y aller à pied. La réponse peut être : « Nein, nicht weit. Circa fünf Minuten zu Fuß. » — Non, pas loin. Environ cinq minutes à pied."
      },
      {
        "question_text": "La passante dit : « Biegen Sie an der Ampel links ab. » Que signifie « die Ampel » ?",
        "option_a": "Le carrefour",
        "option_b": "Le feu tricolore",
        "option_c": "Le panneau de signalisation",
        "option_d": "Le rond-point",
        "correct_option": "B",
        "explanation": "« die Ampel » = le feu tricolore (feu de signalisation). « Biegen Sie links ab » = tournez à gauche. La phrase complète signifie : « Tournez à gauche au feu. » C'est une des indications les plus fréquentes en Allemagne. « die Kreuzung » = le carrefour, « der Kreisverkehr » = le rond-point."
      },
      {
        "question_text": "Amina n'a pas compris les indications. Que dit-elle pour demander à la personne de répéter ?",
        "option_a": "Auf Wiedersehen!",
        "option_b": "Ich verstehe nicht Deutsch.",
        "option_c": "Können Sie das bitte wiederholen?",
        "option_d": "Wo wohnen Sie?",
        "correct_option": "C",
        "explanation": "« Können Sie das bitte wiederholen? » signifie « Pouvez-vous répéter cela, s'il vous plaît ? ». C'est une phrase essentielle à mémoriser pour l'examen oral et pour la vie quotidienne. On peut aussi dire plus simplement : « Noch einmal bitte! » — Encore une fois, s'il vous plaît !"
      }
    ]
  },
  {
    "level": "A1",
    "skill": "SPRECHEN",
    "exam_type": "GOETHE",
    "title": "Im Geschäft und im Restaurant — Dans un magasin et au restaurant",
    "intro": "Faire ses courses et commander au restaurant sont des situations incontournables de la vie quotidienne en Allemagne. Cette leçon vous donne les phrases essentielles pour interagir avec les vendeurs et les serveurs avec confiance, que vous soyez au supermarché ou dans un restaurant.",
    "content": "<h3>Situation 1 — Au supermarché (Im Supermarkt)</h3><blockquote><p><strong>Fatou:</strong> Entschuldigung, wo finde ich den Reis?</p><p><strong>Mitarbeiter:</strong> Der Reis ist in Gang 3, auf der linken Seite.</p><p><strong>Fatou:</strong> Danke! Und haben Sie auch Halal-Fleisch?</p><p><strong>Mitarbeiter:</strong> Ja, das Fleisch ist im Kühlregal, Gang 5.</p><p><strong>Fatou:</strong> Perfekt. Was kostet dieses Öl hier?</p><p><strong>Mitarbeiter:</strong> Das kostet 2 Euro 99.</p><p><strong>Fatou:</strong> Gut, ich nehme es. Vielen Dank!</p><p>[An der Kasse — À la caisse]</p><p><strong>Kassiererin:</strong> Das macht zusammen 12 Euro 45.</p><p><strong>Fatou:</strong> Kann ich mit Karte zahlen?</p><p><strong>Kassiererin:</strong> Ja, natürlich. Bitte.</p></blockquote><h3>Phrases utiles au supermarché</h3><ul><li><em><strong>Wo finde ich...?</strong></em> — Où puis-je trouver... ?</li><li><em><strong>Haben Sie...?</strong></em> — Avez-vous... ?</li><li><em><strong>Was kostet das?</strong></em> — Combien ça coûte ?</li><li><em><strong>Ich nehme das.</strong></em> — Je prends ça.</li><li><em><strong>Kann ich mit Karte zahlen?</strong></em> — Puis-je payer par carte ?</li></ul><h3>Situation 2 — Au restaurant (Im Restaurant)</h3><blockquote><p><strong>Moussa:</strong> Guten Abend! Einen Tisch für zwei Personen, bitte.</p><p><strong>Kellner:</strong> Guten Abend! Ja, natürlich. Kommen Sie bitte.</p><p><strong>Moussa:</strong> Danke. Die Speisekarte bitte.</p><p><strong>Kellner:</strong> Hier ist die Speisekarte. Möchten Sie etwas trinken?</p><p><strong>Moussa:</strong> Ja, ich hätte gern ein Wasser und meine Frau möchte einen Orangensaft.</p><p><strong>Kellner:</strong> Und zum Essen?</p><p><strong>Moussa:</strong> Ich nehme das Hähnchen mit Reis. Und meine Frau nimmt die Nudelsuppe.</p><p><strong>Kellner:</strong> Sehr gut. Kommt sofort!</p><p>[Später — Plus tard]</p><p><strong>Moussa:</strong> Zahlen bitte!</p><p><strong>Kellner:</strong> Das macht 24 Euro 50. Zusammen oder getrennt?</p><p><strong>Moussa:</strong> Zusammen, bitte.</p></blockquote><h3>Phrases utiles au restaurant</h3><ul><li><em><strong>Einen Tisch für... Personen, bitte.</strong></em> — Une table pour ... personnes, s'il vous plaît.</li><li><em><strong>Die Speisekarte bitte.</strong></em> — La carte, s'il vous plaît.</li><li><em><strong>Ich hätte gern...</strong></em> — J'aimerais... (plus poli que « ich möchte »)</li><li><em><strong>Zahlen bitte!</strong></em> — L'addition, s'il vous plaît !</li><li><em><strong>Zusammen oder getrennt?</strong></em> — Ensemble ou séparément ?</li></ul>",
    "exercises": [
      {
        "question_text": "Fatou cherche le riz au supermarché. Quelle question pose-t-elle au vendeur ?",
        "option_a": "Was kostet der Reis?",
        "option_b": "Wo finde ich den Reis?",
        "option_c": "Haben Sie Reis?",
        "option_d": "Ich möchte Reis kaufen.",
        "correct_option": "B",
        "explanation": "« Wo finde ich den Reis? » = Où puis-je trouver le riz ? C'est la question la plus naturelle pour demander l'emplacement d'un produit en magasin. « den Reis » = le riz à l'accusatif (masculin). On peut aussi dire « Wo ist der Reis? » — Où est le riz ? Les deux formules sont correctes."
      },
      {
        "question_text": "À la caisse, Fatou veut payer par carte. Que dit-elle ?",
        "option_a": "Ich habe kein Geld.",
        "option_b": "Das ist zu teuer.",
        "option_c": "Kann ich mit Karte zahlen?",
        "option_d": "Was macht das?",
        "correct_option": "C",
        "explanation": "« Kann ich mit Karte zahlen? » = Puis-je payer par carte ? « mit Karte » = par carte. En Allemagne, bien que la carte soit de plus en plus acceptée, certains magasins et petits commerces préfèrent encore le liquide (Bargeld). Il est utile de poser la question à l'avance."
      },
      {
        "question_text": "Au restaurant, Moussa veut voir le menu. Que demande-t-il ?",
        "option_a": "Was kostet das Essen?",
        "option_b": "Ich möchte zahlen.",
        "option_c": "Die Speisekarte bitte.",
        "option_d": "Haben Sie einen Tisch?",
        "correct_option": "C",
        "explanation": "« Die Speisekarte bitte. » = La carte / le menu, s'il vous plaît. « die Speisekarte » = la carte du restaurant (Speise = plat, Karte = carte). C'est une formule directe et poli. On peut aussi dire « Könnten wir die Speisekarte haben? » dans un contexte plus formel."
      },
      {
        "question_text": "Le serveur demande à Moussa : « Zusammen oder getrennt? » Que veut-il dire ?",
        "option_a": "Vous mangez ensemble ou séparément ?",
        "option_b": "Vous payez ensemble ou séparément ?",
        "option_c": "Vous voulez de la sauce ou pas ?",
        "option_d": "Vous avez fini ou pas ?",
        "correct_option": "B",
        "explanation": "« Zusammen oder getrennt? » = Vous payez ensemble ou séparément ? C'est la question que pose le serveur au moment de l'addition. « zusammen » = ensemble (une seule note), « getrennt » = séparément (chacun paie sa part). En Allemagne, il est courant de payer séparément (getrennt)."
      },
      {
        "question_text": "Comment Moussa commande-t-il poliment un verre d'eau au restaurant ?",
        "option_a": "Ich will ein Wasser.",
        "option_b": "Wasser, sofort!",
        "option_c": "Geben Sie mir Wasser.",
        "option_d": "Ich hätte gern ein Wasser, bitte.",
        "correct_option": "D",
        "explanation": "« Ich hätte gern ein Wasser, bitte. » est la formule la plus polie pour commander. « ich hätte gern » = j'aimerais (forme du subjonctif II, très utilisée pour les commandes polies). « Ich will » est grammaticalement correct mais sonne trop direct/impoli dans un restaurant. Toujours ajouter « bitte » !"
      }
    ]
  },
  {
    "level": "A1",
    "skill": "SCHREIBEN",
    "exam_type": "GOETHE",
    "title": "Formulare ausfüllen — Remplir des formulaires administratifs",
    "intro": "En Allemagne, vous devrez remplir de nombreux formulaires : inscription à un cours de langue, demande de logement, ouverture de compte bancaire, dossier d'immigration. Cette leçon vous apprend à comprendre et remplir correctement ces documents essentiels grâce à un exemple complet.",
    "content": "<h3>Abréviations courantes sur les formulaires allemands</h3><table border='1' cellpadding='8' style='border-collapse:collapse;width:100%;'><tr><th>Abréviation</th><th>Signification complète</th><th>Traduction</th></tr><tr><td><strong>Str.</strong></td><td>Straße</td><td>Rue</td></tr><tr><td><strong>Nr.</strong></td><td>Nummer</td><td>Numéro</td></tr><tr><td><strong>Geb.-Datum</strong></td><td>Geburtsdatum</td><td>Date de naissance</td></tr><tr><td><strong>Tel.</strong></td><td>Telefonnummer</td><td>Numéro de téléphone</td></tr><tr><td><strong>PLZ</strong></td><td>Postleitzahl</td><td>Code postal</td></tr><tr><td><strong>Jh.</strong></td><td>Jahrhundert</td><td>Siècle</td></tr><tr><td><strong>m/w/d</strong></td><td>männlich/weiblich/divers</td><td>masculin/féminin/autre</td></tr></table><h3>Formulaire d'inscription — Anmeldeformular (exemple fictif)</h3><table border='1' cellpadding='8' style='border-collapse:collapse;width:100%;'><tr><td><strong>Name (Nachname)</strong></td><td>TOURÉ</td></tr><tr><td><strong>Vorname</strong></td><td>Amina</td></tr><tr><td><strong>Geb.-Datum</strong></td><td>12.08.1995</td></tr><tr><td><strong>Geburtsort</strong></td><td>Abidjan</td></tr><tr><td><strong>Staatsangehörigkeit</strong></td><td>ivorisch</td></tr><tr><td><strong>Geschlecht (m/w/d)</strong></td><td>w</td></tr><tr><td><strong>Adresse (Str. + Nr.)</strong></td><td>Lindenstraße 7</td></tr><tr><td><strong>PLZ + Ort</strong></td><td>10115 Berlin</td></tr><tr><td><strong>Tel.</strong></td><td>+49 162 9876543</td></tr><tr><td><strong>E-Mail</strong></td><td>amina.toure@gmail.com</td></tr><tr><td><strong>Familienstand</strong></td><td>ledig</td></tr><tr><td><strong>Beruf</strong></td><td>Kellnerin</td></tr><tr><td><strong>Kursname</strong></td><td>Deutsch A1 — Integrationskurs</td></tr></table><h3>Points importants à retenir</h3><ul><li>La date s'écrit toujours <strong>JJ.MM.JJJJ</strong> en Allemagne (ex : 12.08.1995)</li><li>Pour le code postal (PLZ), il faut toujours 5 chiffres</li><li><strong>Geschlecht :</strong> m = männlich (masculin), w = weiblich (féminin), d = divers</li><li>L'adresse s'écrit : Nom de rue + numéro (ex: Lindenstraße 7, pas le 7 Lindenstraße)</li><li>La nationalité s'écrit en minuscule comme adjectif : <em>ivorisch, senegalesisch, kamerunisch</em></li></ul>",
    "exercises": [
      {
        "question_text": "Sur le formulaire d'Amina, que signifie l'abréviation « PLZ » ?",
        "option_a": "Numéro de téléphone",
        "option_b": "Lieu de naissance",
        "option_c": "Code postal",
        "option_d": "Numéro de dossier",
        "correct_option": "C",
        "explanation": "« PLZ » = Postleitzahl = code postal. En Allemagne, le code postal comporte toujours 5 chiffres. Sur le formulaire d'Amina : PLZ 10115 Berlin. Le code postal précède toujours le nom de la ville. C'est une abréviation à connaître absolument pour remplir tout formulaire d'adresse."
      },
      {
        "question_text": "Amina est née le 12 août 1995. Comment doit-elle écrire sa date de naissance sur le formulaire ?",
        "option_a": "1995-08-12",
        "option_b": "12/08/95",
        "option_c": "August 12, 1995",
        "option_d": "12.08.1995",
        "correct_option": "D",
        "explanation": "En Allemagne, les dates s'écrivent dans le format JJ.MM.JJJJ avec des points : 12.08.1995. L'ordre est Jour-Mois-Année. Le format international avec tirets (1995-08-12) ou barres (12/08/95) n'est pas utilisé sur les formulaires officiels allemands."
      },
      {
        "question_text": "Amina est célibataire. Que doit-elle écrire dans le champ « Familienstand » ?",
        "option_a": "verheiratet",
        "option_b": "ledig",
        "option_c": "geschieden",
        "option_d": "verwitwet",
        "correct_option": "B",
        "explanation": "« ledig » = célibataire. C'est la mention correcte pour le champ « Familienstand » (situation matrimoniale) quand on n'est pas marié(e). Sur le formulaire d'Amina, on voit bien « ledig » dans ce champ. « verheiratet » = marié(e), « geschieden » = divorcé(e), « verwitwet » = veuf/veuve."
      },
      {
        "question_text": "Que signifie « w » dans le champ « Geschlecht (m/w/d) » d'Amina ?",
        "option_a": "Masculin",
        "option_b": "Autre genre",
        "option_c": "Féminin",
        "option_d": "Non précisé",
        "correct_option": "C",
        "explanation": "Dans le champ « Geschlecht » (genre/sexe), « w » = weiblich = féminin. « m » = männlich = masculin, « d » = divers = autre. Cette notation à trois options est devenue obligatoire sur les formulaires officiels allemands depuis 2018 pour reconnaître les personnes ne s'identifiant ni homme ni femme."
      },
      {
        "question_text": "Amina est serveuse. Quelle est la forme féminine correcte à écrire dans le champ « Beruf » ?",
        "option_a": "Kellner",
        "option_b": "Kellnerinnen",
        "option_c": "die Kellner",
        "option_d": "Kellnerin",
        "correct_option": "D",
        "explanation": "La forme féminine de « Kellner » (serveur) est « Kellnerin » (serveuse). En allemand, on ajoute « -in » pour former le féminin de la plupart des métiers. Sur un formulaire, on écrit le métier sans article. « Kellnerinnen » = les serveuses (pluriel), ce qui est incorrect au singulier."
      }
    ]
  },
  {
    "level": "A1",
    "skill": "SCHREIBEN",
    "exam_type": "GOETHE",
    "title": "Eine kurze Nachricht schreiben — Écrire un message court",
    "intro": "À l'examen Goethe A1, vous devrez peut-être écrire un court message ou remplir une partie de formulaire. Dans la vie quotidienne, vous devrez confirmer des rendez-vous, laisser des notes ou envoyer des emails simples. Cette leçon vous donne des modèles prêts à utiliser et les formules indispensables.",
    "content": "<h3>Message 1 — SMS de confirmation de rendez-vous</h3><blockquote><p>📱 <strong>SMS formel</strong><br><br>Guten Tag,<br>ich bestätige meinen Termin am Montag, den 10. März um 9 Uhr.<br>Mit freundlichen Grüßen,<br>Mamadou Diallo</p></blockquote><h3>Traduction et explications — Message 1</h3><ul><li><em>ich bestätige</em> — je confirme (verbe « bestätigen »)</li><li><em>meinen Termin</em> — mon rendez-vous (accusatif masculin)</li><li><em>am Montag, den 10. März</em> — le lundi 10 mars</li><li><em>um 9 Uhr</em> — à 9 heures</li><li><em>Mit freundlichen Grüßen</em> — Avec mes salutations cordiales (= Cordialement)</li></ul><h3>Message 2 — Note pour le voisin</h3><blockquote><p>📝 <strong>Note informelle</strong><br><br>Lieber Nachbar,<br>ich bin heute bis 18 Uhr nicht zu Hause. Mein Paket kommt heute Nachmittag. Können Sie das Paket für mich annehmen? Ich hole es heute Abend ab.<br>Vielen Dank!<br>Fatou, Wohnung 4</p></blockquote><h3>Traduction et explications — Message 2</h3><ul><li><em>Lieber Nachbar</em> — Cher voisin (informel)</li><li><em>ich bin nicht zu Hause</em> — je ne suis pas à la maison</li><li><em>das Paket annehmen</em> — réceptionner le colis</li><li><em>Ich hole es ab</em> — Je viendrai le chercher</li></ul><h3>Message 3 — Email simple de demande de renseignement</h3><blockquote><p>📧 <strong>Email formel</strong><br><br>Sehr geehrte Damen und Herren,<br><br>ich schreibe wegen meines Termins am 15. April. Könnten Sie mir sagen, welche Dokumente ich mitbringen soll?<br><br>Mit freundlichen Grüßen,<br>Kofi Mensah<br>Tel.: +49 176 12345678</p></blockquote><h3>Formules essentielles à mémoriser</h3><table border='1' cellpadding='8' style='border-collapse:collapse;width:100%;'><tr><th>Formule</th><th>Contexte</th><th>Traduction</th></tr><tr><td><strong>Sehr geehrte Damen und Herren,</strong></td><td>Début d'email formel</td><td>Madame, Monsieur,</td></tr><tr><td><strong>Lieber... / Liebe...</strong></td><td>Début de message informel</td><td>Cher.../Chère...</td></tr><tr><td><strong>Ich schreibe wegen...</strong></td><td>Objet du message</td><td>Je vous écris au sujet de...</td></tr><tr><td><strong>Könnten Sie mir sagen...?</strong></td><td>Demande polie</td><td>Pourriez-vous me dire... ?</td></tr><tr><td><strong>Mit freundlichen Grüßen,</strong></td><td>Fin d'email formel</td><td>Cordialement,</td></tr><tr><td><strong>Vielen Dank!</strong></td><td>Remerciement</td><td>Merci beaucoup !</td></tr></table>",
    "exercises": [
      {
        "question_text": "Quelle formule utilise-t-on pour terminer un email formel en allemand ?",
        "option_a": "Tschüss!",
        "option_b": "Bis bald!",
        "option_c": "Mit freundlichen Grüßen,",
        "option_d": "Liebe Grüße,",
        "correct_option": "C",
        "explanation": "« Mit freundlichen Grüßen, » = Cordialement / Avec mes salutations cordiales. C'est la formule de politesse standard pour terminer un email ou une lettre formelle en Allemagne. « Liebe Grüße » est informel (entre amis). « Tschüss » et « Bis bald » sont des formules orales informelles."
      },
      {
        "question_text": "Mamadou veut confirmer son rendez-vous du lundi 10 mars à 9h par SMS. Quelle phrase utilise-t-il ?",
        "option_a": "Ich habe einen Termin am Montag.",
        "option_b": "Ich bestätige meinen Termin am Montag, den 10. März um 9 Uhr.",
        "option_c": "Mein Termin ist gut.",
        "option_d": "Ich komme am Montag.",
        "correct_option": "B",
        "explanation": "« Ich bestätige meinen Termin am Montag, den 10. März um 9 Uhr. » est la formule complète et précise pour confirmer un rendez-vous. « bestätigen » = confirmer. Cette formulation donne toutes les informations nécessaires : le jour (Montag), la date (10. März) et l'heure (9 Uhr). C'est essentiel pour éviter tout malentendu administratif."
      },
      {
        "question_text": "Comment traduire « Je vous écris au sujet de ma demande de visa » en allemand ?",
        "option_a": "Ich schreibe für mein Visum.",
        "option_b": "Ich schreibe wegen meiner Visumsanfrage.",
        "option_c": "Ich habe ein Visum geschrieben.",
        "option_d": "Mein Visum ist eine Anfrage.",
        "correct_option": "B",
        "explanation": "« Ich schreibe wegen meiner Visumsanfrage. » = Je vous écris au sujet de ma demande de visa. « wegen » + génitif = au sujet de / à cause de. « die Visumsanfrage » = la demande de visa. C'est la formule standard pour introduire l'objet d'un email formel."
      },
      {
        "question_text": "Quelle est la formule de politesse formelle correcte pour commencer un email à l'Ausländerbehörde ?",
        "option_a": "Hallo!",
        "option_b": "Lieber Freund,",
        "option_c": "Sehr geehrte Damen und Herren,",
        "option_d": "Guten Tag,",
        "correct_option": "C",
        "explanation": "« Sehr geehrte Damen und Herren, » = Madame, Monsieur (formule très formelle). C'est la salutation standard quand on ne connaît pas le nom du destinataire. « Sehr geehrt » = très honoré(e). Si vous connaissez le nom : « Sehr geehrte Frau Müller, » ou « Sehr geehrter Herr Schmidt, ». « Guten Tag » peut être utilisé dans des emails semi-formels."
      },
      {
        "question_text": "Complétez le début de l'email : « Sehr geehrte Damen und Herren, ich ___ Mamadou Diallo. »",
        "option_a": "heiße",
        "option_b": "bin",
        "option_c": "habe",
        "option_d": "wohne",
        "correct_option": "A",
        "explanation": "La phrase complète est : « Ich heiße Mamadou Diallo. » — Je m'appelle Mamadou Diallo. « heißen » = s'appeler. C'est la façon standard de se présenter par écrit dans un email. On peut aussi écrire « Ich bin Mamadou Diallo » (Je suis...) mais « Ich heiße » est plus précis pour donner son nom."
      }
    ]
  }
]