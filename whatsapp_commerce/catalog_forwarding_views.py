from decimal import Decimal
from hashlib import sha256
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from business.models import BusinessProfile
from whatsapp_agent.media import private_storage
from .catalog_forwarding import (
    CatalogueReview, Status, _matching_items, attach_photo, issue_pairing, photo_targets, receiver_number,
    review_submission,
)
from .catalog_messages import CURRENCIES
from .models import WhatsAppCatalogSender, WhatsAppCatalogSubmission
from .services import normalize_phone

PHOTO_PREVIEW_SALT = "whatsapp_commerce.catalog_photo_preview"


class OfferReviewForm(forms.Form):
    title = forms.CharField(label="Nom du produit", max_length=140)
    price_amount = forms.DecimalField(label="Prix", max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    currency = forms.ChoiceField(label="Devise", choices=CURRENCIES)
    sku = forms.RegexField(label="Référence", regex=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$", required=False, max_length=80)
    stock = forms.IntegerField(label="Stock", min_value=0, max_value=999999999, required=False)

    def clean_sku(self):
        return self.cleaned_data["sku"].upper()

    def clean(self):
        data = super().clean()
        price = data.get("price_amount")
        if data.get("currency") == "XAF" and price is not None and price != price.to_integral_value():
            self.add_error("price_amount", "Indique un montant entier en francs CFA.")
        return data


def _business(request, business_id):
    return get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)


def _drafts(business):
    return WhatsAppCatalogSubmission.objects.filter(sender__business=business, owner_id=business.owner_id)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def catalogue(request, business_id):
    business = _business(request, business_id)
    sender = WhatsAppCatalogSender.objects.filter(business=business, owner=request.user).first()
    destination = receiver_number()
    session_key = f"catalog_pair_{business.pk}"
    url = reverse("whatsapp_commerce:catalog_forwarding", args=[business.pk])
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "disconnect" and sender:
            WhatsAppCatalogSender.objects.filter(pk=sender.pk, owner=request.user).update(
                phone=None, requested_phone="", pairing_digest="", pairing_expires_at=None, auto_publish=False,
            )
            request.session.pop(session_key, None)
            messages.success(request, "Le numéro expéditeur a été dissocié.")
        elif action == "settings" and sender and sender.phone:
            WhatsAppCatalogSender.objects.filter(pk=sender.pk, owner=request.user, phone=sender.phone).update(
                auto_publish=request.POST.get("auto_publish") == "on",
            )
            messages.success(request, "Mode de publication enregistré.")
        elif action == "pair" and destination:
            phone = normalize_phone(request.POST.get("sender_phone", ""))
            occupied = WhatsAppCatalogSender.objects.filter(phone=phone).exclude(business=business).exists()
            if not phone or phone == destination:
                messages.error(request, "Indique le numéro WhatsApp du prestataire, avec son indicatif.")
            elif occupied:
                messages.error(request, "Ce numéro est déjà associé à une fiche. Dissocie-le avant de le réutiliser.")
            else:
                request.session[session_key] = issue_pairing(business, phone)
        else:
            messages.error(request, "L’import WhatsApp est indisponible pour ce réglage.")
        return redirect(url)
    code = ""
    if sender and sender.pairing_expires_at and sender.pairing_expires_at > timezone.now():
        candidate = request.session.get(session_key, "")
        if sha256(candidate.encode()).hexdigest() == sender.pairing_digest:
            code = candidate
    wa_link = f"https://wa.me/{destination.lstrip('+')}" if destination else ""
    response = render(request, "whatsapp_commerce/catalog_forwarding.html", {
        "business": business, "sender": sender, "destination": destination,
        "pairing_code": code,
        "pairing_link": f"{wa_link}?{urlencode({'text': f'LIER {code}'})}" if wa_link and code else "",
        "submissions": _drafts(business).select_related("item", "attached_to__item")[:25],
    })
    response["Referrer-Policy"] = "no-referrer"
    return response


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def review(request, business_id, submission_id):
    business = _business(request, business_id)
    submission = get_object_or_404(_drafts(business), pk=submission_id, status=Status.REVIEW)
    form = OfferReviewForm(request.POST if request.method == "POST" else None, initial={
        "title": submission.title, "price_amount": submission.price_amount,
        "currency": submission.currency, "sku": submission.sku, "stock": submission.stock,
    })
    action = request.POST.get("action") if request.method == "POST" else None
    approved_fields = form.cleaned_data if action in {"publish", "update"} and form.is_valid() else None
    title = approved_fields["title"] if approved_fields else submission.title
    sku = approved_fields["sku"] if approved_fields else submission.sku
    matches = _matching_items(business, title, sku) if title or sku else []
    existing = matches[0] if len(matches) == 1 else None
    if request.method == "POST":
        if action == "reject" or approved_fields:
            if action == "update" and existing is None:
                form.add_error(None, "Recharge la page pour vérifier l’article à mettre à jour.")
            else:
                try:
                    reviewed = review_submission(
                        business, submission.pk, {**(approved_fields or {}), "item_version": request.POST.get("item_version", "")},
                        update_item_id=existing.pk if action == "update" else None, reject=action == "reject",
                    )
                except CatalogueReview as exc:
                    form.add_error(None, str(exc))
                except WhatsAppCatalogSubmission.DoesNotExist as exc:
                    raise Http404 from exc
                else:
                    if action == "reject":
                        messages.success(request, "Le brouillon a été écarté.")
                    else:
                        messages.success(request, "Le produit est publié sur ta fiche.")
                        from .tasks import notify_whatsapp_catalog_published

                        try:
                            notify_whatsapp_catalog_published.apply_async(args=[reviewed.pk], retry=False, expires=90)
                        except Exception:
                            messages.info(request, "Le lien du produit reste disponible dans ce tableau de bord.")
                    return redirect("whatsapp_commerce:catalog_forwarding", business_id=business.pk)
    return render(request, "whatsapp_commerce/catalog_forward_review.html", {
        "business": business, "submission": submission, "form": form, "existing": existing,
        "item_version": f"{existing.pk}:{existing.updated_at.isoformat()}" if existing else "",
    })


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def photo_attachment(request, business_id, submission_id):
    business = _business(request, business_id)
    source = get_object_or_404(_drafts(business), pk=submission_id)
    if not source.can_attach_photo:
        raise Http404
    url = reverse("whatsapp_commerce:catalog_forward_attach", args=[business.pk, source.pk])
    if request.method == "POST":
        try:
            approval = signing.loads(request.POST.get("approval", ""), salt=PHOTO_PREVIEW_SALT, max_age=900)
            if approval["scope"] != [business.pk, request.user.pk, source.pk]:
                raise signing.BadSignature
            target = attach_photo(
                business, source.pk, approval["kind"], approval["target"],
                approval["source_version"], approval["target_version"],
            )
        except signing.BadSignature:
            messages.error(request, "L’aperçu a expiré. Sélectionne de nouveau la destination.")
            return redirect(url)
        except CatalogueReview as exc:
            messages.error(request, str(exc))
            return redirect(url)
        if approval["kind"] == "draft":
            messages.success(request, "Photo rattachée au brouillon. Vérifie l’offre avant de la publier.")
            return redirect("whatsapp_commerce:catalog_forward_review", business_id=business.pk, submission_id=target.pk)
        messages.success(request, "La photo de l’article publié a été mise à jour.")
        return redirect("whatsapp_commerce:catalog_forwarding", business_id=business.pk)

    query = request.GET.get("q", "").strip()[:100]
    drafts = photo_targets(business, source, "draft")
    items = photo_targets(business, source, "item")
    if query:
        terms = Q(title__icontains=query) | Q(sku__icontains=query)
        drafts = drafts.filter(terms | Q(body__icontains=query))
        items = items.filter(terms)
    selection = request.GET.get("target", "")
    kind, _, target_id = selection.partition(":")
    target = None
    approval = ""
    if kind in {"draft", "item"} and target_id.isascii() and target_id.isdecimal() and len(target_id) <= 18:
        target = get_object_or_404(photo_targets(business, source, kind), pk=int(target_id))
        approval = signing.dumps({
            "scope": [business.pk, request.user.pk, source.pk],
            "kind": kind, "target": target.pk,
            "source_version": source.updated_at.isoformat(), "target_version": target.updated_at.isoformat(),
        }, salt=PHOTO_PREVIEW_SALT)
    return render(request, "whatsapp_commerce/catalog_attach_photo.html", {
        "business": business, "source": source, "drafts": drafts[:25], "items": items[:50],
        "query": query, "selection": selection, "target": target, "kind": kind, "approval": approval,
    })


@login_required
@never_cache
@require_GET
def image(request, business_id, submission_id):
    business = _business(request, business_id)
    submission = get_object_or_404(_drafts(business), pk=submission_id, status=Status.REVIEW)
    if not submission.private_image:
        raise Http404
    try:
        photo = private_storage().open(submission.private_image)
    except FileNotFoundError as exc:
        raise Http404 from exc
    response = FileResponse(photo, content_type="image/jpeg")
    response["X-Content-Type-Options"] = "nosniff"
    return response
