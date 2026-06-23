from .base import BaseAgent
from .local_llm import OllamaClient


class StoryAgent(BaseAgent):
    name = 'StoryAgent'

    def run(self, user_prompt: str) -> dict:
        self.progress('Génération du scénario avec Ollama', 10)
        system = (
            'Tu es un scénariste francophone spécialisé en vidéos courtes émotionnelles. '
            'Tu produis un scénario clair, structuré et adapté à une narration vidéo.'
        )
        prompt = f"""
À partir du prompt utilisateur ci-dessous, écris un scénario original en français.
Le résultat doit contenir un titre, un synopsis, un arc narratif et une narration globale.
Le style doit être cinématographique, humain, respectueux et facile à découper en scènes.

Prompt utilisateur : {user_prompt}
"""
        text = OllamaClient().generate(prompt=prompt, system=system, temperature=0.8)
        title = self._guess_title(text, user_prompt)
        return {'title': title, 'story_text': text}

    def _guess_title(self, text: str, fallback: str) -> str:
        for line in text.splitlines():
            clean = line.strip(' #:-')
            if clean and len(clean) <= 120:
                return clean
        return fallback[:100]
