from .base import BaseAgent
from .local_llm import OllamaClient, extract_json


class SceneAgent(BaseAgent):
    name = 'SceneAgent'

    def run(self, story_text: str, target_scene_count: int = 6) -> list[dict]:
        self.progress('Découpage du scénario en scènes', 22)
        system = 'Tu es un assistant de découpage vidéo. Tu réponds uniquement en JSON valide.'
        prompt = f"""
Découpe le scénario suivant en {target_scene_count} scènes vidéo.
Réponds uniquement avec un tableau JSON. Chaque élément doit contenir :
- order : nombre entier à partir de 1
- title : titre court
- description : description visuelle précise
- narration : texte de voix off en français, 2 à 4 phrases
- duration_seconds : durée recommandée entre 5 et 9 secondes

SCÉNARIO :
{story_text}
"""
        raw = OllamaClient().generate(prompt=prompt, system=system, temperature=0.4)
        try:
            scenes = extract_json(raw)
            return self._normalize(scenes)
        except Exception:
            return self._fallback(story_text, target_scene_count)

    def _normalize(self, scenes: list[dict]) -> list[dict]:
        normalized = []
        for index, scene in enumerate(scenes, start=1):
            normalized.append({
                'order': int(scene.get('order') or index),
                'title': str(scene.get('title') or f'Scène {index}'),
                'description': str(scene.get('description') or ''),
                'narration': str(scene.get('narration') or scene.get('description') or ''),
                'duration_seconds': float(scene.get('duration_seconds') or 6.0),
            })
        return normalized

    def _fallback(self, story_text: str, target_scene_count: int) -> list[dict]:
        paragraphs = [p.strip() for p in story_text.split('\n') if len(p.strip()) > 40]
        if not paragraphs:
            paragraphs = [story_text]
        selected = paragraphs[:target_scene_count]
        return [
            {
                'order': i,
                'title': f'Scène {i}',
                'description': paragraph[:350],
                'narration': paragraph,
                'duration_seconds': 6.0,
            }
            for i, paragraph in enumerate(selected, start=1)
        ]
