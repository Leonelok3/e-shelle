from .base import BaseAICoach


class AICoachEO(BaseAICoach):
    section = "eo"

    @staticmethod
    def weaknesses(score):
        if score < 75:
            return [
                "Manque de fluidité",
                "Prononciation hésitante",
            ]
        return []

    @staticmethod
    def advice(score):
        return [
            "Parler 10 minutes par jour à voix haute",
            "S’enregistrer et s’écouter",
            "Travailler l’argumentation",
        ]
