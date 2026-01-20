from PIL import Image, ImageDraw
import os

# Chemin racine du projet
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "static", "img")
os.makedirs(OUT_DIR, exist_ok=True)

def generate_photo(path, ok=True):
    W, H = 900, 900
    bg = (245, 245, 245) if ok else (30, 30, 30)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    border = (40, 170, 90) if ok else (200, 60, 60)
    d.rectangle([60, 60, W-60, H-60], outline=border, width=10)

    # visage stylisé (démo, légal)
    d.ellipse([320, 240, 580, 500], outline=(90, 90, 90), width=8)
    d.ellipse([400, 330, 430, 360], fill=(90, 90, 90))
    d.ellipse([470, 330, 500, 360], fill=(90, 90, 90))
    d.arc([400, 390, 500, 470], 10, 170, fill=(90, 90, 90), width=6)

    d.text((90, 90), "PHOTO VISA", fill=(0, 0, 0) if ok else (240, 240, 240))
    d.text((90, 130),
           "CONFORME" if ok else "NON CONFORME",
           fill=border)

    img.save(path, "JPEG", quality=92)
    print("✔ Généré :", path)

generate_photo(os.path.join(OUT_DIR, "photo_ok.jpg"), ok=True)
generate_photo(os.path.join(OUT_DIR, "photo_non_ok.jpg"), ok=False)
