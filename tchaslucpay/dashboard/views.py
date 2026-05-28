from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from io import BytesIO

from .forms import ClientTerrainForm, NouvelleTransactionForm
from .mixins import client_required, collecteur_required
from tchaslucpay.accounts.models import ClientProfile, UserRole
from tchaslucpay.transactions.models import AccountBalance, Transaction, TransactionStatus, TransactionType
from tchaslucpay.transactions.services import creer_transaction


OBJECTIF_MENSUEL_COLLECTEUR = Decimal("1000000.00")


def _dashboard_context(user):
    balance = AccountBalance.objects.filter(user=user).first()
    transactions = Transaction.objects.filter(account=user).order_by("-created_at")[:10]
    client_profile = ClientProfile.objects.filter(user=user).first()
    return {"balance": balance, "client_profile": client_profile, "transactions": transactions}


def home(request):
    dashboard_url = reverse("tchaslucpay_accounts:login")
    role = getattr(request.user, "role", None)
    if request.user.is_authenticated:
        if request.user.is_staff or role == UserRole.ADMIN:
            dashboard_url = reverse("tchaslucpay_dashboard:admin")
        elif role == UserRole.COLLECTEUR:
            dashboard_url = reverse("tchaslucpay_dashboard:collecteur")
        elif role == UserRole.CLIENT:
            dashboard_url = reverse("tchaslucpay_dashboard:client")

    return render(request, "tchaslucpay/dashboard/index.html", {"dashboard_url": dashboard_url})


@login_required
def admin_dashboard(request):
    context = {
        "balances_count": ClientProfile.objects.count(),
        "transactions": Transaction.objects.select_related("account", "collector").order_by("-created_at")[:25],
    }
    return render(request, "tchaslucpay/dashboard/admin.html", context)


@login_required
@collecteur_required
def collecteur_dashboard(request):
    collecteur = getattr(request.user, "collecteur_profile", None)
    if collecteur is None:
        messages.error(request, "Votre profil collecteur n'est pas encore configure.")
        return render(request, "tchaslucpay/dashboard/index.html", status=403)

    clients = collecteur.clients.select_related("user", "trusted_collecteur").order_by("user__first_name", "user__last_name")
    client_form = ClientTerrainForm(request.POST or None)

    if request.method == "POST":
        if client_form.is_valid():
            client = client_form.save(collecteur)
            messages.success(
                request,
                f"Client {client.user.get_full_name() or client.user.username} ajoute et assigne a votre portefeuille. "
                "Aucun depot n'a ete enregistre automatiquement : utilisez « Enregistrer une operation » pour creer un depot ou un retrait."
            )
            return redirect("tchaslucpay_dashboard:collecteur")
        messages.error(request, "Veuillez corriger les informations du nouveau client.")

    now = timezone.localtime(timezone.now())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    volume_mensuel = (
        Transaction.objects.filter(
            collector=request.user,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.POSTED,
            created_at__gte=month_start,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    progress_value = min(int((volume_mensuel / OBJECTIF_MENSUEL_COLLECTEUR) * 100), 100)

    context = {
        "collecteur": collecteur,
        "clients": clients,
        "client_form": client_form,
        "volume_mensuel": volume_mensuel,
        "objectif_mensuel": OBJECTIF_MENSUEL_COLLECTEUR,
        "progress_value": progress_value,
        "is_elite": volume_mensuel >= OBJECTIF_MENSUEL_COLLECTEUR,
        "collected_transactions": Transaction.objects.filter(collector=request.user)
        .select_related("account")
        .order_by("-created_at")[:25],
        "demo_mode": request.user.username.startswith("collecteur_"),
    }
    return render(request, "tchaslucpay/dashboard/dashboard_collecteur.html", context)


@login_required
@collecteur_required
def collecteur_action(request):
    collecteur = getattr(request.user, "collecteur_profile", None)
    if collecteur is None:
        messages.error(request, "Seul un collecteur actif peut enregistrer une operation.")
        return redirect("tchaslucpay_dashboard:home")

    clients = (
        ClientProfile.objects.filter(trusted_collecteur=collecteur)
        .select_related("user", "trusted_collecteur")
        .order_by("user__first_name", "user__last_name", "account_number")
    )

    if request.method == "POST":
        client_id = request.POST.get("client_id")
        type_op = request.POST.get("type_op")
        montant = request.POST.get("montant")
        note = request.POST.get("note")

        if type_op not in {"DEPOT", "RETRAIT"}:
            messages.error(request, "Type d'operation invalide.")
            return redirect("tchaslucpay_dashboard:collecteur_action")

        if not clients.filter(pk=client_id).exists():
            messages.error(request, "Ce client n'est pas assigne a votre portefeuille.")
            return redirect("tchaslucpay_dashboard:collecteur_action")

        try:
            transaction_obj = creer_transaction(
                client_id=client_id,
                collecteur_id=collecteur.pk,
                type_op=type_op,
                montant=montant,
                note=note,
            )
        except (ValidationError, ValueError) as exc:
            error = " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            messages.error(request, error)
        else:
            messages.success(request, f"Operation validee. TRID: {transaction_obj.trid}.")
            return redirect("tchaslucpay_dashboard:collecteur")

    return render(request, "tchaslucpay/dashboard/collecteur_action.html", {"clients": clients})


@login_required
@collecteur_required
def nouvelle_transaction(request):
    collecteur = getattr(request.user, "collecteur_profile", None)
    if collecteur is None:
        messages.error(request, "Seul un collecteur actif peut enregistrer une transaction.")
        return redirect("tchaslucpay_dashboard:home")

    form = NouvelleTransactionForm(request.POST or None, collecteur=collecteur)
    if request.method == "POST" and form.is_valid():
        client = form.cleaned_data["client"]
        try:
            transaction_obj = creer_transaction(
                client_id=client.pk,
                collecteur_id=collecteur.pk,
                type_op=form.cleaned_data["type_op"],
                montant=form.cleaned_data["montant"],
                note=form.cleaned_data.get("note"),
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, f"Transaction {transaction_obj.trid} enregistree avec succes.")
            return redirect("tchaslucpay_dashboard:collecteur")

    return render(request, "dashboard/nouvelle_transaction.html", {"form": form})


@login_required
@client_required
def client_dashboard(request):
    client_profile = getattr(request.user, "client_profile", None)
    if client_profile is None:
        messages.error(request, "Votre profil client n'est pas encore configure.")
        return render(request, "tchaslucpay/dashboard/index.html", status=403)

    collecteur = client_profile.trusted_collecteur
    transactions = Transaction.objects.filter(account=request.user).select_related("collector").order_by("-created_at")[:25]
    context = {
        "client_profile": client_profile,
        "collecteur": collecteur,
        "transactions": transactions,
    }
    return render(request, "tchaslucpay/dashboard/dashboard_client.html", context)


@login_required
def receipt_pdf(request, transaction_id):
    transaction_obj = get_object_or_404(
        Transaction.objects.select_related("account", "collector"),
        pk=transaction_id,
    )
    role = getattr(request.user, "role", "CLIENT")
    if role == "COLLECTEUR" and transaction_obj.collector_id != request.user.pk:
        messages.error(request, "Vous ne pouvez telecharger que vos propres recus.")
        return redirect("tchaslucpay_dashboard:home")
    if role == "CLIENT" and transaction_obj.account_id != request.user.pk:
        messages.error(request, "Ce recu ne correspond pas a votre compte.")
        return redirect("tchaslucpay_dashboard:home")

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        messages.error(request, "ReportLab doit etre installe pour generer les recus PDF.")
        return redirect("tchaslucpay_dashboard:home")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    created_at = timezone.localtime(transaction_obj.created_at)
    client_name = transaction_obj.account.get_full_name() or transaction_obj.account.username
    collector_name = transaction_obj.collector.get_full_name() if transaction_obj.collector else "N/A"
    transaction_label = transaction_obj.get_transaction_type_display()
    amount = f"{transaction_obj.amount:,.0f} XAF".replace(",", " ")
    balance_before = f"{transaction_obj.balance_before:,.0f} XAF".replace(",", " ")
    balance_after = f"{transaction_obj.balance_after:,.0f} XAF".replace(",", " ")

    navy = colors.HexColor("#07182F")
    emerald = colors.HexColor("#0FA36B")
    cream = colors.HexColor("#F7F4ED")
    muted = colors.HexColor("#667085")
    border = colors.HexColor("#D8DEE8")

    def money_card(x, y, title, value, fill):
        pdf.setFillColor(fill)
        pdf.roundRect(x, y, 156, 70, 8, stroke=0, fill=1)
        pdf.setFillColor(colors.white if fill == navy else navy)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(x + 14, y + 45, title)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x + 14, y + 22, value)

    def row(label, value, x, y):
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x, y, label)
        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x + 115, y, value)

    # En-tete institutionnel.
    pdf.setFillColor(navy)
    pdf.rect(0, height - 132, width, 132, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(48, height - 58, "Tchaslucpay")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, height - 80, "Microfinance digitale de proximite")
    pdf.setFillColor(emerald)
    pdf.roundRect(width - 178, height - 70, 130, 32, 6, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(width - 113, height - 58, "TRANSACTION VALIDEE")

    # Titre et reference.
    y = height - 178
    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(48, y, "Recu de transaction")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(muted)
    pdf.drawString(48, y - 20, f"Emis le {created_at.strftime('%d/%m/%Y')} a {created_at.strftime('%H:%M')}")
    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(width - 48, y, f"TRID: {transaction_obj.trid}")

    # Cartes de synthese financiere.
    y -= 108
    money_card(48, y, "Montant de l'operation", amount, emerald)
    money_card(220, y, "Solde avant", balance_before, cream)
    money_card(392, y, "Solde apres", balance_after, navy)

    # Bloc details.
    y -= 54
    pdf.setStrokeColor(border)
    pdf.setFillColor(colors.white)
    pdf.roundRect(48, y - 170, width - 96, 176, 8, stroke=1, fill=1)
    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(70, y - 25, "Details de l'operation")
    row("Type", transaction_label, 70, y - 58)
    row("Client", client_name, 70, y - 84)
    row("Collecteur", collector_name, 70, y - 110)
    row("Date et heure", created_at.strftime("%d/%m/%Y %H:%M"), 70, y - 136)
    row("Statut", "Validee", 70, y - 162)

    # Message de confiance.
    y -= 220
    pdf.setFillColor(cream)
    pdf.roundRect(48, y - 58, width - 96, 76, 8, stroke=0, fill=1)
    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(70, y - 10, "Preuve de confiance")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#344054"))
    pdf.drawString(70, y - 30, "Ce recu confirme l'enregistrement comptable de votre operation dans Tchaslucpay.")
    pdf.drawString(70, y - 45, "Conservez le TRID pour toute verification ou assistance.")

    # Pied de page.
    pdf.setStrokeColor(border)
    pdf.line(48, 66, width - 48, 66)
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(48, 46, "Tchaslucpay - Plateforme de microfinance digitale")
    pdf.drawRightString(width - 48, 46, "Recu genere automatiquement")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="recu-{transaction_obj.trid}.pdf"'
    return response
