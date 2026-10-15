"""Server-side CamPay API client and verified transaction reconciliation."""
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import quote, urlparse

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Transaction


class CampayError(Exception):
    """A safe, user-independent CamPay integration error."""


class CampayClient:
    API_URLS = {
        "sandbox": "https://demo.campay.net/api",
        "production": "https://www.campay.net/api",
    }
    REQUEST_TIMEOUT = (5, 20)
    REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    def __init__(self):
        mode = getattr(settings, "CAMPAY_MODE", "sandbox")
        self.mode = mode
        self.base_url = self.API_URLS.get(mode)
        if not self.base_url:
            raise CampayError("CamPay mode must be sandbox or production.")
        self._token = getattr(settings, "CAMPAY_TOKEN", "")

    def _request(self, method, path, *, authenticated=True, payload=None):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = f"Token {self._access_token()}"

        try:
            response = requests.request(
                method,
                f"{self.base_url}/{path.lstrip('/')}",
                json=payload,
                headers=headers,
                timeout=self.REQUEST_TIMEOUT,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise CampayError("CamPay could not be reached.") from exc

        if not response.ok:
            raise CampayError(f"CamPay returned HTTP {response.status_code}.")
        try:
            result = response.json()
        except ValueError as exc:
            raise CampayError("CamPay returned an invalid response.") from exc
        if not isinstance(result, dict):
            raise CampayError("CamPay returned an invalid response.")
        return result

    def _access_token(self):
        if self._token:
            return self._token

        username = getattr(settings, "CAMPAY_USERNAME", "")
        password = getattr(settings, "CAMPAY_PASSWORD", "")
        if not username or not password:
            raise CampayError("CamPay credentials are not configured.")

        result = self._request(
            "POST",
            "token",
            authenticated=False,
            payload={"username": username, "password": password},
        )
        token = result.get("token")
        if not isinstance(token, str) or not token:
            raise CampayError("CamPay did not return an access token.")
        self._token = token
        return token

    def create_payment_link(self, transaction_obj, *, description, redirect_url):
        amount = Decimal(transaction_obj.montant)
        if amount <= 0 or amount != amount.to_integral_value():
            raise CampayError("CamPay requires a positive whole-number XAF amount.")
        if transaction_obj.devise != "XAF":
            raise CampayError("CamPay checkout currently supports XAF only.")
        if not _is_https_url(redirect_url):
            raise CampayError("CamPay return URLs must use HTTPS.")

        user = transaction_obj.utilisateur
        full_name = user.get_full_name().strip() if user else ""
        first_name, _, last_name = full_name.partition(" ")
        payload = {
            "amount": int(amount),
            "currency": transaction_obj.devise,
            "description": description[:100],
            "external_reference": transaction_obj.reference,
            "redirect_url": redirect_url,
            "failure_redirect_url": redirect_url,
            "payment_options": "MOMO",
        }
        if user:
            if first_name:
                payload["first_name"] = first_name
            if last_name:
                payload["last_name"] = last_name
            if user.email:
                payload["email"] = user.email

        result = self._request("POST", "get_payment_link", payload=payload)
        link = result.get("link")
        reference = result.get("reference")
        if (
            not isinstance(link, str)
            or len(link) > 1000
            or not _is_campay_checkout_url(link)
            or not isinstance(reference, str)
            or not self.REFERENCE_PATTERN.fullmatch(reference)
        ):
            raise CampayError("CamPay returned an invalid checkout link.")
        return link, reference

    def get_transaction(self, provider_reference):
        if not isinstance(provider_reference, str) or not self.REFERENCE_PATTERN.fullmatch(
            provider_reference
        ):
            raise CampayError("Invalid CamPay transaction reference.")
        return self._request(
            "GET",
            f"transactions/{quote(provider_reference, safe='')}",
        )


def reconcile_transaction(transaction_obj, client=None):
    """Verify provider facts before recording payment; never fulfill the order."""
    if transaction_obj.methode != "campay" or not transaction_obj.ref_operateur:
        raise CampayError("CamPay transaction reference is missing.")

    client = client or CampayClient()
    result = client.get_transaction(transaction_obj.ref_operateur)
    status = result.get("status")
    if result.get("reference") != transaction_obj.ref_operateur:
        raise CampayError("CamPay transaction reference did not match.")
    if result.get("currency") != transaction_obj.devise:
        raise CampayError("CamPay transaction currency did not match.")
    try:
        provider_amount = Decimal(str(result.get("amount")))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CampayError("CamPay transaction amount is invalid.") from exc
    if provider_amount != transaction_obj.montant:
        raise CampayError("CamPay transaction amount did not match.")
    if status not in {"PENDING", "SUCCESSFUL", "FAILED"}:
        raise CampayError("CamPay returned an unknown transaction status.")

    with transaction.atomic():
        current = Transaction.objects.select_for_update().get(pk=transaction_obj.pk)
        metadata = dict(current.metadata or {})
        metadata["campay"] = {
            "provider_status": status,
            "verified_at": timezone.now().isoformat(),
            "mode": client.mode,
        }
        current.metadata = metadata
        if status == "SUCCESSFUL":
            if current.statut not in {"succes", "rembourse"}:
                current.statut = "pending_awaiting_manual_validation"
            current.erreur = ""
        elif status == "FAILED":
            if current.statut not in {"succes", "rembourse", "pending_awaiting_manual_validation"}:
                current.statut = "echec"
                current.erreur = "CamPay payment failed."
        elif current.statut not in {"succes", "rembourse", "pending_awaiting_manual_validation", "echec"}:
            current.statut = "en_attente"
        current.save(update_fields=["metadata", "statut", "erreur", "updated_at"])

    transaction_obj.refresh_from_db()
    return transaction_obj


def _is_https_url(value):
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _is_campay_checkout_url(value):
    if not _is_https_url(value):
        return False
    hostname = (urlparse(value).hostname or "").lower()
    return hostname in {"campay.net", "demo.campay.net", "www.campay.net"}
