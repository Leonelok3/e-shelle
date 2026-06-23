from pathlib import Path

from django.conf import settings

from .base import BaseAgent


class SubtitleAgent(BaseAgent):
    name = 'SubtitleAgent'

    def run(self, scene, text: str, duration_seconds: float) -> Path:
        self.progress(f'Création sous-titres scène {scene.order}', 72)
        folder = settings.MEDIA_ROOT / 'generated' / 'subtitles'
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / f'project_{scene.project_id}_scene_{scene.order}.srt'
        output.write_text(self._to_srt(text, duration_seconds), encoding='utf-8')
        return output

    def _to_srt(self, text: str, duration_seconds: float) -> str:
        end = self._format_time(duration_seconds)
        clean = ' '.join(text.split())
        return f'1\n00:00:00,000 --> {end}\n{clean}\n'

    def _format_time(self, seconds: float) -> str:
        milliseconds = int((seconds - int(seconds)) * 1000)
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h:02d}:{m:02d}:{s:02d},{milliseconds:03d}'
