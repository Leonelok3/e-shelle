"""
Service d'intégration Stripe pour cartes bancaires
"""
import stripe
from django.conf import settings
from .payment_config import STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY

stripe.api_key = STRIPE_SECRET_KEY


def create_stripe_checkout_session(amount_usd, plan_name, user_email, success_url, cancel_url, transaction_id):
    """
    Crée une session Stripe Checkout
    
    Args:
        amount_usd: Montant en USD
        plan_name: Nom du plan
        user_email: Email de l'utilisateur
        success_url: URL de retour après succès
        cancel_url: URL de retour après annulation
        transaction_id: ID de la transaction
    
    Returns:
        dict: Session Stripe avec checkout_url
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Immigration97 - {plan_name}',
                        'description': f'Abonnement {plan_name}',
                    },
                    'unit_amount': int(float(amount_usd) * 100),  # Stripe utilise les centimes
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url + f'?session_id={{CHECKOUT_SESSION_ID}}&transaction_id={transaction_id}',
            cancel_url=cancel_url + f'?transaction_id={transaction_id}',
            customer_email=user_email,
            metadata={
                'transaction_id': str(transaction_id),
            }
        )
        
        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def verify_stripe_session(session_id):
    """
    Vérifie le statut d'une session Stripe
    
    Args:
        session_id: ID de la session Stripe
    
    Returns:
        dict: Statut du paiement
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        return {
            "success": session.payment_status == "paid",
            "status": session.payment_status,
            "amount": session.amount_total / 100,  # Convertir centimes en dollars
            "metadata": session.metadata
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }