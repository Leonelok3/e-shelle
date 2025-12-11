"""
Service d'intégration Cinetpay pour Mobile Money
"""
import requests
import hashlib
from django.conf import settings
from .payment_config import (
    CINETPAY_API_KEY, CINETPAY_SITE_ID, CINETPAY_SECRET_KEY,
    CINETPAY_BASE_URL, CINETPAY_NOTIFY_URL, CINETPAY_RETURN_URL, CINETPAY_CANCEL_URL
)


def initiate_cinetpay_payment(transaction_id, amount, currency="XAF", customer_name="", customer_email=""):
    """
    Initie un paiement avec Cinetpay
    
    Args:
        transaction_id: ID unique de la transaction
        amount: Montant à payer
        currency: Devise (XAF par défaut)
        customer_name: Nom du client
        customer_email: Email du client
    
    Returns:
        dict: Réponse de l'API Cinetpay avec payment_url
    """
    payload = {
        "apikey": CINETPAY_API_KEY,
        "site_id": CINETPAY_SITE_ID,
        "transaction_id": str(transaction_id),
        "amount": int(amount),
        "currency": currency,
        "description": f"Paiement Immigration97 - Transaction #{transaction_id}",
        "customer_name": customer_name,
        "customer_surname": customer_name,
        "customer_email": customer_email,
        "customer_phone_number": "",
        "customer_address": "",
        "customer_city": "",
        "customer_country": "CM",
        "customer_state": "",
        "customer_zip_code": "",
        "notify_url": CINETPAY_NOTIFY_URL,
        "return_url": CINETPAY_RETURN_URL,
        "channels": "ALL",  # Tous les moyens de paiement
    }
    
    try:
        response = requests.post(CINETPAY_BASE_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == "201":
            return {
                "success": True,
                "payment_url": data["data"]["payment_url"],
                "payment_token": data["data"]["payment_token"],
            }
        else:
            return {
                "success": False,
                "error": data.get("message", "Erreur inconnue")
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def verify_cinetpay_payment(transaction_id):
    """
    Vérifie le statut d'un paiement Cinetpay
    
    Args:
        transaction_id: ID de la transaction
    
    Returns:
        dict: Statut du paiement
    """
    payload = {
        "apikey": CINETPAY_API_KEY,
        "site_id": CINETPAY_SITE_ID,
        "transaction_id": str(transaction_id),
    }
    
    try:
        response = requests.post(
            "https://api-checkout.cinetpay.com/v2/payment/check",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": data.get("code") == "00",
            "status": data.get("data", {}).get("status"),
            "amount": data.get("data", {}).get("amount"),
            "metadata": data.get("data", {})
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }