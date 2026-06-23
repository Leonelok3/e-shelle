from .base import BaseAgent
from .local_llm import OllamaClient, extract_json


class ImagePromptAgent(BaseAgent):
    name = 'ImagePromptAgent'

    def run(self, scenes: list[dict]) -> list[dict]:
        self.progress('Création des prompts visuels pour Stable Diffusion', 35)
        system = 'Tu es un prompt engineer Stable Diffusion. Tu réponds uniquement en JSON valide.'
        prompt = f"""
Transforme ces scènes en prompts d'images Stable Diffusion.
Réponds uniquement avec un tableau JSON. Chaque élément doit contenir :
- order
- image_prompt : prompt en anglais, riche, cinématographique, 16:9, photorealistic
- negative_prompt : éléments à éviter

SCÈNES :
{scenes}
"""
        raw = OllamaClient().generate(prompt=prompt, system=system, temperature=0.5)
        try:
            prompts = extract_json(raw)
            by_order = {int(p.get('order')): p for p in prompts}
            for scene in scenes:
                item = by_order.get(int(scene['order']), {})
                scene['image_prompt'] = item.get('image_prompt') or self._fallback_prompt(scene)
                scene['negative_prompt'] = item.get('negative_prompt') or 'blurry, low quality, watermark, text, logo, distorted hands'
            return scenes
        except Exception:
            for scene in scenes:
                scene['image_prompt'] = self._fallback_prompt(scene)
                scene['negative_prompt'] = 'blurry, low quality, watermark, text, logo, distorted hands'
            return scenes

    def _fallback_prompt(self, scene: dict) -> str:
        return (
            f"Cinematic photorealistic 16:9 scene, {scene.get('description', '')}, "
            'natural light, emotional atmosphere, detailed environment, high quality, sharp focus'
        )
