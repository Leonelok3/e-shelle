"""Finite, original practice bank. Never presented as an official exam or AI output."""
from html import escape

# Each entry: passage, focus, question, correct answer, three distractors, explanation.
DE = {
    'A1': ('Ich heiße Amina. Ich wohne in Berlin. Mein Deutschkurs beginnt um neun Uhr.', 'Se présenter et lire une heure', 'Wann beginnt der Kurs?', 'Um neun Uhr', ['Um acht Uhr', 'Um zehn Uhr', 'Am Abend'], '« um neun Uhr » signifie à neuf heures.'),
    'A2': ('Gestern hat Paul den Bus verpasst. Deshalb ist er zu Fuß zur Schule gegangen. Morgen möchte er früher aufstehen.', 'Raconter au passé composé', 'Warum ist Paul zu Fuß gegangen?', 'Er hat den Bus verpasst.', ['Er hat kein Fahrrad.', 'Die Schule war geschlossen.', 'Er wollte Sport machen.'], 'Le texte donne une cause explicite : Paul a manqué le bus. « Deshalb » introduit la conséquence.'),
    'B1': ('Obwohl Sara wenig Zeit hat, besucht sie einen Abendkurs. Sie möchte eine Ausbildung beginnen, für die sie bessere Deutschkenntnisse braucht. Wenn ihr Arbeitgeber zustimmt, wird sie früher Feierabend machen.', 'Concession et condition', 'Wovon hängt der frühere Feierabend ab?', 'Von der Zustimmung des Arbeitgebers.', ['Von der Kursgebühr.', 'Von einer Prüfung.', 'Vom Wetter.'], '« Wenn ihr Arbeitgeber zustimmt » pose la condition : l’accord de son employeur.'),
    'B2': ('Die Firma führt flexible Arbeitszeiten ein. Zwar begrüßen viele Beschäftigte die neue Regelung, doch einige befürchten, dass die Abstimmung im Team schwieriger wird. Die Leitung schlägt deshalb gemeinsame Kernzeiten vor, ohne die individuelle Zeiteinteilung vollständig einzuschränken.', 'Nuancer une proposition', 'Welchen Zweck haben die Kernzeiten?', 'Sie verbinden Zusammenarbeit und Flexibilität.', ['Sie schaffen flexible Arbeitszeiten ab.', 'Sie ersetzen die Teamleitung.', 'Sie verkürzen alle Arbeitstage.'], 'Les plages communes répondent au problème de coordination tout en conservant une part de liberté.'),
    'C1': ('Die Evaluation bescheinigt dem Pilotprojekt erhebliche Fortschritte, räumt jedoch ein, dass die Auswahl besonders motivierter Teilnehmender die Aussagekraft der Ergebnisse einschränkt. Eine flächendeckende Einführung wäre daher verfrüht, sofern nicht zuvor unter weniger günstigen Bedingungen vergleichbare Effekte nachgewiesen würden.', 'Distinguer résultat et portée', 'Worauf beruht der Vorbehalt gegenüber einer Ausweitung?', 'Die Ergebnisse sind möglicherweise nicht übertragbar.', ['Das Projekt hat keine Fortschritte erzielt.', 'Die Teilnehmenden waren unmotiviert.', 'Eine Evaluation fehlt vollständig.'], 'Le biais de sélection limite la généralisation. Les résultats positifs ne sont pas niés.'),
    'C2': ('Man feierte die Reform als Befreiung von bürokratischen Fesseln; dass fortan jede Ausnahme einer eigens eingerichteten Genehmigungsstelle vorzulegen war, galt dabei offenbar als vernachlässigbare Fußnote. Wer hierin einen Widerspruch erblickte, hatte, so hieß es, den Geist der Vereinfachung noch nicht erfasst.', 'Reconnaître l’ironie argumentative', 'Welche Haltung vermittelt der Text?', 'Er stellt die behauptete Vereinfachung ironisch infrage.', ['Er lobt die Reform uneingeschränkt.', 'Er fordert die Abschaffung aller Ausnahmen.', 'Er erklärt neutral ein Antragsverfahren.'], 'Le décalage entre « Befreiung » et une nouvelle instance d’autorisation révèle l’ironie ; la dernière phrase la renforce.'),
}
FR = {
    'A1': ('Bonjour Léa. Le cours commence à dix heures, dans la salle deux. Apporte ton cahier.', 'Repérer une information explicite', 'À quelle heure commence le cours ?', 'À dix heures', ['À deux heures', 'À midi', 'À huit heures'], 'Le message indique directement « à dix heures ».'),
    'A2': ('La bibliothèque sera fermée samedi pour des travaux. Vous pouvez rendre vos livres vendredi avant dix-huit heures ou lundi matin. La boîte de retour sera également fermée pendant les travaux.', 'Comprendre une annonce pratique', 'Quand peut-on rendre les livres ?', 'Lundi matin', ['Samedi dans la boîte', 'Samedi matin au comptoir', 'Vendredi à vingt heures'], 'Le lundi matin est explicitement proposé. La boîte est fermée samedi.'),
    'B1': ('Le covoiturage permet à Nadia de réduire ses dépenses. Pourtant, elle prend le train le mercredi, car ses horaires ne correspondent pas à ceux de ses collègues. Elle préfère cette organisation à l’achat d’une voiture.', 'Relier une décision à sa cause', 'Pourquoi Nadia prend-elle le train le mercredi ?', 'Ses horaires diffèrent de ceux de ses collègues.', ['Elle a acheté une voiture.', 'Le covoiturage est interdit.', 'Le train est toujours gratuit.'], 'La proposition introduite par « car » donne la raison ; aucune gratuité n’est annoncée.'),
    'B2': ('La municipalité souhaite agrandir les pistes cyclables. Les commerçants soutiennent le projet à condition que les livraisons restent possibles. Ils proposent donc des créneaux réservés, plutôt que le maintien permanent de toutes les places de stationnement.', 'Comprendre un accord sous condition', 'Quelle est la position des commerçants ?', 'Ils acceptent le projet avec un aménagement pour les livraisons.', ['Ils rejettent toutes les pistes.', 'Ils exigent davantage de parkings en permanence.', 'Ils veulent interdire les livraisons.'], '« À condition que » exprime une réserve précise, et non un rejet global.'),
    'C1': ('Si l’enquête révèle une corrélation entre autonomie et satisfaction professionnelle, elle ne permet pas d’établir que la première engendre la seconde. Il se pourrait que des conditions de travail favorables expliquent simultanément ces deux observations. Toute prescription générale fondée sur ce seul résultat serait donc prématurée.', 'Évaluer la portée d’un raisonnement', 'Pourquoi l’auteur écarte-t-il une prescription immédiate ?', 'Une autre variable pourrait expliquer la corrélation.', ['Aucune corrélation n’a été observée.', 'L’autonomie est nécessairement nuisible.', 'La satisfaction est impossible à mesurer.'], 'Une corrélation n’établit pas la causalité ; l’auteur envisage un facteur commun.'),
    'C2': ('On nous promettait une consultation exemplaire : chacun pourrait s’exprimer, pourvu qu’il souscrive aux conclusions arrêtées la veille. Rarement le pluralisme aura été célébré avec un tel souci d’en prévenir les inconvénients.', 'Interpréter une critique implicite', 'Que dénonce principalement ce passage ?', 'Une consultation dont le résultat est fixé à l’avance.', ['Une absence totale de participants.', 'La lenteur du dépouillement.', 'Des conclusions trop imprécises.'], 'La condition imposée vide la consultation de son sens ; la célébration du pluralisme est ironique.'),
}


def lesson(language, level, skill):
    bank = DE if language == 'de' else FR
    passage, focus, question, answer, distractors, explanation = bank[level]
    oral = skill in ('HOREN', 'co')
    production = skill in ('SPRECHEN', 'SCHREIBEN', 'ee', 'eo')
    content = ('<!-- eshelle:local -->'
        '<p>Atelier de la banque locale. Entraînement ciblé, indépendant des sujets officiels.</p>'
        f'<h3>{escape(focus)}</h3><p>{escape(passage)}</p>'
        '<h3>Méthode</h3><p>Repérez les informations, les connecteurs et le point de vue. '
        'Justifiez votre réponse par un passage précis, puis comparez avec le corrigé.</p>')
    if oral:
        content += '<p>Version avec transcription : lisez à voix haute, puis reformulez sans regarder le texte. Cet atelier ne mesure pas votre compréhension d’un audio inédit.</p>'
    if production:
        content += '<h3>À vous de produire</h3><p>Reformulez la situation dans la langue étudiée, puis proposez une réponse personnelle. Vérifiez le respect de la consigne, la cohérence, les accords et les temps. Le QCM sert seulement à vérifier la compréhension du modèle.</p>'
    options = [answer] + distractors
    # Stable spread of correct positions, without creating duplicate variants.
    offset = list(bank).index(level) % 4
    options = options[offset:] + options[:offset]
    exercise = dict(zip(('option_a','option_b','option_c','option_d'), options))
    exercise.update(question_text=question, audio_text=passage,
        correct_option='ABCD'[options.index(answer)], explanation=explanation)
    if language == 'fr' and production:
        exercise.update(question_text='Reformulez ce document puis exprimez votre réaction en français.',
            option_a='', option_b='', option_c='', option_d='', correct_option='A',
            explanation='Autoévaluation : informations fidèles au document, progression des idées, vocabulaire précis et correction grammaticale. Aucune note automatique de production.')
    return {'title': f'Atelier local {level} — {skill} — {focus}',
        'intro': 'Entraînement ciblé de la banque locale, avec corrigé explicatif.',
        'content': content, 'exercises': [exercise]}
