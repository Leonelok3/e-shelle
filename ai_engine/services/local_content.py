"""Deterministic assistance grounded in supplied data; no synthetic credentials."""
from html import escape
import re


def resume_documents(candidate_context, offer_context='', language='fr'):
    labels = {
        'fr': ('Curriculum vitæ', 'Coordonnées et projet', 'Expériences professionnelles', 'Formation', 'Langues'),
        'en': ('Resume', 'Contact and career objective', 'Work experience', 'Education', 'Languages'),
        'de': ('Lebenslauf', 'Kontaktdaten und Berufsziel', 'Berufserfahrung', 'Ausbildung', 'Sprachen'),
        'bilingual': ('CV / Resume', 'Coordonnées / Contact', 'Expériences / Experience', 'Formation / Education', 'Langues / Languages'),
    }
    key = language if language in labels else 'fr'
    words = labels[key]
    blocks = re.split(r'===\s*[^=]+\s*===', candidate_context)
    first = candidate_context.splitlines()[0] if candidate_context.strip() else ''
    name = first.split(':', 1)[-1].strip() or ('Candidate' if key=='en' else 'Candidat')
    html = ['<!-- eshelle:local -->', '<article style="font-family:Arial,sans-serif;color:#172033;line-height:1.5">',
            f'<h1>{escape(name)}</h1><p>{words[0]}</p>']
    if key == 'de':
        # The existing Word exporter splits German documents at this marker.
        html.insert(1, '<!-- Rechte Spalte -->')
    for i, block in enumerate(blocks):
        lines = [line.strip().lstrip('- ') for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        html.append(f'<h2>{words[min(i+1,4)]}</h2>')
        html.extend(f'<p>{escape(line)}</p>' for line in lines)
    html.append('</article>')
    if key == 'de':
        letter = f'''Sehr geehrte Damen und Herren,

hiermit bewerbe ich mich um die ausgeschriebene Stelle. In meinem beigefügten Lebenslauf finden Sie meine bisherigen Tätigkeiten, meine Ausbildung und meine Sprachkenntnisse.

Gern erläutere ich Ihnen in einem persönlichen Gespräch, wie meine bisherigen Erfahrungen zu den Aufgaben dieser Stelle passen. Über eine Einladung zu einem Gespräch freue ich mich.

Mit freundlichen Grüßen
{name}'''
    elif key == 'en':
        letter = f'''Dear Hiring Team,

I am writing to apply for the advertised position. My enclosed resume presents my work experience, education and language skills using the information in my profile.

I would welcome the opportunity to explain how my background relates to the role and to learn more about your team's expectations. Thank you for considering my application.

Sincerely,
{name}'''
    else:
        letter = f'''Madame, Monsieur,

Je vous adresse ma candidature pour le poste proposé. Mon CV ci-joint présente mes expériences, ma formation et mes compétences linguistiques.

Je serais heureux de vous expliquer lors d’un entretien comment mon parcours peut répondre aux missions du poste et d’en apprendre davantage sur vos attentes. Je vous remercie pour l’attention portée à ma candidature.

Cordialement,
{name}'''
    if key == 'bilingual':
        letter += '\n\n--- English ---\n\n' + resume_documents(candidate_context, offer_context, 'en')[1]
    return ''.join(html), letter


INTERVIEW_QUESTIONS = {
    'fr': ["Présentez votre parcours et le poste que vous recherchez.", "Pourquoi ce poste vous intéresse-t-il ?", "Décrivez une situation où vous avez résolu un problème au travail.", "Donnez un exemple de travail en équipe et expliquez votre rôle.", "Comment organisez-vous vos tâches quand plusieurs demandes sont urgentes ?", "Quelle compétence souhaitez-vous développer pour ce poste ?", "Quelle question souhaitez-vous poser au recruteur ?"],
    'de': ["Bitte stellen Sie sich kurz vor und erklären Sie, warum Sie sich für diese Ausbildung interessieren.", "Was wissen Sie über diesen Beruf?", "Beschreiben Sie eine Situation, in der Sie ein Problem gelöst haben.", "Wie arbeiten Sie im Team? Bitte nennen Sie ein Beispiel.", "Wie gehen Sie mit Zeitdruck um?", "Welche Fähigkeiten möchten Sie während der Ausbildung entwickeln?", "Welche Fragen haben Sie an das Unternehmen?"],
}


def interview_question(history, language='fr'):
    questions = INTERVIEW_QUESTIONS[language]
    count = sum(1 for item in history if item.get('role') == 'user')
    if count >= len(questions):
        return 'Vielen Dank. Lesen Sie Ihre Antworten noch einmal und ergänzen Sie konkrete Beispiele.' if language=='de' else 'L’entretien guidé est terminé. Relisez vos réponses et ajoutez un exemple concret à chacune.'
    return questions[count]


def interview_review(history):
    answers = [item.get('content','') for item in history if item.get('role') == 'user']
    words = sum(len(str(answer).split()) for answer in answers)
    return (f'=== SCORE ===\nNon évalué automatiquement\n\n=== CORRECTIONS ===\n'
        f'Bilan guidé sans IA : {len(answers)} réponse(s), {words} mots au total. '
        'Aucune note linguistique ou correction individuelle n’est attribuée sans analyse IA.\n\n'
        '=== VOCABULAIRE ===\nZusammenarbeit : collaboration ; Verantwortung : responsabilité ; '
        'Berufserfahrung : expérience professionnelle.\n\n=== RECOMMANDATIONS ===\n'
        'Pour chaque réponse, vérifiez la présence d’une situation précise, de votre action et de son résultat. '
        'Relisez les temps verbaux et entraînez-vous à répondre à voix haute.')


def canada_guidance(message=''):
    return ("Mode guidé sans IA. Préparez votre objectif (emploi, études ou visite), votre parcours, "
        "vos résultats de langue et vos questions. Vérifiez les critères et les documents dans les pages officielles "
        "correspondant à votre situation : https://www.canada.ca/fr/immigration-refugies-citoyennete/services/immigrer-canada.html . "
        "Ce guide ne détermine pas votre admissibilité et ne prédit pas l’obtention d’un visa. "
        "Pour une candidature, commencez par compléter votre profil, relire votre CV et consulter la source de chaque offre.")


def offer_summary(offer):
    return (f'Fiche pratique (sans IA). {offer.title} — {offer.company}. '
        f'Lieu : {offer.city or "consulter la source"}. Salaire : {offer.salary_display}. '
        'Consultez l’annonce originale pour les exigences, les dates et la candidature. '
        'Préparez votre CV, vos justificatifs de formation et vos questions sur le poste. '
        'Cette annonce ne garantit ni recrutement international ni visa.')
