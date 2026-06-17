#!/usr/bin/env python
"""
Agent local LEBELAGE -> Shopify.

Usage rapide:
  python tools/lebelage_shopify_agent.py --limit 10
  python tools/lebelage_shopify_agent.py --limit 10 --import-shopify

Variables Shopify:
  SHOPIFY_SHOP_DOMAIN=ma-boutique.myshopify.com
  SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_xxx
  SHOPIFY_API_VERSION=2026-01

Variables E-Shelle deja compatibles:
  TIBO_SHOPIFY_SHOP_DOMAIN
  TIBO_SHOPIFY_ACCESS_TOKEN
  TIBO_SHOPIFY_API_VERSION
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


BASE_URL = "https://en.lebelage.co.kr/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; EShelle-LebelageImporter/1.0; "
        "+https://e-shelle.com)"
    ),
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}


@dataclass
class Product:
    title: str
    price: str
    price_amount: str
    currency: str
    description: str
    image_url: str
    source_url: str
    tags: list[str]
    final_price_amount: str = ""
    selling_description: str = ""


class LinkImageParser(HTMLParser):
    """Petit parser sans dependance externe pour liens, images et meta."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.images: list[str] = []
        self.meta: dict[str, str] = {}
        self.title = ""
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append((attrs.get("href", ""), attrs.get("title", "")))
        elif tag == "img":
            src = attrs.get("src") or attrs.get("data-src") or attrs.get("ec-data-src")
            if src:
                self.images.append(src)
        elif tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            value = attrs.get("content")
            if key and value:
                self.meta[key.lower()] = value
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            self.title = " ".join(self._title_parts).strip()

    def handle_data(self, data):
        if self._in_title and data.strip():
            self._title_parts.append(data.strip())


def fetch(url: str, timeout=30) -> str:
    logging.info("GET %s", url)
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_html(text: str) -> LinkImageParser:
    parser = LinkImageParser()
    parser.feed(text)
    return parser


def normalize_url(base: str, href: str) -> str:
    href = html.unescape(href or "").strip()
    if href.startswith("//"):
        return "https:" + href
    return urljoin(base, href)


def with_page(url: str, page: int) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query["page"] = str(page)
    return urlunparse(parsed._replace(query=urlencode(query)))


def discover_category_urls(home_url: str, html_text: str) -> list[str]:
    parser = parse_html(html_text)
    urls = {home_url}
    for href, _title in parser.links:
        url = normalize_url(home_url, href)
        if "en.lebelage.co.kr" not in url:
            continue
        if "/category/" in url or "/product/list" in url:
            urls.add(url.split("#")[0])
    return sorted(urls)


def discover_product_urls(page_url: str, html_text: str) -> list[str]:
    parser = parse_html(html_text)
    urls = set()
    for href, title in parser.links:
        url = normalize_url(page_url, href)
        if "en.lebelage.co.kr" not in url:
            continue
        if "/product/" not in url:
            continue
        if not title and re.search(r"/product/[^/]+/\d+", url) is None:
            continue
        urls.add(url.split("#")[0])
    return sorted(urls)


def crawl_product_urls(start_url: str, max_pages: int, limit: int, sleep: float) -> list[str]:
    home = fetch(start_url)
    categories = discover_category_urls(start_url, home)
    logging.info("Categories/pages candidates: %s", len(categories))

    seen_products: list[str] = []
    seen_set = set()
    for category_url in categories:
        for page in range(1, max_pages + 1):
            page_url = category_url if page == 1 else with_page(category_url, page)
            try:
                text = fetch(page_url)
            except Exception as exc:
                logging.warning("Skip page %s: %s", page_url, exc)
                break
            found = discover_product_urls(page_url, text)
            new_count = 0
            for url in found:
                if url in seen_set:
                    continue
                seen_set.add(url)
                seen_products.append(url)
                new_count += 1
                if limit and len(seen_products) >= limit:
                    return seen_products
            if new_count == 0 and page > 1:
                break
            time.sleep(sleep)
    return seen_products


def text_from_html(raw_html: str) -> str:
    text = re.sub(r"<(script|style).*?</\1>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_price(value: str) -> tuple[str, str, str]:
    value = html.unescape(value or "").strip()
    match = re.search(r"([$€£])\s*([0-9]+(?:[.,][0-9]{1,2})?)", value)
    if not match:
        return value, "", "USD"
    currency_symbol, amount = match.groups()
    currency = {"$": "USD", "€": "EUR", "£": "GBP"}.get(currency_symbol, "USD")
    return f"{currency_symbol}{amount}", amount.replace(",", "."), currency


def extract_between(text: str, start: str, end_candidates: Iterable[str]) -> str:
    idx = text.lower().find(start.lower())
    if idx < 0:
        return ""
    fragment = text[idx + len(start):]
    end_positions = [fragment.lower().find(end.lower()) for end in end_candidates]
    end_positions = [pos for pos in end_positions if pos > 0]
    if end_positions:
        fragment = fragment[: min(end_positions)]
    return fragment.strip(" :|-")


def choose_main_image(product_url: str, parser: LinkImageParser) -> str:
    og_image = parser.meta.get("og:image") or parser.meta.get("twitter:image")
    if og_image:
        return normalize_url(product_url, og_image)
    candidates = [
        normalize_url(product_url, src)
        for src in parser.images
        if not any(bad in src.lower() for bad in ["icon", "btn", "blank", "logo", "payment"])
    ]
    for image in candidates:
        if "/web/product/" in image or "/product/" in image:
            return image
    return candidates[0] if candidates else ""


def scrape_product(product_url: str) -> Product:
    raw = fetch(product_url)
    parser = parse_html(raw)
    text = text_from_html(raw)

    title = (
        extract_between(text, "Product Name", ["Price", "Domestic", "Shipping"])
        or parser.meta.get("og:title", "")
        or parser.title.replace("- LEBELAGE", "").strip()
    )
    title = re.sub(r"\s+", " ", title).strip(" []")
    if "LEBELAGE" in title:
        title = title.split("- LEBELAGE")[0].strip()

    price_text = extract_between(text, "Price", ["Domestic", "Payment", "Shipping", "Monthly"])
    price, amount, currency = parse_price(price_text)

    meta_desc = parser.meta.get("description") or parser.meta.get("og:description") or ""
    description = meta_desc.strip()
    if not description or len(description) < 20:
        description = (
            f"{title}. Imported from LEBELAGE. Hypoallergenic skincare product. "
            "Please review ingredients and usage details before publishing."
        )

    image_url = choose_main_image(product_url, parser)
    if not title:
        raise ValueError(f"Product title not found: {product_url}")
    if not amount:
        logging.warning("Price not parsed for %s. Raw price=%r", title, price_text)

    return Product(
        title=title,
        price=price,
        price_amount=amount or "0.00",
        currency=currency,
        description=description,
        image_url=image_url,
        source_url=product_url,
        tags=["hypoallergenic", "LEBELAGE", "k-beauty", "imported"],
    )


class ShopifyClient:
    def __init__(self, shop_domain: str, access_token: str, api_version: str = "2026-01"):
        if not shop_domain or not access_token:
            raise ValueError("SHOPIFY_SHOP_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN are required.")
        self.shop_domain = shop_domain.replace("https://", "").strip("/")
        self.access_token = access_token
        self.api_version = api_version

    @property
    def base_url(self) -> str:
        return f"https://{self.shop_domain}/admin/api/{self.api_version}"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }

    def find_product_by_title(self, title: str) -> dict | None:
        response = requests.get(
            f"{self.base_url}/products.json",
            headers=self.headers,
            params={"title": title, "limit": 50},
            timeout=30,
        )
        response.raise_for_status()
        for product in response.json().get("products", []):
            if product.get("title", "").strip().lower() == title.strip().lower():
                return product
        return None

    def list_products(self, limit: int = 250) -> list[dict]:
        products: list[dict] = []
        page_info = ""
        while True:
            params = {"limit": min(limit, 250)}
            if page_info:
                params["page_info"] = page_info
            response = requests.get(
                f"{self.base_url}/products.json",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            products.extend(response.json().get("products", []))
            page_info = _next_page_info(response.headers.get("Link", ""))
            if not page_info:
                break
        return products

    def create_product(self, product: Product, status: str = "draft") -> dict:
        payload = {"product": self._product_payload(product, status=status)}
        response = requests.post(
            f"{self.base_url}/products.json",
            headers=self.headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["product"]

    def update_product(self, shopify_id: int, product: Product, status: str = "draft") -> dict:
        payload = {"product": {"id": shopify_id, **self._product_payload(product, status=status)}}
        response = requests.put(
            f"{self.base_url}/products/{shopify_id}.json",
            headers=self.headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["product"]

    def _product_payload(self, product: Product, status: str = "draft") -> dict:
        description = product.selling_description or product.description
        price = product.final_price_amount or product.price_amount
        body_html = (
            f"<p>{html.escape(description)}</p>"
            f"<p><strong>Source:</strong> <a href=\"{html.escape(product.source_url)}\">LEBELAGE product page</a></p>"
        )
        payload = {
            "title": product.title,
            "body_html": body_html,
            "vendor": "LEBELAGE",
            "product_type": "Skincare",
            "tags": ", ".join(product.tags),
            "status": status,
            "variants": [{"price": price, "sku": source_sku(product.source_url)}],
            "metafields": [
                {
                    "namespace": "source",
                    "key": "lebelage_url",
                    "type": "single_line_text_field",
                    "value": product.source_url,
                }
            ],
        }
        if product.image_url:
            payload["images"] = [{"src": product.image_url}]
        return payload


def source_sku(source_url: str) -> str:
    match = re.search(r"/product/[^/]+/(\d+)", source_url)
    return f"LEBELAGE-{match.group(1)}" if match else "LEBELAGE"


def money_to_float(value: str | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.,-]", "", str(value)).replace(",", ".")
    if cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "", cleaned.count(".") - 1)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def calculate_final_price(source_price: str | float, shipping: float = 0.0, margin: float = 0.0) -> str:
    final_price = money_to_float(source_price) + float(shipping or 0) + float(margin or 0)
    return f"{max(final_price, 0):.2f}"


def build_selling_description(product: Product) -> str:
    title = product.title.strip()
    base = product.description.strip()
    benefits = [
        "formule pensee pour une routine beaute simple et efficace",
        "presentation claire pour rassurer le client avant l'achat",
        "produit ideal pour enrichir une boutique skincare ou K-beauty",
    ]
    return (
        f"{title} est un soin LEBELAGE selectionne pour les clients qui recherchent une solution "
        f"skincare pratique et qualitative. {base}\n\n"
        f"Points forts:\n"
        f"- {benefits[0]}\n"
        f"- {benefits[1]}\n"
        f"- {benefits[2]}\n\n"
        f"Conseil boutique: verifier les ingredients, les consignes d'utilisation et les obligations "
        f"cosmetiques locales avant publication."
    )


def enrich_products(products: list[Product], shipping: float = 0.0, margin: float = 0.0) -> list[Product]:
    enriched = []
    for product in products:
        product.final_price_amount = calculate_final_price(product.price_amount, shipping=shipping, margin=margin)
        product.selling_description = build_selling_description(product)
        enriched.append(product)
    return enriched


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def compare_lebelage_to_shopify(lebelage_products: list[dict], shopify_products: list[dict]) -> dict:
    shopify_by_title: dict[str, list[dict]] = {}
    for product in shopify_products:
        key = normalize_key(product.get("title", ""))
        if key:
            shopify_by_title.setdefault(key, []).append(product)

    new_products = []
    duplicates = []
    price_differences = []

    for product in lebelage_products:
        key = normalize_key(product.get("title", ""))
        matches = shopify_by_title.get(key, [])
        source_price = money_to_float(product.get("final_price_amount") or product.get("price_amount"))
        if not matches:
            new_products.append(product)
            continue

        duplicates.append({"lebelage": product, "shopify_matches": matches})
        for match in matches:
            variants = match.get("variants") or [{}]
            shopify_price = money_to_float(variants[0].get("price", "0") if variants else "0")
            if abs(source_price - shopify_price) >= 0.01:
                price_differences.append(
                    {
                        "title": product.get("title", ""),
                        "lebelage_price": f"{source_price:.2f}",
                        "shopify_price": f"{shopify_price:.2f}",
                        "difference": f"{source_price - shopify_price:.2f}",
                        "shopify_id": match.get("id", ""),
                    }
                )

    return {
        "new_products": new_products,
        "duplicates": duplicates,
        "price_differences": price_differences,
        "summary": {
            "lebelage_count": len(lebelage_products),
            "shopify_count": len(shopify_products),
            "new_count": len(new_products),
            "duplicate_count": len(duplicates),
            "price_difference_count": len(price_differences),
        },
    }


def save_json(products: list[Product], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(p) for p in products], ensure_ascii=False, indent=2), encoding="utf-8")


def save_csv(products: list[Product], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(products[0]).keys()) if products else ["title"])
        writer.writeheader()
        for product in products:
            row = asdict(product)
            row["tags"] = ", ".join(product.tags)
            writer.writerow(row)


def _next_page_info(link_header: str) -> str:
    for part in link_header.split(","):
        if 'rel="next"' not in part:
            continue
        match = re.search(r"[?&]page_info=([^&>]+)", part)
        if match:
            return match.group(1)
    return ""


def save_shopify_products(products: list[dict], json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = []
    for product in products:
        variants = product.get("variants") or [{}]
        images = product.get("images") or [{}]
        rows.append(
            {
                "id": product.get("id", ""),
                "title": product.get("title", ""),
                "handle": product.get("handle", ""),
                "status": product.get("status", ""),
                "vendor": product.get("vendor", ""),
                "product_type": product.get("product_type", ""),
                "tags": product.get("tags", ""),
                "price": variants[0].get("price", "") if variants else "",
                "sku": variants[0].get("sku", "") if variants else "",
                "image_url": images[0].get("src", "") if images else "",
                "created_at": product.get("created_at", ""),
                "updated_at": product.get("updated_at", ""),
            }
        )

    fieldnames = [
        "id",
        "title",
        "handle",
        "status",
        "vendor",
        "product_type",
        "tags",
        "price",
        "sku",
        "image_url",
        "created_at",
        "updated_at",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_comparison_report(report: dict, json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = []
    for product in report.get("new_products", []):
        rows.append(
            {
                "type": "nouveau",
                "title": product.get("title", ""),
                "lebelage_price": product.get("final_price_amount") or product.get("price_amount", ""),
                "shopify_price": "",
                "difference": "",
                "shopify_id": "",
                "source_url": product.get("source_url", ""),
            }
        )
    for item in report.get("duplicates", []):
        product = item.get("lebelage", {})
        for match in item.get("shopify_matches", []):
            variants = match.get("variants") or [{}]
            rows.append(
                {
                    "type": "doublon",
                    "title": product.get("title", ""),
                    "lebelage_price": product.get("final_price_amount") or product.get("price_amount", ""),
                    "shopify_price": variants[0].get("price", "") if variants else "",
                    "difference": "",
                    "shopify_id": match.get("id", ""),
                    "source_url": product.get("source_url", ""),
                }
            )
    for item in report.get("price_differences", []):
        rows.append(
            {
                "type": "prix_different",
                "title": item.get("title", ""),
                "lebelage_price": item.get("lebelage_price", ""),
                "shopify_price": item.get("shopify_price", ""),
                "difference": item.get("difference", ""),
                "shopify_id": item.get("shopify_id", ""),
                "source_url": "",
            }
        )

    fieldnames = ["type", "title", "lebelage_price", "shopify_price", "difference", "shopify_id", "source_url"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def shopify_client_from_env() -> ShopifyClient:
    return ShopifyClient(
        shop_domain=os.getenv("SHOPIFY_SHOP_DOMAIN")
        or os.getenv("TIBO_SHOPIFY_SHOP_DOMAIN", ""),
        access_token=os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
        or os.getenv("TIBO_SHOPIFY_ACCESS_TOKEN", ""),
        api_version=os.getenv("SHOPIFY_API_VERSION")
        or os.getenv("TIBO_SHOPIFY_API_VERSION", "2026-01"),
    )


def export_shopify_products(json_path: Path, csv_path: Path) -> list[dict]:
    client = shopify_client_from_env()
    products = client.list_products()
    save_shopify_products(products, json_path, csv_path)
    return products


def import_to_shopify(products: list[Product], update_existing: bool) -> None:
    client = shopify_client_from_env()
    for product in products:
        existing = client.find_product_by_title(product.title)
        if existing and update_existing:
            updated = client.update_product(existing["id"], product)
            logging.info("Updated Shopify product %s (%s)", updated["title"], updated["id"])
        elif existing:
            logging.info("Skip existing Shopify product: %s (%s)", product.title, existing["id"])
        else:
            created = client.create_product(product)
            logging.info("Created Shopify product %s (%s)", created["title"], created["id"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scrape LEBELAGE products and optionally import into Shopify.")
    parser.add_argument("--source-url", default=BASE_URL)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--shipping", type=float, default=0.0)
    parser.add_argument("--margin", type=float, default=0.0)
    parser.add_argument("--out", default="tmp/lebelage_products.json")
    parser.add_argument("--csv", default="tmp/lebelage_products.csv")
    parser.add_argument("--export-shopify", action="store_true")
    parser.add_argument("--shopify-out", default="tmp/shopify_products.json")
    parser.add_argument("--shopify-csv", default="tmp/shopify_products.csv")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--compare-out", default="tmp/lebelage_shopify_comparison.json")
    parser.add_argument("--compare-csv", default="tmp/lebelage_shopify_comparison.csv")
    parser.add_argument("--import-shopify", action="store_true")
    parser.add_argument("--update-existing", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s %(message)s")

    if args.export_shopify:
        shopify_products = export_shopify_products(Path(args.shopify_out), Path(args.shopify_csv))
        logging.info(
            "Saved %s Shopify products to %s and %s",
            len(shopify_products),
            args.shopify_out,
            args.shopify_csv,
        )
        return 0

    product_urls = crawl_product_urls(args.source_url, args.max_pages, args.limit, args.sleep)
    logging.info("Discovered %s product URLs", len(product_urls))

    products: list[Product] = []
    seen_titles = set()
    for url in product_urls:
        try:
            product = scrape_product(url)
        except Exception as exc:
            logging.exception("Product scrape failed for %s: %s", url, exc)
            continue
        key = product.title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        products.append(product)
        logging.info("Scraped: %s | %s | %s", product.title, product.price, product.image_url)
        time.sleep(args.sleep)

    products = enrich_products(products, shipping=args.shipping, margin=args.margin)
    save_json(products, Path(args.out))
    save_csv(products, Path(args.csv))
    logging.info("Saved %s products to %s and %s", len(products), args.out, args.csv)

    if args.compare:
        shopify_path = Path(args.shopify_out)
        if shopify_path.exists():
            shopify_products = json.loads(shopify_path.read_text(encoding="utf-8"))
        else:
            shopify_products = export_shopify_products(Path(args.shopify_out), Path(args.shopify_csv))
        report = compare_lebelage_to_shopify([asdict(product) for product in products], shopify_products)
        save_comparison_report(report, Path(args.compare_out), Path(args.compare_csv))
        logging.info("Comparison saved to %s and %s", args.compare_out, args.compare_csv)

    if args.import_shopify:
        import_to_shopify(products, update_existing=args.update_existing)
    else:
        logging.info("Dry-run only. Add --import-shopify to create products in Shopify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
