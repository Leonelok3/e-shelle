"""
AdGen — Video Composer Service
Orchestre l'assemblage complet des scènes en FFmpeg.
"""
import os
import logging
import requests
import subprocess
from django.conf import settings
from adgen.views import generate_ad_music, get_premium_font
from .timeline_planner import TimelinePlanner
from .ffmpeg_filters import FFmpegFilterGenerator, escape_ffmpeg_path

logger = logging.getLogger(__name__)

class VideoComposer:
    """Orchestrateur de composition vidéo publicitaire."""

    def __init__(self, campaign, duration: float = 30.0, music_style: str = "piano", bg_config: dict = None):
        self.campaign = campaign
        self.duration = duration
        self.music_style = music_style
        self.bg_config = bg_config or {}
        
        # Dossier de stockage temporaire
        self.temp_dir = os.path.join(settings.MEDIA_ROOT, "adgen", "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Dossier d'export final
        self.output_dir = os.path.join(settings.MEDIA_ROOT, "adgen", "videos")
        os.makedirs(self.output_dir, exist_ok=True)

    def compose(self, silent_video_url: str) -> str:
        """
        Télécharge la vidéo muette, prépare l'audio, construit les filtres
        et exécute la composition en FFmpeg en bouclant le flux d'origine.
        """
        is_local = False
        silent_video_path = ""
        audio_path = ""

        try:
            logger.info(f"[VideoComposer] Début composition pour la campagne #{self.campaign.pk} ({self.duration}s)")

            # 1. Résolution de la vidéo muette source
            if silent_video_url.startswith(settings.MEDIA_URL):
                relative_path = silent_video_url[len(settings.MEDIA_URL):]
                if relative_path.startswith("/"):
                    relative_path = relative_path[1:]
                local_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                if os.path.exists(local_path):
                    silent_video_path = local_path
                    is_local = True
                    logger.info(f"[VideoComposer] Utilisation de la vidéo source locale : {silent_video_path}")

            if not is_local:
                logger.info(f"[VideoComposer] Téléchargement de la vidéo source depuis {silent_video_url}...")
                resp = requests.get(silent_video_url, timeout=30)
                resp.raise_for_status()
                silent_video_path = os.path.join(self.temp_dir, f"source_{self.campaign.pk}.mp4")
                with open(silent_video_path, "wb") as f:
                    f.write(resp.content)

            # 2. Synthèse de l'audio avec fondu de fin (fade-out)
            audio_path = os.path.join(self.temp_dir, f"audio_{self.campaign.pk}.wav")
            generate_ad_music(audio_path, duration=self.duration, style=self.music_style)
            logger.info(f"[VideoComposer] Musique synthétisée ({self.music_style}) générée à : {audio_path}")

            # 3. Planification de la timeline et des textes
            planner = TimelinePlanner(self.campaign, duration=int(self.duration))
            timeline = planner.get_timeline()
            content_data = planner.get_content_data()

            # 4. Construction des filtres FFmpeg
            font_path = get_premium_font()
            filter_gen = FFmpegFilterGenerator(self.temp_dir, self.campaign.pk, font_path)
            vf_chain = filter_gen.build_vf_chain(timeline, content_data, self.bg_config, self.duration)

            # 5. Fichier final de sortie
            output_filename = f"ad_video_{self.campaign.pk}.mp4"
            output_filepath = os.path.join(self.output_dir, output_filename)

            # 6. Exécution FFmpeg
            # -stream_loop -1 permet de boucler la vidéo source (qui fait 8s) indéfiniment.
            # -shortest avec -map 1:a force l'arrêt dès que l'audio (qui fait exactement la durée configurée) s'arrête.
            # -af afade applique un fondu audio en sortie de 1.5 seconde.
            cmd = [
                "ffmpeg",
                "-y",
                "-stream_loop", "-1",
                "-i", silent_video_path,
                "-i", audio_path,
                "-filter:v", vf_chain,
                "-filter:a", f"afade=t=out:st={self.duration - 1.5}:d=1.5",
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-t", str(self.duration),
                output_filepath
            ]

            logger.info(f"[VideoComposer] Commande FFmpeg : {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"[VideoComposer] Échec FFmpeg: {res.stderr}")
                raise RuntimeError(f"FFmpeg error: {res.stderr}")

            # 7. Nettoyage des fichiers temporaires du dossier temp
            self.cleanup_temp_files(content_data)
            if not is_local:
                try:
                    os.remove(silent_video_path)
                except Exception:
                    pass
            try:
                os.remove(audio_path)
            except Exception:
                pass

            media_url_base = settings.MEDIA_URL
            if not media_url_base.endswith("/"):
                media_url_base += "/"
            
            final_url = f"{media_url_base}adgen/videos/{output_filename}"
            logger.info(f"[VideoComposer] Vidéo finale de {self.duration}s disponible sur : {final_url}")
            return final_url

        except Exception as e:
            logger.error(f"[VideoComposer] Erreur de composition : {e}")
            # Nettoyage de sécurité en cas de crash
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                if not is_local and silent_video_path and os.path.exists(silent_video_path):
                    os.remove(silent_video_path)
            except Exception:
                pass
            raise

    def cleanup_temp_files(self, content_data: dict):
        """Supprime tous les fichiers texte temporaires écrits pour FFmpeg."""
        names = ["hook", "presentation", "benefits_title", "old_price", "price", "cta_title", "cta_contact"]
        for i in range(len(content_data.get("benefits", []))):
            names.append(f"benefit_{i}")
        names.append("extra")
        names.append("offer")

        for name in names:
            file_path = os.path.join(self.temp_dir, f"{name}_{self.campaign.pk}.txt")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
