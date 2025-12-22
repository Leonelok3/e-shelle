class BaseAICoach:
    section = None  # "co" / "ce" / "ee" / "eo"

    @classmethod
    def analyze_attempt(cls, attempt):
        total = attempt.total_items or 1
        correct = attempt.raw_score or 0
        score = round((correct / total) * 100)

        return {
            "section": cls.section.upper(),
            "score": score,
            "level": cls.estimate_level(score),
            "strengths": cls.strengths(score),
            "weaknesses": cls.weaknesses(score),
            "advice": cls.advice(score),
        }

    @staticmethod
    def estimate_level(score):
        if score < 50:
            return "A2-"
        if score < 65:
            return "B1"
        if score < 80:
            return "B2"
        if score < 90:
            return "C1"
        return "C2"

    @staticmethod
    def strengths(score):
        return []

    @staticmethod
    def weaknesses(score):
        return []

    @staticmethod
    def advice(score):
        return []
