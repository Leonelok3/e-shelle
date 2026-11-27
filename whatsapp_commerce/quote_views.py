import re

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from .entitlements import require_whatsapp_entitlement
from .inbox import send_business_reply
from .models import BusinessWhatsAppContact, WhatsAppQuote
from .onboarding import MetaOnboardingError
from .views import _owned_business

Status = WhatsAppQuote.Status


class QuoteForm(forms.ModelForm):
    contact = forms.ModelChoiceField(queryset=BusinessWhatsAppContact.objects.none(), label="Client")
    currency = forms.ChoiceField(choices=[(currency, currency) for currency in ("XAF", "EUR", "CAD", "USD")], label="Devise")

    class Meta:
        model = WhatsAppQuote
        fields = ["contact", "subject", "description", "amount", "currency", "valid_until"]
        labels = {"subject": "Objet", "description": "Détail", "amount": "Montant", "valid_until": "Valable jusqu’au"}
        widgets = {"valid_until": forms.DateInput(attrs={"type": "date"}), "description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contact"].queryset = BusinessWhatsAppContact.objects.filter(business=business, opted_out_at__isnull=True)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Indique un montant supérieur à zéro.")
        return amount

    def clean_valid_until(self):
        date = self.cleaned_data["valid_until"]
        if date < timezone.localdate():
            raise forms.ValidationError("Choisis une date de validité à venir.")
        return date


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def quotes(request, business_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_use_crm"):
        return redirect("tarifs")
    form = QuoteForm(request.POST if request.method == "POST" else None, business=business)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Brouillon de devis enregistré.")
        return redirect("whatsapp_commerce:quotes", business_id=business.pk)
    records = WhatsAppQuote.objects.filter(contact__business=business).select_related("contact").order_by("-created_at", "-pk")
    due = BusinessWhatsAppContact.objects.filter(
        business=business, next_follow_up_at__lte=timezone.localdate(), opted_out_at__isnull=True,
    ).exclude(pipeline_status__in=[BusinessWhatsAppContact.PipelineStatus.WON, BusinessWhatsAppContact.PipelineStatus.LOST])
    page = Paginator(records, 25).get_page(request.GET.get("page"))
    return render(request, "whatsapp_commerce/quotes.html", {"business": business, "form": form, "page": page, "due": due[:20], "today": timezone.localdate()})


@login_required
@require_POST
def update_quote(request, business_id, quote_id):
    business = _owned_business(request, business_id)
    if not require_whatsapp_entitlement(business, "can_use_crm"):
        return redirect("tarifs")
    rows = WhatsAppQuote.objects.filter(contact__business=business, pk=quote_id)
    quote = get_object_or_404(rows.select_related("contact"))
    action = request.POST.get("action")
    if action == "close":
        rows.filter(status__in=[Status.DRAFT, Status.SENT, Status.ACCEPTED, Status.REVIEW]).update(status=Status.CLOSED, updated_at=timezone.now())
    elif action == "send":
        if rows.filter(status=Status.DRAFT, valid_until__gte=timezone.localdate(), contact__consent_service=True).update(status=Status.SENDING, updated_at=timezone.now()):
            text = f"Devis de {business.display_name}\n{quote.subject}\n{quote.description}\n{quote.amount} {quote.currency}\nValable jusqu’au {quote.valid_until:%d/%m/%Y}.\nRéponds ACCEPTER DEVIS {quote.code} pour donner ton accord."
            try:
                send_business_reply(quote.contact, text)
            except MetaOnboardingError as exc:
                rows.filter(status=Status.SENDING).update(status=Status.REVIEW, updated_at=timezone.now())
                messages.error(request, str(exc))
            else:
                rows.filter(status=Status.SENDING).update(status=Status.SENT, updated_at=timezone.now())
    else:
        raise Http404
    return redirect("whatsapp_commerce:quotes", business_id=business.pk)


def accept_quote(contact, body):
    match = re.fullmatch(r"ACCEPTER\s+DEVIS\s+([a-f0-9]{32})", body.strip(), re.IGNORECASE)
    if not match:
        return None
    rows = WhatsAppQuote.objects.filter(contact=contact, reference=match[1], valid_until__gte=timezone.localdate())
    if rows.filter(status=Status.SENT).update(status=Status.ACCEPTED, updated_at=timezone.now()):
        return "Ton accord sur le devis a été transmis à l’équipe.", True
    if rows.filter(status=Status.ACCEPTED).exists():
        return "Ton accord a déjà été enregistré.", False
    return "Ce devis est introuvable ou sa validité a expiré.", False
