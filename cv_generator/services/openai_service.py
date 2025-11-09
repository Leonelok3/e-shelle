# cv_generator/services/openai_service.py
"""
Service centralisé pour les appels OpenAI.
- Mode démo si OPENAI_API_KEY absent
- Gestion d'erreurs robuste et retours JSON sûrs
- Helpers pour parser les réponses numérotées et JSON "sale"
"""

from typing import Any, Dict, List, Optional
import json
import os
import logging
import re
import time

import openai
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Wrapper léger autour du client openai.ChatCompletion.
    Usage:
        svc = OpenAIService()
        summaries = svc.generate_career_summaries(...)
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, max_retries: int = 2):
        # Ordre de priorité : param -> settings -> env
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.model = model or getattr(settings, "OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4"))
        self.max_retries = max_retries

        if self.api_key:
            openai.api_key = self.api_key

    # ----------------------------
    # Bas niveau : appel OpenAI
    # ----------------------------
    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float = 0.7,
                     max_tokens: int = 800, request_timeout: int = 15) -> Optional[str]:
        """
        Appelle l'API ChatCompletion et retourne le texte (ou None en cas d'erreur).
        Si pas de clé, renvoie une réponse de démonstration.
        Retry simple pour erreurs transitoires.
        """
        if not self.api_key:
            logger.debug("OpenAI API key not configured — using demo responses.")
            return self._get_demo_response(system_prompt, user_prompt)

        attempt = 0
        while attempt <= self.max_retries:
            try:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_timeout=request_timeout,
                )
                text = None
                try:
                    text = response.choices[0].message.content.strip()
                except Exception:
                    try:
                        text = response.choices[0].text.strip()
                    except Exception:
                        text = str(response)
                logger.debug("OpenAI response length=%d", len(text) if text else 0)
                return text
            except openai.error.RateLimitError as e:
                logger.warning("OpenAI RateLimitError: %s — attempt %d/%d", e, attempt, self.max_retries)
                attempt += 1
                time.sleep(1 + attempt * 2)
            except openai.error.OpenAIError as e:
                logger.warning("OpenAI APIError: %s — attempt %d/%d", e, attempt, self.max_retries)
                attempt += 1
                time.sleep(1 + attempt * 2)
            except Exception as e:
                logger.exception("OpenAI unexpected error: %s", e)
                break

        # fallback demo si impossible d'appeler l'API
        return self._get_demo_response(system_prompt, user_prompt)

    # ----------------------------
    # Helpers pour parsing sécurisé
    # ----------------------------
    @staticmethod
    def _parse_numbered_list(text: str) -> List[str]:
        if not text:
            return []
        items = []
        lines = text.splitlines()
        current = None
        for ln in lines:
            ln = ln.strip()
            if re.match(r'^\d+\.', ln):
                if current:
                    items.append(current.strip())
                current = re.sub(r'^\d+\.\s*', '', ln)
            elif ln.startswith(('-', '•', '*')):
                items.append(ln.lstrip('-•* ').strip())
            elif current is not None:
                current += ' ' + ln
            else:
                if ln:
                    items.append(ln)
        if current:
            items.append(current.strip())
        return [i.strip() for i in items if i and i.strip()]

    @staticmethod
    def _safe_json_loads(text: str) -> Any:
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
            if match:
                candidate = match.group(1)
                try:
                    return json.loads(candidate)
                except Exception:
                    logger.debug("safe_json_loads: extraction failed for candidate JSON")
        return None

    # ----------------------------
    # Réponses de démonstration (fallback)
    # ----------------------------
    def _get_demo_response(self, system_prompt: str, user_prompt: str) -> str:
        sp = (system_prompt or "").lower()
        if "template" in sp and "recommand" in sp:
            return "Ce template est recommandé car il correspond aux attentes RH locales et facilite la lecture ATS."
        if "résumé" in sp or "summary" in sp:
            return (
                "1. Professionnel orienté résultats avec expertise technique et expérience en gestion de projets.\n"
                "2. Axé sur la livraison, amélioration continue et collaboration interfonctionnelle.\n"
                "3. Compétences en technologies clés du secteur + communication bilingue."
            )
        if "questions" in sp or "clarify" in sp or "quantifi" in sp:
            return "- Combien de projets avez-vous géré ?\n- Quelle était la taille de l'équipe ?\n- Quels résultats mesurables avez-vous obtenus ?"
        if "enhance" in sp or "transforme" in sp:
            return "✓ Pilotage réussi de 5 projets stratégiques, coordination d'une équipe de 10 personnes et respect strict du budget."
        if "skill" in sp or "compétences" in sp:
            return json.dumps({
                "categorized": {
                    "technical": ["Python", "Django"],
                    "languages": ["Français", "Anglais"],
                    "soft": ["Communication", "Leadership"]
                },
                "suggestions": ["Git", "Docker", "CI/CD"],
                "ats_keywords": ["Agile", "Scrum", "Project Management"]
            })
        if "analyse" in sp or "ats" in sp or "score" in sp:
            return json.dumps({
                "ats_score": 72,
                "breakdown": {
                    "ats_compatibility": 22,
                    "action_verbs": 14,
                    "quantification": 16,
                    "grammar": 12,
                    "local_standards": 8
                },
                "recommendations": [
                    "Ajoutez davantage de métriques chiffrées dans vos expériences.",
                    "Démarrez les bullet points par des verbes d'action.",
                    "Ajoutez mots-clés ATS spécifiques au poste."
                ]
            })
        return "Réponse de démonstration - configurez OPENAI_API_KEY pour obtenir des réponses réelles."

    # ----------------------------
    # Méthodes publiques
    # ----------------------------
    def explain_template_recommendation(self, template_name: str, industry: str, country: str) -> str:
        system_prompt = "Tu es un expert en recrutement pour le marché nord-américain. Explique en 1-2 phrases pourquoi un template est adapté."
        user_prompt = f"Template: {template_name}\nSecteur: {industry}\nPays: {country}\nExplique en 1-2 phrases."
        return self._call_openai(system_prompt, user_prompt, temperature=0.6) or ""

    def generate_career_summaries(self, job_title: str, years_experience: int, industry: str, country: str) -> List[str]:
        system_prompt = (
            f"Tu es un expert en rédaction de CV pour {country}. Produis EXACTEMENT 3 résumés numérotés 1,2,3: "
            "- 3-4 lignes max, verbes d'action, mots-clés du secteur."
        )
        user_prompt = f"Poste: {job_title}\nExpérience: {years_experience} ans\nSecteur: {industry}\nGénère 3 résumés."
        response = self._call_openai(system_prompt, user_prompt, temperature=0.8)
        items = self._parse_numbered_list(response or "")
        while len(items) < 3:
            items.append(f"Professionnel {job_title} avec {years_experience} ans d'expérience dans {industry}.")
        return items[:3]

    def generate_clarifying_questions(self, raw_description: str, job_title: str, industry: str) -> List[str]:
        system_prompt = f"Tu es coach carrière pour {industry}. Pose 3-4 questions courtes pour quantifier et clarifier."
        user_prompt = f"Poste: {job_title}\nDescription: {raw_description}\nQuestions:"
        response = self._call_openai(system_prompt, user_prompt, temperature=0.6)
        qs = self._parse_numbered_list(response or "")
        if len(qs) < 3:
            qs += [
                "Pouvez-vous quantifier vos résultats ?",
                "Quelle était la taille de l'équipe ?",
                "Quel impact mesurable avez-vous eu ?"
            ]
        return qs[:4]

    def enhance_experience_description(self, raw_description: str, job_title: str, industry: str,
                                       clarifications: Optional[Dict[str, str]] = None) -> str:
        system_prompt = (
            f"Tu es un expert en rédaction de CV pour {industry}. Transforme la description en une réalisation quantifiable "
            "commençant par un verbe d'action, 1-2 phrases max, optimize pour ATS, préfixe ✓."
        )
        clar_text = "\n".join([f"- {k}: {v}" for k, v in (clarifications or {}).items()])
        user_prompt = f"Poste: {job_title}\nDescription originale: {raw_description}\nClarifications:\n{clar_text}\nReformule:"
        return self._call_openai(system_prompt, user_prompt, temperature=0.7) or ""

    def optimize_skills(self, skills: List[str], job_title: str, industry: str, country: str) -> Dict[str, Any]:
        system_prompt = (
            f"Tu es un expert ATS pour {country} dans {industry}. Catégorise compétences en technical/languages/soft, "
            "suggère 5-8 compétences manquantes et liste mots-clés ATS. Retourne un JSON."
        )
        skills_text = ", ".join(skills) if isinstance(skills, (list, tuple)) else str(skills)
        user_prompt = f"Poste: {job_title}\nCompétences actuelles: {skills_text}\nRetourne JSON structuré."
        response = self._call_openai(system_prompt, user_prompt, temperature=0.5)
        parsed = self._safe_json_loads(response or "")
        if isinstance(parsed, dict):
            return parsed
        return {
            "categorized": {
                "technical": skills if isinstance(skills, list) else [skills],
                "languages": [],
                "soft": []
            },
            "suggestions": ["Git", "Docker", "CI/CD"],
            "ats_keywords": ["Agile", "Project Management"]
        }

    def analyze_cv_quality(self, cv_data: Dict[str, Any], industry: str, country: str) -> Dict[str, Any]:
        system_prompt = f"Tu es un système ATS expert pour {country}. Analyse le CV et retourne JSON avec ats_score, recommandations, breakdown."
        user_prompt = f"CV: {json.dumps(cv_data)}\nSecteur: {industry}\nRetourne JSON structuré."
        response = self._call_openai(system_prompt, user_prompt, temperature=0.5)
        parsed = self._safe_json_loads(response or "")
        if isinstance(parsed, dict):
            return parsed
        return {
            "ats_score": 50,
            "breakdown": {},
            "recommendations": ["Vérifiez le format et la clarté des expériences."]
        }
