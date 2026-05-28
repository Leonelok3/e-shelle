"""Service central de routage pour E-Shelle AI.

Ce module devient le cerveau commun du chat public et, progressivement, de
l'agent IA avance. Il garde la compatibilite avec le routeur existant tout en
ajoutant la priorite aux prestataires Premium/Business.
"""

import json
import logging
import urllib.parse

from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


class CentralAgentService:
    """Route les demandes utilisateur vers le bon module E-Shelle."""

    def route_message(self, user_message: str, conversation_history: list | None = None, user=None) -> dict:
        conversation_history = conversation_history or []

        from chat import services as legacy

        fallback = legacy._fallback_route(user_message)
        fallback = self._attach_results(fallback, user_message)

        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not api_key:
            return fallback

        system_prompt = self._system_prompt(legacy.SYSTEM_PROMPT, user)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-10:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o"),
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.7,
            )
            result = json.loads(response.choices[0].message.content)
            result = legacy._normalize_result(result, fallback)
            result = self._attach_results(result, user_message)
            if result.get("generate_image") and result.get("image_prompt"):
                result["image_url"] = legacy.generate_image(result["image_prompt"])
            else:
                result["image_url"] = ""
            return result
        except Exception as exc:
            logger.exception("Central agent routing error: %s", exc)
            fallback["error"] = str(exc)
            return fallback

    def _attach_results(self, route: dict, query: str) -> dict:
        from chat import services as legacy

        module = route.get("module", "general")
        premium_results = self._premium_business_results(query, module=module, limit=3)
        extra_results = self._extra_module_results(module, query, limit=3)
        module_results = legacy.get_module_results(module, query, limit=3)

        results = self._merge_results(premium_results, extra_results, module_results)
        if not results:
            results = legacy._results_or_external(module, query)
        if self._should_ask_location(module, query):
            results = self._merge_results(results, [self._location_followup_card(module, query)])
        if self._should_add_order_followup(module, results):
            results = self._merge_results(results, [self._order_followup_card(module, query)])

        route["results"] = results
        route["message"] = self._commercial_message(route, query, results)
        return route

    def _system_prompt(self, base_prompt: str, user=None) -> str:
        context = self._user_business_context(user)
        if not context:
            return base_prompt
        return f"{base_prompt}\n\nContexte utilisateur connu par E-Shelle AI:\n{context}\nUtilise ce contexte pour personnaliser la reponse sans inventer de donnees."

    def _user_business_context(self, user=None) -> str:
        if not getattr(user, "is_authenticated", False):
            return ""

        parts = []
        try:
            from e_shelle_ai.services.memory_service import MemoryService

            memory = MemoryService().get_memory_for_prompt(user)
            if memory:
                parts.append(memory)
        except Exception as exc:
            logger.debug("AI memory unavailable: %s", exc)

        try:
            from business.models import BusinessProfile

            businesses = BusinessProfile.objects.filter(owner=user, is_active=True).order_by("-updated_at")[:3]
            for business in businesses:
                parts.append(
                    "Fiche business: "
                    f"{business.name}, module={business.get_module_display()}, "
                    f"ville={business.city or '-'}, quartier={business.district or '-'}, "
                    f"plan={business.get_plan_display()}, vues={business.views_count}, contacts={business.leads_count}"
                )
        except Exception as exc:
            logger.debug("Business context unavailable: %s", exc)

        return "\n".join(parts)

    def _commercial_message(self, route: dict, query: str, results: list) -> str:
        module = route.get("module", "general")
        message = route.get("message", "")
        if not results:
            return message

        prefixes = {
            "resto": "J'ai trouve des restaurants et offres premium que tu peux contacter directement.",
            "gaz": "J'ai trouve des fournisseurs de gaz avec action rapide pour commander.",
            "pressing": "J'ai trouve des pressings disponibles avec contact direct.",
            "sante": "J'ai trouve des resultats sante/pharmacie utiles avec contact rapide.",
            "immobilier": "J'ai trouve des annonces immobilieres et contacts utiles.",
            "auto": "J'ai trouve des vehicules ou contacts auto pour avancer rapidement.",
            "agro": "J'ai trouve des produits ou acteurs agro disponibles.",
            "boutique": "J'ai trouve des produits boutique a consulter directement.",
            "transport": "J'ai trouve des options de transport ou le bon module pour continuer.",
            "business_onboarding": "Oui, tu peux inscrire ton business et recevoir des clients via E-Shelle.",
        }
        prefix = prefixes.get(module)
        if not prefix:
            return message

        premium_count = sum(1 for item in results if str(item.get("badge", "")).lower() in {"premium", "business"})
        premium_note = " Les resultats Premium/Business sont mis en avant." if premium_count else ""
        location_note = " Donne ta ville ou ton quartier si tu veux que je filtre plus precisement." if self._should_ask_location(module, query) else ""
        return f"{prefix}{premium_note}{location_note} Clique sur une carte pour commander ou contacter."

    def _should_ask_location(self, module: str, query: str) -> bool:
        local_modules = {"resto", "gaz", "pressing", "sante", "immobilier", "auto", "transport", "agro", "services"}
        if module not in local_modules:
            return False
        terms = self._search_terms(query)
        known_locations = {
            "douala", "yaounde", "yaoundé", "bafoussam", "buea", "limbe", "akwa", "bonamoussadi",
            "kotto", "bonaberi", "bonaberie", "bastos", "mvan", "bali", "deido", "logpom",
        }
        return not any(term in known_locations for term in terms)

    def _location_followup_card(self, module: str, query: str) -> dict:
        examples = {
            "resto": "je veux manger a Bonamoussadi",
            "gaz": "je veux du gaz a Kotto",
            "pressing": "je cherche un pressing a Akwa",
            "sante": "je cherche une pharmacie a Bonaberi",
            "immobilier": "je cherche un terrain a Douala",
            "auto": "je veux acheter une voiture a Yaounde",
            "transport": "je cherche transport Douala Yaounde",
            "agro": "je cherche manioc a Douala",
        }
        example = examples.get(module, f"{query} a Douala")
        return {
            "title": "Préciser la zone",
            "subtitle": "Résultats plus proches et plus fiables",
            "details": "Ajoutez votre ville ou quartier pour que E-Shelle AI priorise les bonnes offres autour de vous.",
            "badge": "Conseil IA",
            "url": f"/chat/?q={urllib.parse.quote(example)}",
            "primary_label": "Filtrer par zone",
            "primary_url": f"/chat/?q={urllib.parse.quote(example)}",
            "secondary_label": "Continuer",
            "secondary_url": "",
        }

    def _should_add_order_followup(self, module: str, results: list) -> bool:
        return module in {"resto", "gaz", "pressing", "sante", "boutique", "agro", "auto", "immobilier"} and bool(results)

    def _order_followup_card(self, module: str, query: str) -> dict:
        labels = {
            "resto": "Commander maintenant",
            "gaz": "Commander du gaz",
            "pressing": "Contacter un pressing",
            "sante": "Contacter une pharmacie",
            "boutique": "Voir le produit",
            "agro": "Demander un devis",
            "auto": "Contacter le vendeur",
            "immobilier": "Planifier une visite",
        }
        label = labels.get(module, "Continuer")
        message = f"{query}. Je veux passer a l'action maintenant."
        return {
            "title": "Prêt à passer à l'action ?",
            "subtitle": "E-Shelle AI peut vous orienter vers le meilleur choix",
            "details": "Cliquez ici si vous voulez commander, appeler ou envoyer un message WhatsApp maintenant.",
            "badge": "Action",
            "url": f"/chat/?q={urllib.parse.quote(message)}",
            "primary_label": label,
            "primary_url": f"/chat/?q={urllib.parse.quote(message)}",
            "secondary_label": "Comparer encore",
            "secondary_url": "",
        }

    def _premium_business_results(self, query: str, module: str = "general", limit: int = 3) -> list:
        try:
            from business.models import BusinessLeadEvent, BusinessProfile
            from business.services import create_tracking_event, record_business_impression
        except Exception as exc:
            logger.debug("Premium business unavailable: %s", exc)
            return []

        module_map = {
            "formation": BusinessProfile.Module.FORMATION,
            "resto": BusinessProfile.Module.RESTO,
            "gaz": BusinessProfile.Module.GAZ,
            "pressing": BusinessProfile.Module.PRESSING,
            "sante": BusinessProfile.Module.SANTE,
            "jobs": BusinessProfile.Module.JOBS,
            "boutique": BusinessProfile.Module.BOUTIQUE,
            "agro": BusinessProfile.Module.AGRO,
            "immobilier": BusinessProfile.Module.IMMOBILIER,
            "quincaillerie": BusinessProfile.Module.QUINCAILLERIE,
        }

        mapped_module = module_map.get(module)
        if not mapped_module and module not in {"general", "services"}:
            return []

        qs = BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.PREMIUM, BusinessProfile.Plan.BUSINESS],
        )
        if mapped_module:
            qs = qs.filter(module=mapped_module)

        qs = self._filter_businesses(qs, query)
        qs = qs.order_by("-boost_expires_at", "-subscription_expires_at", "-leads_count", "-views_count", "name")

        cards = []
        for business in qs[:limit]:
            record_business_impression(
                business,
                source="central_agent",
                metadata={"query": query, "module": module, "placement": "premium_business_result"},
            )
            target_url = self._business_target_url(business)
            event = create_tracking_event(
                business,
                BusinessLeadEvent.EventType.ORDER,
                target_url,
                source="central_agent",
                metadata={"query": query, "module": module},
            )
            cards.append(
                {
                    "title": business.promo_headline or business.name,
                    "subtitle": self._business_subtitle(business),
                    "details": business.promo_offer or self._shorten(business.description, 140),
                    "badge": business.get_plan_display(),
                    "url": event.tracking_url(),
                    "primary_label": "Commander" if business.module in {BusinessProfile.Module.RESTO, BusinessProfile.Module.GAZ, BusinessProfile.Module.SANTE} else "Contacter",
                    "primary_url": event.tracking_url(),
                    "secondary_label": f"{business.views_count} vues",
                    "secondary_url": "",
                }
            )
        return cards

    def _extra_module_results(self, module: str, query: str, limit: int = 3) -> list:
        builders = {
            "immobilier": self._immobilier_results,
            "boutique": self._boutique_results,
            "sante": self._pharma_results,
            "transport": self._transport_results,
            "auto": self._auto_results,
            "agro": self._agro_results,
            "rencontres": self._rencontres_results,
            "business_onboarding": self._business_onboarding_results,
        }
        builder = builders.get(module)
        if not builder:
            return []
        try:
            return builder(query, limit)
        except Exception as exc:
            logger.exception("Central agent module result error for %s: %s", module, exc)
            return []

    def _immobilier_results(self, query: str, limit: int) -> list:
        from immobilier_cameroun.models import Bien, StatutBien

        qs = Bien.objects.filter(statut=StatutBien.PUBLIE).order_by(
            "-est_mis_en_avant", "-est_coup_de_coeur", "-created_at"
        )
        qs = self._apply_text_filter(qs, query, "titre", "description", "ville", "quartier", "adresse_complete")

        cards = []
        for bien in qs[:limit]:
            details = [part for part in [bien.quartier, bien.get_type_bien_display(), bien.prix_formate] if part]
            cards.append(
                {
                    "title": bien.titre,
                    "subtitle": f"{bien.get_type_transaction_display()} - {bien.ville}",
                    "details": " - ".join(details),
                    "badge": "Premium" if bien.est_mis_en_avant else "Immobilier",
                    "url": bien.get_absolute_url(),
                    "primary_label": "Contacter",
                    "primary_url": bien.get_whatsapp_url(),
                    "secondary_label": f"{bien.vues} vues",
                    "secondary_url": bien.get_absolute_url(),
                }
            )
        return cards

    def _boutique_results(self, query: str, limit: int) -> list:
        from boutique.models import Produit

        qs = Produit.objects.filter(is_published=True).select_related("categorie").order_by(
            "-is_featured", "-nb_ventes", "titre"
        )
        qs = self._apply_text_filter(qs, query, "titre", "description", "description_courte", "categorie__nom")

        cards = []
        for produit in qs[:limit]:
            price = "Gratuit" if produit.is_gratuit else self._money_text(produit.prix)
            cards.append(
                {
                    "title": produit.titre,
                    "subtitle": produit.categorie.nom if produit.categorie_id else "Boutique E-Shelle",
                    "details": self._join_text(price, self._shorten(produit.description_courte or produit.description, 120)),
                    "badge": "En vedette" if produit.is_featured else "Boutique",
                    "url": f"/boutique/{produit.slug}/",
                    "primary_label": "Voir le produit",
                    "primary_url": f"/boutique/{produit.slug}/",
                    "secondary_label": f"{produit.nb_ventes} ventes",
                    "secondary_url": "/boutique/catalogue/",
                }
            )
        return cards

    def _pharma_results(self, query: str, limit: int) -> list:
        from pharma.models import Pharmacie, StockPharmacie

        terms = self._search_terms(query)
        stock_qs = (
            StockPharmacie.objects.filter(disponible=True, pharmacie__is_active=True, pharmacie__abonnement_actif=True)
            .select_related("medicament", "pharmacie", "pharmacie__ville", "pharmacie__quartier")
            .order_by("-pharmacie__is_featured", "-pharmacie__is_verified", "medicament__nom")
        )
        if terms:
            q = Q()
            for term in terms:
                q |= Q(medicament__nom__icontains=term) | Q(pharmacie__nom__icontains=term) | Q(pharmacie__ville__nom__icontains=term) | Q(pharmacie__quartier__nom__icontains=term)
            matched = stock_qs.filter(q).distinct()
            if matched.exists():
                stock_qs = matched

        cards = []
        for stock in stock_qs[:limit]:
            pharmacie = stock.pharmacie
            med = stock.medicament
            location = self._join_text(
                pharmacie.ville.nom if pharmacie.ville_id else "",
                pharmacie.quartier.nom if pharmacie.quartier_id else "",
            )
            cards.append(
                {
                    "title": med.nom,
                    "subtitle": pharmacie.nom,
                    "details": self._join_text(location, self._money_text(stock.prix) or "Prix a confirmer"),
                    "badge": "Pharmacie verifiee" if pharmacie.is_verified else "Pharmacie",
                    "url": f"/pharma/medicament/{med.slug}/",
                    "primary_label": "Demander sur WhatsApp",
                    "primary_url": pharmacie.whatsapp_url_medicament(med.nom),
                    "secondary_label": "Appeler",
                    "secondary_url": pharmacie.tel_url,
                }
            )
        if cards:
            return cards

        pharmacies = Pharmacie.objects.filter(is_active=True, abonnement_actif=True).order_by("-is_featured", "-is_verified", "nom")
        pharmacies = self._apply_text_filter(pharmacies, query, "nom", "description", "ville__nom", "quartier__nom")
        return [
            {
                "title": pharmacie.nom,
                "subtitle": self._join_text(pharmacie.ville.nom if pharmacie.ville_id else "", pharmacie.quartier.nom if pharmacie.quartier_id else ""),
                "details": f"{pharmacie.nb_medicaments_dispo} medicaments disponibles",
                "badge": "Pharmacie verifiee" if pharmacie.is_verified else "Pharmacie",
                "url": f"/pharma/pharmacie/{pharmacie.slug}/",
                "primary_label": "Contacter",
                "primary_url": pharmacie.whatsapp_url,
                "secondary_label": "Appeler",
                "secondary_url": pharmacie.tel_url,
            }
            for pharmacie in pharmacies[:limit]
        ]

    def _transport_results(self, query: str, limit: int) -> list:
        from django.utils import timezone
        from transport_core.models import Trajet

        qs = (
            Trajet.objects.filter(is_active=True, statut=Trajet.Statut.OUVERT, date_depart__gte=timezone.localdate())
            .select_related("depart", "arrivee")
            .order_by("-is_featured", "date_depart", "heure_depart")
        )
        qs = self._apply_text_filter(qs, query, "titre", "depart__nom", "arrivee__nom", "lieu_depart", "lieu_arrivee", "vehicule")

        cards = []
        for trajet in qs[:limit]:
            cards.append(
                {
                    "title": trajet.titre,
                    "subtitle": f"{trajet.depart.nom} -> {trajet.arrivee.nom}",
                    "details": f"{trajet.date_depart} a {trajet.heure_depart.strftime('%H:%M')} - {trajet.prix_display}",
                    "badge": trajet.get_type_trajet_display(),
                    "url": trajet.get_absolute_url(),
                    "primary_label": "Reserver",
                    "primary_url": trajet.whatsapp_url,
                    "secondary_label": f"{trajet.places_disponibles} places",
                    "secondary_url": trajet.get_absolute_url(),
                }
            )
        return cards

    def _auto_results(self, query: str, limit: int) -> list:
        from auto_cameroun.models import StatutVehicule, Vehicule

        qs = Vehicule.objects.filter(statut=StatutVehicule.PUBLIE).order_by(
            "-est_mis_en_avant", "-est_coup_de_coeur", "-created_at"
        )
        qs = self._apply_text_filter(qs, query, "titre", "marque", "modele", "ville", "quartier", "description")

        cards = []
        for vehicule in qs[:limit]:
            details = self._join_text(
                vehicule.ville,
                f"{vehicule.kilometrage} km" if vehicule.kilometrage else "",
                vehicule.prix_formate,
            )
            cards.append(
                {
                    "title": vehicule.titre,
                    "subtitle": f"{vehicule.marque} {vehicule.modele} - {vehicule.annee}",
                    "details": details,
                    "badge": "Premium" if vehicule.est_mis_en_avant else "Auto",
                    "url": vehicule.get_absolute_url(),
                    "primary_label": "Contacter",
                    "primary_url": vehicule.get_whatsapp_url(),
                    "secondary_label": f"{vehicule.vues} vues",
                    "secondary_url": vehicule.get_absolute_url(),
                }
            )
        return cards

    def _agro_results(self, query: str, limit: int) -> list:
        from agro.models import ProduitAgro

        qs = (
            ProduitAgro.objects.filter(statut="publie")
            .select_related("acteur", "categorie")
            .order_by("-est_mis_en_avant", "-nb_vues", "nom")
        )
        qs = self._apply_text_filter(qs, query, "nom", "description", "categorie__nom", "acteur__nom_entreprise", "acteur__ville", "acteur__pays")

        cards = []
        for produit in qs[:limit]:
            acteur = produit.acteur
            number = (acteur.whatsapp or acteur.telephone or "").replace("+", "").replace(" ", "").replace("-", "")
            whatsapp_url = ""
            if number:
                if not number.startswith("237"):
                    number = f"237{number}"
                text = urllib.parse.quote(f"Bonjour, je suis interesse par {produit.nom} vu sur E-Shelle Agro.")
                whatsapp_url = f"https://wa.me/{number}?text={text}"
            price = f"{int(produit.prix_unitaire):,} {produit.devise}/{produit.unite_mesure}".replace(",", " ")
            cards.append(
                {
                    "title": produit.nom,
                    "subtitle": self._join_text(acteur.nom_entreprise, acteur.ville),
                    "details": self._join_text(price, f"Stock: {produit.quantite_stock:g} {produit.unite_mesure}"),
                    "badge": "Premium" if produit.est_mis_en_avant else "Agro",
                    "url": produit.get_absolute_url(),
                    "primary_label": "Demander un devis",
                    "primary_url": whatsapp_url or produit.get_absolute_url(),
                    "secondary_label": f"{produit.nb_vues} vues",
                    "secondary_url": produit.get_absolute_url(),
                }
            )
        return cards

    def _rencontres_results(self, query: str, limit: int) -> list:
        return [
            {
                "title": "E-Shelle Love",
                "subtitle": "Rencontres serieuses et profils verifies",
                "details": "Cree ton profil, precise tes criteres et decouvre les profils compatibles.",
                "badge": "Rencontres",
                "url": "/rencontres/",
                "primary_label": "Commencer",
                "primary_url": "/rencontres/",
                "secondary_label": "Premium",
                "secondary_url": "/rencontres/premium/",
            }
        ][:limit]

    def _business_onboarding_results(self, query: str, limit: int) -> list:
        return [
            {
                "title": "Inscrire mon business",
                "subtitle": "Vitrine Premium ou Business sur E-Shelle",
                "details": "Ajoutez vos contacts, offres, visuels de carrousel et recevez des clients depuis E-Shelle AI.",
                "badge": "Prestataire",
                "url": "/business/onboarding/",
                "primary_label": "Creer ma fiche",
                "primary_url": "/business/onboarding/",
                "secondary_label": "Voir les plans",
                "secondary_url": "/business/plans/",
            }
        ][:limit]

    def _filter_businesses(self, qs, query: str):
        terms = self._search_terms(query)
        if not terms:
            return qs

        query_filter = Q()
        for term in terms:
            query_filter |= (
                Q(name__icontains=term)
                | Q(city__icontains=term)
                | Q(district__icontains=term)
                | Q(description__icontains=term)
                | Q(promo_headline__icontains=term)
                | Q(promo_offer__icontains=term)
            )

        matched = qs.filter(query_filter).distinct()
        return matched if matched.exists() else qs

    def _business_target_url(self, business) -> str:
        if business.promo_url:
            return business.promo_url

        number = (business.whatsapp or business.phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if number:
            if not number.startswith("237"):
                number = f"237{number}"
            text = urllib.parse.quote(f"Bonjour {business.name}, je viens de E-Shelle AI.")
            return f"https://wa.me/{number}?text={text}"

        query = urllib.parse.quote(f"Je veux contacter {business.name}")
        return f"/chat/?q={query}"

    def _business_subtitle(self, business) -> str:
        location = " - ".join([part for part in [business.city, business.district] if part])
        module = business.get_module_display()
        return f"{module} - {location}" if location else module

    def _merge_results(self, *groups: list) -> list:
        merged = []
        seen = set()
        for group in groups:
            for item in group:
                key = (item.get("title"), item.get("primary_url") or item.get("url"))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged[:8]

    def _search_terms(self, query: str) -> list:
        from chat import services as legacy

        terms = legacy._search_terms(query)
        return [term for term in terms if term not in legacy._INTENT_WORDS]

    def _shorten(self, value: str, limit: int) -> str:
        value = (value or "").strip()
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "..."

    def _apply_text_filter(self, qs, query: str, *fields: str):
        terms = self._search_terms(query)
        if not terms:
            return qs

        query_filter = Q()
        for term in terms:
            for field in fields:
                query_filter |= Q(**{f"{field}__icontains": term})

        matched = qs.filter(query_filter).distinct()
        return matched if matched.exists() else qs

    def _join_text(self, *values: str) -> str:
        return " - ".join(str(value).strip() for value in values if value)

    def _money_text(self, value) -> str:
        try:
            amount = int(value)
        except (TypeError, ValueError):
            return ""
        if amount <= 0:
            return "Gratuit"
        return f"{amount:,} FCFA".replace(",", " ")


def log_central_agent_query(user_message: str, route: dict, user=None, session_key: str = "") -> None:
    """Enregistre les recherches pour l'admin IA et la strategie commerciale."""
    try:
        from e_shelle_ai.models import CentralAgentQueryLog

        results = route.get("results") or []
        premium_results_count = sum(
            1
            for item in results
            if str(item.get("badge", "")).lower() in {"premium", "business", "en vedette"}
        )
        CentralAgentQueryLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            session_key=session_key or "",
            query=user_message,
            module=route.get("module", "general"),
            response=route.get("message", ""),
            results_count=len(results),
            premium_results_count=premium_results_count,
            had_results=bool(results),
        )
    except Exception as exc:
        logger.debug("Central agent query log unavailable: %s", exc)


def route_message(user_message: str, conversation_history: list | None = None, user=None) -> dict:
    """API pratique pour appeler l'agent central."""

    return CentralAgentService().route_message(user_message, conversation_history, user=user)
