import os
import logging
import urllib.parse
import hashlib
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_audio(text: str, language: str = "de", output_dir: str = "audio/german") -> str:
    """
    Génère un fichier audio MP3 à partir d'un texte allemand (ou autre langue)
    en utilisant la bibliothèque gTTS qui gère automatiquement les longs textes sans troncature.
    Sauvegarde le fichier dans MEDIA_ROOT / output_dir et retourne le chemin relatif.
    """
    logger.info(f"[TTS] Génération audio ({language}) pour : {text[:60]}...")
    
    # Créer le répertoire de sortie s'il n'existe pas
    full_output_dir = os.path.join(settings.MEDIA_ROOT, output_dir)
    os.makedirs(full_output_dir, exist_ok=True)
    
    # Créer un nom de fichier unique basé sur le hash du texte
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    filename = f"tts_{text_hash}.mp3"
    relative_path = os.path.join(output_dir, filename).replace("\\", "/")
    full_path = os.path.join(full_output_dir, filename)
    
    # Si le fichier existe déjà, pas besoin de le recréer
    if os.path.exists(full_path):
        logger.info(f"[TTS] Fichier existant trouvé : {relative_path}")
        return relative_path
        
    try:
        from gtts import gTTS
        tts = gTTS(text=text.strip(), lang=language)
        tts.save(full_path)
        logger.info(f"[TTS] Succès de la génération gTTS : {relative_path}")
        return relative_path
    except Exception as e:
        logger.error(f"[TTS] Échec de la génération audio gTTS : {e}")
        raise
