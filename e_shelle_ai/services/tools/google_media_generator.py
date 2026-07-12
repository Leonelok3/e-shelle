import logging
import base64
import os
import uuid
import json
import requests
from django.conf import settings
from e_shelle_ai.services.tools.image_generator import enhance_image_prompt
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

def get_vertex_client() -> tuple[genai.Client | None, str | None]:
    """
    Initialise le client Google GenAI avec Vertex AI si configuré.
    Retourne (client, error_message).
    """
    key_path = getattr(settings, "GCP_VERTEX_KEY_PATH", "")
    if not key_path or not os.path.exists(key_path):
        return None, "Fichier de clé de compte de service introuvable."
    
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        with open(key_path, 'r', encoding='utf-8') as f:
            key_data = json.load(f)
        project_id = key_data.get("project_id", "e-shelle")
        
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1"
        )
        return client, None
    except Exception as e:
        logger.exception("Exception initializing Vertex Client")
        return None, str(e)


def generate_google_image(prompt: str, context: str = "general") -> dict:
    """
    Génère une image avec Google Imagen 3 (via Vertex AI SDK si configuré, sinon API REST AI Studio).
    """
    enhanced_prompt = enhance_image_prompt(prompt, context)
    
    # Mappage de l'aspect ratio
    aspect_ratio = "1:1"
    if context == "banner":
        aspect_ratio = "16:9"
    elif context == "social_media":
        aspect_ratio = "9:16"

    # Essai d'initialisation de Vertex AI SDK
    client, _ = get_vertex_client()
    if client:
        try:
            model_id = "imagen-3.0-generate-002"
            response = client.models.generate_images(
                model=model_id,
                prompt=enhanced_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type="image/png"
                )
            )
            if not response.generated_images:
                return {"error": "Aucune image générée par Vertex AI."}
            
            # Récupération des octets de l'image
            image_bytes = response.generated_images[0].image.image_bytes
            
            # Sauvegarde locale sous media/ai_images/
            media_dir = os.path.join(settings.MEDIA_ROOT, "ai_images")
            os.makedirs(media_dir, exist_ok=True)
            filename = f"google_{uuid.uuid4().hex}.png"
            filepath = os.path.join(media_dir, filename)

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            local_url = f"{settings.MEDIA_URL}ai_images/{filename}"
            return {
                "image_url": local_url,
                "local_path": f"ai_images/{filename}",
                "media_url": local_url,
                "enhanced_prompt": enhanced_prompt,
                "error": None,
            }
        except Exception as e:
            logger.exception("Error generating image via Vertex AI SDK")
            return {"error": f"Erreur Vertex AI: {str(e)}"}
    
    # Fallback vers l'API REST AI Studio
    api_key = getattr(settings, "GOOGLE_API_KEY", "")
    if not api_key:
        return {"error": "Aucune clé API Google ou compte de service Vertex AI configuré."}
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "instances": [
            {"prompt": enhanced_prompt}
        ],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "outputMimeType": "image/png"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response_data = response.json()

        if response.status_code != 200:
            error_msg = response_data.get("error", {}).get("message", "Erreur inconnue")
            logger.error(f"Imagen 3 API error: {error_msg}")
            return {"error": error_msg}

        predictions = response_data.get("predictions", [])
        if not predictions:
            return {"error": "Aucune image générée."}

        encoded_image = predictions[0].get("bytesBase64Encoded")
        if not encoded_image:
            return {"error": "Données d'image manquantes dans la réponse."}

        media_dir = os.path.join(settings.MEDIA_ROOT, "ai_images")
        os.makedirs(media_dir, exist_ok=True)
        filename = f"google_{uuid.uuid4().hex}.png"
        filepath = os.path.join(media_dir, filename)

        image_bytes = base64.b64decode(encoded_image)
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        local_url = f"{settings.MEDIA_URL}ai_images/{filename}"
        return {
            "image_url": local_url,
            "local_path": f"ai_images/{filename}",
            "media_url": local_url,
            "enhanced_prompt": enhanced_prompt,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error calling Imagen 3 API: {e}")
        return {"error": str(e)}


def start_google_video(prompt: str, aspect_ratio: str = "16:9", resolution: str = "720p", image_b64: str = None, duration: int = 5) -> dict:
    """
    Démarre la génération d'une vidéo avec Google Veo (Vertex AI ou AI Studio).
    Retourne le nom de l'opération (ex: operations/12345 ou projects/.../operations/12345).
    """
    if aspect_ratio not in ["16:9", "9:16", "1:1"]:
        aspect_ratio = "16:9"

    if resolution not in ["720p", "1080p"]:
        resolution = "720p"

    # Veo reference_to_video ne supporte QUE 8 secondes
    if image_b64:
        duration = 8

    # Essai d'authentification avec Vertex AI SDK
    client, _ = get_vertex_client()
    if client:
        try:
            model = getattr(settings, "GOOGLE_VIDEO_MODEL", "veo-2.0-generate-001")
            
            config_params = {
                "aspect_ratio": aspect_ratio,
                "duration_seconds": duration
            }
            if image_b64:
                try:
                    import base64
                    image_bytes = base64.b64decode(image_b64)
                    config_params["reference_images"] = [
                        types.VideoGenerationReferenceImage(
                            image=types.Image(imageBytes=image_bytes, mimeType="image/png"),
                            referenceType="ASSET"
                        )
                    ]
                except Exception as ex_img:
                    logger.warning(f"Error parsing reference image for Vertex: {ex_img}")

            logger.info(f"Starting Vertex AI video generation with model {model}...")
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                config=types.GenerateVideosConfig(**config_params)
            )
            
            return {
                "operation_name": operation.name,
                "error": None
            }
        except Exception as e:
            logger.warning(f"Error starting video generation via Vertex AI SDK (model {model}): {e}. Trying fallback model...")
            try:
                fallback_model = "veo-3.1-fast-generate-preview"
                config_params = {
                    "aspect_ratio": aspect_ratio,
                    "duration_seconds": duration
                }
                if image_b64:
                    try:
                        import base64
                        image_bytes = base64.b64decode(image_b64)
                        config_params["reference_images"] = [
                            types.VideoGenerationReferenceImage(
                                image=types.Image(imageBytes=image_bytes, mimeType="image/png"),
                                referenceType="ASSET"
                            )
                        ]
                    except Exception as ex_img2:
                        logger.warning(f"Error parsing reference image for Vertex fallback: {ex_img2}")

                operation = client.models.generate_videos(
                    model=fallback_model,
                    prompt=prompt,
                    config=types.GenerateVideosConfig(**config_params)
                )
                return {
                    "operation_name": operation.name,
                    "error": None
                }
            except Exception as e2:
                logger.warning(f"Error during fallback video generation via Vertex AI SDK: {e2}. Falling back to AI Studio REST API...")

    # Fallback vers l'API REST AI Studio
    api_key = getattr(settings, "GOOGLE_API_KEY", "")
    if not api_key:
        return {"error": "Aucune clé API Google ou compte de service Vertex AI configuré."}
    
    model = getattr(settings, "GOOGLE_VIDEO_MODEL", "veo-2.0-generate-001")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning?key={api_key}"
    headers = {"Content-Type": "application/json"}

    instance = {"prompt": prompt}
    if image_b64:
        instance["referenceImages"] = [
            {
                "image": {
                    "bytesBase64Encoded": image_b64,
                    "mimeType": "image/png"
                },
                "referenceType": "ASSET"
            }
        ]

    payload = {
        "instances": [instance],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "resolution": resolution,
            "durationSeconds": duration
        }
    }

    try:
        logger.info(f"Starting AI Studio REST video generation with model {model}...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response_data = response.json()

        if response.status_code != 200:
            error_msg = response_data.get("error", {}).get("message", "Erreur inconnue")
            logger.error(f"Veo API error: {error_msg}")

            if "not found" in error_msg.lower() or "404" in error_msg or "model" in error_msg.lower():
                fallback_model = "veo-3.1-fast-generate-preview"
                logger.info(f"Retrying video generation with fallback model: {fallback_model}")
                fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/{fallback_model}:predictLongRunning?key={api_key}"
                response = requests.post(fallback_url, headers=headers, json=payload, timeout=60)
                response_data = response.json()
                if response.status_code != 200:
                    error_msg = response_data.get("error", {}).get("message", "Erreur fallback inconnue")
                    return {"error": error_msg}
            else:
                return {"error": error_msg}

        operation_name = response_data.get("name")
        if not operation_name:
            return {"error": "Pas de nom d'opération retourné par l'API Google."}

        return {
            "operation_name": operation_name,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error starting Veo video generation via REST API: {e}")
        return {"error": str(e)}


def check_google_video_status(operation_name: str) -> dict:
    """
    Vérifie le statut d'une opération de génération de vidéo (via Vertex AI SDK ou REST AI Studio).
    Si terminée, télécharge le fichier vidéo et le sauvegarde localement.
    """
    is_vertex = operation_name.startswith("projects/")

    # Essai d'utilisation du Vertex AI SDK pour l'opération Vertex AI
    if is_vertex:
        client, _ = get_vertex_client()
        if client:
            try:
                op_obj = types.GenerateVideosOperation(name=operation_name)
                operation = client.operations.get(op_obj)
                
                if not operation.done:
                    return {"done": False}
                
                if operation.error:
                    return {"error": operation.error.message}
                
                # Succès ! Le résultat contient la vidéo
                response_content = operation.response
                if not response_content:
                    return {"error": "Réponse vide de l'opération."}
                
                generated_videos = getattr(response_content, "generated_videos", [])
                if not generated_videos:
                    return {"error": "Aucune vidéo générée trouvée."}
                
                video_bytes = generated_videos[0].video.video_bytes
                if not video_bytes:
                    return {"error": "Données vidéo vides dans le résultat."}
                
                # Téléchargement de la vidéo via le client genai
                media_dir = os.path.join(settings.MEDIA_ROOT, "ai_videos")
                os.makedirs(media_dir, exist_ok=True)
                filename = f"google_{uuid.uuid4().hex}.mp4"
                filepath = os.path.join(media_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(video_bytes)
                
                local_url = f"{settings.MEDIA_URL}ai_videos/{filename}"
                return {
                    "done": True,
                    "video_url": local_url,
                    "local_path": f"ai_videos/{filename}",
                    "error": None
                }
            except Exception as e:
                logger.exception("Error checking video operation status via Vertex AI SDK")
                return {"error": f"Erreur Vertex AI: {str(e)}"}

    # Fallback/Méthode REST classique pour AI Studio
    api_key = getattr(settings, "GOOGLE_API_KEY", "")
    if not api_key:
        return {"error": "Clé API Google non configurée."}
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}?key={api_key}"

    try:
        response = requests.get(url, timeout=30)
        response_data = response.json()

        if response.status_code != 200:
            error_msg = response_data.get("error", {}).get("message", "Erreur lors de la vérification de la vidéo.")
            return {"error": error_msg}

        done = response_data.get("done", False)
        if not done:
            return {"done": False}

        error = response_data.get("error")
        if error:
            return {"error": error.get("message", "Erreur lors de la génération de la vidéo.")}

        response_content = response_data.get("response", {})
        generated_videos = response_content.get("generatedVideos", [])
        if not generated_videos:
            return {"error": "Aucune vidéo générée trouvée."}

        video_uri = generated_videos[0].get("video", {}).get("uri")
        if not video_uri:
            return {"error": "URI de vidéo manquante dans le résultat."}

        download_url = video_uri
        if "key=" not in download_url:
            download_url += f"&key={api_key}" if "?" in download_url else f"?key={api_key}"

        video_response = requests.get(download_url, timeout=120)
        video_response.raise_for_status()

        media_dir = os.path.join(settings.MEDIA_ROOT, "ai_videos")
        os.makedirs(media_dir, exist_ok=True)
        filename = f"google_{uuid.uuid4().hex}.mp4"
        filepath = os.path.join(media_dir, filename)

        with open(filepath, "wb") as f:
            f.write(video_response.content)

        local_url = f"{settings.MEDIA_URL}ai_videos/{filename}"
        return {
            "done": True,
            "video_url": local_url,
            "local_path": f"ai_videos/{filename}",
            "error": None
        }

    except Exception as e:
        logger.error(f"Error checking video status/downloading: {e}")
        return {"error": str(e)}
