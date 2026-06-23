from django.core.files import File
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
        render = None
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
                handle.seek(0)
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
            if render:
                render.status = VideoRender.Status.FAILED
                render.log = str(exc)
                render.save(update_fields=['status', 'log'])
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
