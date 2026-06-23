from pathlib import Path

from .base import BaseAgent
from images.services import LocalImageService


class ImageAgent(BaseAgent):
    name = 'ImageAgent'

    def run(self, scene, prompt: str, negative_prompt: str = '') -> Path:
        self.progress(f'Génération image scène {scene.order}', 45)
        service = LocalImageService()
        return service.generate_for_scene(scene=scene, prompt=prompt, negative_prompt=negative_prompt)
