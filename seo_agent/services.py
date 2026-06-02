import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify


@dataclass
class SEOIssue:
    level: str
    title: str
    detail: str
    file_path: str


PUBLIC_URLS = [
    ("/", "Accueil E-Shelle", "Page mere de conversion"),
    ("/business/local/", "GEO Local Business", "Pages ville + service deja amorcees"),
    ("/resto/", "Restaurants", "Module restaurants"),
    ("/gaz/", "Gaz", "Livraison gaz"),
    ("/pressing/", "Pressing", "Pressing et blanchisserie"),
    ("/immobilier/", "Immobilier", "Biens immobiliers"),
    ("/auto/", "Auto", "Vente auto"),
    ("/agro/", "Agro", "Marketplace agro"),
    ("/sante/", "Sante", "Produits et professionnels sante"),
    ("/jobs/", "Jobs", "Emplois et missions"),
    ("/seo/articles/marche-numerique-afrique-2025/", "Article marche numerique", "Contenu pilier SEO"),
]


GEO_CITIES = ["Douala", "Yaounde", "Bafoussam", "Garoua", "Bamenda", "Kribi", "Limbe"]
GEO_SERVICES = [
    ("restaurants", "restaurants proches, menus et commandes WhatsApp"),
    ("pressing", "pressing, lavage, repassage et livraison"),
    ("gaz", "livraison de gaz domestique"),
    ("immobilier", "appartements, studios, terrains et villas"),
    ("auto", "voitures d'occasion et annonces auto"),
    ("sante", "pharmacies, produits sante et professionnels"),
    ("agro", "produits agricoles, grossistes et producteurs"),
]


class SEOAuditAgent:
    """Audit technique local des templates HTML E-Shelle."""

    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or settings.BASE_DIR)

    def run(self, limit=120):
        files = self._template_files()
        issues = []
        pages_ok = 0
        for path in files[:limit]:
            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = str(path.relative_to(self.base_dir))
            found = self._inspect_template(text, rel)
            issues.extend(found)
            if not found:
                pages_ok += 1
        critical = sum(1 for item in issues if item.level == "danger")
        warning = sum(1 for item in issues if item.level == "warning")
        score = max(0, 100 - critical * 4 - warning * 2)
        return {
            "score": score,
            "files_scanned": min(len(files), limit),
            "pages_ok": pages_ok,
            "critical": critical,
            "warning": warning,
            "issues": issues[:80],
        }

    def _template_files(self):
        candidates = []
        for root in [self.base_dir / "templates", *self.base_dir.glob("*/templates"), *self.base_dir.glob("apps/*/templates")]:
            if root.exists():
                candidates.extend(root.rglob("*.html"))
        return sorted(set(candidates))

    def _inspect_template(self, text, rel):
        issues = []
        lower = text.lower()
        public_like = not any(part in rel.lower() for part in ["admin", "dashboard", "mon_compte", "accounts/login"])

        if public_like and "{% block title" not in lower and "<title" not in lower:
            issues.append(SEOIssue("danger", "Titre SEO absent", "Ajouter un block title ou une balise title claire.", rel))
        if public_like and "meta_description" not in lower and 'name="description"' not in lower:
            issues.append(SEOIssue("warning", "Meta description absente", "Ajouter une description persuasive entre 120 et 155 caracteres.", rel))
        if public_like and not re.search(r"<h1[\s>]", lower):
            issues.append(SEOIssue("warning", "H1 non detecte", "Chaque page indexable doit avoir un seul H1 utile.", rel))

        image_tags = re.findall(r"<img\b[^>]*>", text, flags=re.I)
        missing_alt = [tag for tag in image_tags if " alt=" not in tag.lower()]
        if public_like and missing_alt:
            issues.append(SEOIssue("warning", "Images sans alt", f"{len(missing_alt)} image(s) sans texte alternatif.", rel))
        if public_like and "schema.org" not in lower and "application/ld+json" not in lower:
            issues.append(SEOIssue("warning", "Schema.org absent", "Ajouter JSON-LD: LocalBusiness, Product, Service, FAQ ou Breadcrumb.", rel))
        if public_like and all(token not in lower for token in ["whatsapp", "demander", "commander", "reserver", "contacter", "s'inscrire"]):
            issues.append(SEOIssue("warning", "CTA faible", "Ajouter un appel a l'action clair vers WhatsApp, devis ou inscription.", rel))
        return issues


class LocalSEOAgent:
    """Propose des pages GEO a creer pour capter les recherches locales."""

    SERVICE_VALUE = {
        "immobilier": 10,
        "livraison-gaz": 8,
        "restaurants": 7,
        "pressing": 7,
        "pharmacies": 7,
        "agro": 7,
        "boutiques": 6,
        "artisans": 6,
        "emplois": 5,
    }

    def ideas(self):
        ideas = []
        for city in GEO_CITIES:
            for service, intent in GEO_SERVICES:
                slug_city = city.lower().replace(" ", "-")
                slug_service = service.lower().replace(" ", "-")
                ideas.append(
                    {
                        "title": f"{service.capitalize()} a {city}",
                        "url": f"/business/local/{slug_city}/{slug_service}/",
                        "intent": intent,
                        "cta": f"Trouver un prestataire {service} a {city}",
                    }
                )
        return ideas

    def prioritized_pages(self, request=None, limit=24):
        """Classe les pages GEO selon l'intention commerciale et les donnees en base."""

        try:
            from business.models import BusinessProfile
            from business.seo_geo import SEO_SERVICE_MAP
        except Exception:
            return self._fallback_priorities(request, limit)

        pages = []
        cities = (
            BusinessProfile.objects.filter(is_active=True)
            .exclude(city="")
            .values_list("city", flat=True)
            .distinct()
        )
        for city in cities:
            city_slug = slugify(city)
            for service_slug, service in SEO_SERVICE_MAP.items():
                count = BusinessProfile.objects.filter(
                    is_active=True,
                    city__iexact=city,
                    module=service["module"],
                ).count()
                if not count:
                    continue
                value = self.SERVICE_VALUE.get(service_slug, 5)
                score = min(100, 35 + count * 8 + value * 4)
                path = reverse("business:geo_landing", args=[city_slug, service_slug])
                pages.append(
                    {
                        "title": f"{service['plural'].capitalize()} a {city}",
                        "url": request.build_absolute_uri(path) if request else path,
                        "path": path,
                        "city": city,
                        "service": service_slug,
                        "count": count,
                        "score": score,
                        "reason": f"{count} fiche(s) active(s), intention commerciale {value}/10",
                    }
                )
        pages.sort(key=lambda item: (-item["score"], -item["count"], item["title"]))
        return pages[:limit]

    def _fallback_priorities(self, request, limit):
        pages = []
        for item in self.ideas()[:limit]:
            pages.append({**item, "path": item["url"], "count": 0, "score": 50, "reason": "Page conseillee par defaut"})
        return pages


class SchemaAgent:
    """Cartographie les schemas utiles par module."""

    def suggestions(self):
        return [
            {"module": "Accueil", "schema": "Organization + WebSite", "priority": "Haute"},
            {"module": "Business profiles", "schema": "LocalBusiness + BreadcrumbList", "priority": "Haute"},
            {"module": "Resto", "schema": "Restaurant + Menu + AggregateRating", "priority": "Haute"},
            {"module": "Gaz/Pressing/Sante", "schema": "Service + LocalBusiness", "priority": "Haute"},
            {"module": "Immobilier/Auto", "schema": "Product + Offer", "priority": "Moyenne"},
            {"module": "Articles SEO", "schema": "Article + FAQPage", "priority": "Haute"},
        ]


class CTAAgent:
    """Recommande les appels a l'action par intention."""

    def suggestions(self):
        return [
            {"page": "Pages service locales", "cta": "Voir les prestataires disponibles + Contacter sur WhatsApp"},
            {"page": "Fiches business", "cta": "Demander un devis / Ecrire sur WhatsApp / Voir itineraire"},
            {"page": "Articles SEO", "cta": "Publier mon business sur E-Shelle + Recevoir des clients"},
            {"page": "Modules marketplace", "cta": "Comparer les offres + Ajouter au panier + Appeler"},
            {"page": "Dashboard prestataire", "cta": "Booster ma fiche + Creer une campagne WhatsApp"},
        ]


class ContentSEOAgent:
    """Briefs d'articles utiles et non generiques."""

    def briefs(self):
        return [
            "Ou commander du gaz a Douala rapidement ?",
            "Comment trouver un bon pressing a Yaounde ?",
            "Prix d'un appartement meuble a Douala : quartiers et conseils",
            "Comment vendre plus avec WhatsApp Business au Cameroun ?",
            "Marketplace au Cameroun : comment les PME gagnent des clients en ligne",
            "Restaurants a Douala : comment etre visible sur Google et WhatsApp",
            "Guide SEO local pour prestataires camerounais",
        ]


class GoogleBusinessAgent:
    """Textes prets pour fiches Google Business Profile."""

    def drafts(self):
        return [
            {
                "type": "Description E-Shelle",
                "text": "E-Shelle aide les clients au Cameroun a trouver rapidement restaurants, gaz, pressing, immobilier, auto, sante, jobs et services locaux avec contact WhatsApp direct.",
            },
            {
                "type": "Post Google Business",
                "text": "Besoin de clients en ligne ? Publiez votre business sur E-Shelle et recevez des demandes via WhatsApp, Google et notre marketplace locale.",
            },
            {
                "type": "Reponse avis",
                "text": "Merci pour votre retour. L'equipe E-Shelle continue d'ameliorer la visibilite des business locaux et la mise en relation avec les clients.",
            },
        ]


class SEOCorrectionAgent:
    """Prepare des corrections SEO pretes a appliquer pour un template."""

    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or settings.BASE_DIR).resolve()

    def plan_for(self, relative_path, issue_title=""):
        path = (self.base_dir / relative_path).resolve()
        if self.base_dir not in path.parents and path != self.base_dir:
            raise ValueError("Chemin refuse.")
        if not path.exists() or path.suffix.lower() != ".html":
            raise ValueError("Template introuvable.")

        text = path.read_text(encoding="utf-8", errors="ignore")
        page_name = self._page_name(relative_path)
        return {
            "file_path": relative_path,
            "issue_title": issue_title or "Optimisation SEO",
            "page_name": page_name,
            "has_title": "{% block title" in text.lower() or "<title" in text.lower(),
            "has_meta": "meta_description" in text.lower() or 'name="description"' in text.lower(),
            "has_h1": bool(re.search(r"<h1[\s>]", text, flags=re.I)),
            "has_schema": "schema.org" in text.lower() or "application/ld+json" in text.lower(),
            "title_block": f"{{% block title %}}{page_name} - E-Shelle Cameroun{{% endblock %}}",
            "meta_block": (
                "{% block meta_description %}"
                f"Decouvrez {page_name.lower()} sur E-Shelle, comparez les offres locales et contactez rapidement un prestataire au Cameroun."
                "{% endblock %}"
            ),
            "h1_example": f"<h1>{page_name} au Cameroun</h1>",
            "cta_block": (
                '<a class="btn btn-primary" href="/business/onboarding/?plan=free">'
                "Publier mon business sur E-Shelle"
                "</a>"
            ),
            "schema_block": self._schema_block(page_name),
        }

    def _page_name(self, relative_path):
        stem = Path(relative_path).stem.replace("_", " ").replace("-", " ")
        parts = [part.capitalize() for part in stem.split() if part]
        return " ".join(parts) or "Page E-Shelle"

    def _schema_block(self, page_name):
        return f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "{page_name} - E-Shelle",
  "description": "Page E-Shelle optimisee pour le referencement naturel au Cameroun.",
  "inLanguage": "fr-CM"
}}
</script>'''


def build_sitemap_entries(request):
    base = f"{request.scheme}://{request.get_host()}"
    entries = [{"loc": f"{base}{url}", "label": label, "kind": kind} for url, label, kind in PUBLIC_URLS]
    for page in LocalSEOAgent().prioritized_pages(request=request, limit=30):
        entries.append({"loc": page["url"], "label": page["title"], "kind": "GEO rentable"})
    return entries
