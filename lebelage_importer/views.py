from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import render

from tools.lebelage_shopify_agent import (
    BASE_URL,
    Product,
    compare_lebelage_to_shopify,
    crawl_product_urls,
    enrich_products,
    export_shopify_products,
    import_to_shopify,
    save_comparison_report,
    save_csv,
    save_json,
    scrape_product,
)


EXPORT_JSON = Path(settings.BASE_DIR) / "tmp" / "lebelage_products.json"
EXPORT_CSV = Path(settings.BASE_DIR) / "tmp" / "lebelage_products.csv"
SHOPIFY_EXPORT_JSON = Path(settings.BASE_DIR) / "tmp" / "shopify_products.json"
SHOPIFY_EXPORT_CSV = Path(settings.BASE_DIR) / "tmp" / "shopify_products.csv"
COMPARISON_JSON = Path(settings.BASE_DIR) / "tmp" / "lebelage_shopify_comparison.json"
COMPARISON_CSV = Path(settings.BASE_DIR) / "tmp" / "lebelage_shopify_comparison.csv"


def _int_from_post(request, key: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(request.POST.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _float_from_post(request, key: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(request.POST.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _latest_products() -> list[dict]:
    if not EXPORT_JSON.exists():
        return []
    try:
        import json

        with EXPORT_JSON.open("r", encoding="utf-8") as fh:
            products = json.load(fh)
    except (OSError, ValueError):
        return []
    return products if isinstance(products, list) else []


def _latest_shopify_products() -> list[dict]:
    if not SHOPIFY_EXPORT_JSON.exists():
        return []
    try:
        import json

        with SHOPIFY_EXPORT_JSON.open("r", encoding="utf-8") as fh:
            products = json.load(fh)
    except (OSError, ValueError):
        return []
    return products if isinstance(products, list) else []


def _latest_comparison() -> dict:
    if not COMPARISON_JSON.exists():
        return {}
    try:
        import json

        with COMPARISON_JSON.open("r", encoding="utf-8") as fh:
            report = json.load(fh)
    except (OSError, ValueError):
        return {}
    return report if isinstance(report, dict) else {}


def _products_from_dicts(rows: list[dict]) -> list[Product]:
    products = []
    for row in rows:
        products.append(
            Product(
                title=row.get("title", ""),
                price=row.get("price", ""),
                price_amount=row.get("price_amount", "0.00"),
                currency=row.get("currency", "USD"),
                description=row.get("description", ""),
                image_url=row.get("image_url", ""),
                source_url=row.get("source_url", ""),
                tags=row.get("tags", []) if isinstance(row.get("tags", []), list) else [],
                final_price_amount=row.get("final_price_amount", ""),
                selling_description=row.get("selling_description", ""),
            )
        )
    return products


def _shopify_ready() -> bool:
    shop = os.getenv("SHOPIFY_SHOP_DOMAIN") or os.getenv("TIBO_SHOPIFY_SHOP_DOMAIN")
    token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN") or os.getenv("TIBO_SHOPIFY_ACCESS_TOKEN")
    return bool(shop and token)


def download_export(request, bucket: str, file_format: str):
    bucket = bucket.lower()
    file_format = file_format.lower()
    if file_format not in {"json", "csv"}:
        raise Http404

    mappings = {
        "export": (EXPORT_JSON, EXPORT_CSV),
        "shopify": (SHOPIFY_EXPORT_JSON, SHOPIFY_EXPORT_CSV),
        "comparison": (COMPARISON_JSON, COMPARISON_CSV),
    }
    candidates = mappings.get(bucket)
    if not candidates:
        raise Http404

    file_path = candidates[0] if file_format == "json" else candidates[1]
    if not file_path.exists():
        raise Http404

    response = FileResponse(file_path.open("rb"), as_attachment=True)
    response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
    return response


def dashboard(request):
    form_state = {
        "source_url": BASE_URL,
        "limit": 10,
        "max_pages": 1,
        "sleep": 0.25,
        "shipping": 0,
        "margin": 0,
    }
    products = _latest_products()
    shopify_products = _latest_shopify_products()
    comparison = _latest_comparison()

    if request.method == "POST":
        action = request.POST.get("action", "scrape")
        form_state = {
            "source_url": request.POST.get("source_url", BASE_URL).strip() or BASE_URL,
            "limit": _int_from_post(request, "limit", 10, 1, 200),
            "max_pages": _int_from_post(request, "max_pages", 1, 1, 20),
            "sleep": _float_from_post(request, "sleep", 0.25, 0.0, 5.0),
            "shipping": _float_from_post(request, "shipping", 0, 0.0, 100000.0),
            "margin": _float_from_post(request, "margin", 0, 0.0, 100000.0),
        }

        try:
            if action == "export_shopify":
                if not _shopify_ready():
                    messages.error(
                        request,
                        "Variables Shopify manquantes: ajoute SHOPIFY_SHOP_DOMAIN et SHOPIFY_ADMIN_ACCESS_TOKEN.",
                    )
                else:
                    shopify_products = export_shopify_products(SHOPIFY_EXPORT_JSON, SHOPIFY_EXPORT_CSV)
                    messages.success(
                        request,
                        f"{len(shopify_products)} produit(s) Shopify exporte(s) en local.",
                    )
            elif action == "compare":
                products = _latest_products()
                shopify_products = _latest_shopify_products()
                if not products:
                    messages.error(request, "Exporte d'abord les produits LEBELAGE en local.")
                elif not shopify_products:
                    messages.error(request, "Exporte d'abord les produits Shopify en local.")
                else:
                    comparison = compare_lebelage_to_shopify(products, shopify_products)
                    save_comparison_report(comparison, COMPARISON_JSON, COMPARISON_CSV)
                    summary = comparison.get("summary", {})
                    messages.success(
                        request,
                        (
                            f"Comparaison terminee: {summary.get('new_count', 0)} nouveau(x), "
                            f"{summary.get('duplicate_count', 0)} doublon(s), "
                            f"{summary.get('price_difference_count', 0)} prix different(s)."
                        ),
                    )
            elif action == "import_draft":
                confirmation = request.POST.get("confirmation", "").strip().upper()
                if confirmation != "BROUILLON":
                    messages.error(request, "Tape BROUILLON pour confirmer l'import Shopify en brouillon.")
                elif not _shopify_ready():
                    messages.error(
                        request,
                        "Variables Shopify manquantes: ajoute SHOPIFY_SHOP_DOMAIN et SHOPIFY_ADMIN_ACCESS_TOKEN.",
                    )
                else:
                    local_products = _products_from_dicts(_latest_products())
                    if not local_products:
                        messages.error(request, "Aucun produit LEBELAGE local a importer.")
                    else:
                        import_to_shopify(local_products, update_existing=False)
                        messages.success(
                            request,
                            f"{len(local_products)} produit(s) envoye(s) dans Shopify en brouillon.",
                        )
            else:
                product_urls = crawl_product_urls(
                    start_url=form_state["source_url"],
                    max_pages=form_state["max_pages"],
                    limit=form_state["limit"],
                    sleep=form_state["sleep"],
                )
                scraped_products = []
                for product_url in product_urls:
                    scraped_products.append(scrape_product(product_url))

                scraped_products = enrich_products(
                    scraped_products,
                    shipping=form_state["shipping"],
                    margin=form_state["margin"],
                )
                save_json(scraped_products, EXPORT_JSON)
                save_csv(scraped_products, EXPORT_CSV)
                products = [asdict(product) for product in scraped_products]
                messages.success(request, f"{len(products)} produit(s) LEBELAGE exporte(s) en local.")

        except Exception as exc:  # noqa: BLE001 - shown in local operator UI
            messages.error(request, f"Erreur: {exc}")

    context = {
        "form": form_state,
        "products": products,
        "product_count": len(products),
        "shopify_products": shopify_products[:12],
        "shopify_product_count": len(shopify_products),
        "comparison": comparison,
        "comparison_summary": comparison.get("summary", {}),
        "new_products": comparison.get("new_products", [])[:12],
        "duplicates": comparison.get("duplicates", [])[:8],
        "price_differences": comparison.get("price_differences", [])[:12],
        "export_json": EXPORT_JSON,
        "export_csv": EXPORT_CSV,
        "shopify_export_json": SHOPIFY_EXPORT_JSON,
        "shopify_export_csv": SHOPIFY_EXPORT_CSV,
        "comparison_json": COMPARISON_JSON,
        "comparison_csv": COMPARISON_CSV,
        "has_export_json": EXPORT_JSON.exists(),
        "has_export_csv": EXPORT_CSV.exists(),
        "has_shopify_export_json": SHOPIFY_EXPORT_JSON.exists(),
        "has_shopify_export_csv": SHOPIFY_EXPORT_CSV.exists(),
        "has_comparison_json": COMPARISON_JSON.exists(),
        "has_comparison_csv": COMPARISON_CSV.exists(),
        "shopify_ready": _shopify_ready(),
    }
    return render(request, "lebelage_importer/dashboard.html", context)
