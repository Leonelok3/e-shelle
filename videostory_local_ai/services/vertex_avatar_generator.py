import logging
import base64
import os
import uuid
import json
import requests
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

class VertexAvatarGenerator:
    """Service to animate a static avatar picture using Google Veo on Vertex AI."""

    def __init__(self) -> None:
        self.key_path = getattr(settings, "GCP_VERTEX_KEY_PATH", "")
        self.model = getattr(settings, "GOOGLE_VIDEO_MODEL", "veo-2.0-generate-001")

    def _get_client(self):
        """Initializes and returns the Google GenAI Client using Vertex AI."""
        if not self.key_path or not os.path.exists(self.key_path):
            raise ValueError(f"GCP Vertex key not found at path: {self.key_path}")
        
        try:
            from google import genai
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.key_path
            with open(self.key_path, 'r', encoding='utf-8') as f:
                key_data = json.load(f)
            project_id = key_data.get("project_id", "e-shelle")
            
            client = genai.Client(
                vertexai=True,
                project=project_id,
                location="us-central1"
            )
            return client
        except Exception as e:
            logger.exception("Failed to initialize Vertex AI client")
            raise

    def extract_environment(self, script_text: str) -> str:
        """Uses Gemini 1.5 Flash on Vertex AI to extract and enrich the background style from the script."""
        try:
            client = self._get_client()
            prompt = (
                "You are a professional video director. Analyze the following French script and extract the setting, location, or environment described. "
                "Then write a detailed, premium, cinematic studio background prompt in English (under 30 words) for a video generation AI like Google Veo. "
                "Focus on professional studio decor, lighting, and mood. Do not include character descriptions. "
                "Only return the English background description, nothing else.\n\n"
                f"Script: \"{script_text}\""
            )
            logger.info("Extracting environment description using Gemini 1.5 Flash on Vertex AI...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            desc = response.text.strip()
            # Clean up markdown code blocks if any
            if desc.startswith("```"):
                desc = desc.replace("```text", "").replace("```", "").strip()
            # Remove enclosing quotes if any
            if desc.startswith('"') and desc.endswith('"'):
                desc = desc[1:-1].strip()
            logger.info(f"Extracted background prompt: '{desc}'")
            return desc
        except Exception as e:
            logger.exception("Failed to extract environment from script using Gemini, falling back to default.")
            # Fallback based on keywords
            script_lower = script_text.lower()
            if "bureau" in script_lower:
                return "A high-end modern corporate office studio with professional warm desk lighting and elegant bookshelf decor."
            elif "studio" in script_lower:
                return "A state-of-the-art television news room broadcast studio with soft blurred screens in background."
            elif "cinema" in script_lower or "plateau" in script_lower:
                return "A cinematic film set with moody atmospheric lighting, background depth, and beautiful bokeh."
            return "A professional modern corporate office studio with warm lighting and elegant blurred background."

    def get_background_prompt(self, style: str) -> str:
        """Translates a background style into a detailed visual prompt."""
        styles = {
            "office": "high-end modern corporate office studio with professional warm interior design",
            "studio": "state-of-the-art television news room broadcast studio with soft blurred screens in background",
            "sober": "minimalist elegant solid dark blue background with premium studio spotlight lighting",
            "cinema": "cinematic film set with moody atmospheric lighting, background depth, and beautiful bokeh",
        }
        if style in styles:
            return styles[style]
        return style

    def start_animation(self, image_path: Path, background_style: str = "office", aspect_ratio: str = "9:16", duration: int = 5) -> str:
        """
        Starts the video generation operation with Google Veo.
        Returns the operation name.
        """
        client = self._get_client()
        from google.genai import types

        # Build detailed prompt for animating the avatar talking
        bg_desc = self.get_background_prompt(background_style)
        prompt = (
            f"A professional talking avatar speaker talking dynamically, "
            f"realistic head movements, natural blinking, subtle talking mouth animations, "
            f"natural body gestures, facing the camera, set in a {bg_desc}, "
            f"professional lighting, highly realistic, photo-like, 1080p"
        )

        # Load image bytes
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Resolve mime type
        mime_type = "image/jpeg"
        if image_path.suffix.lower() == ".png":
            mime_type = "image/png"

        models_to_try = [self.model]
        for fallback in ["veo-3.1-generate-001", "veo-3.1-fast-generate-001", "veo-2.0-generate-001", "veo-3.1-lite-generate-001"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_exception = None
        for model_name in models_to_try:
            logger.info(f"Attempting Vertex Veo video generation with model: {model_name}, aspect_ratio: {aspect_ratio}")
            try:
                operation = client.models.generate_videos(
                    model=model_name,
                    prompt=prompt,
                    image={"image_bytes": image_bytes, "mime_type": mime_type},
                    config=types.GenerateVideosConfig(
                        aspect_ratio=aspect_ratio,
                        duration_seconds=duration,
                    )
                )
                logger.info(f"Successfully started Veo generation operation using model {model_name}")
                return operation.name
            except Exception as e:
                logger.warning(f"Failed to generate video with model {model_name}: {e}. Trying next fallback...")
                last_exception = e

        raise RuntimeError(f"Vertex AI failed for all attempted models. Last error: {last_exception}")

    def check_status(self, operation_name: str) -> dict:
        """
        Checks the status of the long-running video generation operation.
        Returns a dict: {"done": bool, "video_path": Path | None, "error": str | None}
        """
        client = self._get_client()
        from google.genai import types

        try:
            op_obj = types.GenerateVideosOperation(name=operation_name)
            operation = client.operations.get(op_obj)

            if not operation.done:
                return {"done": False, "video_path": None, "error": None}

            if operation.error:
                error_data = operation.error
                error_msg = ""
                if isinstance(error_data, dict):
                    error_msg = error_data.get("message", str(error_data))
                else:
                    error_msg = getattr(error_data, "message", str(error_data))
                return {"done": True, "video_path": None, "error": error_msg}

            response_content = operation.response
            if not response_content:
                return {"done": True, "video_path": None, "error": "Empty response from Google Veo"}

            generated_videos = getattr(response_content, "generated_videos", [])
            if not generated_videos:
                return {"done": True, "video_path": None, "error": "No videos found in response"}

            video_bytes = generated_videos[0].video.video_bytes
            if not video_bytes:
                return {"done": True, "video_path": None, "error": "Empty video bytes returned"}

            # Save the video to media directory
            media_dir = Path(settings.MEDIA_ROOT) / "generated" / "videos"
            media_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"avatar_veo_{uuid.uuid4().hex}.mp4"
            filepath = media_dir / filename

            with open(filepath, "wb") as f:
                f.write(video_bytes)

            logger.info(f"Veo video downloaded successfully to: {filepath}")
            return {"done": True, "video_path": filepath, "error": None}

        except Exception as e:
            logger.exception("Error checking video generation status")
            return {"done": True, "video_path": None, "error": str(e)}

    def generate_image_imagen(self, prompt: str, aspect_ratio: str = "9:16") -> Path:
        """Generates a high definition image using Google Imagen 3 on Vertex AI."""
        try:
            client = self._get_client()
            from google.genai import types
            
            logger.info(f"Generating image with Google Imagen 3. Prompt: {prompt}, aspect_ratio: {aspect_ratio}")
            
            response = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type="image/png"
                )
            )
            if not response.generated_images:
                raise RuntimeError("Aucune image générée par Vertex AI.")
            
            image_bytes = response.generated_images[0].image.image_bytes
            
            # Save to media/generated/images/
            media_dir = Path(settings.MEDIA_ROOT) / "generated" / "images"
            media_dir.mkdir(parents=True, exist_ok=True)
            filename = f"imagen_{uuid.uuid4().hex}.png"
            filepath = media_dir / filename
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
                
            logger.info(f"Imagen 3 image saved successfully to {filepath}")
            return filepath
        except Exception as e:
            logger.exception("Error generating image via Imagen 3 SDK, trying REST API fallback...")
            # Fallback using requests and GOOGLE_API_KEY
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError(f"Vertex AI Imagen 3 failed and no GOOGLE_API_KEY or GEMINI_API_KEY found for REST fallback. Error: {e}")
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "instances": [
                    {"prompt": prompt}
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": aspect_ratio,
                    "outputMimeType": "image/png"
                }
            }
            
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            res_data = res.json()
            
            predictions = res_data.get("predictions", [])
            if not predictions:
                raise RuntimeError("No image generated by Google REST API.")
                
            encoded_image = predictions[0].get("bytesBase64Encoded")
            if not encoded_image:
                raise RuntimeError("Missing image bytes in REST response.")
                
            image_bytes = base64.b64decode(encoded_image)
            media_dir = Path(settings.MEDIA_ROOT) / "generated" / "images"
            media_dir.mkdir(parents=True, exist_ok=True)
            filename = f"imagen_{uuid.uuid4().hex}.png"
            filepath = media_dir / filename
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
                
            logger.info(f"Imagen 3 image generated via REST fallback successfully saved to {filepath}")
            return filepath

