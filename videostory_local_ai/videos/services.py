from pathlib import Path

from django.conf import settings
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip


class LocalVideoService:
    """Assemble les images et voix off en MP4 avec MoviePy et FFmpeg.

    Extended: support vertical formats (1080x1920) and a simple Ken Burns effect (zoom + pan).
    """

    def render_project(self, project, resolution=(1280, 720), ken_burns=True) -> Path:
        output_dir = settings.MEDIA_ROOT / 'generated' / 'videos'
        output_dir.mkdir(parents=True, exist_ok=True)
        w, h = resolution
        output_path = output_dir / f'video_finale_project_{project.pk}.mp4'

        clips = []
        for scene in project.scenes.select_related('generated_image', 'voice_over').all():
            image_path = scene.generated_image.image.path
            audio_path = scene.voice_over.audio.path
            audio_clip = AudioFileClip(audio_path)
            duration = max(audio_clip.duration, scene.duration_seconds)
            clip = self._image_to_clip(image_path, duration, (w, h), ken_burns=ken_burns)
            clip = clip.set_audio(audio_clip)
            clips.append(clip)

        if not clips:
            raise ValueError('Aucune scène disponible pour assembler la vidéo.')

        final_clip = concatenate_videoclips(clips, method='compose')
        final_clip.write_videofile(str(output_path), fps=24, codec='libx264', audio_codec='aac', preset='medium')
        final_clip.close()
        for clip in clips:
            clip.close()
        return output_path

    def _image_to_clip(self, image_path: str, duration: float, size: tuple[int, int], ken_burns: bool = True):
        """Create an ImageClip sized to `size` and apply a simple Ken Burns effect.

        The Ken Burns implemented here slowly scales the image and optionally pans left/right.
        """
        target_w, target_h = size
        img_clip = ImageClip(image_path).set_duration(duration)

        # scale to cover target
        iw, ih = img_clip.size
        scale = max(target_w / iw, target_h / ih)

        if ken_burns:
            # gradual zoom from scale to scale * 1.08
            def s(t):
                return scale * (1 + 0.08 * (t / max(duration, 1)))

            zoomed = img_clip.resize(s)

            # simple pan: move horizontally from left to right over the duration if image larger
            def pos(t):
                cur_w, cur_h = zoomed.size
                max_dx = max(0, cur_w - target_w)
                x = int(-max_dx * (t / max(duration, 1)))  # pan from left to right
                return (x, 'center')

            comp = CompositeVideoClip([zoomed.set_position(pos)], size=(target_w, target_h)).set_duration(duration)
            return comp

        # no ken burns: simply resize and center
        img_clip = img_clip.resize(scale)
        comp = CompositeVideoClip([img_clip.set_position(('center', 'center'))], size=(target_w, target_h)).set_duration(duration)
        return comp
