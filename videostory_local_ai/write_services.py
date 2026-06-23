from pathlib import Path

ROOT = Path('/home/ubuntu/videostory_local_ai')

files = {
    'images/services.py': r'''import base64
import io
import time
import uuid
from pathlib import Path

import requests
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


class LocalImageService:
    """Génère une image localement via ComfyUI ou Stable Diffusion WebUI, avec fallback de développement."""

    def __init__(self) -> None:
        self.backend = settings.IMAGE_BACKEND.lower()

    def generate_for_scene(self, scene, prompt: str, negative_prompt: str = '') -> Path:
        output_dir = settings.MEDIA_ROOT / 'generated' / 'images'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'project_{scene.project_id}_scene_{scene.order}.png'

        if self.backend == 'sdwebui':
            try:
                return self._generate_with_sd_webui(prompt, negative_prompt, output_path)
            except Exception:
                return self._create_placeholder(scene, prompt, output_path)

        if self.backend == 'comfyui':
            try:
                return self._generate_with_comfyui(prompt, negative_prompt, output_path)
            except Exception:
                return self._create_placeholder(scene, prompt, output_path)

        return self._create_placeholder(scene, prompt, output_path)

    def _generate_with_sd_webui(self, prompt: str, negative_prompt: str, output_path: Path) -> Path:
        payload = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': 1280,
            'height': 720,
            'steps': 25,
            'cfg_scale': 7,
            'sampler_name': 'DPM++ 2M Karras',
        }
        response = requests.post(f'{settings.SD_WEBUI_BASE_URL.rstrip("/")}/sdapi/v1/txt2img', json=payload, timeout=600)
        response.raise_for_status()
        image_data = response.json()['images'][0]
        image = Image.open(io.BytesIO(base64.b64decode(image_data.split(',', 1)[-1])))
        image.save(output_path)
        return output_path

    def _generate_with_comfyui(self, prompt: str, negative_prompt: str, output_path: Path) -> Path:
        workflow = self._basic_comfyui_workflow(prompt, negative_prompt)
        base_url = settings.COMFYUI_BASE_URL.rstrip('/')
        client_id = str(uuid.uuid4())
        response = requests.post(f'{base_url}/prompt', json={'prompt': workflow, 'client_id': client_id}, timeout=60)
        response.raise_for_status()
        prompt_id = response.json()['prompt_id']

        for _ in range(180):
            history = requests.get(f'{base_url}/history/{prompt_id}', timeout=30).json()
            if prompt_id in history:
                outputs = history[prompt_id].get('outputs', {})
                for node_output in outputs.values():
                    for image_info in node_output.get('images', []):
                        params = {
                            'filename': image_info['filename'],
                            'subfolder': image_info.get('subfolder', ''),
                            'type': image_info.get('type', 'output'),
                        }
                        image_response = requests.get(f'{base_url}/view', params=params, timeout=120)
                        image_response.raise_for_status()
                        output_path.write_bytes(image_response.content)
                        return output_path
            time.sleep(1)
        raise TimeoutError('ComfyUI n’a pas retourné d’image dans le délai prévu.')

    def _basic_comfyui_workflow(self, prompt: str, negative_prompt: str) -> dict:
        return {
            '3': {'class_type': 'KSampler', 'inputs': {'seed': 42, 'steps': 25, 'cfg': 7, 'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1, 'model': ['4', 0], 'positive': ['6', 0], 'negative': ['7', 0], 'latent_image': ['5', 0]}},
            '4': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'v1-5-pruned-emaonly.ckpt'}},
            '5': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1280, 'height': 720, 'batch_size': 1}},
            '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['4', 1]}},
            '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative_prompt or 'low quality, blurry, text, watermark', 'clip': ['4', 1]}},
            '8': {'class_type': 'VAEDecode', 'inputs': {'samples': ['3', 0], 'vae': ['4', 2]}},
            '9': {'class_type': 'SaveImage', 'inputs': {'filename_prefix': 'videostory', 'images': ['8', 0]}},
        }

    def _create_placeholder(self, scene, prompt: str, output_path: Path) -> Path:
        image = Image.new('RGB', (1280, 720), color=(18, 24, 38))
        draw = ImageDraw.Draw(image)
        title = f'Scène {scene.order}: {scene.title}'
        text = self._wrap(prompt, 80)[:900]
        draw.rectangle((0, 0, 1280, 720), outline=(80, 120, 180), width=10)
        draw.text((60, 70), title, fill=(255, 255, 255))
        draw.text((60, 140), text, fill=(210, 220, 235))
        image.save(output_path)
        return output_path

    def _wrap(self, text: str, width: int) -> str:
        words = text.split()
        lines, line = [], []
        for word in words:
            line.append(word)
            if len(' '.join(line)) >= width:
                lines.append(' '.join(line))
                line = []
        if line:
            lines.append(' '.join(line))
        return '\n'.join(lines)
''',
    'voices/services.py': r'''import subprocess
import wave
from pathlib import Path

from django.conf import settings
from moviepy.editor import AudioFileClip


class LocalVoiceService:
    """Génère la voix off localement avec Coqui TTS ou Piper TTS."""

    def __init__(self) -> None:
        self.backend = settings.VOICE_BACKEND.lower()

    def generate_for_scene(self, scene, text: str) -> Path:
        output_dir = settings.MEDIA_ROOT / 'generated' / 'audio'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'project_{scene.project_id}_scene_{scene.order}.wav'

        try:
            if self.backend == 'piper':
                self._generate_with_piper(text, output_path)
            else:
                self._generate_with_coqui(text, output_path)
        except Exception:
            self._create_silent_wav(output_path, max(scene.duration_seconds, 2.0))

        try:
            clip = AudioFileClip(str(output_path))
            scene.duration_seconds = max(float(clip.duration), scene.duration_seconds)
            scene.save(update_fields=['duration_seconds'])
            clip.close()
        except Exception:
            pass
        return output_path

    def _generate_with_coqui(self, text: str, output_path: Path) -> None:
        from TTS.api import TTS

        tts = TTS(model_name=settings.COQUI_TTS_MODEL, progress_bar=False, gpu=False)
        tts.tts_to_file(text=text, file_path=str(output_path))

    def _generate_with_piper(self, text: str, output_path: Path) -> None:
        command = [settings.PIPER_EXE, '--model', settings.PIPER_MODEL, '--output_file', str(output_path)]
        subprocess.run(command, input=text, text=True, check=True, capture_output=True)

    def _create_silent_wav(self, output_path: Path, duration_seconds: float) -> None:
        sample_rate = 22050
        frames = int(sample_rate * duration_seconds)
        with wave.open(str(output_path), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b'\x00\x00' * frames)
''',
    'videos/services.py': r'''from pathlib import Path

from django.conf import settings
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips


class LocalVideoService:
    """Assemble les images et voix off en MP4 avec MoviePy et FFmpeg."""

    def render_project(self, project) -> Path:
        output_dir = settings.MEDIA_ROOT / 'generated' / 'videos'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f'video_finale_project_{project.pk}.mp4'

        clips = []
        for scene in project.scenes.select_related('generated_image', 'voice_over').all():
            image_path = scene.generated_image.image.path
            audio_path = scene.voice_over.audio.path
            audio_clip = AudioFileClip(audio_path)
            duration = max(audio_clip.duration, scene.duration_seconds)
            clip = ImageClip(image_path).set_duration(duration).resize((1280, 720)).set_audio(audio_clip)
            clip = clip.fadein(0.4).fadeout(0.4)
            clips.append(clip)

        if not clips:
            raise ValueError('Aucune scène disponible pour assembler la vidéo.')

        final_clip = concatenate_videoclips(clips, method='compose')
        final_clip.write_videofile(
            str(output_path),
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            threads=4,
        )
        final_clip.close()
        for clip in clips:
            clip.close()
        return output_path
''',
}

for relative_path, content in files.items():
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

print('Services écrits.')
