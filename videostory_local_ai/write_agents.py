from pathlib import Path

ROOT = Path('/home/ubuntu/videostory_local_ai')

files = {
    'agents/base.py': r'''from dataclasses import dataclass
from typing import Any, Callable, Optional

ProgressCallback = Optional[Callable[[str, int], None]]


@dataclass
class AgentResult:
    ok: bool
    data: Any = None
    error: str = ''


class BaseAgent:
    """Classe mère minimaliste pour standardiser les agents locaux."""

    name = 'BaseAgent'

    def __init__(self, progress_callback: ProgressCallback = None) -> None:
        self.progress_callback = progress_callback

    def progress(self, message: str, value: int) -> None:
        if self.progress_callback:
            self.progress_callback(message, value)
''',
    'agents/local_llm.py': r'''import json
import re
from typing import Any

import requests
from django.conf import settings


class OllamaClient:
    """Client HTTP simple pour Ollama, exécuté localement sur la machine Windows."""

    def __init__(self, model: str | None = None) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    def generate(self, prompt: str, system: str = '', temperature: float = 0.7) -> str:
        payload = {
            'model': self.model,
            'prompt': prompt,
            'system': system,
            'stream': False,
            'options': {'temperature': temperature},
        }
        response = requests.post(f'{self.base_url}/api/generate', json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get('response', '').strip()


def extract_json(text: str) -> Any:
    """Extrait un objet ou tableau JSON d'une réponse LLM parfois entourée de texte."""
    cleaned = text.strip()
    cleaned = re.sub(r'^```(?:json)?', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'```$', '', cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'(\{.*\}|\[.*\])', cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))
''',
    'agents/story_agent.py': r'''from .base import BaseAgent
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
''',
    'agents/scene_agent.py': r'''from .base import BaseAgent
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
''',
    'agents/image_prompt_agent.py': r'''from .base import BaseAgent
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
''',
    'agents/image_agent.py': r'''from pathlib import Path

from .base import BaseAgent
from images.services import LocalImageService


class ImageAgent(BaseAgent):
    name = 'ImageAgent'

    def run(self, scene, prompt: str, negative_prompt: str = '') -> Path:
        self.progress(f'Génération image scène {scene.order}', 45)
        service = LocalImageService()
        return service.generate_for_scene(scene=scene, prompt=prompt, negative_prompt=negative_prompt)
''',
    'agents/voice_agent.py': r'''from pathlib import Path

from .base import BaseAgent
from voices.services import LocalVoiceService


class VoiceAgent(BaseAgent):
    name = 'VoiceAgent'

    def run(self, scene, text: str) -> Path:
        self.progress(f'Génération voix off scène {scene.order}', 62)
        service = LocalVoiceService()
        return service.generate_for_scene(scene=scene, text=text)
''',
    'agents/subtitle_agent.py': r'''from pathlib import Path

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
''',
    'agents/video_agent.py': r'''from pathlib import Path

from .base import BaseAgent
from videos.services import LocalVideoService


class VideoAgent(BaseAgent):
    name = 'VideoAgent'

    def run(self, project) -> Path:
        self.progress('Assemblage de la vidéo finale MP4', 88)
        service = LocalVideoService()
        return service.render_project(project)
''',
    'agents/orchestrator.py': r'''from django.core.files import File
from django.db import transaction

from images.models import GeneratedImage
from scenes.models import Scene
from stories.models import StoryProject
from voices.models import VoiceOver
from videos.models import VideoRender

from .image_agent import ImageAgent
from .image_prompt_agent import ImagePromptAgent
from .scene_agent import SceneAgent
from .story_agent import StoryAgent
from .subtitle_agent import SubtitleAgent
from .video_agent import VideoAgent
from .voice_agent import VoiceAgent


class VideoStoryOrchestrator:
    """Chef d'orchestre du workflow Prompt → Scénario → Scènes → Images → Voix → Sous-titres → MP4."""

    def __init__(self, project: StoryProject) -> None:
        self.project = project

    def _progress(self, step: str, value: int) -> None:
        self.project.mark_progress(step, value)

    def run(self) -> StoryProject:
        try:
            self.project.status = StoryProject.Status.RUNNING
            self.project.error_message = ''
            self.project.save(update_fields=['status', 'error_message', 'updated_at'])

            story_data = StoryAgent(self._progress).run(self.project.prompt)
            self.project.title = story_data['title']
            self.project.story_text = story_data['story_text']
            self.project.save(update_fields=['title', 'story_text', 'updated_at'])

            scene_data = SceneAgent(self._progress).run(self.project.story_text)
            scene_data = ImagePromptAgent(self._progress).run(scene_data)
            self._create_scene_rows(scene_data)

            image_agent = ImageAgent(self._progress)
            voice_agent = VoiceAgent(self._progress)
            subtitle_agent = SubtitleAgent(self._progress)

            for scene in self.project.scenes.all():
                image_path = image_agent.run(scene, scene.image_prompt)
                with image_path.open('rb') as handle:
                    GeneratedImage.objects.update_or_create(
                        scene=scene,
                        defaults={'prompt': scene.image_prompt, 'image': File(handle, name=image_path.name)},
                    )

                audio_path = voice_agent.run(scene, scene.narration)
                with audio_path.open('rb') as handle:
                    VoiceOver.objects.update_or_create(
                        scene=scene,
                        defaults={'text': scene.narration, 'audio': File(handle, name=audio_path.name)},
                    )

                subtitle_agent.run(scene, scene.narration, scene.duration_seconds)

            render = VideoRender.objects.create(project=self.project)
            video_path = VideoAgent(self._progress).run(self.project)
            with video_path.open('rb') as handle:
                render.video.save(video_path.name, File(handle), save=True)
                self.project.final_video.save(video_path.name, File(handle), save=False)
            self.project.status = StoryProject.Status.DONE
            self.project.progress = 100
            self.project.current_step = 'Vidéo finale prête'
            self.project.save()
            render.status = VideoRender.Status.DONE
            render.save(update_fields=['status'])
            return self.project
        except Exception as exc:
            self.project.status = StoryProject.Status.FAILED
            self.project.error_message = str(exc)
            self.project.current_step = 'Erreur pendant la génération'
            self.project.save(update_fields=['status', 'error_message', 'current_step', 'updated_at'])
            raise

    @transaction.atomic
    def _create_scene_rows(self, scenes: list[dict]) -> None:
        self.project.scenes.all().delete()
        for data in scenes:
            Scene.objects.create(
                project=self.project,
                order=data['order'],
                title=data['title'],
                description=data['description'],
                narration=data['narration'],
                image_prompt=data.get('image_prompt', ''),
                duration_seconds=data.get('duration_seconds', 6.0),
            )
''',
}

for relative_path, content in files.items():
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

print('Agents écrits.')
