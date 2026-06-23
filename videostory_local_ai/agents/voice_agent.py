from pathlib import Path

from .base import BaseAgent
from voices.services import LocalVoiceService


class VoiceAgent(BaseAgent):
    name = 'VoiceAgent'

    def run(self, scene, text: str) -> Path:
        self.progress(f'Génération voix off scène {scene.order}', 62)
        service = LocalVoiceService()
        return service.generate_for_scene(scene=scene, text=text)
