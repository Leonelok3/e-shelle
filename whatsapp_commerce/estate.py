"""Ground real-estate answers in the agency attached to the receiving number."""

import re
import unicodedata

from immobilier_cameroun.agency import property_url, public_agency_properties
from immobilier_cameroun.models import Bien, Devise, PeriodePrix, TypeBien, TypeTransaction
from immobilier_cameroun.services.whatsapp_parser import QUARTIERS_DOUALA, QUARTIERS_YAOUNDE

from .bookings import BOOKING_WORDS, SLOT_HELP, booking_reply
from .models import BusinessWhatsAppContact

REFERENCE = re.compile(r"\bbien\s*#?\s*(\d{1,12})\b", re.I)
BUDGET = re.compile(
    r"\b(?:budget(?:\s+de)?|max(?:imum)?|moins de|jusqu[' ]?a)\s*[:=]?\s*"
    r"(?P<amount>\d{1,3}(?:[ .]\d{3})+|\d{1,12})\s*(?P<scale>millions?\b|k\b)?\s*"
    r"(?P<currency>f\s*cfa|fcfa|xaf|euros?|eur|usd|dollars?)?",
)
CURRENCY_AMOUNT = re.compile(
    r"\b(?P<amount>\d{1,3}(?:[ .]\d{3})+|\d{1,12})\s*(?P<scale>millions?\b|k\b)?\s*"
    r"(?P<currency>f\s*cfa|fcfa|xaf|euros?|eur|usd|dollars?)\b",
)
ROOM_COUNTS = {"une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9}
CHAMBERS = re.compile(r"\b(\d{1,2}|" + "|".join(ROOM_COUNTS) + r")\s*chambres?\b")
PROPERTY_HELP = re.compile(r"\b(biens?|annonces?|offres?|disponibles?|catalogue|appartements?|villas?|terrains?|studios?)\b")
DETAIL = re.compile(r"\b(prix|photos?|equipements?|ascenseur|parking|piscine|surface|climatisation|meuble|disponible|details?|combien|adresse|ou)\b")
HANDOFF = re.compile(r"\b(acompte|paiement|payer|depot|virement|titre foncier|notaire|juridique|negocier|negociation|garantie|annuler)\b")


def normalise(value):
    folded = unicodedata.normalize("NFKD", value.casefold().replace("’", "'"))
    return "".join(char for char in folded if not unicodedata.combining(char))


def _search_updates(text, inventory):
    updates = {}
    for pattern, transaction_type in (
        (r"\b(colocation|coloc)\b", TypeTransaction.COLOCATION),
        (r"\b(achat|acheter|vente|a vendre)\b", TypeTransaction.VENTE),
        (r"\b(location|louer|a louer|loyer)\b", TypeTransaction.LOCATION),
    ):
        if re.search(pattern, text):
            updates["type_transaction"] = transaction_type
            break
    for pattern, property_types in (
        (r"\bstudios?\b", [TypeBien.STUDIO]),
        (r"\b(villas?|maisons?)\b", [TypeBien.VILLA]),
        (r"\bduplex\b", [TypeBien.DUPLEX]),
        (r"\bterrains?\b", [TypeBien.TERRAIN]),
        (r"\bbureaux?\b|\bbureau\b", [TypeBien.BUREAU]),
        (r"\bboutiques?\b", [TypeBien.BOUTIQUE]),
        (r"\bappart(?:s|ement|ements)?\b", [TypeBien.APPARTEMENT_MEUBLE, TypeBien.APPARTEMENT_NON_MEUBLE]),
    ):
        if re.search(pattern, text):
            updates["type_bien__in"] = property_types
            break
    for field in ("ville", "quartier"):
        # Include the standard city list so a request outside the agency's catalogue returns no matches.
        options = (
            dict(Bien._meta.get_field("ville").choices) if field == "ville"
            else {name: name for name in QUARTIERS_DOUALA + QUARTIERS_YAOUNDE}
        )
        options.update({name: name for name in inventory.exclude(**{field: ""}).order_by(field).values_list(field, flat=True).distinct()[:300]})
        for key, name in sorted(options.items(), key=lambda pair: len(pair[1]), reverse=True):
            if re.search(r"(?<!\w)" + re.escape(normalise(name)) + r"(?!\w)", text):
                updates[field + "__iexact"] = key
                break
    match = BUDGET.search(text) or CURRENCY_AMOUNT.search(text)
    if match:
        amount = int(match["amount"].replace(" ", "").replace(".", ""))
        scale = match["scale"] or ""
        amount *= 1_000_000 if scale.startswith("million") else 1000 if scale == "k" else 1
        if 0 < amount < 10 ** 14:
            currency = match["currency"] or "xaf"
            updates["prix__lte"] = amount
            updates["devise"] = Devise.EUR if currency.startswith("eur") else Devise.USD if currency.startswith(("usd", "dollar")) else Devise.XAF
    rooms = CHAMBERS.search(text)
    if rooms:
        updates["nombre_chambres__gte"] = int(rooms[1]) if rooms[1].isdecimal() else ROOM_COUNTS[rooms[1]]
    if re.search(r"(?:\bpar mois\b|/mois\b|\bmensuel(?:le)?\b)", text):
        updates["periode_prix"] = PeriodePrix.PAR_MOIS
    elif re.search(r"(?:\bpar jour\b|/jour\b|\bjournalier\b)", text):
        updates["periode_prix"] = PeriodePrix.PAR_JOUR
    return updates


def _price(bien):
    return f"{bien.prix_formate} · {bien.get_periode_prix_display()}"


def _details(bien):
    equipment = ", ".join(item.get_nom_display() for item in bien.equipements.all()[:8])
    facts = [f"{bien.get_type_transaction_display()} · {_price(bien)}", f"{bien.quartier}, {bien.ville}"]
    if bien.nombre_chambres:
        facts.append(f"{bien.nombre_chambres} chambre(s)")
    if bien.surface:
        facts.append(f"{bien.surface:g} m²")
    if equipment:
        facts.append(equipment)
    return (
        f"BIEN {bien.pk} · {bien.titre}\n"
        + " | ".join(facts) + "\n"
        + f"{bien.description[:450]}\nPhotos et fiche : {property_url(bien)}\nÉcris VISITE pour demander un créneau."
    )


def _results(inventory):
    matches = list(inventory[:3])
    if not matches:
        return "Aucun bien disponible ne correspond à ces critères dans cette agence. Écris NOUVELLE RECHERCHE pour repartir de zéro."
    lines = [
        f"BIEN {item.pk} · {item.titre} · {item.quartier}, {item.ville} · {_price(item)}"
        for item in matches
    ]
    return "Biens disponibles dans cette agence :\n" + "\n".join(lines) + "\nÉcris BIEN suivi de la référence pour voir les détails, ou précise la ville, le type et ton budget."


def _remember(contact, *, filters, selected=None):
    BusinessWhatsAppContact.objects.filter(pk=contact.pk).update(
        property_filters=filters, selected_property=selected,
    )


def estate_preview(business):
    return _results(public_agency_properties(business))


def estate_reply(activation, contact, body, *, typed, offer_click=None, reply_message_id=None):
    """Return None to allow the shared FAQ, or an empty string for the agency's team."""
    inventory = public_agency_properties(contact.business)
    text = normalise(body[:2000]).strip()
    if HANDOFF.search(text):
        return ""
    filters = contact.property_filters if isinstance(contact.property_filters, dict) else {}
    selected = inventory.filter(pk=contact.selected_property_id).first() if contact.selected_property_id else None
    if text in {"nouvelle recherche", "recommencer", "biens"}:
        _remember(contact, filters={})
        return _results(inventory)
    wants_booking = BOOKING_WORDS.search(text) or SLOT_HELP.search(body)
    reference = REFERENCE.search(text)
    if reference:
        selected = inventory.filter(pk=reference[1]).first()
        _remember(contact, filters=filters, selected=selected)
        if selected is None:
            return "Ce bien n’est plus proposé par cette agence. Écris BIENS pour voir ses offres disponibles."
        if not wants_booking:
            return _details(selected)
    if wants_booking and (selected or text.startswith(("rdv ", "reporter "))):
        reply = booking_reply(
            activation, contact, body, typed=typed, listing=selected, estate=True,
            offer_click=offer_click, reply_message_id=reply_message_id,
        )
        return reply if reply is not None else ""
    if selected and DETAIL.search(text):
        return _details(selected)
    updates = _search_updates(text, inventory)
    if updates:
        filters = {**filters, **updates}
        _remember(contact, filters=filters)
        return _results(inventory.filter(**filters))
    if PROPERTY_HELP.search(text) or BOOKING_WORDS.search(text) or text in {"bonjour", "salut", "bonsoir"}:
        return _results(inventory.filter(**filters))
    return None
