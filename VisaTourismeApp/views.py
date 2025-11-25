from io import BytesIO

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import get_template, render_to_string

from xhtml2pdf import pisa

from .forms import VisaTourismeForm
from .models import VisaTourismRequest


# -------------------------------------------------------------------
# PROMPT DU COACH IA (à utiliser si tu branches une API)
# -------------------------------------------------------------------
COACH_VISA_PROMPT = """
Tu es COACH VISA E-SHELLE, un assistant spécialisé dans la préparation de dossiers de visa tourisme
(Schengen, Royaume-Uni, États-Unis, Canada et autres pays).

RÔLE GÉNÉRAL
- Tu aides les utilisateurs à comprendre et améliorer leur DOSSIER DE VISA TOURISME.
- Tu expliques, reformules, proposes des stratégies concrètes.
- Tu restes toujours prudent : tu ne promets JAMAIS que le visa sera accepté.

OBJECTIFS :
1. Clarifier la situation de l’utilisateur avec des mots simples.
2. Expliquer pourquoi certains points sont considérés comme forts ou faibles.
3. Donner des actions concrètes pour améliorer le dossier (sans tricher ni falsifier).
4. Rassurer, mais rester honnête sur les risques.
5. Toujours encourager l’utilisateur à vérifier les informations sur le site officiel de l’ambassade ou du centre de visas.

CONTRAINTES :
- Tu ne donnes pas d’informations contraires aux lois ou règlements des visas.
- Tu déconseilles toute falsification (faux relevés, fausses attestations, faux billets, etc.).
- Tu peux aider à rédiger des textes (lettre d’explication, lettre de motivation, etc.) mais tu insistes sur la vérité.
- Tu ne garantis JAMAIS l’obtention du visa.

STYLE :
- Professionnel, bienveillant, clair et structuré.
- Français par défaut, anglais si l’utilisateur écrit clairement en anglais.
- Structure conseillée :
  1) Analyse rapide de ta situation
  2) Ce qui est positif dans ton dossier
  3) Ce qui peut poser problème
  4) Plan d’action concret
  5) Remarques importantes
"""


# -------------------------------------------------------------------
# OUTILS PDF & EMAIL
# -------------------------------------------------------------------
def render_to_pdf(template_src, context_dict=None):
    if context_dict is None:
        context_dict = {}
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse("Erreur lors de la génération du PDF", status=500)


def envoyer_plan_par_email(instance: VisaTourismRequest):
    """
    Envoie le plan de visa à l'email du client (si renseigné),
    en utilisant un template texte dédié.
    """
    if not instance.email:
        return

    sujet = "Votre plan de visa tourisme - E-SHELLE"
    contexte = {'result': instance}
    message = render_to_string('VisaTourismeApp/email_visa_plan.txt', contexte)

    expediteur = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@e-shelle.com')
    try:
        send_mail(
            sujet,
            message,
            expediteur,
            [instance.email],
            fail_silently=True,
        )
    except Exception:
        # On ignore l'erreur pour ne pas casser le flux utilisateur
        pass


# -------------------------------------------------------------------
# COACH IA : fonction d'appel à l'IA (à adapter avec ton provider)
# -------------------------------------------------------------------
def appelle_coach_ia(question: str, resume_dossier: str) -> str:
    """
    Cette fonction prépare le texte à envoyer à ton IA.
    Pour l'instant, elle renvoie une réponse “dummy” pour que le module fonctionne
    même sans connexion à une API. Tu pourras remplacer le bloc "TODO" par ton code
    OpenAI / autre.

    Exemples d’intégration (pseudo-code) :

    from openai import OpenAI
    client = OpenAI(api_key=...)

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": COACH_VISA_PROMPT},
            {"role": "user", "content": prompt_utilisateur},
        ],
    )
    return completion.choices[0].message.content
    """
    # On construit un prompt utilisateur complet :
    prompt_utilisateur = (
        "Résumé du dossier de visa :\n"
        + resume_dossier
        + "\n\nQuestion de l’utilisateur :\n"
        + question
    )

    # TODO : Remplacer ce bloc par un appel réel à ton IA
    reponse = (
        "Je suis le Coach Visa E-SHELLE. Pour l’instant, la connexion à l’IA n’est pas encore "
        "configurée dans le code, donc je ne peux donner qu’un message générique.\n\n"
        "Quand tu intégreras une API (ChatGPT, etc.), c’est ici que la vraie réponse du coach "
        "sera générée à partir de ton dossier et de ta question."
    )

    return reponse


# -------------------------------------------------------------------
# CONSTRUCTION DE L’ANALYSE
# -------------------------------------------------------------------
def construire_recommandations(instance: VisaTourismRequest):
    destination = instance.destination
    duree_sejour = instance.duree_sejour
    a_un_emploi = instance.a_un_emploi
    a_invitation = instance.a_invitation
    a_deja_voyage = instance.a_deja_voyage
    budget = instance.budget
    age = instance.age

    documents = [
        "Passeport valide (au moins 6 mois après la date de retour).",
        "Formulaire de demande de visa correctement rempli.",
        "Photo d’identité récente conforme au format de l’ambassade.",
        "Réservation de billet d’avion aller-retour.",
        "Réservation d’hôtel OU attestation d’hébergement.",
        "Assurance voyage couvrant la durée du séjour.",
        "Preuves de ressources financières (relevés bancaires, épargne, etc.).",
    ]

    points_forts = []
    points_faibles = []

    if a_un_emploi:
        documents += [
            "Attestation de travail / contrat de travail.",
            "Trois (3) dernières fiches de paie.",
            "Autorisation d’absence signée par l’employeur.",
        ]
        points_forts.append("Vous avez un emploi, ce qui renforce vos attaches dans votre pays.")
    else:
        documents += [
            "Justificatifs de revenus alternatifs (business, freelance, etc.).",
            "Si sponsorisé : lettre de prise en charge + justificatifs du sponsor.",
        ]
        points_faibles.append("Absence d’emploi : il faudra bien prouver vos attaches et votre retour.")

    if a_invitation:
        documents += [
            "Lettre d’invitation (famille / ami / entreprise / agence).",
            "Copie de la pièce d’identité ou titre de séjour de l’hébergeant.",
            "Justificatif de domicile de l’hébergeant.",
        ]
        points_forts.append("Lettre d’invitation disponible : cela renforce la crédibilité de votre séjour.")
    else:
        points_faibles.append("Aucune invitation : la réservation d’hôtel doit être cohérente avec vos moyens.")

    if a_deja_voyage:
        points_forts.append("Vous avez déjà voyagé : bon point pour la crédibilité de vos retours.")
    else:
        points_faibles.append("Premier voyage : bien insister sur vos attaches familiales et professionnelles.")

    if budget == 'faible':
        points_faibles.append(
            "Budget faible : attention, le compte bancaire doit montrer un minimum de fonds stables."
        )
    elif budget == 'eleve':
        points_forts.append(
            "Budget confortable : bon point pour prouver que vous pouvez financer le séjour."
        )

    remarques_destination = []

    if destination == 'schengen':
        remarques_destination.append(
            "Visa Schengen : déposez le dossier au consulat du pays où vous passez le plus de temps."
        )
        documents.append("Relevés bancaires des 3 à 6 derniers mois.")
    elif destination == 'usa':
        remarques_destination.append(
            "Visa USA (B1/B2) : compte en ligne, formulaire DS-160, paiement des frais, puis prise de RDV."
        )
    elif destination == 'uk':
        remarques_destination.append(
            "Visa UK : demande entièrement en ligne avant RDV au centre de biométrie."
        )
    elif destination == 'canada':
        remarques_destination.append(
            "Visa Canada : création de compte IRCC, téléchargement des documents, paiement en ligne."
        )
    else:
        remarques_destination.append(
            "Consultez le site officiel de l’ambassade pour les exigences spécifiques du pays choisi."
        )

    etapes = [
        "1. Vérifier sur le site officiel de l’ambassade la liste exacte des documents.",
        "2. Rassembler tous les originaux + copies lisibles.",
        "3. Remplir le formulaire de demande (en ligne ou papier).",
        "4. Payer les frais de visa selon la procédure indiquée.",
        "5. Prendre rendez-vous pour le dépôt au centre de visas / consulat.",
        "6. Se présenter au rendez-vous à l’heure avec un dossier parfaitement classé.",
    ]

    if duree_sejour == '30_90':
        etapes.append(
            "7. Pour les séjours longs (30 à 90 jours), détailler le programme de voyage et le financement."
        )

    conseils = [
        "Ne jamais falsifier un document : le risque d’interdiction de territoire est réel.",
        "Tout doit être cohérent : dates, réservations, montants sur le compte.",
        "Éviter les gros dépôts récents juste avant la demande de visa.",
        "Préparer des réponses simples et claires pour l’entretien éventuel.",
    ]

    score = 50

    if a_un_emploi:
        score += 15
    else:
        score -= 10

    if a_invitation:
        score += 10
    else:
        score -= 5

    if a_deja_voyage:
        score += 10

    if budget == 'faible':
        score -= 10
    elif budget == 'eleve':
        score += 5

    if age < 21:
        score -= 5

    score = max(5, min(95, score))

    if score >= 80:
        niveau_risque = "Dossier très solide (risque faible)"
    elif score >= 60:
        niveau_risque = "Dossier plutôt bon (risque modéré)"
    elif score >= 40:
        niveau_risque = "Dossier fragile (risque élevé)"
    else:
        niveau_risque = "Dossier très fragile (risque très élevé)"

    instance.score_chances = score
    instance.niveau_risque = niveau_risque
    instance.documents = "\n".join(documents)
    instance.etapes = "\n".join(etapes)
    instance.remarques_destination = "\n".join(remarques_destination)
    instance.conseils = "\n".join(conseils)
    instance.points_forts = "\n".join(points_forts)
    instance.points_faibles = "\n".join(points_faibles)


# -------------------------------------------------------------------
# VUES PRINCIPALES
# -------------------------------------------------------------------
def visa_tourisme_home(request):
    """
    Page d’accueil du module Visa Tourisme.
    """
    return render(request, 'VisaTourismeApp/home.html', {})


def visa_tourisme_assistant(request):
    """
    Formulaire + analyse.
    """
    result_obj = None

    if request.method == 'POST':
        form = VisaTourismeForm(request.POST)
        if form.is_valid():
            instance: VisaTourismRequest = form.save(commit=False)
            construire_recommandations(instance)
            instance.save()
            result_obj = instance
            # Envoi mail si email présent
            envoyer_plan_par_email(result_obj)
    else:
        form = VisaTourismeForm()

    context = {
        'form': form,
        'result': result_obj,
    }
    return render(request, 'VisaTourismeApp/tourism_visa_assistant.html', context)


def visa_tourisme_history(request):
    demandes = VisaTourismRequest.objects.all()[:30]
    return render(
        request,
        'VisaTourismeApp/tourism_visa_history.html',
        {'demandes': demandes},
    )


def visa_tourisme_pdf(request, pk):
    obj = get_object_or_404(VisaTourismRequest, pk=pk)
    return render_to_pdf('VisaTourismeApp/tourism_visa_pdf.html', {'result': obj})


# -------------------------------------------------------------------
# VUE DU COACH IA
# -------------------------------------------------------------------
def visa_tourisme_coach(request):
    """
    Petit chat avec le COACH VISA.
    On peut lui passer un id de dossier : /visa-tourisme/coach/?id=123
    pour qu’il commente ce plan précis.
    """
    result = None
    coach_response = None
    question = ""

    dossier_id = request.GET.get('id')
    if dossier_id:
        result = get_object_or_404(VisaTourismRequest, pk=dossier_id)

    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        dossier_id_post = request.POST.get('dossier_id')
        if dossier_id_post:
            result = get_object_or_404(VisaTourismRequest, pk=dossier_id_post)

        # Construire un résumé texte du dossier pour l’IA
        resume = ""
        if result:
            resume = (
                f"Destination : {result.get_destination_display()}\n"
                f"Nationalité : {result.nationalite}\n"
                f"Pays de résidence : {result.pays_residence}\n"
                f"Durée : {result.get_duree_sejour_display()}\n"
                f"Score de chances : {result.score_chances}% ({result.niveau_risque})\n"
                f"Points forts : {', '.join(result.points_forts_list())}\n"
                f"Points faibles : {', '.join(result.points_faibles_list())}\n"
            )

        if question:
            coach_response = appelle_coach_ia(question, resume)

    context = {
        'result': result,
        'question': question,
        'coach_response': coach_response,
    }
    return render(request, 'VisaTourismeApp/coach_chat.html', context)
