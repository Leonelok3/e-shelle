from pathlib import Path
from django.core.files import File
from django.db import transaction

from services.ai_copywriter import AICopywriter
from services.music_generator import MusicGenerator
from services.music_selector import MusicSelector
from agents.voice_agent import VoiceAgent
from agents.subtitle_agent import SubtitleAgent
from agents.video_agent import VideoAgent

from stories.models import StoryProject
from scenes.models import Scene
from images.models import GeneratedImage
from voices.models import VoiceOver
from videos.models import VideoRender
from businesses.models import BusinessPhoto
from ads.models import AdProject


class AdOrchestrator:
    """Create a StoryProject from an AdProject (Business + uploaded photos) and run the video pipeline."""

    def __init__(self, ad_project: AdProject, progress_callback=None):
        self.ad = ad_project
        self.progress_callback = progress_callback
        self.copywriter = AICopywriter()
        self.music_gen = MusicGenerator()
        self.music_sel = MusicSelector()

    def _progress(self, step: str, value: int) -> None:
        if self.progress_callback:
            self.progress_callback(step, value)

    @transaction.atomic
    def run(self) -> AdProject:
        # 1) generate marketing angle and script
        business = self.ad.business
        angle = self.copywriter.generate_angle(business.name, business.sector, business.city)
        script = self.copywriter.generate_script(angle, duration_seconds=self.ad.duration_seconds)

        # create a StoryProject wrapper to reuse existing pipeline
        story = StoryProject.objects.create(prompt=f'Ad for {business.name}', title=angle, story_text=script)

        # map BusinessPhoto to scenes
        photos = list(business.photos.all()[:10])
        if not photos:
            raise ValueError('No photos uploaded for this business')

        # split script into sentences and allocate to photos
        sentences = [s.strip() for s in script.replace('\n', ' ').split('.') if s.strip()]
        per_photo = max(1, len(sentences) // len(photos))

        story.scenes.all().delete()
        for idx, photo in enumerate(photos, start=1):
            text = ' '.join(sentences[(idx - 1) * per_photo: (idx) * per_photo]) or business.description or business.name
            Scene.objects.create(
                project=story,
                order=idx,
                title=f'Scène {idx}',
                description=photo.image.name,
                narration=text,
                image_prompt='',
                duration_seconds=6.0,
            )

        # attach the uploaded photos as GeneratedImage for each scene
        for scene in story.scenes.all():
            bp = photos[scene.order - 1]
            # copy file into GeneratedImage
            with bp.image.open('rb') as handle:
                GeneratedImage.objects.update_or_create(
                    scene=scene,
                    defaults={'prompt': scene.description, 'image': File(handle, name=Path(bp.image.name).name)},
                )

        # generate voice, subtitles
        voice_agent = VoiceAgent(self._progress)
        subtitle_agent = SubtitleAgent(self._progress)

        for scene in story.scenes.all():
            audio_path = voice_agent.run(scene, scene.narration)
            with audio_path.open('rb') as handle:
                VoiceOver.objects.update_or_create(scene=scene, defaults={'text': scene.narration, 'audio': File(handle, name=Path(audio_path).name)})
            subtitle_agent.run(scene, scene.narration, scene.duration_seconds)

        # pick or generate music
        try:
            music_path = self.music_sel.pick()
        except FileNotFoundError:
            music_path = Path('media/generated/music') / f'ad_music_{self.ad.pk}.wav'
            self.music_gen.generate(music_path, duration=self.ad.duration_seconds or 30)

        # create render and call existing VideoAgent (uses LocalVideoService)
        render = VideoRender.objects.create(project=story)
        video_path = VideoAgent(self._progress).run(story)
        with video_path.open('rb') as handle:
            render.video.save(video_path.name, File(handle), save=True)
            handle.seek(0)
            self.ad.final_video.save(video_path.name, File(handle), save=False)

        self.ad.status = 'done'
        self.ad.save(update_fields=['status', 'updated_at'])
        render.status = VideoRender.Status.DONE
        render.save(update_fields=['status'])
        return self.ad
