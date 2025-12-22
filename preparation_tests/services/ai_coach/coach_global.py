from preparation_tests.services.ai_coach import get_ai_coach


class AICoachGlobal:
    """
    Coach IA GLOBAL – analyse multi-compétences
    """

    @classmethod
    def analyze_session(cls, attempts):
        """
        attempts = queryset Attempt (CO, CE, EE, EO)
        """
        section_reports = {}
        scores = []

        for attempt in attempts:
            section_code = attempt.section.code.lower()
            coach = get_ai_coach(section_code)

            if not coach:
                continue

            report = coach.analyze_attempt(attempt)
            section_reports[section_code] = report
            scores.append(report["score"])

        if not scores:
            return None

        avg_score = round(sum(scores) / len(scores))

        return {
            "avg_score": avg_score,
            "estimated_level": cls.estimate_global_level(avg_score),
            "sections": section_reports,
            "priorities": cls.detect_priorities(section_reports),
            "global_advice": cls.global_advice(avg_score),
        }

    @staticmethod
    def estimate_global_level(score):
        if score < 50:
            return "A2"
        if score < 65:
            return "B1"
        if score < 80:
            return "B2"
        if score < 90:
            return "C1"
        return "C2"

    @staticmethod
    def detect_priorities(section_reports):
        """
        Classe les sections de la plus faible à la plus forte
        """
        ordered = sorted(
            section_reports.items(),
            key=lambda x: x[1]["score"]
        )

        return [
            {
                "section": sec.upper(),
                "score": data["score"],
                "level": data["level"],
            }
            for sec, data in ordered
        ]

    @staticmethod
    def global_advice(score):
        if score < 65:
            return [
                "Renforcer les bases grammaticales",
                "Travailler la compréhension avant la production",
                "Suivre un plan d’étude structuré",
            ]
        if score < 80:
            return [
                "Accent sur les stratégies d’examen",
                "Simuler des examens complets",
                "Corriger systématiquement les erreurs",
            ]
        return [
            "Maintenir le niveau",
            "S’entraîner en conditions réelles",
            "Optimiser la gestion du temps",
        ]
