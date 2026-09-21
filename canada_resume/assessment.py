"""Original orientation questions. Not a standardized language examination."""
QUESTIONS = [
    ('a1', 'La bibliothèque ouvre à 9 h et ferme à 18 h. À quelle heure ouvre-t-elle ?', ['9 h', '18 h', '8 h'], 0, 'Le verbe « ouvre » indique le début des horaires.'),
    ('a1b', 'Complétez : « Nous … un rendez-vous demain. »', ['avez', 'avons', 'ont'], 1, 'Avec « nous », le verbe avoir devient « avons ».'),
    ('a2', '« Le rendez-vous de mardi est reporté à jeudi. » Quand aura-t-il lieu ?', ['Mardi', 'Mercredi', 'Jeudi'], 2, '« Reporté à jeudi » annonce la nouvelle date.'),
    ('a2b', 'Complétez : « Hier, elle … ses documents par courriel. »', ['enverra', 'a envoyé', 'envoie demain'], 1, '« Hier » appelle ici un événement passé : « a envoyé ».'),
    ('b1', '« Bien que le trajet soit long, elle préfère le train. » Quel lien exprime cette phrase ?', ['Une concession', 'Une conséquence', 'Une comparaison de prix'], 0, 'La préférence demeure malgré la longueur du trajet : c’est une concession.'),
    ('b1b', 'Choisissez la phrase correcte.', ['Si j’aurais le temps, je lirais.', 'Si j’avais le temps, je lirais.', 'Si j’avais le temps, je lirai hier.'], 1, 'Pour une hypothèse, on utilise ici si + imparfait, puis le conditionnel.'),
    ('b2', '« La mesure pourrait réduire les dépenses, à condition que sa mise en œuvre soit accompagnée. » Que dit l’auteur ?', ['Le résultat est certain.', 'Le résultat dépend d’une condition.', 'La mesure a déjà échoué.'], 1, '« Pourrait » et « à condition que » expriment un résultat possible, sous condition.'),
    ('b2b', 'Quel énoncé nuance une opinion ?', ['Cette solution est parfaite, sans exception.', 'Cette solution a des avantages ; toutefois, son coût reste à examiner.', 'Tout le monde pense la même chose.'], 1, '« Toutefois » introduit une réserve sans supprimer les avantages.'),
]


def score_answers(answers):
    feedback = []
    for key, question, options, correct, explanation in QUESTIONS:
        selected = answers.get(key)
        if selected not in ('0', '1', '2'):
            raise ValueError('Répondez à chaque question avant de valider le bilan.')
        feedback.append({'question': question, 'correct': int(selected) == correct,
                         'answer': options[correct], 'explanation': explanation})
    score = sum(item['correct'] for item in feedback)
    level = 'A1' if score < 3 else 'A2' if score < 5 else 'B1' if score < 7 else 'B2'
    return {'score': score, 'total': len(QUESTIONS), 'suggested_level': level, 'feedback': feedback}
