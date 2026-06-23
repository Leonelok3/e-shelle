import logging
import time
import uuid
from pathlib import Path
from django.core.files import File
from django.conf import settings

from stories.models import StoryProject
from videos.models import RenderJob
from services.openai_tts_service import OpenAITTSService
from services.vertex_avatar_generator import VertexAvatarGenerator
from .base import BaseAgent

logger = logging.getLogger(__name__)

class AvatarOrchestrator(BaseAgent):
    """Orchestrates the Talking Avatar generation pipeline: TTS -> Google Veo -> Audio/Video Merge."""

    name = 'AvatarOrchestrator'

    def __init__(self, project: StoryProject, progress_callback=None) -> None:
        if progress_callback is None:
            progress_callback = lambda msg, val: project.mark_progress(msg, val)
        super().__init__(progress_callback)
        self.project = project
        self.tts_service = OpenAITTSService()
        self.avatar_generator = VertexAvatarGenerator()

    def run(self) -> StoryProject:
        try:
            self.progress("Initialisation de la génération d'avatar", 5)
            
            # Check inputs
            if not self.project.script_text or not self.project.script_text.strip():
                raise ValueError("Script texte manquant pour le projet.")

            # Create job record if not exists
            job, _ = RenderJob.objects.get_or_create(
                project=self.project,
                job_type='avatar',
                defaults={'status': RenderJob.Status.RUNNING, 'progress': 5}
            )
            job.status = RenderJob.Status.RUNNING
            job.progress = 5
            job.log = "Workflow démarré"
            job.save()

            # Step 1: Generate TTS Audio
            if self.project.cloned_voice:
                self.progress("Génération de la voix off via ElevenLabs (Voix Clonée)", 15)
                from services.elevenlabs_service import ElevenLabsService
                eleven_service = ElevenLabsService()
                audio_dir = Path(settings.MEDIA_ROOT) / "generated" / "audio"
                audio_dir.mkdir(parents=True, exist_ok=True)
                audio_filename = f"avatar_voice_cloned_{self.project.pk}_{uuid.uuid4().hex}.mp3"
                audio_path = audio_dir / audio_filename
                eleven_service.generate_tts(self.project.script_text, self.project.cloned_voice.voice_id, audio_path)
            else:
                self.progress("Génération de la voix off de haute qualité via OpenAI TTS", 15)
                audio_dir = Path(settings.MEDIA_ROOT) / "generated" / "audio"
                audio_dir.mkdir(parents=True, exist_ok=True)
                audio_filename = f"avatar_voice_{self.project.pk}_{uuid.uuid4().hex}.mp3"
                audio_path = audio_dir / audio_filename
                self.tts_service.generate(self.project.script_text, audio_path)
            
            # Step 2: Get audio duration to specify video duration
            from moviepy.editor import AudioFileClip
            try:
                audio_clip = AudioFileClip(str(audio_path))
                audio_duration = audio_clip.duration
                audio_clip.close()
            except Exception as e:
                logger.warning(f"Failed to read audio duration: {e}. Defaulting to 5 seconds.")
                audio_duration = 5.0

            # Google Veo image_to_video supports max 8 seconds (durations: [5, 6, 7, 8]).
            # We request 8 seconds from Veo and loop it to 10 seconds in post-processing.
            video_duration = 8
            logger.info(f"Generated audio duration: {audio_duration}s. Requesting Veo video duration: {video_duration}s")

            # Step 3: Determine / Generate Presentation Image
            avatar_path = None
            if self.project.avatar_image:
                avatar_path = Path(self.project.avatar_image.path)
                aspect_ratio = "9:16"
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(avatar_path) as img:
                        w, h = img.size
                        aspect_ratio = "16:9" if w > h else "9:16"
                except Exception as e:
                    logger.warning(f"Could not read image dimensions: {e}. Defaulting to 9:16.")
            else:
                self.progress("Génération de l'image de présentation avec Google Imagen 3...", 35)
                job.progress = 35
                job.log = "Appel à Google Imagen 3 pour créer l'image..."
                job.save()
                
                # Determine background style
                bg_style = self.project.avatar_background
                if bg_style == 'auto':
                    try:
                        bg_style = self.avatar_generator.extract_environment(self.project.script_text)
                    except Exception as e:
                        logger.warning(f"Failed to auto-extract environment: {e}. Defaulting to 'office'.")
                        bg_style = "office"
                
                bg_desc = self.avatar_generator.get_background_prompt(bg_style)
                image_prompt = (
                    f"A high quality professional presentation screen, slide, or professional presenter scene "
                    f"showing a clean, modern visual representation for: {self.project.script_text[:120]}. "
                    f"Cinematic studio atmosphere, set in a {bg_desc}, 4k, photorealistic."
                )
                
                try:
                    generated_image_path = self.avatar_generator.generate_image_imagen(image_prompt, aspect_ratio="9:16")
                    avatar_path = generated_image_path
                    # Save generated image to project model
                    from django.core.files import File
                    with open(generated_image_path, 'rb') as img_f:
                        self.project.avatar_image.save(generated_image_path.name, File(img_f), save=True)
                except Exception as e:
                    logger.exception("Failed to generate image via Imagen 3")
                    raise RuntimeError(f"Échec de la génération d'image Imagen 3: {e}")

            # Step 4: Rapid Static Video Rendering (Create video from static image + audio)
            self.progress("Rendu de la vidéo statique de présentation...", 70)
            job.progress = 70
            job.log = "Création du montage vidéo statique..."
            job.save()
            
            output_dir = Path(settings.MEDIA_ROOT) / "generated" / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)
            final_filename = f"avatar_final_{self.project.pk}_{uuid.uuid4().hex}.mp4"
            final_path = output_dir / final_filename

            # Run compilation using moviepy
            from moviepy.editor import ImageClip, AudioFileClip
            
            image_clip = ImageClip(str(avatar_path)).set_duration(audio_duration)
            audio_clip = AudioFileClip(str(audio_path))
            video_clip = image_clip.set_audio(audio_clip)
            
            # Temporary audio path
            temp_audio = output_dir / f"temp_merge_{self.project.pk}_{uuid.uuid4().hex}.m4a"
            
            # Render video
            video_clip.write_videofile(
                str(final_path),
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=str(temp_audio),
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            image_clip.close()
            audio_clip.close()
            video_clip.close()

            # Step 5: Save the final video to the database
            with open(final_path, 'rb') as f:
                self.project.final_video.save(final_filename, File(f), save=False)
                
            self.project.status = StoryProject.Status.DONE
            self.project.progress = 100
            self.project.current_step = "Vidéo de présentation prête avec succès !"
            self.project.save(update_fields=['status', 'progress', 'current_step', 'final_video', 'updated_at'])

            job.status = RenderJob.Status.DONE
            job.progress = 100
            job.log = "Terminé avec succès !"
            job.save()

            # Clean up temp generated audio
            try:
                if audio_path.exists():
                    audio_path.unlink()
            except Exception as e:
                logger.warning(f"Error cleaning up temporary audio file: {e}")

            logger.info("Talking Avatar project completed successfully.")
            return self.project

        except Exception as e:
            logger.exception("Error in Talking Avatar workflow")
            error_msg = str(e)
            
            self.project.status = StoryProject.Status.FAILED
            self.project.error_message = error_msg
            self.project.current_step = "Erreur durant la génération de l'avatar"
            self.project.save(update_fields=['status', 'error_message', 'current_step', 'updated_at'])

            # Try to update job too
            try:
                job = RenderJob.objects.filter(project=self.project, job_type='avatar').first()
                if job:
                    job.status = RenderJob.Status.FAILED
                    job.log = f"Erreur: {error_msg}"
                    job.save()
            except Exception:
                pass
                
            raise

    def merge_audio_video(self, video_path: Path, audio_path: Path, output_path: Path) -> Path:
        """Merges audio track with the Google Veo generated video."""
        from moviepy.editor import VideoFileClip, AudioFileClip
        from moviepy.video.fx.all import loop
        
        video_clip = VideoFileClip(str(video_path))
        audio_clip = AudioFileClip(str(audio_path))
        
        audio_duration = audio_clip.duration
        video_duration = video_clip.duration
        
        logger.info(f"Merging audio ({audio_duration}s) and video ({video_duration}s)")
        
        # Target at least 10 seconds of output video, or match audio if audio is longer
        target_duration = max(10.0, audio_duration)
        logger.info(f"Targeting final video duration of {target_duration}s")
        
        if video_clip.duration < target_duration:
            video_clip = video_clip.fx(loop, duration=target_duration)
        else:
            video_clip = video_clip.subclip(0, target_duration)
            
        final_clip = video_clip.set_audio(audio_clip)
        
        # Write file with a unique temp audio file to avoid conflicts
        temp_audio = output_path.parent / f"temp_merge_{self.project.pk}_{uuid.uuid4().hex}.m4a"
        final_clip.write_videofile(
            str(output_path),
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=str(temp_audio),
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        video_clip.close()
        audio_clip.close()
        final_clip.close()
        return output_path
