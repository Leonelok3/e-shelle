"""
AdGen — Video Composer Service
Orchestre l'assemblage complet des scènes en FFmpeg.
"""
import os
import logging
import requests
import subprocess
import glob
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
        product_scene_paths = []

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

            # 3.5 Génération de l'image de fond 1080x1920 pour le format vertical
            bg_image_path = os.path.join(self.temp_dir, f"bg_1080_1920_{self.campaign.pk}.jpg")
            self.generate_background_image(bg_image_path)
            logger.info(f"[VideoComposer] Fond vertical de 1080x1920 généré à : {bg_image_path}")

            bg_image_rel = bg_image_path
            if os.path.isabs(bg_image_rel):
                try:
                    bg_image_rel = os.path.relpath(bg_image_rel, os.getcwd())
                except ValueError:
                    pass
            bg_image_rel = bg_image_rel.replace("\\", "/")

            # 3.6 Plans studio depuis les photos additionnelles du produit
            product_scene_paths = self.generate_product_scene_images()
            product_scene_rels = []
            for scene_path in product_scene_paths:
                scene_rel = scene_path
                if os.path.isabs(scene_rel):
                    try:
                        scene_rel = os.path.relpath(scene_rel, os.getcwd())
                    except ValueError:
                        pass
                product_scene_rels.append(scene_rel.replace("\\", "/"))

            # 4. Construction des filtres FFmpeg
            font_path = get_premium_font()
            filter_gen = FFmpegFilterGenerator(self.temp_dir, self.campaign.pk, font_path)
            vf_chain = filter_gen.build_vf_chain(
                timeline,
                content_data,
                self.bg_config,
                self.duration,
                product_scene_count=len(product_scene_rels),
            )

            # 5. Fichier final de sortie
            output_filename = f"ad_video_{self.campaign.pk}.mp4"
            output_filepath = os.path.join(self.output_dir, output_filename)

            # 6. Exécution FFmpeg
            # -stream_loop -1 permet de boucler la vidéo source (qui fait 8s) indéfiniment.
            # -filter_complex permet d'incruster la vidéo 16:9 au centre de l'image de fond 1080x1920.
            # -af afade applique un fondu audio en sortie de 1.5 seconde.
            cmd = [
                "ffmpeg",
                "-y",
                "-stream_loop", "-1",
                "-i", silent_video_path,
                "-i", audio_path,
                "-loop", "1",
                "-i", bg_image_rel,
            ]
            for scene_rel in product_scene_rels:
                cmd.extend(["-loop", "1", "-i", scene_rel])

            cmd.extend([
                "-filter_complex", vf_chain,
                "-filter:a", f"afade=t=out:st={self.duration - 1.5}:d=1.5",
                "-map", "[outv]",
                "-map", "1:a",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-t", str(self.duration),
                output_filepath
            ])

            logger.info(f"[VideoComposer] Commande FFmpeg : {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            
            # Nettoyage immédiat du fichier d'arrière-plan temporaire
            try:
                os.remove(bg_image_path)
            except Exception:
                pass
            for scene_path in product_scene_paths:
                try:
                    os.remove(scene_path)
                except Exception:
                    pass

            if res.returncode != 0:
                logger.error(f"[VideoComposer] Échec FFmpeg: {res.stderr}")
                raise RuntimeError(f"FFmpeg error: {res.stderr}")

            # Force les permissions de lecture pour s'assurer que Nginx/le serveur web puisse servir le fichier
            try:
                os.chmod(output_filepath, 0o644)
            except Exception:
                pass

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
                if 'bg_image_path' in locals() and os.path.exists(bg_image_path):
                    os.remove(bg_image_path)
            except Exception:
                pass
            for scene_path in product_scene_paths:
                try:
                    if os.path.exists(scene_path):
                        os.remove(scene_path)
                except Exception:
                    pass
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                if not is_local and silent_video_path and os.path.exists(silent_video_path):
                    os.remove(silent_video_path)
            except Exception:
                pass
            raise

    def compose_from_photos(self) -> str:
        """
        Compose une publicité complète directement depuis les photos produit.
        Mode rapide : pas d'attente Sora, uniquement motion design local + musique.
        """
        audio_path = ""
        bg_image_path = ""
        product_scene_paths = []

        try:
            logger.info(f"[VideoComposer] Début composition photo rapide pour la campagne #{self.campaign.pk} ({self.duration}s)")
            fast_width = int(getattr(settings, "ADGEN_VIDEO_FAST_WIDTH", 720))
            fast_height = int(getattr(settings, "ADGEN_VIDEO_FAST_HEIGHT", 1280))
            scene_height = int(fast_height * 0.72)

            audio_path = os.path.join(self.temp_dir, f"audio_{self.campaign.pk}.wav")
            generate_ad_music(audio_path, duration=self.duration, style=self.music_style)

            planner = TimelinePlanner(self.campaign, duration=int(self.duration))
            timeline = planner.get_timeline()
            content_data = planner.get_content_data()

            bg_image_path = os.path.join(self.temp_dir, f"bg_{fast_width}_{fast_height}_{self.campaign.pk}.jpg")
            self.generate_background_image(bg_image_path, width=fast_width, height=fast_height)
            bg_image_rel = self._ffmpeg_relative_path(bg_image_path)

            product_scene_paths = self.generate_product_scene_images(width=fast_width, height=scene_height)
            if not product_scene_paths:
                raise RuntimeError("Ajoutez au moins une photo du produit pour générer une vidéo rapide.")

            product_scene_rels = [self._ffmpeg_relative_path(scene_path) for scene_path in product_scene_paths]

            font_path = get_premium_font()
            filter_gen = FFmpegFilterGenerator(self.temp_dir, self.campaign.pk, font_path)
            vf_chain = filter_gen.build_fast_photo_chain(
                timeline,
                content_data,
                self.bg_config,
                self.duration,
                product_scene_count=len(product_scene_rels),
                width=fast_width,
                height=fast_height,
            )

            output_filename = f"ad_video_{self.campaign.pk}.mp4"
            output_filepath = os.path.join(self.output_dir, output_filename)

            cmd = [
                "ffmpeg",
                "-y",
                "-i", audio_path,
                "-loop", "1",
                "-i", bg_image_rel,
            ]
            for scene_rel in product_scene_rels:
                cmd.extend(["-loop", "1", "-i", scene_rel])

            cmd.extend([
                "-filter_complex", vf_chain,
                "-filter:a", f"afade=t=out:st={self.duration - 1.5}:d=1.5",
                "-map", "[outv]",
                "-map", "0:a",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "24",
                "-preset", "ultrafast",
                "-crf", "25",
                "-c:a", "aac",
                "-b:a", "96k",
                "-t", str(self.duration),
                "-shortest",
                "-movflags", "+faststart",
                output_filepath,
            ])

            logger.info(f"[VideoComposer] Commande FFmpeg rapide : {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"[VideoComposer] Échec FFmpeg rapide: {res.stderr}")
                raise RuntimeError("FFmpeg n'a pas pu finaliser la vidéo. Veuillez réessayer avec une autre photo produit.")

            try:
                os.chmod(output_filepath, 0o644)
            except Exception:
                pass

            media_url_base = settings.MEDIA_URL
            if not media_url_base.endswith("/"):
                media_url_base += "/"

            final_url = f"{media_url_base}adgen/videos/{output_filename}"
            logger.info(f"[VideoComposer] Vidéo photo rapide disponible sur : {final_url}")
            return final_url
        except Exception as e:
            logger.error(f"[VideoComposer] Erreur de composition photo rapide : {e}")
            raise
        finally:
            for file_path in [audio_path, bg_image_path, *product_scene_paths]:
                try:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
            try:
                self.cleanup_temp_files({})
            except Exception:
                pass

    def cleanup_temp_files(self, content_data: dict):
        """Supprime tous les fichiers texte temporaires écrits pour FFmpeg."""
        pattern = os.path.join(self.temp_dir, f"*_{self.campaign.pk}.txt")
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
            except Exception:
                pass

    def _ffmpeg_relative_path(self, path: str) -> str:
        if os.path.isabs(path):
            try:
                path = os.path.relpath(path, os.getcwd())
            except ValueError:
                pass
        return path.replace("\\", "/")

    def generate_background_image(self, output_path: str, width: int = 1080, height: int = 1920):
        """Génère l'image d'arrière-plan 1080x1920 (couleur, dégradé ou template)."""
        from PIL import Image, ImageDraw
        canvas_w = width
        canvas_h = height
        bg = Image.new("RGBA", (canvas_w, canvas_h))
        draw = ImageDraw.Draw(bg)
        
        bg_config = self.bg_config
        bg_type = "color"
        if bg_config:
            bg_type = bg_config.get("bg_type", "color")
            
        if bg_type == "color":
            color_hex = bg_config.get("bg_color", "#050910")
            hex_val = color_hex.lstrip('#')
            r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
            draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(r, g, b, 255))
            
        elif bg_type == "gradient":
            colors_hex = bg_config.get("bg_gradient", ["#050910", "#1e293b"])
            if len(colors_hex) < 2:
                colors_hex.append("#1e293b")
            hex1 = colors_hex[0].lstrip('#')
            hex2 = colors_hex[1].lstrip('#')
            r1, g1, b1 = int(hex1[0:2], 16), int(hex1[2:4], 16), int(hex1[4:6], 16)
            r2, g2, b2 = int(hex2[0:2], 16), int(hex2[2:4], 16), int(hex2[4:6], 16)
            
            direction = bg_config.get("bg_grad_dir", "horizontal")
            if direction == "vertical":
                grad = Image.new("RGB", (1, 2))
                grad.putpixel((0, 0), (r1, g1, b1))
                grad.putpixel((0, 1), (r2, g2, b2))
                grad_resized = grad.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)
                bg.paste(grad_resized, (0, 0))
            elif direction == "diagonal":
                grad = Image.new("RGB", (2, 2))
                grad.putpixel((0, 0), (r1, g1, b1))
                grad.putpixel((1, 0), (int((r1+r2)/2), int((g1+g2)/2), int((b1+b2)/2)))
                grad.putpixel((0, 1), (int((r1+r2)/2), int((g1+g2)/2), int((b1+b2)/2)))
                grad.putpixel((1, 1), (r2, g2, b2))
                grad_resized = grad.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)
                bg.paste(grad_resized, (0, 0))
            else: # horizontal
                grad = Image.new("RGB", (2, 1))
                grad.putpixel((0, 0), (r1, g1, b1))
                grad.putpixel((1, 0), (r2, g2, b2))
                grad_resized = grad.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)
                bg.paste(grad_resized, (0, 0))
                
        elif bg_type == "template":
            template = bg_config.get("bg_template", "dark")
            if template == "minimal":
                draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(245, 245, 247, 255))
            elif template == "luxury":
                draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(10, 10, 12, 255))
                draw.line([(0, 20), (canvas_w, 20)], fill=(212, 175, 55, 255), width=6)
                draw.line([(0, canvas_h-20), (canvas_w, canvas_h-20)], fill=(212, 175, 55, 255), width=6)
            elif template == "tech":
                draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(11, 19, 43, 255))
                draw.ellipse([(-100, -100), (400, 400)], outline=(0, 180, 216, 50), width=2)
                draw.ellipse([(canvas_w-400, canvas_h-400), (canvas_w+100, canvas_h+100)], outline=(0, 180, 216, 50), width=2)
            elif template == "modern":
                grad = Image.new("RGB", (2, 1))
                grad.putpixel((0, 0), (108, 63, 232))
                grad.putpixel((1, 0), (20, 120, 240))
                grad_resized = grad.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR).convert("RGBA")
                bg.paste(grad_resized, (0, 0))
            elif template == "fashion":
                grad = Image.new("RGB", (2, 1))
                grad.putpixel((0, 0), (245, 220, 215))
                grad.putpixel((1, 0), (230, 200, 190))
                grad_resized = grad.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR).convert("RGBA")
                bg.paste(grad_resized, (0, 0))
            elif template == "food":
                grad = Image.new("RGB", (2, 1))
                grad.putpixel((0, 0), (251, 146, 60))
                grad.putpixel((1, 0), (245, 85, 30))
                grad_resized = grad.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR).convert("RGBA")
                bg.paste(grad_resized, (0, 0))
            elif template == "automotive":
                draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(20, 24, 30, 255))
                for y in range(0, canvas_h, 80):
                    draw.line([(0, y), (canvas_w, y+240)], fill=(255, 255, 255, 6), width=4)
            else:
                draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(5, 9, 16, 255))
        else:
            draw.rectangle([(0, 0), (canvas_w, canvas_h)], fill=(5, 9, 16, 255))
            
        final_img = bg.convert("RGB")
        final_img.save(output_path, format="JPEG", quality=90)

    def generate_product_scene_images(self, width: int = 1080, height: int = 1440) -> list[str]:
        """Prépare les photos produit en plans verticaux premium 1080x1440."""
        from PIL import Image, ImageDraw, ImageFilter, ImageOps

        scene_paths = []
        photos = []
        if hasattr(self.campaign, "product_photos"):
            photos = self.campaign.product_photos()

        for index, image_field in enumerate(photos[:3]):
            try:
                if hasattr(image_field, "open"):
                    try:
                        image_field.open("rb")
                    except Exception:
                        pass
                if hasattr(image_field, "seek"):
                    try:
                        image_field.seek(0)
                    except Exception:
                        pass

                img = Image.open(image_field).convert("RGB")
                img = ImageOps.exif_transpose(img)

                canvas_w, canvas_h = width, height
                bg = ImageOps.fit(img, (canvas_w, canvas_h), method=Image.Resampling.LANCZOS)
                blur_radius = max(14, int(canvas_w * 0.024))
                bg = bg.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 70))
                bg = Image.alpha_composite(bg.convert("RGBA"), overlay)

                max_w, max_h = int(canvas_w * 0.86), int(canvas_h * 0.82)
                fg = img.copy()
                fg.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

                padding = max(14, int(canvas_w * 0.033))
                radius = max(20, int(canvas_w * 0.031))
                card_w, card_h = fg.width + (padding * 2), fg.height + (padding * 2)
                card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 0))
                draw = ImageDraw.Draw(card)
                draw.rounded_rectangle(
                    (0, 0, card_w - 1, card_h - 1),
                    radius=radius,
                    fill=(255, 255, 255, 245),
                    outline=(255, 255, 255, 200),
                    width=3,
                )
                card.alpha_composite(fg.convert("RGBA"), (padding, padding))

                x = (canvas_w - card_w) // 2
                y = (canvas_h - card_h) // 2
                shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                shadow_draw = ImageDraw.Draw(shadow)
                shadow_draw.rounded_rectangle(
                    (x + padding, y + padding + 6, x + card_w + padding, y + card_h + padding + 6),
                    radius=radius,
                    fill=(0, 0, 0, 95),
                )
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(12, int(canvas_w * 0.02))))
                bg = Image.alpha_composite(bg, shadow)
                bg.alpha_composite(card, (x, y))

                scene_path = os.path.join(self.temp_dir, f"product_scene_{index}_{self.campaign.pk}.jpg")
                bg.convert("RGB").save(scene_path, format="JPEG", quality=92)
                scene_paths.append(scene_path)
            except Exception as exc:
                logger.warning("[VideoComposer] Photo produit ignorée pendant la préparation du plan: %s", exc)

        return scene_paths
