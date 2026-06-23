from pathlib import Path

from .base import BaseAgent
from videos.services import LocalVideoService


class VideoAgent(BaseAgent):
    name = 'VideoAgent'

    def run(self, project) -> Path:
        self.progress('Assemblage de la vidéo finale MP4', 88)
        service = LocalVideoService()
        return service.render_project(project)
