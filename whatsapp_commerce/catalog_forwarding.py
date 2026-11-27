"""Pair a merchant's sender and import forwarded offers into that merchant's catalogue."""

import hmac
import io
import logging
import secrets
from datetime import timedelta
from hashlib import sha256

from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from business.models import BusinessCatalogItem, BusinessProfile
from whatsapp_agent.media import MB, private_storage, retrieve_media, save_private

from .catalog_messages import format_price, parse_offer
from .models import BusinessWhatsAppConnection, WhatsAppCatalogSender, WhatsAppCatalogSubmission
from .onboarding import _graph_url, _request_meta
from .services import normalize_phone

logger = logging.getLogger(__name__)
Status = WhatsAppCatalogSubmission.Status
FIELDS = ("title", "price_amount", "currency", "sku", "stock")


class CatalogueReview(ValueError):
    pass


def _receiver():
    return (
        settings.WHATSAPP_CATALOG_IMPORT_WABA_ID,
        settings.WHATSAPP_CATALOG_IMPORT_PHONE_ID,
        settings.WHATSAPP_CATALOG_IMPORT_TOKEN,
    )


def receiver_number():
    waba, phone_id, token = _receiver()
    if not all((waba, phone_id, token)) or _is_shared_phone(phone_id):
        return ""
    return normalize_phone(settings.WHATSAPP_CATALOG_IMPORT_NUMBER)


def _is_shared_phone(phone_id):
    return phone_id == getattr(settings, "WHATSAPP_PHONE_ID", "") or BusinessWhatsAppConnection.objects.filter(
        phone_number_id=phone_id,
    ).exists()


def issue_pairing(business, phone):
    code = secrets.token_hex(6).upper()
    with transaction.atomic():
        locked = BusinessProfile.objects.select_for_update().get(pk=business.pk, owner_id=business.owner_id)
        sender, _ = WhatsAppCatalogSender.objects.select_for_update().get_or_create(business=locked, defaults={
            "owner_id": business.owner_id,
        })
        if sender.owner_id != locked.owner_id:
            sender.phone = None
            sender.auto_publish = False
        sender.owner_id = locked.owner_id
        sender.requested_phone = phone
        sender.pairing_digest = sha256(code.encode()).hexdigest()
        sender.pairing_expires_at = timezone.now() + timedelta(minutes=15)
        sender.save()
    return code


def _pair(phone, code):
    digest = sha256(code.upper().encode()).hexdigest()
    try:
        with transaction.atomic():
            sender = WhatsAppCatalogSender.objects.select_for_update().filter(
                requested_phone=phone, pairing_digest=digest,
                pairing_expires_at__gt=timezone.now(),
            ).first()
            if not sender or not hmac.compare_digest(sender.pairing_digest, digest):
                return
            if sender.owner_id != sender.business.owner_id:
                return
            if sender.phone != phone:
                sender.auto_publish = False
            sender.phone = phone
            sender.requested_phone = sender.pairing_digest = ""
            sender.pairing_expires_at = None
            sender.save()
    except IntegrityError:
        # A phone is owned by exactly one catalogue, including on simultaneous confirmations.
        return


def _receive(message):
    phone = normalize_phone(message.get("from"))
    message_id = message.get("id")
    kind = message.get("type")
    if not phone or not isinstance(message_id, str) or not 1 <= len(message_id) <= 200 or kind not in {"text", "image"}:
        return
    content = message.get(kind)
    if not isinstance(content, dict):
        return
    text = content.get("body" if kind == "text" else "caption") or ""
    media = content.get("id") if kind == "image" else ""
    if not isinstance(text, str) or not isinstance(media, str):
        return
    text = text.strip()[:4096]
    if kind == "text" and text.upper().startswith("LIER "):
        _pair(phone, text[5:].strip())
        return
    if not (text or media):
        return
    with transaction.atomic():
        sender = WhatsAppCatalogSender.objects.select_for_update().filter(phone=phone).first()
        if not sender or sender.owner_id != sender.business.owner_id or not sender.business.is_active:
            return
        WhatsAppCatalogSubmission.objects.get_or_create(wa_message_id=message_id, defaults={
            "sender": sender, "owner_id": sender.owner_id, "sender_phone": phone, "body": text, "media_id": media[:80],
        })


def receive_and_exclude_catalog(data):
    """Consume the dedicated phone's signed changes before routing ordinary WhatsApp messages."""
    waba, phone_id, token = _receiver()
    if not phone_id:
        return data
    if _is_shared_phone(phone_id):
        return data
    remaining = []
    for entry in data.get("entry", []):
        if not isinstance(entry, dict):
            continue
        changes = []
        for change in entry.get("changes", []):
            value = change.get("value") if isinstance(change, dict) else None
            metadata = value.get("metadata") if isinstance(value, dict) else None
            if not isinstance(metadata, dict) or str(metadata.get("phone_number_id")) != phone_id:
                changes.append(change)
                continue
            if not (waba and token and str(entry.get("id")) == waba and change.get("field") == "messages"):
                continue
            for message in value.get("messages", []):
                if isinstance(message, dict):
                    _receive(message)
        if changes:
            remaining.append({**entry, "changes": changes})
    return {**data, "entry": remaining}


def _read_image(submission):
    _waba, phone_id, token = _receiver()
    with io.BytesIO() as raw:
        mime = retrieve_media(submission.media_id, token, raw, max_bytes=8 * MB, phone_number_id=phone_id,
                              media_kind="image", graph_base=_graph_url("").rstrip("/"))
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            raise CatalogueReview("La photo n’a pas pu être récupérée")
        with Image.open(raw) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 16_000_000:
                raise CatalogueReview("Vérifie le format ou la taille de la photo")
            with source.convert("RGB") as image, io.BytesIO() as output:
                image.thumbnail((1600, 1600))
                image.save(output, format="JPEG", quality=86)
                return save_private(ContentFile(output.getvalue()), "produit.jpg").removeprefix("private:")


def _suggest_from_photo(image):
    from phone_ocr_agent.services import extract_from_image

    with private_storage().open(image) as photo:
        result = extract_from_image(photo)
    return parse_offer(result.text[:4096])[0]


def _matching_items(business, title, sku):
    items = BusinessCatalogItem.objects.filter(business=business)
    if sku:
        matches = items.filter(sku__iexact=sku)
        if matches.exists():
            return list(matches[:2])
    return list(items.filter(title__iexact=title)[:2])


def _set_item_image(item, image):
    try:
        with private_storage().open(image) as photo:
            item.image.save("produit.jpg", photo, save=False)
    except (OSError, ValueError) as exc:
        raise CatalogueReview("La photo n’a pas pu être enregistrée. Vérifie le brouillon avant de réessayer.") from exc


def _publish(business, submission, *, update_item=None):
    if not business.is_published:
        raise CatalogueReview("La fiche Business doit être visible pour publier cet article")
    matches = _matching_items(business, submission.title, submission.sku)
    if matches and (len(matches) != 1 or matches[0].pk != getattr(update_item, "pk", None)):
        raise CatalogueReview("Un article correspond déjà à ce nom ou à cette référence")
    if update_item and (not matches or (
        update_item.sku and submission.sku and update_item.sku.casefold() != submission.sku.casefold()
    )):
        raise CatalogueReview("Confirme la référence exacte de l’article que tu veux modifier")
    if update_item is None:
        limit = business.catalog_item_limit
        if limit is not None and business.catalog_items.count() >= limit:
            raise CatalogueReview("Le catalogue a atteint la limite de la formule")
    item = update_item or BusinessCatalogItem(business=business)
    item.title = submission.title
    if not item.sku:
        item.sku = submission.sku
    item.price_label = format_price(submission.price_amount, submission.currency)
    item.price_label_en = ""
    item.is_active = True
    if submission.stock is not None:
        item.stock_quantity = submission.stock
    if submission.private_image:
        _set_item_image(item, submission.private_image)
    item.save()
    submission.item = item
    submission.status = Status.PUBLISHED
    submission.reason = ""
    submission.private_image = ""
    return item


def _notice(submission):
    _waba, phone, token = _receiver()
    if not phone or not token or _is_shared_phone(phone) or not WhatsAppCatalogSender.objects.filter(
        pk=submission.sender_id, phone=submission.sender_phone,
        business__owner_id=submission.owner_id, owner_id=submission.owner_id,
    ).exists():
        return
    origin = settings.SITE_URL.rstrip("/")
    if submission.status == Status.PUBLISHED:
        from .offer_tracking import catalogue_offer_path

        if not submission.item_id:
            return
        path = catalogue_offer_path(submission.sender.business, submission.item_id)
        body = f"Produit publié. {submission.title} · {format_price(submission.price_amount, submission.currency)}.\nLien à partager : {origin}{path}"
    else:
        path = reverse("whatsapp_commerce:catalog_forwarding", args=[submission.sender.business_id])
        body = f"Produit à valider dans ton espace E-Shelle. {submission.reason}\n{origin}{path}"
    try:
        _request_meta("POST", f"{phone}/messages", token=token, payload={
            "messaging_product": "whatsapp", "to": submission.sender_phone.lstrip("+"),
            "type": "text", "text": {"body": body, "preview_url": False},
        })
    except Exception as exc:
        logger.warning("Confirmation d’import WhatsApp indisponible (import=%s, %s).", submission.pk, type(exc).__name__)


def process_submission(submission_id):
    if not WhatsAppCatalogSubmission.objects.filter(pk=submission_id, status=Status.PENDING).update(
        status=Status.PROCESSING, updated_at=timezone.now(),
    ):
        return
    draft = WhatsAppCatalogSubmission.objects.select_related("sender__business").get(pk=submission_id)
    if draft.owner_id != draft.sender.business.owner_id or draft.sender.phone != draft.sender_phone:
        WhatsAppCatalogSubmission.objects.filter(pk=draft.pk, status=Status.PROCESSING).update(
            status=Status.REJECTED, reason="L’association du numéro a changé", updated_at=timezone.now(),
        )
        return
    parsed, reason = parse_offer(draft.body)
    image = ""
    if draft.media_id:
        try:
            image = _read_image(draft)
        except Exception as exc:
            logger.warning("Photo d’import WhatsApp indisponible (import=%s, %s).", draft.pk, type(exc).__name__)
            reason = ". ".join(filter(None, (reason, "La photo n’a pas pu être importée")))
    if image and not draft.body:
        try:
            parsed = _suggest_from_photo(image)
        except Exception as exc:
            logger.warning("Lecture de l’image indisponible (import=%s, %s).", draft.pk, type(exc).__name__)
        reason = "Vérifie le nom et le prix indiqués sur la photo."
    with transaction.atomic():
        business = BusinessProfile.objects.select_for_update().get(pk=draft.sender.business_id)
        sender = WhatsAppCatalogSender.objects.select_for_update().get(pk=draft.sender_id)
        submission = WhatsAppCatalogSubmission.objects.select_for_update().get(pk=draft.pk)
        if submission.status != Status.PROCESSING:
            if image:
                private_storage().delete(image)
            return
        for field, value in parsed.items():
            setattr(submission, field, value)
        submission.private_image = image
        submission.status = Status.REVIEW
        submission.reason = (reason or "Vérifie les données avant publication")[:245]
        if submission.owner_id != business.owner_id or sender.owner_id != business.owner_id or sender.phone != submission.sender_phone:
            submission.status = Status.REJECTED
            submission.reason = "L’association du numéro a changé"
            submission.private_image = ""
        elif sender.auto_publish and not reason:
            try:
                _publish(business, submission)
            except CatalogueReview as exc:
                submission.reason = str(exc)
        submission.save()
        if image and not submission.private_image:
            transaction.on_commit(lambda: private_storage().delete(image), robust=True)
    if submission.status in {Status.PUBLISHED, Status.REVIEW}:
        _notice(submission)


@transaction.atomic
def review_submission(business, submission_id, fields, *, update_item_id=None, reject=False):
    locked = BusinessProfile.objects.select_for_update().get(pk=business.pk, owner_id=business.owner_id)
    submission = WhatsAppCatalogSubmission.objects.select_for_update().get(
        pk=submission_id, sender__business=locked, owner_id=locked.owner_id, status=Status.REVIEW,
    )
    image = submission.private_image
    if reject:
        submission.status = Status.REJECTED
        submission.private_image = ""
    else:
        for field in FIELDS:
            setattr(submission, field, fields[field])
        item = None
        if update_item_id is not None:
            item = locked.catalog_items.select_for_update().filter(pk=update_item_id).first()
            if item is None or f"{item.pk}:{item.updated_at.isoformat()}" != fields.get("item_version"):
                raise CatalogueReview("L’article a changé. Recharge la page avant de valider")
        _publish(locked, submission, update_item=item)
    submission.save()
    if image:
        transaction.on_commit(lambda: private_storage().delete(image), robust=True)
    return submission


def photo_targets(business, source, kind):
    if kind == "draft":
        return WhatsAppCatalogSubmission.objects.filter(
            sender__business=business, owner_id=business.owner_id, status=Status.REVIEW,
        ).exclude(pk=source.pk).exclude(body="")
    if kind == "item" and business.is_published:
        return business.catalog_items.filter(is_active=True)
    return BusinessCatalogItem.objects.none()


@transaction.atomic
def attach_photo(business, source_id, kind, target_id, source_version, target_version):
    locked = BusinessProfile.objects.select_for_update().get(pk=business.pk, owner_id=business.owner_id)
    source = WhatsAppCatalogSubmission.objects.select_for_update().filter(
        pk=source_id, sender__business=locked, owner_id=locked.owner_id,
    ).first()
    if source is None or not source.can_attach_photo or source.updated_at.isoformat() != source_version:
        raise CatalogueReview("Cette photo a changé. Repars de la liste des imports.")
    target = photo_targets(locked, source, kind).select_for_update().filter(pk=target_id).first()
    if target is None or target.updated_at.isoformat() != target_version:
        raise CatalogueReview("La destination a changé. Vérifie-la de nouveau avant de confirmer.")

    image = source.private_image
    if not private_storage().exists(image):
        raise CatalogueReview("La photo est introuvable. Transfère-la de nouveau depuis WhatsApp.")
    if kind == "draft":
        previous = target.private_image
        target.private_image = image
        target.save(update_fields=["private_image", "updated_at"])
        source.attached_to = target
        if previous and previous != image:
            transaction.on_commit(lambda: private_storage().delete(previous), robust=True)
    else:
        _set_item_image(target, image)
        target.save(update_fields=["image", "updated_at"])
        source.item = target
        transaction.on_commit(lambda: private_storage().delete(image), robust=True)
    source.status = Status.ATTACHED
    source.private_image = ""
    source.reason = ""
    source.save(update_fields=["status", "private_image", "reason", "item", "attached_to", "updated_at"])
    return target


def dispatch_catalog_submissions(publish):
    waba, phone_id, token = _receiver()
    if not all((waba, phone_id, token)) or _is_shared_phone(phone_id):
        return 0
    now = timezone.now()
    WhatsAppCatalogSubmission.objects.filter(status=Status.PROCESSING, updated_at__lt=now - timedelta(minutes=5)).update(
        status=Status.REVIEW, reason="Traitement interrompu. Vérifie les informations.",
        updated_at=now,
    )
    due = WhatsAppCatalogSubmission.objects.filter(
        status=Status.PENDING, dispatch_after__lte=now,
    ).order_by("dispatch_after", "pk").values_list("pk", flat=True)[:20]
    count = 0
    for pk in list(due):
        if not WhatsAppCatalogSubmission.objects.filter(pk=pk, status=Status.PENDING, dispatch_after__lte=now).update(
            dispatch_after=now + timedelta(seconds=30),
        ):
            continue
        try:
            publish(pk)
        except Exception:
            logger.warning("Envoi Celery indisponible pour l’import WhatsApp %s.", pk, exc_info=True)
        else:
            count += 1
    return count
