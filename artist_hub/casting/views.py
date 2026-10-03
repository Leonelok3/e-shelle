"""
artist_hub/casting/views.py
Vues publiques du module casting :
- Page d'accueil et de présentation de la session (Fashion Week Douala 2026)
- Formulaire d'inscription par étapes avec upload sécurisé et paiement atomique
- Espace candidat « Suivre ma candidature »
- Téléchargement sécurisé de la fiche officielle PDF & reçu
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from artist_hub.casting.models import (
    CastingSession,
    Candidate,
    CandidatePhoto,
    CandidateStatus,
    PhotoType,
)
from artist_hub.casting.forms import CandidateRegistrationForm
from artist_hub.casting.services import (
    generate_candidate_number,
    generate_access_code,
    process_uploaded_image,
    generate_candidate_pdf,
)
from artist_hub.payments.services import create_payment
from artist_hub.payments.providers.factory import get_payment_provider
from artist_hub.conf import hub_settings

logger = logging.getLogger("artist_hub.casting")


def get_active_session():
    """Récupère la session de casting active par défaut."""
    return CastingSession.objects.filter(is_active=True).first()


class CastingIndexView(TemplateView):
    """
    Page officielle de présentation du casting Douala Fashion Week 2026.
    Affiche le compte à rebours, les critères, tarifs et boutons d'inscription.
    """

    template_name = "artist_hub/casting/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        session = get_active_session()
        ctx["session"] = session
        ctx["hub_settings"] = hub_settings
        ctx["min_height_male"] = session.min_height_male if session else 183
        ctx["min_height_female"] = session.min_height_female if session else 175
        ctx["fee_cameroon"] = session.fee_cameroon if session else 3000
        ctx["fee_international"] = session.fee_international if session else 5000
        return ctx


class CandidateRegisterWizardView(View):
    """
    Formulaire d'inscription en 4 étapes pour les mannequins.
    Création atomique du candidat + paiement + photos traitées.
    """

    def get(self, request):
        session = get_active_session()
        if not session or not session.is_open:
            messages.warning(request, _("Les inscriptions pour cette session de casting sont actuellement fermées."))
            return redirect("artist_hub:casting:index")

        form = CandidateRegistrationForm(session=session)
        return render(
            request,
            "artist_hub/casting/register.html",
            {
                "session": session,
                "form": form,
                "hub_settings": hub_settings,
            },
        )

    def post(self, request):
        session = get_active_session()
        if not session or not session.is_open:
            messages.error(request, _("Cette session de casting est clôturée."))
            return redirect("artist_hub:casting:index")

        form = CandidateRegistrationForm(request.POST, request.FILES, session=session)
        if not form.is_valid():
            messages.error(request, _("Veuillez corriger les erreurs indiquées dans le formulaire."))
            return render(
                request,
                "artist_hub/casting/register.html",
                {
                    "session": session,
                    "form": form,
                    "hub_settings": hub_settings,
                },
            )

        cd = form.cleaned_data
        country = cd.get("country", "").strip()
        is_international = bool(country and country.lower() != "cameroun")
        amount = session.fee_international if is_international else session.fee_cameroon

        with transaction.atomic():
            # 1. Génération des identifiants uniques
            candidate_number = generate_candidate_number(session)
            access_code = generate_access_code()

            # 2. Création de l'entité Payment
            proof_file = cd.get("proof_file")
            proof_notes = cd.get("proof_notes", "")
            payment_method = cd.get("payment_method")

            payment = create_payment(
                amount=amount,
                currency=session.currency,
                payer_name=f"{cd['first_name']} {cd['last_name']}",
                payer_phone=cd["phone"],
                payer_email=cd["email"],
                method=payment_method,
                provider_name=hub_settings.ACTIVE_PAYMENT_PROVIDER,
                proof_file=proof_file,
                proof_notes=proof_notes,
            )

            # 3. Création du Candidat
            candidate = Candidate.objects.create(
                session=session,
                first_name=cd["first_name"],
                last_name=cd["last_name"],
                birth_date=cd["birth_date"],
                gender=cd["gender"],
                height_cm=cd["height_cm"],
                weight_kg=cd.get("weight_kg"),
                measurements=cd.get("measurements", ""),
                city=cd["city"],
                country=country,
                is_international=is_international,
                phone=cd["phone"],
                email=cd["email"],
                experience=cd.get("experience", ""),
                social_links=cd.get("social_links", ""),
                candidate_number=candidate_number,
                access_code=access_code,
                status=CandidateStatus.EN_ATTENTE_VALIDATION if proof_file else CandidateStatus.EN_ATTENTE_PAIEMENT,
                payment=payment,
                video_url=cd.get("video_url", ""),
                video_file=cd.get("video_file"),
                is_minor=cd.get("birth_date") and (datetime.date.today().year - cd["birth_date"].year < 18),
                guardian_name=cd.get("guardian_name", ""),
                guardian_phone=cd.get("guardian_phone", ""),
                parental_consent=cd.get("parental_consent", False),
                gdpr_consent=cd.get("gdpr_consent", False),
                selection_disclaimer_accepted=cd.get("selection_disclaimer_accepted", False),
            )

            # Mettre à jour l'objet cible du paiement
            payment.content_object = candidate
            payment.save(update_fields=["content_type", "object_id"])

            # 4. Traitement et sauvegarde sécurisée des photos avec Pillow
            photo_portrait = cd.get("photo_portrait")
            if photo_portrait:
                processed_portrait = process_uploaded_image(photo_portrait)
                CandidatePhoto.objects.create(
                    candidate=candidate,
                    photo_type=PhotoType.PORTRAIT,
                    image=processed_portrait,
                    order=1,
                )

            photo_full = cd.get("photo_full_length")
            if photo_full:
                processed_full = process_uploaded_image(photo_full)
                CandidatePhoto.objects.create(
                    candidate=candidate,
                    photo_type=PhotoType.FULL_LENGTH,
                    image=processed_full,
                    order=2,
                )

        logger.info(
            "CANDIDATE_REGISTERED: Num=%s, Nom=%s, Tel=%s, Montant=%s %s",
            candidate.candidate_number,
            candidate.full_name,
            candidate.phone,
            amount,
            session.currency,
        )

        messages.success(
            request,
            _("Votre dossier de candidature a été créé avec succès ! Vos identifiants ont été générés."),
        )

        # 5. Initiation de la passerelle de paiement
        provider = get_payment_provider(payment.provider)
        init_result = provider.initiate(payment)

        if init_result.success and init_result.payment_url:
            return redirect(init_result.payment_url)

        return redirect("artist_hub:payments:waiting", reference=payment.reference)


class CandidateTrackView(View):
    """
    Espace candidat pour suivre l'état de validation et de sélection.
    Connexion directe via :
    - Code d'accès (ex: OPUS-4921-X), OU
    - Numéro de candidature (CAST-2026-XXXX) + Téléphone.
    """

    def get(self, request):
        code = request.GET.get("code", "").strip()
        num = request.GET.get("num", "").strip()
        phone = request.GET.get("phone", "").strip()

        candidate = None
        if code:
            candidate = Candidate.objects.filter(access_code__iexact=code).first()
        elif num and phone:
            cleaned_phone = "".join(phone.split())
            candidate = Candidate.objects.filter(
                candidate_number__iexact=num,
                phone__icontains=cleaned_phone[-8:],
            ).first()

        return render(
            request,
            "artist_hub/casting/track.html",
            {
                "candidate": candidate,
                "code": code,
                "num": num,
                "phone": phone,
                "hub_settings": hub_settings,
            },
        )


class CandidateCardPdfView(View):
    """
    Génération et téléchargement de la Fiche Officielle & Reçu PDF.
    Accès sécurisé par code d'accès, staff ou session.
    """

    def get(self, request, candidate_number):
        candidate = get_object_or_404(Candidate, candidate_number=candidate_number)

        # Vérification d'autorisation basique : staff ou code d'accès fourni en GET
        req_code = request.GET.get("code", "").strip()
        if not request.user.is_staff and req_code != candidate.access_code :
            return HttpResponseForbidden("Accès réservé au titulaire de la candidature validée.")

        pdf_bytes = generate_candidate_pdf(candidate)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="Fiche_Casting_{candidate.candidate_number}.pdf"'
        return response
