import base64
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

        try:
            from services.vertex_avatar_generator import VertexAvatarGenerator
            generator = VertexAvatarGenerator()
            # aspect ratio for video scenes is widescreen 16:9
            generated_path = generator.generate_image_imagen(prompt, aspect_ratio="16:9")
            
            import shutil
            shutil.copy(str(generated_path), str(output_path))
            return output_path
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Imagen 3 generation failed for scene: {e}. Falling back to placeholder.")
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
