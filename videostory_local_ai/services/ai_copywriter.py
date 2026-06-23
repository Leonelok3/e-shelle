from agents.local_llm import OllamaClient


class AICopywriter:
    """Generate marketing angle and short ad scripts."""

    def __init__(self, model=None):
        self.client = OllamaClient(model=model)

    def generate_angle(self, business_name: str, sector: str, city: str) -> str:
        prompt = (
            f"Donne un angle marketing court pour une entreprise nommée {business_name}"
            f" dans le secteur {sector} située à {city}. Une ligne courte, percutante."
        )
        return self.client.generate(prompt=prompt, system='')

    def generate_script(self, angle: str, duration_seconds: int = 30, language: str = 'fr') -> str:
        prompt = (
            f"Rédige un script publicitaire en {language} basé sur cet angle : {angle}."
            f" Durée cible : {duration_seconds} secondes. Format : 2-4 phrases pour la voix off."
        )
        return self.client.generate(prompt=prompt, system='')
