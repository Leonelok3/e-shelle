"""
AdGen — FFmpeg Filters Service
Génère la chaîne de filtres FFmpeg pour la composition et l'animation des scènes.
"""
import os
import logging

logger = logging.getLogger(__name__)

def escape_ffmpeg_path(path: str) -> str:
    """Échappe le chemin de fichier pour FFmpeg sur Windows."""
    return path.replace('\\', '/').replace(':', '\\:')

def wrap_text(text: str, max_chars: int = 20) -> str:
    """Sépare le texte par des sauts de ligne pour éviter qu'il ne déborde de l'écran."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 > max_chars:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + 1
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)

class FFmpegFilterGenerator:
    """Génère la chaîne complexe de filtres vidéo FFmpeg."""

    def __init__(self, temp_dir: str, campaign_id: int, font_path: str = ""):
        self.temp_dir = temp_dir
        self.campaign_id = campaign_id
        
        if font_path and os.path.exists(font_path):
            if os.path.isabs(font_path):
                try:
                    font_path = os.path.relpath(font_path, os.getcwd())
                except ValueError:
                    pass
            font_path = font_path.replace("\\", "/")
            self.font_opt = f":fontfile='{font_path}'"
        else:
            self.font_opt = ""

    def get_alpha_expr(self, start: float, end: float, fade_in: float = 0.5, fade_out: float = 0.5) -> str:
        """Retourne l'expression FFmpeg pour l'opacité (fadeIn/fadeOut)."""
        return (
            f"if(lt(t,{start}),0,"
            f"if(lt(t,{start}+{fade_in}),(t-{start})/{fade_in},"
            f"if(lt(t,{end}-{fade_out}),1,"
            f"if(lt(t,{end}),1-(t-({end}-{fade_out}))/{fade_out},0))))"
        )

    def write_temp_text(self, name: str, content: str) -> str:
        """Écrit un texte dans un fichier temporaire et retourne son chemin échappé pour FFmpeg."""
        file_path = os.path.join(self.temp_dir, f"{name}_{self.campaign_id}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        if os.path.isabs(file_path):
            try:
                file_path = os.path.relpath(file_path, os.getcwd())
            except ValueError:
                pass
        return file_path.replace("\\", "/")

    def build_vf_chain(self, timeline: dict, content_data: dict, bg_config: dict, duration: float) -> str:
        """
        Construit l'enchaînement complet des filtres vidéo :
        1. Recadrage vertical progressif + Floating (Ken Burns)
        2. Mise à l'échelle en 1080x1920 (pour un rendu de police ultra net)
        3. Filigrane de marque permanent
        4. Scénisation des incrustations (Hook, Présentation, Bénéfices, Prix, CTA) avec animations
        """
        # --- 1. Résolution du contraste ---
        from adgen.views import is_bg_light
        is_light = is_bg_light(bg_config)
        
        if is_light:
            text_color = "0x0f0723"        # Noir violet profond
            accent_color = "0xc2410c"      # Orange/Brique
            box_color = "white@0.85"        # Boîte blanche translucide
            contact_box = "0xdcfce7@0.9"   # Vert WhatsApp clair
            contact_text = "0x14532d"      # Vert WhatsApp foncé
        else:
            text_color = "white"
            accent_color = "0xffd91f"      # Jaune/Or vif
            box_color = "0x0f0723@0.75"    # Boîte violette foncée translucide
            contact_box = "0x14532d@0.85"  # Vert WhatsApp foncé
            contact_text = "white"

        filters = []

        # --- 2. Placement de la vidéo au centre du fond vertical 9:16 ---
        # Redimensionnement 16:9 à la largeur de 1080, puis superposition centrée sur le fond 1080x1920
        speed_ratio = duration / 8.0
        overlay_y = (1920 - 608) // 2  # 656
        crop_zoom = (
            f"[0:v]setpts={speed_ratio}*PTS,scale=1080:608[vid];"
            f"[2:v][vid]overlay=0:{overlay_y}"
        )
        filters.append(crop_zoom)

        # --- 3. Filigrane permanent ---
        watermark = f"drawtext=text='E-SHELLE.COM':x=w-tw-w*0.06:y=h*0.04{self.font_opt}:fontsize=32:fontcolor=white:alpha=0.35"
        filters.append(watermark)

        # --- 4. Scène : Hook ---
        if "hook" in timeline:
            start, end = timeline["hook"]
            hook_text = wrap_text(content_data["hook"].upper(), 18)
            hook_file = self.write_temp_text("hook", hook_text)
            
            # Animation slideDown + ease-out (quadratic) + fadeIn/fadeOut
            alpha = self.get_alpha_expr(start, end)
            y_expr = f"280 - 100 * pow(1 - clip((t - {start}) / 0.8, 0, 1), 2)"
            
            filters.append(
                f"drawtext=textfile='{hook_file}':x=(w-text_w)/2:y='{y_expr}':alpha='{alpha}'{self.font_opt}:"
                f"fontsize=64:fontcolor={text_color}:box=1:boxcolor={box_color}:boxborderw=20"
            )

        # --- 5. Scène : Présentation ---
        if "presentation" in timeline:
            start, end = timeline["presentation"]
            pres_text = wrap_text(content_data["presentation"], 20)
            pres_file = self.write_temp_text("presentation", pres_text)
            
            # Animation slideUp + ease-out + fadeIn/fadeOut
            alpha = self.get_alpha_expr(start, end)
            y_expr = f"600 + 150 * pow(1 - clip((t - {start}) / 0.8, 0, 1), 2)"
            
            filters.append(
                f"drawtext=textfile='{pres_file}':x=(w-text_w)/2:y='{y_expr}':alpha='{alpha}'{self.font_opt}:"
                f"fontsize=48:fontcolor={text_color}:box=1:boxcolor={box_color}:boxborderw=20"
            )

        # --- 6. Scène : Bénéfices (Apparition progressive stagger) ---
        if "benefits" in timeline:
            start, end = timeline["benefits"]
            
            # Titre des bénéfices
            title_file = self.write_temp_text("benefits_title", "POURQUOI CHOISIR ?")
            alpha_title = self.get_alpha_expr(start, end)
            filters.append(
                f"drawtext=textfile='{title_file}':x=(w-text_w)/2:y=350{self.font_opt}:"
                f"fontsize=52:fontcolor={accent_color}:alpha='{alpha_title}':box=1:boxcolor={box_color}:boxborderw=15"
            )

            # 3 Bénéfices progressifs (stagger de 1.5s chacun)
            benefits_list = content_data["benefits"]
            for i, benefit in enumerate(benefits_list[:3]):
                stagger_delay = start + 0.8 + (i * 1.5)
                benefit_text = f"  {benefit}" # Ajout d'espaces pour simuler une coche
                b_file = self.write_temp_text(f"benefit_{i}", wrap_text(benefit_text, 22))
                
                alpha_b = self.get_alpha_expr(stagger_delay, end, fade_in=0.6, fade_out=0.5)
                y_pos = 550 + (i * 220)
                x_expr = f"120 - 100 * pow(1 - clip((t - {stagger_delay}) / 0.6, 0, 1), 2)"
                
                # Coche verte
                filters.append(
                    f"drawtext=text='V':x='{x_expr}':y={y_pos}{self.font_opt}:"
                    f"fontsize=44:fontcolor=0x22c55e:alpha='{alpha_b}':box=1:boxcolor={box_color}:boxborderw=15"
                )
                
                # Texte du bénéfice
                filters.append(
                    f"drawtext=textfile='{b_file}':x='{x_expr} + 60':y={y_pos}{self.font_opt}:"
                    f"fontsize=42:fontcolor={text_color}:alpha='{alpha_b}':box=1:boxcolor={box_color}:boxborderw=15"
                )

        # --- 7. Scène additionnelle : Extra (pour 45s, 60s) ---
        if "extra" in timeline:
            start, end = timeline["extra"]
            ext_text = wrap_text(content_data["extra"], 20)
            ext_file = self.write_temp_text("extra", ext_text)
            alpha = self.get_alpha_expr(start, end)
            filters.append(
                f"drawtext=textfile='{ext_file}':x=(w-text_w)/2:y=650{self.font_opt}:"
                f"fontsize=46:fontcolor={text_color}:alpha='{alpha}':box=1:boxcolor={box_color}:boxborderw=20"
            )

        # --- 8. Scène additionnelle : Offre commerciale (pour 60s) ---
        if "offer" in timeline:
            start, end = timeline["offer"]
            off_text = wrap_text(content_data["offer"], 18)
            off_file = self.write_temp_text("offer", off_text)
            alpha = self.get_alpha_expr(start, end)
            y_expr = f"600 - 100 * pow(1 - clip((t - {start}) / 0.8, 0, 1), 2)"
            filters.append(
                f"drawtext=textfile='{off_file}':x=(w-text_w)/2:y='{y_expr}':alpha='{alpha}'{self.font_opt}:"
                f"fontsize=50:fontcolor={accent_color}:box=1:boxcolor={box_color}:boxborderw=20"
            )

        # --- 9. Scène : Prix ---
        if "price" in timeline:
            start, end = timeline["price"]
            prix = content_data["prix"]
            ancien_prix = content_data["ancien_prix"]
            alpha = self.get_alpha_expr(start, end)
            
            # Animation bounce/scale simulée avec slide
            y_expr = f"920 - 100 * pow(1 - clip((t - {start}) / 0.7, 0, 1), 2)"

            if ancien_prix:
                # Si ancien prix disponible, on l'affiche barré / plus petit au dessus
                old_text = f"Ancien Prix: {ancien_prix}"
                old_file = self.write_temp_text("old_price", old_text)
                
                filters.append(
                    f"drawtext=textfile='{old_file}':x=(w-text_w)/2:y='{y_expr} - 120':alpha='{alpha}'{self.font_opt}:"
                    f"fontsize=40:fontcolor=0xef4444:box=1:boxcolor={box_color}:boxborderw=12"
                )
                
                # Prix spécial en dessous
                new_text = f"PRIX SPÉCIAL: {prix}"
                new_file = self.write_temp_text("price", new_text)
                filters.append(
                    f"drawtext=textfile='{new_file}':x=(w-text_w)/2:y='{y_expr}':alpha='{alpha}'{self.font_opt}:"
                    f"fontsize=72:fontcolor={accent_color}:box=1:boxcolor={box_color}:boxborderw=20"
                )
            else:
                # Prix unique dominant au centre
                new_text = f"PRIX: {prix}"
                new_file = self.write_temp_text("price", new_text)
                filters.append(
                    f"drawtext=textfile='{new_file}':x=(w-text_w)/2:y='{y_expr}':alpha='{alpha}'{self.font_opt}:"
                    f"fontsize=76:fontcolor={accent_color}:box=1:boxcolor={box_color}:boxborderw=20"
                )

        # --- 10. Scène : CTA / WhatsApp ---
        if "cta" in timeline:
            start, end = timeline["cta"]
            whatsapp = content_data["whatsapp"]
            ville = content_data["ville"]
            
            # Titre CTA
            cta_file = self.write_temp_text("cta_title", "COMMANDER MAINTENANT")
            alpha = self.get_alpha_expr(start, end)
            y_cta = f"1450 - 100 * pow(1 - clip((t - {start}) / 0.8, 0, 1), 2)"
            
            filters.append(
                f"drawtext=textfile='{cta_file}':x=(w-text_w)/2:y='{y_cta}':alpha='{alpha}'{self.font_opt}:"
                f"fontsize=52:fontcolor=white:box=1:boxcolor=0x16a34a:boxborderw=22" # Bouton vert brillant
            )

            # WhatsApp + Ville en dessous (zone sécurisée)
            contact_str = f"WhatsApp: {whatsapp}"
            if ville:
                contact_str += f"\n({ville})"
            contact_file = self.write_temp_text("cta_contact", contact_str)
            
            y_contact = f"{y_cta} + 180"
            filters.append(
                f"drawtext=textfile='{contact_file}':x=(w-text_w)/2:y='{y_contact}':alpha='{alpha}'{self.font_opt}:"
                f"fontsize=46:fontcolor={contact_text}:box=1:boxcolor={contact_box}:boxborderw=18"
            )

        return ",".join(filters) + "[outv]"
