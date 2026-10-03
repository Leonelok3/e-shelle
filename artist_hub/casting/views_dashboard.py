"""Staff-only casting management, shared filters, verified actions and statistics."""
import csv
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import View, ListView, DetailView, TemplateView
from .models import Candidate, CandidateStatus, CandidateGender
from .staff_filters import filtered_candidates
from artist_hub.conf import hub_settings
from artist_hub.payments.models import Payment, PaymentStatus
from artist_hub.payments.services import handle_payment_success
from .services import finalize_candidate_registration

@method_decorator(never_cache, name="dispatch")
class StaffOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and user.is_staff
    def handle_no_permission(self):
        messages.error(self.request, "Accès réservé aux membres de l’équipe staff.")
        return redirect(reverse("admin:login") + "?next=" + self.request.path)

def metrics(qs):
    total = qs.count()
    paid = qs.filter(payment__status=PaymentStatus.SUCCESS).count()
    payments = Payment.objects.filter(pk__in=qs.order_by().values("payment_id"), status=PaymentStatus.SUCCESS)
    by_currency = list(payments.values("currency").annotate(amount=Sum("amount"), count=Count("pk")).order_by("currency"))
    return {"total": total, "inscrits": paid,
        "pending_validation": qs.filter(status=CandidateStatus.EN_ATTENTE_VALIDATION).count(),
        "preselected": qs.filter(status=CandidateStatus.PRESELECTIONNE).count(),
        "retained": qs.filter(status=CandidateStatus.RETENU).count(),
        "revenue": payments.filter(currency="XAF").aggregate(total=Sum("amount"))["total"] or 0,
        "revenue_count": payments.count(), "by_currency": by_currency,
        "conversion_rate": round(paid * 100 / total, 1) if total else 0}

def filter_context(request, qs, form):
    query = request.GET.copy()
    query.pop("page", None)
    return {"hub_settings": hub_settings, "filter_form": form, "filter_query": query.urlencode(), "kpis": metrics(qs)}

def validate_payment(candidate, user):
    if not candidate.payment_id:
        raise ValueError("Ce dossier n’a aucun paiement associé.")
    payment = Payment.objects.select_for_update().get(pk=candidate.payment_id)
    if not payment.content_type_id or str(payment.object_id) != str(candidate.pk) or payment.content_type.model_class() is not Candidate:
        raise ValueError("Le paiement n’est pas rattaché à ce candidat.")
    if payment.currency != candidate.session.currency or payment.amount < candidate.required_fee:
        raise ValueError("Le montant ou la devise ne correspond pas aux frais exigés.")
    if payment.status != PaymentStatus.SUCCESS:
        if payment.provider != "manual_proof" and not (settings.DEBUG and payment.provider == "mock"):
            raise ValueError("Ce paiement doit être confirmé par sa passerelle.")
        if payment.provider == "manual_proof" and not (payment.proof_file or payment.external_reference):
            raise ValueError("Ajoutez une preuve ou une référence de versement avant validation.")
    handle_payment_success(payment, verified_by_user=user)
    candidate.refresh_from_db()
    finalize_candidate_registration(candidate, verified_by_user=user)

def set_candidate_status(candidate, status):
    allowed = {CandidateStatus.INSCRIT, CandidateStatus.PRESELECTIONNE, CandidateStatus.RETENU, CandidateStatus.REFUSE}
    if status not in allowed:
        raise ValueError("Statut non autorisé : les étapes de paiement sont gérées automatiquement.")
    if status != CandidateStatus.REFUSE and not (candidate.payment and candidate.payment.is_successful):
        raise ValueError("Le paiement doit être confirmé avant l’inscription ou la sélection.")
    candidate.status = status
    candidate.save(update_fields=["status", "updated_at"])

class StaffDashboardListView(StaffOnlyMixin, ListView):
    model = Candidate
    template_name = "artist_hub/staff/dashboard.html"
    context_object_name = "candidates"
    paginate_by = 25
    def get_queryset(self):
        self.filtered, self.filter_form = filtered_candidates(self.request.GET)
        return self.filtered
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(filter_context(self.request, self.filtered, self.filter_form))
        return ctx

class StaffCandidateDetailView(StaffOnlyMixin, DetailView):
    model = Candidate
    queryset = Candidate.objects.select_related("session", "payment").prefetch_related("photos")
    template_name = "artist_hub/staff/candidate_detail.html"
    context_object_name = "candidate"
    slug_field = "candidate_number"
    slug_url_kwarg = "candidate_number"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(hub_settings=hub_settings, photos=self.object.photos.all(), payment=self.object.payment)
        ctx["status_choices"] = [(value, label) for value, label in CandidateStatus.choices if value in
            {CandidateStatus.INSCRIT, CandidateStatus.PRESELECTIONNE, CandidateStatus.RETENU, CandidateStatus.REFUSE}]
        return ctx
    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            candidate = Candidate.objects.select_for_update().get(pk=self.get_object().pk)
            action = request.POST.get("action")
            try:
                if action == "validate_payment":
                    validate_payment(candidate, request.user)
                    messages.success(request, "Paiement confirmé. La décision du jury est conservée.")
                elif action == "set_status":
                    set_candidate_status(candidate, request.POST.get("new_status"))
                    messages.success(request, "Statut du dossier mis à jour.")
                elif action == "save_notes":
                    notes = request.POST.get("admin_notes", "")
                    if len(notes) > 10000: raise ValueError("Les notes sont limitées à 10 000 caractères.")
                    candidate.admin_notes = notes
                    candidate.save(update_fields=["admin_notes", "updated_at"])
                    messages.success(request, "Notes internes enregistrées.")
                else: raise ValueError("Action inconnue.")
            except ValueError as exc:
                messages.error(request, str(exc))
        return redirect("artist_hub:casting:staff_candidate_detail", candidate_number=candidate.candidate_number)

class StaffBulkActionView(StaffOnlyMixin, View):
    def post(self, request):
        selected = request.POST.getlist("selected_candidates")
        action = request.POST.get("bulk_action")
        targets = {"mark_preselected": CandidateStatus.PRESELECTIONNE,
            "mark_retained": CandidateStatus.RETENU, "mark_refused": CandidateStatus.REFUSE}
        if not selected or len(selected) > 200 or any(not value.isdigit() for value in selected):
            messages.error(request, "Sélection invalide : choisissez entre 1 et 200 dossiers.")
            return redirect("artist_hub:casting:dashboard")
        if action not in targets and action != "validate_payments":
            messages.error(request, "Action groupée inconnue.")
            return redirect("artist_hub:casting:dashboard")
        updated = skipped = 0
        for pk in Candidate.objects.filter(pk__in=selected).values_list("pk", flat=True):
            with transaction.atomic():
                candidate = Candidate.objects.select_for_update().select_related("session", "payment").get(pk=pk)
                try:
                    if action == "validate_payments": validate_payment(candidate, request.user)
                    else: set_candidate_status(candidate, targets[action])
                    updated += 1
                except ValueError:
                    skipped += 1
        messages.info(request, f"{updated} dossier(s) traité(s), {skipped} ignoré(s) : paiement à vérifier.")
        return redirect("artist_hub:casting:dashboard")

def csv_cell(value):
    if isinstance(value, str) and value.lstrip(" \t\r\n\ufeff").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value

class StaffExportCsvView(StaffOnlyMixin, View):
    def get(self, request):
        candidates, form = filtered_candidates(request.GET)
        if not form.is_valid(): return HttpResponse("Filtres invalides.", status=400)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="casting_' + timezone.now().strftime("%Y%m%d_%H%M") + '.csv"'
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Numéro", "Code Accès", "Nom", "Prénom", "Sexe", "Date Naissance", "Âge", "Taille (cm)",
            "Poids (kg)", "Mensurations", "Ville", "Pays", "Téléphone", "Email", "Statut", "Paiement Réf", "Montant", "Devise", "Paiement statut", "Date Candidature"])
        for c in candidates:
            p = c.payment
            row = [c.candidate_number, c.access_code, c.last_name, c.first_name, c.get_gender_display(),
                c.birth_date.strftime("%d/%m/%Y"), c.age, c.height_cm, c.weight_kg or "", c.measurements or "",
                c.city, c.country, c.phone, c.email, c.get_status_display(), p.reference if p else "",
                p.amount if p else "", p.currency if p else "", p.get_status_display() if p else "",
                timezone.localtime(c.created_at).strftime("%d/%m/%Y %H:%M")]
            writer.writerow([csv_cell(value) for value in row])
        return response

class StaffPaymentProofView(StaffOnlyMixin, View):
    def get(self, request, candidate_number=None, payment_id=None):
        from django.shortcuts import get_object_or_404
        if payment_id:
            payment = get_object_or_404(Payment, pk=payment_id)
            candidate_number = payment.reference
        else:
            candidate = get_object_or_404(Candidate.objects.select_related("payment"), candidate_number=candidate_number)
            payment = candidate.payment
        if not payment or not payment.proof_file: raise Http404("Aucune preuve disponible.")
        try: file = payment.proof_file.open("rb")
        except (OSError, ValueError): raise Http404("Preuve indisponible.")
        header = file.read(16)
        file.seek(0)
        mime = "application/pdf" if header.startswith(b"%PDF-") else "image/png" if header.startswith(b"\x89PNG") else "image/jpeg" if header.startswith(b"\xff\xd8") else "application/octet-stream"
        response = FileResponse(file, content_type=mime, as_attachment=mime == "application/octet-stream", filename="preuve-" + candidate_number)
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response

class StaffStatsView(StaffOnlyMixin, TemplateView):
    template_name = "artist_hub/staff/stats.html"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs, form = filtered_candidates(self.request.GET)
        ctx.update(filter_context(self.request, qs, form))
        data = ctx["kpis"]
        ctx.update(total=data["total"], revenue_total=data["revenue"], revenue_count=data["revenue_count"],
            femmes=qs.filter(gender=CandidateGender.FEMME).count(), hommes=qs.filter(gender=CandidateGender.HOMME).count())
        ctx["top_cities"] = list(qs.order_by().values("city").annotate(count=Count("pk")).order_by("-count", "city")[:10])
        counts = dict(qs.order_by().values_list("status").annotate(count=Count("pk")))
        ctx["status_data"] = [{"status": label, "count": counts.get(code, 0)} for code, label in CandidateStatus.choices]
        ctx["funnel"] = [{"label": "Dossiers déposés", "count": data["total"]}, {"label": "Paiements confirmés", "count": data["inscrits"]},
            {"label": "Présélectionnés ou retenus", "count": data["preselected"] + data["retained"]}, {"label": "Retenus", "count": data["retained"]}]
        ctx["daily"] = list(qs.order_by().annotate(day=TruncDate("created_at")).values("day").annotate(
            total=Count("pk"), paid=Count("pk", filter=Q(payment__status=PaymentStatus.SUCCESS))).order_by("day"))
        for day in ctx["daily"]: day["rate"] = round(day["paid"] * 100 / day["total"], 1)
        ages = {"Moins de 18 ans": 0, "18–24 ans": 0, "25–34 ans": 0, "35 ans et plus": 0}
        for candidate in qs.only("birth_date", "session_id", "payment_id"):
            age = candidate.age
            label = "Moins de 18 ans" if age < 18 else "18–24 ans" if age < 25 else "25–34 ans" if age < 35 else "35 ans et plus"
            ages[label] += 1
        ctx["age_data"] = [{"label": label, "count": count} for label, count in ages.items()]
        return ctx
