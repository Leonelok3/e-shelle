import csv
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import BusinessCatalogItem


REQUIRED_COLUMNS = {"sku", "nom", "prix_detail", "prix_gros", "stock", "categorie"}
MAX_CSV_BYTES = 5 * 1024 * 1024


class CatalogImportError(ValueError):
    pass


def _parse_xaf(value, *, row_number, column, allow_zero=True):
    try:
        amount = Decimal(str(value).strip().replace(" ", "").replace(",", ""))
    except (InvalidOperation, ValueError):
        raise CatalogImportError(f"Ligne {row_number}: {column} doit être un montant XAF valide.")
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
        raise CatalogImportError(f"Ligne {row_number}: {column} doit être positif.")
    if amount != amount.to_integral_value():
        raise CatalogImportError(f"Ligne {row_number}: {column} doit être un montant entier en XAF.")
    return int(amount)


def _parse_stock(value, *, row_number):
    try:
        stock = int(str(value).strip())
    except (TypeError, ValueError):
        raise CatalogImportError(f"Ligne {row_number}: stock doit être un entier positif ou nul.")
    if stock < 0:
        raise CatalogImportError(f"Ligne {row_number}: stock doit être un entier positif ou nul.")
    return stock


def parse_catalog_csv(upload):
    if getattr(upload, "size", 0) > MAX_CSV_BYTES:
        raise CatalogImportError("Le fichier CSV dépasse la limite de 5 Mo.")
    try:
        raw_content = upload.read()
        if isinstance(raw_content, bytes):
            text = raw_content.decode("utf-8-sig")
        elif isinstance(raw_content, str):
            text = raw_content.lstrip("\ufeff")
        else:
            raise CatalogImportError("Le catalogue doit être un fichier CSV encodé en UTF-8.")
    except UnicodeDecodeError:
        raise CatalogImportError("Le catalogue doit être un fichier CSV encodé en UTF-8.")
    if not text.strip():
        raise CatalogImportError("Le fichier CSV est vide.")

    reader = csv.DictReader(text.splitlines())
    headers = {str(header or "").strip().casefold() for header in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise CatalogImportError(
            "Colonnes CSV manquantes : " + ", ".join(sorted(missing)) + "."
        )

    normalized_rows = []
    seen_skus = set()
    for row_number, row in enumerate(reader, start=2):
        values = {
            str(key or "").strip().casefold(): str(value or "").strip()
            for key, value in row.items()
        }
        sku = values["sku"]
        title = values["nom"]
        category = values["categorie"]
        if not sku or not title or not category:
            raise CatalogImportError(
                f"Ligne {row_number}: sku, nom et categorie ne peuvent pas être vides."
            )
        if len(sku) > 80 or len(title) > 140 or len(category) > 120:
            raise CatalogImportError(f"Ligne {row_number}: sku, nom ou categorie dépasse la longueur autorisée.")
        sku_key = sku.casefold()
        if sku_key in seen_skus:
            raise CatalogImportError(f"Ligne {row_number}: SKU dupliqué dans le fichier ({sku}).")
        seen_skus.add(sku_key)
        normalized_rows.append(
            {
                "sku": sku,
                "title": title,
                "category": category,
                "detail_price": _parse_xaf(values["prix_detail"], row_number=row_number, column="prix_detail", allow_zero=False),
                "wholesale_price": _parse_xaf(values["prix_gros"], row_number=row_number, column="prix_gros", allow_zero=False),
                "stock": _parse_stock(values["stock"], row_number=row_number),
            }
        )
    if not normalized_rows:
        raise CatalogImportError("Le fichier CSV ne contient aucune ligne produit.")
    return normalized_rows


@transaction.atomic
def import_catalog_rows(business, rows):
    created = 0
    updated = 0
    for row in rows:
        item, was_created = BusinessCatalogItem.objects.update_or_create(
            business=business,
            sku=row["sku"],
            defaults={
                "title": row["title"],
                "category": row["category"],
                "item_type": BusinessCatalogItem.ItemType.PRODUCT,
                "price_label": f'{row["detail_price"]} FCFA',
                "prix_gros_xaf": row["wholesale_price"],
                "stock_quantity": row["stock"],
                "is_active": True,
            },
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"created": created, "updated": updated, "total": len(rows)}


def import_catalog_csv(business, upload):
    return import_catalog_rows(business, parse_catalog_csv(upload))


def import_from_photo(image_file, business_id):
    """Read a product label locally, structure it with E-Shelle AI, and upsert it."""
    from business.models import BusinessProfile
    from phone_ocr_agent.services import OCRError, extract_from_image

    if getattr(image_file, "size", 0) > 10 * 1024 * 1024:
        raise CatalogImportError("La photo dépasse la limite de 10 Mo.")
    content_type = getattr(image_file, "content_type", "")
    if content_type and not content_type.startswith("image/"):
        raise CatalogImportError("Choisis un fichier image valide.")
    business = BusinessProfile.objects.get(pk=business_id)
    try:
        image_file.seek(0)
        ocr_result = extract_from_image(image_file)
    except (OCRError, OSError, ValueError) as exc:
        raise CatalogImportError("Le texte de la photo n’a pas pu être lu.") from exc
    finally:
        if hasattr(image_file, "seek"):
            image_file.seek(0)
    if not ocr_result.text.strip():
        raise CatalogImportError("Aucun texte produit lisible sur la photo.")

    from e_shelle_ai.services.openai_service import EshelleAIService

    ai = EshelleAIService()
    if not ai.client:
        raise CatalogImportError("Le service IA de structuration catalogue n’est pas configuré.")
    try:
        response = ai.client.chat.completions.create(
            model=ai.chat_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract one wholesale product from OCR text. Return JSON keys "
                        "sku, nom, nom_en, prix_detail, prix_gros, stock, categorie. "
                        "Prices must be positive integer XAF, stock a non-negative integer. "
                        "Never invent a price or stock: return null if absent. Use a concise "
                        "stable SKU if none is printed."
                    ),
                },
                {"role": "user", "content": ocr_result.text[:5000]},
            ],
        )
        data = json.loads(response.choices[0].message.content)
    except Exception as exc:
        raise CatalogImportError("L’IA n’a pas pu structurer les informations produit.") from exc

    try:
        sku = str(data.get("sku") or "").strip()
        title = str(data.get("nom") or "").strip()
        title_en = str(data.get("nom_en") or "").strip()
        category = str(data.get("categorie") or "").strip()
        detail_price = _parse_xaf(data.get("prix_detail"), row_number=1, column="prix_detail", allow_zero=False)
        wholesale_price = _parse_xaf(data.get("prix_gros"), row_number=1, column="prix_gros", allow_zero=False)
        stock = _parse_stock(data.get("stock"), row_number=1)
        if not sku or not title or not category or len(sku) > 80 or len(title) > 140 or len(category) > 120:
            raise CatalogImportError("Les champs SKU, nom ou catégorie sont absents ou trop longs.")
    except (AttributeError, TypeError) as exc:
        raise CatalogImportError("Les champs produit retournés par l’IA sont invalides.") from exc

    with transaction.atomic():
        item, created = BusinessCatalogItem.objects.update_or_create(
            business=business,
            sku=sku,
            defaults={
                "title": title,
                "title_en": title_en[:140],
                "category": category,
                "item_type": BusinessCatalogItem.ItemType.PRODUCT,
                "price_label": f"{detail_price} FCFA",
                "prix_gros_xaf": wholesale_price,
                "stock_quantity": stock,
                "is_active": True,
            },
        )
        image_file.seek(0)
        item.image.save(getattr(image_file, "name", "product-photo.jpg"), image_file, save=True)
    return {
        "created": created,
        "product": {
            "id": item.pk,
            "sku": item.sku,
            "nom": item.title,
            "nom_en": item.title_en,
            "prix_detail": detail_price,
            "prix_gros": wholesale_price,
            "stock": stock,
            "categorie": item.category,
            "image_url": item.image.url if item.image else "",
        },
    }
