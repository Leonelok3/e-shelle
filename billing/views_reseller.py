import secrets
import string
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from django.http import HttpResponseForbidden, Http404
from django.contrib.contenttypes.models import ContentType

from .models import (
    AffiliateProductConfig, 
    ResellerProductLink, 
    AffiliateOrder, 
    ProviderWallet, 
    Transaction, 
    Commission, 
    AffiliateProfile
)
from business.models import BusinessProfile


def reseller_checkout_view(request, promo_code):
    """
    Page publique de commande rapide (Cash on Delivery) via un lien affilié.
    """
    link = get_object_or_404(ResellerProductLink, promo_code=promo_code)
    
    # Récupérer la config d'affiliation pour ce produit
    config = AffiliateProductConfig.objects.filter(
        content_type=link.content_type,
        object_id=link.object_id,
        is_active=True
    ).first()
    
    if not config:
        raise Http404("Ce produit n'est plus éligible à la revente.")

    product = link.content_object
    if not product:
        raise Http404("Le produit n'existe plus.")
        
    provider_profile = None
    if hasattr(product, "business"):
        provider_profile = product.business
    elif hasattr(product, "restaurant"):
        resto = product.restaurant
        provider_profile = BusinessProfile.objects.filter(
            owner=resto.owner, 
            module="resto"
        ).first()

    if not provider_profile:
        raise Http404("Prestataire non configuré pour la revente.")

    # Vérifier que le portefeuille du prestataire existe et a un solde suffisant
    wallet, _ = ProviderWallet.objects.get_or_create(business=provider_profile)
    required_balance = config.reseller_commission + config.platform_fee

    if wallet.balance < required_balance:
        return render(request, "billing/reseller/provider_unavailable.html", {
            "product": product,
            "provider": provider_profile,
        })

    if request.method == "POST":
        buyer_name = request.POST.get("buyer_name", "").strip()
        buyer_phone = request.POST.get("buyer_phone", "").strip()
        buyer_address = request.POST.get("buyer_address", "").strip()

        if not buyer_name or not buyer_phone or not buyer_address:
            messages.error(request, "Veuillez remplir tous les champs requis.")
        else:
            with db_transaction.atomic():
                # Re-vérification du solde sous verrouillage
                wallet = ProviderWallet.objects.select_for_update().get(pk=wallet.pk)
                if wallet.balance < required_balance:
                    messages.error(request, "Le prestataire n'est plus disponible pour le moment. Veuillez réessayer plus tard.")
                else:
                    order = AffiliateOrder.objects.create(
                        content_type=link.content_type,
                        object_id=link.object_id,
                        reseller=link.reseller,
                        provider_profile=provider_profile,
                        buyer_name=buyer_name,
                        buyer_phone=buyer_phone,
                        buyer_address=buyer_address,
                        amount_total=config.price,
                        reseller_commission=config.reseller_commission,
                        platform_fee=config.platform_fee,
                        status="PENDING",
                    )
                    return redirect("billing:order_success", reference=order.reference)

    return render(request, "billing/reseller/checkout.html", {
        "product": product,
        "config": config,
        "link": link,
        "provider": provider_profile,
    })


def order_success_view(request, reference):
    order = get_object_or_404(AffiliateOrder, reference=reference)
    return render(request, "billing/reseller/order_success.html", {
        "order": order,
    })


@login_required
def provider_orders_view(request):
    """
    Tableau de bord des commandes reçues par affiliation pour le prestataire.
    """
    profiles = BusinessProfile.objects.filter(owner=request.user)
    orders = AffiliateOrder.objects.filter(provider_profile__in=profiles).order_by("-created_at")
    
    wallets = []
    for p in profiles:
        w, _ = ProviderWallet.objects.get_or_create(business=p)
        wallets.append(w)

    return render(request, "billing/reseller/dashboard_orders.html", {
        "orders": orders,
        "wallets": wallets,
        "profiles": profiles,
    })


@login_required
def validate_delivery_view(request, order_id):
    """
    Action pour valider la livraison d'une commande via le code secret à 4 chiffres.
    """
    if request.method != "POST":
        return redirect("billing:provider_affiliate_orders")

    profiles = BusinessProfile.objects.filter(owner=request.user)
    order = get_object_or_404(AffiliateOrder, id=order_id, provider_profile__in=profiles, status="PENDING")

    code_entered = request.POST.get("delivery_code", "").strip()
    
    if code_entered != order.delivery_code:
        messages.error(request, "Code de validation incorrect.")
        return redirect("billing:provider_affiliate_orders")

    required_amount = order.reseller_commission + order.platform_fee
    
    try:
        with db_transaction.atomic():
            wallet = ProviderWallet.objects.select_for_update().get(business=order.provider_profile)
            if wallet.balance < required_amount:
                messages.error(request, f"Votre solde (actuel: {wallet.balance} FCFA) est insuffisant pour valider cette livraison. Veuillez recharger votre portefeuille.")
                return redirect("billing:provider_affiliate_orders")

            # 1. Débiter le portefeuille du prestataire
            wallet.debit(required_amount)

            # 2. Créer la Transaction de crédit pour l'affilié
            buyer_user = request.user
            if order.reseller:
                buyer_user = order.reseller.user
                
            tx = Transaction.objects.create(
                user=buyer_user,
                amount=order.amount_total,
                currency="XAF",
                type="CREDIT",
                status="COMPLETED",
                payment_method="OTHER",
                description=f"Achat revente : {order.reference}",
                metadata={"order_reference": order.reference, "product_type": "affiliate_product"},
            )

            # 3. Créer et payer la Commission du revendeur
            if order.reseller:
                Commission.objects.create(
                    transaction=tx,
                    affiliate=order.reseller,
                    amount=order.reseller_commission,
                    currency="XAF",
                    rate=Decimal(order.reseller_commission / order.amount_total).quantize(Decimal("0.01")),
                    status="PAID",
                )

            # 4. Marquer la commande comme LIVRÉE
            order.status = "DELIVERED"
            order.save(update_fields=["status", "updated_at"])

            messages.success(request, f"Félicitations ! Commande {order.reference} validée avec succès. Les commissions ont été reversées.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la validation : {str(e)}")

    return redirect("billing:provider_affiliate_orders")


@login_required
def provider_wallet_view(request):
    """
    Vue pour consulter et alimenter le portefeuille prépayé.
    """
    profiles = BusinessProfile.objects.filter(owner=request.user)
    wallets = []
    for p in profiles:
        w, _ = ProviderWallet.objects.get_or_create(business=p)
        wallets.append(w)

    if request.method == "POST":
        amount_str = request.POST.get("amount", "0").strip()
        business_id = request.POST.get("business_id")
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                messages.error(request, "Veuillez entrer un montant supérieur à 0.")
            else:
                profile = get_object_or_404(BusinessProfile, id=business_id, owner=request.user)
                wallet = ProviderWallet.objects.get(business=profile)
                wallet.credit(amount)
                messages.success(request, f"Votre portefeuille pour {profile.name} a été rechargé de {amount} FCFA avec succès !")
                return redirect("billing:provider_wallet")
        except ValueError:
            messages.error(request, "Montant invalide.")

    return render(request, "billing/reseller/wallet.html", {
        "wallets": wallets,
        "profiles": profiles,
    })
