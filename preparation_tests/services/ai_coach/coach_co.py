from .base import BaseAICoach


class AICoachCO(BaseAICoach):
    section = "co"

    @staticmethod
    def strengths(score):
        if score >= 75:
            return [
                "Bonne compréhension globale",
                "Bonne gestion du débit audio",
            ]
        return ["Compréhension partielle des idées principales"]

    @staticmethod
    def weaknesses(score):
        if score < 70:
            return [
                "Difficulté avec les accents",
                "Mots-clés mal identifiés",
                "Perte d’informations longues",
            ]
        return []

    @staticmethod
    def advice(score):
        if score < 70:
            return [
                "Écoute quotidienne de podcasts francophones",
                "Noter les mots-clés pendant l’écoute",
                "S’entraîner avec audio x1.25",
            ]
        return [
            "Simuler les conditions réelles d’examen",
            "Travailler les pièges synonymes",
        ]
