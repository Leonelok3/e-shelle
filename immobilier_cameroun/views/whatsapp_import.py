"""
whatsapp_import.py — immobilier_cameroun/views
Vues d'administration pour l'import de messages et photos WhatsApp :
- Import : coller texte + drag & drop 9 photos
- Vérification humaine : création de Bien + photos + partage Facebook
- Gestion des brouillons WhatsAppImmoDraft
"""
import os
import uuid
import logging
import hmac
from django.db import transaction
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.core.files import File
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import (
    Bien,
    PhotoBien,
    StatutBien,
    PeriodePrix,
    TypeBien,
    TypeTransaction,
    VILLES_CAMEROUN,
)
from ..models_whatsapp_draft import WhatsappImmoDraft
from ..services.whatsapp_parser import parse_immo_text, select_best_photos, improve_description
from ..services.facebook_publisher import publier_bien_sur_facebook

logger = logging.getLogger(__name__)
User = get_user_model()


# ─────────────────────────────────────────────────────────────────
# HELPERS STOCKAGE PHOTOS BROUILLON
# ─────────────────────────────────────────────────────────────────

def _save_uploaded_photos(draft_uuid_str: str, uploaded_files) -> list:
    """
    Enregistre les photos uploadées dans media/immobilier/drafts/<uuid>/
    Retourne la liste des chemins relatifs par rapport à MEDIA_ROOT.
    """
    saved_rel_paths = []
    draft_dir = os.path.join(settings.MEDIA_ROOT, "immobilier", "drafts", draft_uuid_str)
    os.makedirs(draft_dir, exist_ok=True)

    for i, f in enumerate(uploaded_files[:9]):  # Limite stricte 9 photos
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else "jpg"
        if ext not in ["jpg", "jpeg", "png", "webp"]:
            ext = "jpg"
        filename = f"photo_{i+1}_{uuid.uuid4().hex[:6]}.{ext}"
        filepath = os.path.join(draft_dir, filename)

        with open(filepath, "wb+") as dest:
            for chunk in f.chunks():
                dest.write(chunk)

        rel_path = os.path.join("immobilier", "drafts", draft_uuid_str, filename).replace("\\", "/")
        saved_rel_paths.append(rel_path)

    return saved_rel_paths


def _get_admin_owner(request_user):
    """Retourne l'utilisateur admin pour attribuer la propriété du bien."""
    if request_user and request_user.is_authenticated:
        return request_user
    super_u = User.objects.filter(is_superuser=True).first()
    return super_u or User.objects.first()


# ─────────────────────────────────────────────────────────────────
# WORKFLOW VALIDATION D'UN BROUILLON -> BIEN + 5 PHOTOS + FACEBOOK
# ─────────────────────────────────────────────────────────────────

def _validate_draft_for_publication(draft: WhatsappImmoDraft) -> None:
    if not draft.details_reviewed_at or not draft.details_reviewed_by_id:
        raise ValueError("Vérifiez et enregistrez les informations de l'annonce avant publication.")

    required_fields = {
        "titre": draft.parsed_titre.strip(),
        "prix": draft.parsed_prix,
        "ville": draft.parsed_ville,
        "quartier": draft.parsed_quartier.strip(),
        "type de bien": draft.parsed_type_bien,
        "type de transaction": draft.parsed_type_transaction,
    }
    missing_fields = [label for label, value in required_fields.items() if not value]
    if draft.parsed_prix is not None:
        if not draft.parsed_prix.is_finite() or draft.parsed_prix <= 0:
            missing_fields.append("prix valide supérieur à zéro")
        elif draft.parsed_prix.adjusted() > 13:
            missing_fields.append("prix dans la limite autorisée")
        elif draft.parsed_prix != draft.parsed_prix.to_integral_value():
            missing_fields.append("prix entier en XAF")
    if draft.parsed_ville and draft.parsed_ville not in dict(VILLES_CAMEROUN):
        missing_fields.append("ville valide")
    if draft.parsed_type_bien and draft.parsed_type_bien not in TypeBien.values:
        missing_fields.append("type de bien valide")
    if draft.parsed_type_transaction and draft.parsed_type_transaction not in TypeTransaction.values:
        missing_fields.append("type de transaction valide")
    description = (
        draft.ai_improved_description
        or draft.parsed_description
        or draft.raw_text
    )
    if not description.strip():
        missing_fields.append("description")

    if missing_fields:
        raise ValueError(
            "Complétez ou corrigez ces informations avant publication : "
            + ", ".join(dict.fromkeys(missing_fields))
            + "."
        )


def execute_draft_validation(
    draft: WhatsappImmoDraft,
    user=None,
    republishing_consent_confirmed=False,
) -> Bien:
    """
    Exécute la création automatique d'un Bien officiel à partir d'un brouillon validé :
    1. Crée l'instance Bien avec statut PUBLIE
    2. Crée jusqu'à 5 instances PhotoBien à partir des photos sélectionnées par Pillow
    3. Déclenche la publication sur la Page Facebook E-Shelle via get_facebook_page_credentials()
    4. Met à jour le brouillon (APPROVED, post_id, created_bien)
    """
    if not republishing_consent_confirmed:
        raise ValueError("Confirmez l'autorisation de republication avant toute diffusion.")

    with transaction.atomic():
        draft = WhatsappImmoDraft.objects.select_for_update().get(pk=draft.pk)
        if draft.status == WhatsappImmoDraft.Status.APPROVED and draft.created_bien_id:
            return draft.created_bien
        if draft.status != WhatsappImmoDraft.Status.PENDING:
            raise ValueError("Seuls les brouillons en attente peuvent être publiés.")
        _validate_draft_for_publication(draft)

        proprietaire = user or draft.created_by or _get_admin_owner(user)
        periode = (
            PeriodePrix.PAR_MOIS
            if draft.parsed_type_transaction == TypeTransaction.LOCATION
            else PeriodePrix.PRIX_FIXE
        )
        desc_finale = draft.ai_improved_description or draft.parsed_description or draft.raw_text

        now = timezone.now()
        bien = Bien.objects.create(
            titre=draft.parsed_titre,
            type_bien=draft.parsed_type_bien,
            type_transaction=draft.parsed_type_transaction,
            description=desc_finale,
            prix=draft.parsed_prix,
            devise="XAF",
            periode_prix=periode,
            ville=draft.parsed_ville,
            quartier=draft.parsed_quartier,
            statut=StatutBien.PUBLIE,
            proprietaire=proprietaire,
            publie_par_admin=True,
            note_admin=f"Importé via WhatsApp ({draft.whatsapp_group_name}) — Contact source : {draft.source_name} ({draft.source_phone})",
            date_publication=now,
        )

        selected_photos = draft.ai_selected_photos_json or draft.raw_images_json or []
        for idx, rel_path in enumerate(selected_photos[:5]):
            abs_path = os.path.join(settings.MEDIA_ROOT, rel_path.replace("/", os.sep))
            if not os.path.exists(abs_path):
                continue
            with open(abs_path, "rb") as photo_file:
                filename = os.path.basename(abs_path)
                photo_obj = PhotoBien(
                    bien=bien,
                    legende=f"Vue {idx + 1} — {bien.titre[:80]}",
                    est_photo_principale=(idx == 0),
                    ordre=idx,
                )
                photo_obj.image.save(filename, File(photo_file), save=True)

        draft.status = WhatsappImmoDraft.Status.APPROVED
        draft.created_bien = bien
        draft.republishing_authorized_at = now
        draft.republishing_authorized_by = user
        draft.save(
            update_fields=[
                "status",
                "created_bien",
                "republishing_authorized_at",
                "republishing_authorized_by",
                "updated_at",
            ]
        )

    fb_post_id = None
    try:
        fb_post_id = publier_bien_sur_facebook(bien, draft=draft)
    except Exception:
        logger.exception(
            "[execute_draft_validation] Exception publication Facebook pour le bien %s",
            bien.pk,
        )
    if fb_post_id:
        draft.facebook_post_id = fb_post_id
        draft.save(update_fields=["facebook_post_id", "updated_at"])

    logger.info(
        "[execute_draft_validation] Bien %s publié depuis le brouillon %s. FB: %s",
        bien.pk,
        draft.uuid,
        fb_post_id,
    )
    return bien


# ─────────────────────────────────────────────────────────────────
# VUES PUBLIQUES / ADMIN
# ─────────────────────────────────────────────────────────────────

@staff_member_required
def import_whatsapp_view(request):
    """
    Page d'import WhatsApp :
    - Coller le message WhatsApp brut
    - Drag & drop de jusqu'à 9 photos
    - Extraction automatique regex + scoring Pillow + IA
    - Redirection vers la liste des brouillons
    """
    if request.method == "POST":
        raw_text = request.POST.get("raw_text", "").strip()
        source_name = request.POST.get("source_name", "").strip() or "Démarcheur WhatsApp"
        source_phone = request.POST.get("source_phone", "").strip()
        group_name = request.POST.get("whatsapp_group_name", "").strip() or "E-Shelle Immobilier"

        if not raw_text:
            messages.error(request, "Veuillez coller le texte du message WhatsApp.")
            return render(request, "immobilier_cameroun/admin/import_whatsapp.html")

        # Parsing automatique du texte
        parsed = parse_immo_text(raw_text)

        # Si le téléphone n'a pas été saisi manuellement, prendre celui extrait du texte
        if not source_phone and parsed.get("telephone"):
            source_phone = parsed["telephone"]

        # Traitement des photos uploadées (jusqu'à 9)
        uploaded_files = request.FILES.getlist("photos")
        draft_uuid = uuid.uuid4()
        saved_rel_paths = _save_uploaded_photos(str(draft_uuid), uploaded_files)

        # Sélection experte des meilleures photos avec Pillow
        abs_paths = [os.path.join(settings.MEDIA_ROOT, p.replace("/", os.sep)) for p in saved_rel_paths]
        selected_eval = select_best_photos(abs_paths, max_photos=5)

        # Les 5 photos retenues
        ai_selected_photos = []
        for s in selected_eval:
            orig_idx = s["original_index"]
            if orig_idx < len(saved_rel_paths):
                ai_selected_photos.append(saved_rel_paths[orig_idx])

        # Si aucune photo n'a pu être évaluée ou moins de 5, prendre les premières disponibles
        if not ai_selected_photos and saved_rel_paths:
            ai_selected_photos = saved_rel_paths[:5]

        # Amélioration de la description
        ai_description = improve_description(raw_text, parsed)

        # Calcul du score qualité global
        quality_score = parsed.get("quality_score", 50.0)
        if len(saved_rel_paths) >= 5:
            quality_score = min(quality_score + 15.0, 100.0)
        elif len(saved_rel_paths) >= 2:
            quality_score = min(quality_score + 8.0, 100.0)

        # Création du brouillon
        WhatsappImmoDraft.objects.create(
            uuid=draft_uuid,
            raw_text=raw_text,
            raw_images_json=saved_rel_paths,
            source_name=source_name,
            source_phone=source_phone,
            whatsapp_group_name=group_name,
            parsed_titre=parsed.get("titre", ""),
            parsed_type_bien=parsed.get("type_bien", ""),
            parsed_type_transaction=parsed.get("type_transaction", ""),
            parsed_prix=parsed.get("prix"),
            parsed_conditions=parsed.get("conditions", ""),
            parsed_ville=parsed.get("ville", ""),
            parsed_quartier=parsed.get("quartier", ""),
            parsed_description=parsed.get("description", raw_text),
            ai_improved_description=ai_description,
            ai_selected_photos_json=ai_selected_photos,
            ai_quality_score=quality_score,
            status=WhatsappImmoDraft.Status.PENDING,
            created_by=request.user,
        )

        messages.success(
            request,
            f"✅ Brouillon importé avec succès ! Score IA : {quality_score:.0f}/100. "
            f"{len(saved_rel_paths)} photo(s) reçue(s), {len(ai_selected_photos)} optimisée(s) retenue(s)."
        )
        return redirect("immobilier:whatsapp_drafts")

    return render(request, "immobilier_cameroun/admin/import_whatsapp.html")


@staff_member_required
def whatsapp_drafts_view(request):
    """
    Liste des brouillons WhatsApp :
    - Filtres : En attente (défaut), Validés, Rejetés, Tous
    - Carte détaillée pour chaque annonce avec aperçu photos, prix, quartier
    - Bouton de validation 1-clic (+ Facebook)
    - Boutons d'édition rapide et de rejet
    """
    statut_filter = request.GET.get("statut", WhatsappImmoDraft.Status.PENDING)
    qs = WhatsappImmoDraft.objects.all().order_by("-created_at")

    if statut_filter in [s.value for s in WhatsappImmoDraft.Status]:
        qs = qs.filter(status=statut_filter)

    counts = {
        "pending": WhatsappImmoDraft.objects.filter(status=WhatsappImmoDraft.Status.PENDING).count(),
        "approved": WhatsappImmoDraft.objects.filter(status=WhatsappImmoDraft.Status.APPROVED).count(),
        "rejected": WhatsappImmoDraft.objects.filter(status=WhatsappImmoDraft.Status.REJECTED).count(),
        "total": WhatsappImmoDraft.objects.count(),
    }

    return render(request, "immobilier_cameroun/admin/whatsapp_drafts.html", {
        "drafts": qs,
        "counts": counts,
        "current_statut": statut_filter,
    })


@staff_member_required
@require_POST
def valider_draft_view(request, draft_uuid):
    """Validation 1-clic : transforme le brouillon en Bien publié + 5 photos + Facebook."""
    draft = get_object_or_404(WhatsappImmoDraft, uuid=draft_uuid)

    if draft.status == WhatsappImmoDraft.Status.APPROVED and draft.created_bien:
        messages.info(request, "Ce brouillon a déjà été validé et publié.")
        return redirect("immobilier:whatsapp_drafts")

    try:
        bien = execute_draft_validation(
            draft,
            user=request.user,
            republishing_consent_confirmed=(
                request.POST.get("confirm_republishing") == "on"
            ),
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("immobilier:modifier_whatsapp_draft", draft_uuid=draft.uuid)

    msg = f"🎉 Le bien « {bien.titre} » a été validé et publié sur E-Shelle !"
    if draft.facebook_post_id:
        msg += f" 🚀 Partagé automatiquement sur la Page Facebook officielle (ID: {draft.facebook_post_id})."
    else:
        msg += " (Publication Facebook en attente de configuration ou ignorée)."

    messages.success(request, msg)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "ok",
            "bien_id": bien.pk,
            "bien_url": bien.get_absolute_url(),
            "facebook_post_id": draft.facebook_post_id,
        })

    return redirect("immobilier:whatsapp_drafts")


@staff_member_required
@require_POST
def rejeter_draft_view(request, draft_uuid):
    """Rejette un brouillon."""
    draft = get_object_or_404(WhatsappImmoDraft, uuid=draft_uuid)
    draft.status = WhatsappImmoDraft.Status.REJECTED
    draft.save()
    messages.warning(request, f"Brouillon « {draft.parsed_titre or draft.uuid} » rejeté.")
    return redirect("immobilier:whatsapp_drafts")


@staff_member_required
@require_http_methods(["GET", "POST"])
def modifier_draft_view(request, draft_uuid):
    """Édition rapide d'un brouillon avant validation."""
    draft = get_object_or_404(WhatsappImmoDraft, uuid=draft_uuid)

    if request.method == "POST":
        if request.POST.get("confirm_details_reviewed") != "on":
            messages.error(request, "Confirmez avoir vérifié les informations de l'annonce.")
            return redirect("immobilier:modifier_whatsapp_draft", draft_uuid=draft.uuid)

        draft.parsed_titre = request.POST.get("titre", draft.parsed_titre).strip()
        draft.parsed_quartier = request.POST.get("quartier", draft.parsed_quartier).strip()
        valid_villes = dict(VILLES_CAMEROUN)
        ville = request.POST.get("ville", draft.parsed_ville).strip()
        if ville and ville not in valid_villes:
            messages.error(request, "Veuillez choisir une ville de la liste.")
            return render(
                request,
                "immobilier_cameroun/admin/modifier_draft.html",
                {
                    "draft": draft,
                    "villes": VILLES_CAMEROUN,
                    "types_bien": TypeBien.choices,
                    "types_transaction": TypeTransaction.choices,
                },
            )
        draft.parsed_ville = ville
        draft.parsed_type_bien = request.POST.get("type_bien", draft.parsed_type_bien).strip()
        draft.parsed_type_transaction = request.POST.get(
            "type_transaction", draft.parsed_type_transaction
        ).strip()
        if draft.parsed_type_bien not in TypeBien.values:
            messages.error(request, "Veuillez choisir un type de bien valide.")
            return redirect("immobilier:modifier_whatsapp_draft", draft_uuid=draft.uuid)
        if draft.parsed_type_transaction not in TypeTransaction.values:
            messages.error(request, "Veuillez choisir une transaction valide.")
            return redirect("immobilier:modifier_whatsapp_draft", draft_uuid=draft.uuid)
        draft.source_name = request.POST.get("source_name", draft.source_name).strip()
        draft.source_phone = request.POST.get("source_phone", draft.source_phone).strip()
        draft.parsed_conditions = request.POST.get("conditions", draft.parsed_conditions).strip()
        draft.ai_improved_description = request.POST.get("description", draft.ai_improved_description).strip()

        prix_raw = request.POST.get("prix", "").strip()
        if prix_raw:
            try:
                parsed_prix = Decimal(prix_raw.replace(" ", ""))
                if (
                    not parsed_prix.is_finite()
                    or parsed_prix <= 0
                    or parsed_prix.adjusted() > 13
                    or parsed_prix != parsed_prix.to_integral_value()
                ):
                    raise ValueError
                draft.parsed_prix = parsed_prix
            except (InvalidOperation, ValueError):
                messages.error(request, "Le prix doit être un nombre valide.")
                return redirect("immobilier:modifier_whatsapp_draft", draft_uuid=draft.uuid)
        else:
            draft.parsed_prix = None

        draft.details_reviewed_at = timezone.now()
        draft.details_reviewed_by = request.user
        draft.save()
        messages.success(request, "Brouillon mis à jour avec succès.")
        return redirect("immobilier:whatsapp_drafts")

    return render(
        request,
        "immobilier_cameroun/admin/modifier_draft.html",
        {
            "draft": draft,
            "villes": VILLES_CAMEROUN,
            "types_bien": TypeBien.choices,
            "types_transaction": TypeTransaction.choices,
        },
    )


# ─────────────────────────────────────────────────────────────────
# API INTERNE D'INGESTION AUTOMATIQUE (WORKER NODE.JS / BAILEYS)
# ─────────────────────────────────────────────────────────────────

from django.views.decorators.csrf import csrf_exempt
import base64
from django.core.files.base import ContentFile

@csrf_exempt
@require_POST
def internal_whatsapp_ingest(request):
    """
    Endpoint API interne appelé par le worker Node.js / Baileys dès qu'un message
    avec texte ou photos arrive dans le groupe WhatsApp E-Shelle Immobilier.
    Sécurisé par un secret token interne.
    Accepte :
    - multipart/form-data avec fichiers 'photos'
    - ou JSON avec images en base64
    """
    # 1. Vérification du token de sécurité interne
    expected_secret = settings.INTERNAL_WHATSAPP_SECRET
    provided_secret = request.headers.get("X-Internal-Secret", "")
    if (
        len(expected_secret) < 32
        or expected_secret == "replace-with-a-random-secret-of-at-least-32-characters"
    ):
        logger.error("INTERNAL_WHATSAPP_SECRET n'est pas configuré correctement.")
        return JsonResponse(
            {"status": "error", "message": "Service d'ingestion non configuré."},
            status=503,
        )
    if not provided_secret or not hmac.compare_digest(
        provided_secret.encode("utf-8"),
        expected_secret.encode("utf-8"),
    ):
        return JsonResponse({"status": "error", "message": "Accès non autorisé."}, status=403)

    raw_text = ""
    source_name = "Démarcheur WhatsApp"
    source_phone = ""
    group_name = "E-Shelle Immobilier"
    uploaded_files = []

    # 2. Extraction des données
    if request.content_type and "application/json" in request.content_type:
        import json
        try:
            data = json.loads(request.body.decode("utf-8"))
            raw_text = data.get("raw_text", "").strip()
            source_name = data.get("source_name", "").strip() or source_name
            source_phone = data.get("source_phone", "").strip()
            group_name = data.get("whatsapp_group_name", "").strip() or group_name
            # Traiter images base64 si fournies
            for idx, b64_str in enumerate(data.get("images_base64", [])[:9]):
                if "," in b64_str:
                    b64_str = b64_str.split(",", 1)[1]
                file_bytes = base64.b64decode(b64_str)
                uploaded_files.append(ContentFile(file_bytes, name=f"photo_{idx+1}.jpg"))
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"JSON invalide: {e}"}, status=400)
    else:
        raw_text = request.POST.get("raw_text", "").strip()
        source_name = request.POST.get("source_name", "").strip() or source_name
        source_phone = request.POST.get("source_phone", "").strip()
        group_name = request.POST.get("whatsapp_group_name", "").strip() or group_name
        uploaded_files = request.FILES.getlist("photos")

    if not raw_text and not uploaded_files:
        return JsonResponse({"status": "error", "message": "Contenu vide."}, status=400)

    # 3. Parsing intelligent du message
    parsed = parse_immo_text(raw_text)
    if not source_phone and parsed.get("telephone"):
        source_phone = parsed["telephone"]

    # 4. Enregistrement et scoring des photos
    draft_uuid = uuid.uuid4()
    saved_rel_paths = _save_uploaded_photos(str(draft_uuid), uploaded_files)
    abs_paths = [os.path.join(settings.MEDIA_ROOT, p.replace("/", os.sep)) for p in saved_rel_paths]
    selected_eval = select_best_photos(abs_paths, max_photos=5)

    ai_selected_photos = []
    for s in selected_eval:
        orig_idx = s["original_index"]
        if orig_idx < len(saved_rel_paths):
            ai_selected_photos.append(saved_rel_paths[orig_idx])

    if not ai_selected_photos and saved_rel_paths:
        ai_selected_photos = saved_rel_paths[:5]

    # 5. Enrichissement SEO et calcul score
    ai_desc = improve_description(raw_text, parsed)
    quality_score = parsed.get("quality_score", 50.0)
    if len(saved_rel_paths) >= 5:
        quality_score = min(quality_score + 15.0, 100.0)
    elif len(saved_rel_paths) >= 2:
        quality_score = min(quality_score + 8.0, 100.0)

    # Admin par défaut
    admin_user = _get_admin_owner(None)

    # 6. Création du brouillon
    draft = WhatsappImmoDraft.objects.create(
        uuid=draft_uuid,
        raw_text=raw_text or "(Annonce avec photos sans texte)",
        raw_images_json=saved_rel_paths,
        source_name=source_name,
        source_phone=source_phone,
        whatsapp_group_name=group_name,
        parsed_titre=parsed.get("titre", "Bien immobilier WhatsApp"),
        parsed_type_bien=parsed.get("type_bien", ""),
        parsed_type_transaction=parsed.get("type_transaction", ""),
        parsed_prix=parsed.get("prix"),
        parsed_conditions=parsed.get("conditions", ""),
        parsed_ville=parsed.get("ville", ""),
        parsed_quartier=parsed.get("quartier", ""),
        parsed_description=parsed.get("description", raw_text),
        ai_improved_description=ai_desc,
        ai_selected_photos_json=ai_selected_photos,
        ai_quality_score=quality_score,
        status=WhatsappImmoDraft.Status.PENDING,
        created_by=admin_user,
    )

    logger.info(f"[internal_whatsapp_ingest] Brouillon créé automatiquement via API: {draft.uuid} (Score: {quality_score})")

    return JsonResponse({
        "status": "ok",
        "draft_uuid": str(draft.uuid),
        "titre": draft.parsed_titre,
        "prix": float(draft.parsed_prix) if draft.parsed_prix else None,
        "quartier": draft.parsed_quartier,
        "ville": draft.parsed_ville,
        "quality_score": draft.ai_quality_score,
        "photos_count": len(saved_rel_paths),
        "selected_photos_count": len(ai_selected_photos),
    })
