import os
import requests
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

class ElevenLabsService:
    """Service to handle voice cloning and TTS generation using ElevenLabs API."""

    def __init__(self) -> None:
        self.api_key = getattr(settings, "ELEVENLABS_API_KEY", "")
        self.base_url = "https://api.elevenlabs.io/v1"

    def clone_voice(self, name: str, sample_path: Path) -> str:
        """
        Envoie un fichier audio d'échantillon à ElevenLabs pour cloner la voix.
        Retourne le voice_id de la voix créée.
        En développement local sans clé d'API, retourne un ID simulé.
        """
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY non configurée. Simulation du clonage de voix en cours...")
            return f"mock_voice_elevenlabs_{os.urandom(4).hex()}"

        url = f"{self.base_url}/voices/add"
        headers = {
            "xi-api-key": self.api_key
        }
        
        try:
            logger.info(f"Appel ElevenLabs pour cloner la voix '{name}' avec le fichier {sample_path}")
            with open(sample_path, 'rb') as f:
                files = {
                    'files': (sample_path.name, f, 'audio/mpeg')
                }
                data = {
                    'name': name,
                    'description': 'Voix clonée via E-Shelle Video Story Studio.'
                }
                
                response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
                response.raise_for_status()
                
                res_data = response.json()
                voice_id = res_data.get("voice_id")
                logger.info(f"Voix clonée avec succès sur ElevenLabs. voice_id: {voice_id}")
                return voice_id
                
        except Exception as e:
            logger.exception("Erreur lors du clonage de voix sur ElevenLabs")
            # En cas d'erreur API, on fournit un ID de fallback simulé plutôt que de bloquer tout le processus
            fallback_id = f"mock_voice_elevenlabs_{os.urandom(4).hex()}"
            logger.warning(f"Utilisation d'une voix de simulation en raison de l'erreur: {fallback_id}")
            return fallback_id

    def generate_tts(self, text: str, voice_id: str, output_path: Path) -> Path:
        """
        Génère un fichier audio à partir de texte en utilisant la voix clonée (voice_id).
        En développement local ou si l'ID est simulé, génère avec gTTS.
        """
        # S'il s'agit d'une voix simulée ou si la clé de production n'est pas présente, utiliser gTTS localement
        if not self.api_key or (voice_id and voice_id.startswith("mock_voice_elevenlabs_")):
            logger.info(f"Voix simulée détectée ({voice_id}). Génération de l'audio via gTTS local en français...")
            return self._generate_mock_tts(text, output_path)

        url = f"{self.base_url}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            logger.info(f"Génération ElevenLabs TTS avec la voix {voice_id} pour un texte de longueur {len(text)}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.post(url, headers=headers, json=payload, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        
            logger.info(f"Fichier audio généré avec succès via ElevenLabs : {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Génération ElevenLabs TTS échouée : {e}. Tentative de repli vers gTTS...")
            return self._generate_mock_tts(text, output_path)

    def _generate_mock_tts(self, text: str, output_path: Path) -> Path:
        """Génère une voix de simulation de haute qualité en français avec gTTS."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from gtts import gTTS
            logger.info("Génération de l'audio simulé via gTTS...")
            tts = gTTS(text=text, lang='fr')
            tts.save(str(output_path))
            logger.info("Audio simulé généré avec succès.")
            return output_path
        except Exception as e:
            logger.error(f"Échec de gTTS : {e}. Génération d'un silence de secours.")
            from voices.services import LocalVoiceService
            service = LocalVoiceService()
            service._create_silent_wav(output_path, duration_seconds=max(5.0, len(text) * 0.1))
            return output_path
