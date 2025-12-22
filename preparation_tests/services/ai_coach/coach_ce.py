from .base import BaseAICoach


class AICoachCE(BaseAICoach):
    section = "ce"

    @staticmethod
    def strengths(score):
        if score >= 70:
            return ["Bonne compréhension textuelle"]
        return []

    @staticmethod
    def weaknesses(score):
        if score < 70:
            return [
                "Lecture trop lente",
                "Difficulté avec les inférences",
            ]
        return []

    @staticmethod
    def advice(score):
        return [
            "Lire sans dictionnaire",
            "Identifier les connecteurs logiques",
            "Lire la presse francophone",
        ]
