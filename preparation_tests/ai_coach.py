from __future__ import annotations

from typing import Dict, List


class AICoachCO:
    """
    Coach IA pour la Compréhension Orale du TEF.

    On se base sur :
    - le score brut (raw_score)
    - le nombre total de questions (total_items)
    pour calculer :
    - score_pct = pourcentage de réussite (0–100)
    - score_tef = score simulé TEF (0–360)
    - level = niveau estimé (B1/B2/C1/C2)
    - errors = petit résumé des erreurs
    - recommendations = conseils personnalisés
    """

    # ---- MAPPING SCORE -> NIVEAU CECR ----
    @staticmethod
    def level_from_pct(score_pct: int) -> str:
        """
        Mapping simple du pourcentage vers un niveau CECR.
        Tu pourras raffiner les seuils plus tard si tu veux.
        """
        if score_pct >= 85:
            return "C2"
        if score_pct >= 70:
            return "C1"
        if score_pct >= 55:
            return "B2"
        return "B1"

    @staticmethod
    def tef_score_from_pct(score_pct: int) -> int:
        """
        Convertit un pourcentage (0–100) en score TEF Listening (0–360)
        de façon linéaire : 0% → 0, 100% → 360.
        """
        if score_pct <= 0:
            return 0
        if score_pct >= 100:
            return 360
        return int(round(score_pct * 3.6))

    # ---- ANALYSE PRINCIPALE ----
    @classmethod
    def analyze_attempt(cls, attempt) -> Dict:
        """
        Prend un Attempt (section TEF CO) et renvoie un dictionnaire
        directement exploitable dans le template.
        """

        # Sécurité : si total_items n'est pas encore renseigné, on le calcule
        total_items = attempt.total_items or attempt.section.questions.count() or 0
        correct_raw = int(attempt.raw_score or 0)

        if total_items <= 0:
            score_pct = 0
        else:
            score_pct = int(round((correct_raw / total_items) * 100))

        score_tef = cls.tef_score_from_pct(score_pct)
        level = cls.level_from_pct(score_pct)

        # Petit résumé des erreurs (simple pour l’instant)
        wrong = max(total_items - correct_raw, 0)
        errors: Dict[str, int] = {}
        if wrong > 0:
            errors["questions ratées"] = wrong

        # Recommandations en fonction du niveau
        recommendations: List[str] = []

        if score_pct < 40:
            recommendations.append(
                "Commence par les leçons de base en CO : annonces publiques, situations simples."
            )
            recommendations.append(
                "Concentre-toi sur les mots-clés évidents (heures, dates, lieux, chiffres)."
            )
            recommendations.append(
                "Refais plusieurs fois les mêmes audios jusqu’à comprendre au moins l’idée générale."
            )
        elif score_pct < 60:
            recommendations.append(
                "Tu comprends l’essentiel mais tu perds des points sur les détails (heures, numéros, contraintes)."
            )
            recommendations.append(
                "Travaille les questions piégeuses : plusieurs informations vraies, une seule vraiment exacte."
            )
        elif score_pct < 80:
            recommendations.append(
                "Ton niveau est solide. Pour viser C1/C2, travaille la précision et les sous-entendus."
            )
            recommendations.append(
                "Refais les exercices en notant les mots qui t’ont fait hésiter et vérifie leur sens."
            )
        else:
            recommendations.append(
                "Excellent niveau ! Vise la régularité : reste au-dessus de 80–85 % sur toutes les séries."
            )
            recommendations.append(
                "Entraîne-toi avec des audios plus rapides (radio, podcasts) pour garder ton avance."
            )

        # Reco générique
        recommendations.append(
            "Utilise les cours CO d’E-SHELLE : choisis une leçon, lis la théorie, puis fais les exercices liés."
        )

        return {
            "score_pct": score_pct,
            "score_tef": score_tef,
            "level": level,
            "errors": errors,
            "recommendations": recommendations,
        }
