"""Extract explicit product facts from a short WhatsApp offer."""

import re
import unicodedata
from decimal import Decimal

CURRENCIES = (("XAF", "F CFA"), ("EUR", "EUR"), ("CAD", "CAD"), ("USD", "USD"))
PRICE = re.compile(
    r"(?<![\d.,+-])(?P<amount>\d{1,3}(?: \d{3})+|\d{1,10})(?P<decimal>[.,]\d{1,2})?"
    r"\s*(?P<currency>F\s*CFA|XAF|EUR|€|CAD|USD)\b"
    r"|(?<![\d.,+-])(?P<euro>\d{1,3}(?: \d{3})+|\d{1,10})(?P<euro_decimal>[.,]\d{1,2})?\s*€(?!\w)",
    re.I,
)
SKU = re.compile(r"\b(?:sku|r[ée]f(?:[ée]rence)?)[.: ]*\s*([a-z0-9][a-z0-9._-]{0,79})\b", re.I)
STOCK = re.compile(r"\bstock\s*[:=]?\s*(\d{1,9})\b", re.I)
UNSURE = re.compile(
    r"\b(?:à partir de|entre|jusqu[’']à|à discuter|prix de gros|négociable|au lieu de|assortiment|environ|dès|frais de livraison)\b|"
    r"\d\s*[-–—/]\s*\d", re.I,
)
PRODUCT = re.compile(r"^\s*(?:produit|article|nom)\s*:\s*", re.I)
PRICE_LABEL = re.compile(r"\bprix\s*[:=]?", re.I)
CONTACT_DETAILS = re.compile(r"https?://|wa\.me/|\b(?:contact|téléphone|tél|whatsapp)\s*[:=]|\+\d{8,}|\b6\d{8}\b", re.I)


def format_price(amount, currency):
    label = dict(CURRENCIES)[currency]
    number = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    number = number.replace(",", " ").replace(".", ",")
    return f"{number} {label}"


def parse_offer(body):
    body = unicodedata.normalize("NFKC", body).strip()
    prices = list(PRICE.finditer(body))
    skus, stocks = SKU.findall(body), STOCK.findall(body)
    fields = {"title": "", "price_amount": None, "currency": "", "sku": "", "stock": None}
    reasons = []
    if len(prices) == 1 and not UNSURE.search(SKU.sub("", body)):
        price = prices[0]
        major = price["amount"] or price["euro"]
        minor = price["decimal"] or price["euro_decimal"] or ""
        amount = Decimal(major.replace(" ", "") + minor.replace(",", "."))
        currency = (price["currency"] or "EUR").upper().replace(" ", "")
        currency = {"FCFA": "XAF", "€": "EUR"}.get(currency, currency)
        if 0 < amount < Decimal("10000000000") and (currency != "XAF" or amount == amount.to_integral_value()):
            fields.update(price_amount=amount, currency=currency)
    if fields["price_amount"] is None:
        reasons.append("Vérifie le prix et sa devise")
    if len(skus) == 1:
        fields["sku"] = skus[0].upper()
    elif skus:
        reasons.append("Plusieurs références sont indiquées")
    if len(stocks) == 1:
        fields["stock"] = int(stocks[0])
    elif stocks or re.search(r"\bstock\b", body, re.I):
        reasons.append("Vérifie le stock")

    leftovers = PRICE_LABEL.sub("", STOCK.sub("", SKU.sub("", PRICE.sub("", body))))
    lines = [PRODUCT.sub("", line).strip(" \t:;,.-–—•") for line in leftovers.splitlines()]
    lines = [line for line in lines if line]
    if lines:
        fields["title"] = lines[0][:140]
    if len(lines) != 1 or len(lines[0]) not in range(2, 141) or not any(char.isalpha() for char in lines[0]):
        reasons.append("Vérifie le nom du produit")
    elif CONTACT_DETAILS.search(lines[0]):
        reasons.append("Vérifie les coordonnées présentes dans le nom proposé")
    return fields, ". ".join(reasons)
