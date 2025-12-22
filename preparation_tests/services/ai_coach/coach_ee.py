from .base import BaseAICoach


class AICoachEE(BaseAICoach):
    section = "ee"

    @staticmethod
    def weaknesses(score):
        if score < 75:
            return [
                "Structure du texte faible",
                "Erreurs grammaticales",
                "Manque de connecteurs",
            ]
        return []

    @staticmethod
    def advice(score):
        return [
            "Utiliser un plan clair (introduction / développement / conclusion)",
            "Réviser accords et conjugaison",
            "Rédiger au moins un texte par jour",
        ]
