import csv
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .services import OCRError, extract_from_image, extract_from_video
from whatsapp_agent.models import Campagne, ContactWhatsApp


ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
    "video/avi",
    "video/x-msvideo",
}


def _dedupe_numbers(numbers):
    deduped = []
    seen = set()
    for number in numbers:
        if not number:
            continue
        if number not in seen:
            seen.add(number)
            deduped.append(number)
    return deduped


def _save_whatsapp_contacts(request, numbers, ville, groupe, note, module, consentement, sync_commercial, only_new=False):
    if not consentement:
        return {
            "error": "Coche la confirmation: ces prospects doivent etre autorises a etre contactes.",
            "created": 0,
            "updated": 0,
        }

    created = 0
    updated = 0
    contact_ids = []
    for numero in numbers:
        contact, was_created = ContactWhatsApp.objects.get_or_create(
            numero=numero,
            defaults={
                "ville": ville,
                "groupe": groupe,
                "note": note,
                "source": ContactWhatsApp.SOURCE_MANUEL,
                "consentement_confirme": True,
                "importe_par": request.user if request.user.is_authenticated else None,
            },
        )
        if was_created:
            created += 1
        else:
            if not only_new:
                changed = False
                for field, value in {"ville": ville, "groupe": groupe, "note": note}.items():
                    if value and getattr(contact, field) != value:
                        setattr(contact, field, value)
                        changed = True
                if not contact.consentement_confirme:
                    contact.consentement_confirme = True
                    changed = True
                if changed:
                    contact.save(update_fields=["ville", "groupe", "note", "consentement_confirme", "mis_a_jour_le"])
                updated += 1
        contact_ids.append(contact.id)

    if sync_commercial and contact_ids:
        try:
            from commercial_agent.services import CommercialAgentService

            CommercialAgentService.sync_from_whatsapp_contacts(
                limit=len(contact_ids),
                assigne_a=request.user if request.user.is_authenticated else None,
                module=module,
                contact_ids=contact_ids,
            )
        except Exception:
            pass

    return {"created": created, "updated": updated, "error": None}


def dashboard(request):
    context = {
        "numbers": [],
        "whatsapp_numbers": [],
        "raw_text": "",
        "error": "",
        "success": "",
        "groupe": "OCR repertoire",
        "note": "",
        "module": "services",
        "consentement": True,
        "sync_commercial": True,
        "only_new": False,
        "campaign_name": "",
        "campaign_message": "",
        "campaign_detail_url": "",
        "recent_imports": [],
    }

    history_groupe = request.GET.get("history_groupe", "").strip()
    context["history_groupe"] = history_groupe

    if request.method == "POST":
        files = request.FILES.getlist("media")
        action = request.POST.get("action", "extract")
        groupe = request.POST.get("groupe", "OCR repertoire").strip()
        note = request.POST.get("note", "").strip()
        module = request.POST.get("module", "services").strip() or "services"
        consentement = request.POST.get("consentement") == "on"
        sync_commercial = request.POST.get("sync_commercial") == "on"
        only_new = request.POST.get("new_only") == "on"
        campaign_name = request.POST.get("campaign_name", "").strip()
        campaign_message = request.POST.get("campaign_message", "").strip()

        context.update({
            "groupe": groupe,
            "note": note,
            "module": module,
            "consentement": consentement,
            "sync_commercial": sync_commercial,
            "only_new": only_new,
            "campaign_name": campaign_name,
            "campaign_message": campaign_message,
        })

        if not files:
            context["error"] = "Charge au moins un fichier image ou vidéo."
        else:
            extracted_numbers = []
            raw_texts = []
            for media in files:
                if media.content_type not in ALLOWED_CONTENT_TYPES:
                    context["error"] = f"Format refuse pour {media.name}. Utilise PNG, JPG, JPEG, MP4, MOV, WEBM ou AVI."
                    break
                try:
                    if media.content_type.startswith("video/"):
                        result = extract_from_video(media)
                    else:
                        result = extract_from_image(media)
                    extracted_numbers.extend(result.whatsapp_numbers)
                    raw_texts.append(result.text)
                except OCRError as exc:
                    context["error"] = str(exc)
                    break

            if not context["error"]:
                all_numbers = _dedupe_numbers(extracted_numbers)
                context["numbers"] = all_numbers
                context["whatsapp_numbers"] = all_numbers
                context["raw_text"] = "\n---\n".join(text for text in raw_texts if text)

                if action == "import":
                    if not all_numbers:
                        context["error"] = "Aucun numero WhatsApp valide trouve pour l'import."
                    else:
                        result = _save_whatsapp_contacts(
                            request,
                            all_numbers,
                            ville="",
                            groupe=groupe,
                            note=note,
                            module=module,
                            consentement=consentement,
                            sync_commercial=sync_commercial,
                            only_new=only_new,
                        )
                        if result["error"]:
                            context["error"] = result["error"]
                        else:
                            context["success"] = (
                                f"Import reussi: {result['created']} nouveaux, {result['updated']} existants/mis a jour."
                            )
                elif action == "create_campaign":
                    if not all_numbers:
                        context["error"] = "Aucun numero WhatsApp valide trouve pour creer la campagne."
                    else:
                        result = _save_whatsapp_contacts(
                            request,
                            all_numbers,
                            ville="",
                            groupe=groupe,
                            note=note,
                            module=module,
                            consentement=consentement,
                            sync_commercial=sync_commercial,
                            only_new=only_new,
                        )
                        if result["error"]:
                            context["error"] = result["error"]
                        else:
                            contacts = ContactWhatsApp.objects.filter(numero__in=all_numbers)
                            campaign_name = campaign_name or f"Campagne WhatsApp OCR {datetime.now():%d/%m %H:%M}"
                            campaign_message = campaign_message or (
                                "Bonjour {{prenom}}, nous vous contactons au sujet d'une offre speciale. Reponds si tu veux en savoir plus."
                            )
                            campagne = Campagne.objects.create(
                                nom=campaign_name,
                                description="Campagne creee depuis Phone OCR.",
                                message_template=campaign_message,
                                statut=Campagne.STATUT_VALIDEE,
                                filtre_role="selection_contacts",
                                total_destinataires=contacts.count(),
                                cree_par=request.user if request.user.is_authenticated else None,
                            )
                            campagne.destinataires_contacts.set(contacts)
                            try:
                                from whatsapp_agent.views import _creer_messages_campagne

                                _creer_messages_campagne(campagne)
                            except Exception:
                                pass
                            context["success"] = (
                                f"Campagne WhatsApp creee avec {contacts.count()} destinataires."
                            )
                            context["campaign_detail_url"] = reverse(
                                "whatsapp_agent:wa_detail", args=[campagne.pk]
                            )

    recent_imports_query = ContactWhatsApp.objects.filter(source=ContactWhatsApp.SOURCE_MANUEL)
    if history_groupe:
        recent_imports_query = recent_imports_query.filter(groupe__icontains=history_groupe)
    context["recent_imports"] = recent_imports_query.order_by("-cree_le")[:15]
    return render(request, "phone_ocr_agent/dashboard.html", context)


@require_POST
def export_csv(request):
    numbers = [line.strip() for line in request.POST.get("numbers", "").splitlines() if line.strip()]
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="contacts-phone-ocr.csv"'
    writer = csv.writer(response)
    writer.writerow(["numero"])
    for number in numbers:
        writer.writerow([f'="{number}"'])
    return response

# Create your views here.
