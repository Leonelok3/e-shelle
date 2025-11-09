from PIL import Image, ImageOps
import cv2
import numpy as np
from pathlib import Path

# Spécifications minimales (MVP) — valeurs usuelles (peuvent être affinées)
PHOTO_SPECS = {
    "dv_lottery":  {"label":"DV Lottery (Green Card)", "size": (600, 600), "fmt": "JPEG", "bg": (255,255,255)},
    "france_visa": {"label":"Visa France",              "size": (413, 531), "fmt": "JPEG", "bg": (255,255,255)},  # ~35x45mm @300dpi
    "canada_visa": {"label":"Visa Canada",              "size": (591, 827), "fmt": "JPEG", "bg": (255,255,255)},  # ~50x70mm @300dpi
    "uk_visa":     {"label":"Visa UK",                  "size": (600, 750), "fmt": "JPEG", "bg": (255,255,255)},  # ratio 4:5
}

def _detect_face_bbox(pil_img: Image.Image):
    """Détection visage (approx) via Haar cascade. Retourne (x,y,w,h) ou None."""
    try:
        cv_img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(80,80))
        if len(faces) == 0:
            return None
        # Prendre le visage le plus grand (souvent le bon)
        x,y,w,h = max(faces, key=lambda f: f[2]*f[3])
        return int(x), int(y), int(w), int(h)
    except Exception:
        return None

def _crop_to_aspect(pil_img: Image.Image, target_w: int, target_h: int):
    """Recadre l'image pour approcher le ratio cible, centré sur le visage si détecté, sinon centré."""
    src_w, src_h = pil_img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    # Déterminer la fenêtre de crop
    if src_ratio > target_ratio:
        # Trop large -> on réduit la largeur
        new_w = int(src_h * target_ratio)
        new_h = src_h
        x0 = (src_w - new_w) // 2
        y0 = 0
    else:
        # Trop haut -> on réduit la hauteur
        new_w = src_w
        new_h = int(src_w / target_ratio)
        x0 = 0
        y0 = (src_h - new_h) // 2

    face = _detect_face_bbox(pil_img)
    if face:
        fx, fy, fw, fh = face
        # recentrer la fenêtre autour du visage (avec marge)
        cx = fx + fw//2
        cy = fy + int(fh*0.45)  # un peu au-dessus du centre du visage
        # demi-tailles
        half_w = new_w // 2
        half_h = new_h // 2
        x0 = max(0, min(src_w - new_w, cx - half_w))
        y0 = max(0, min(src_h - new_h, cy - half_h))

    return pil_img.crop((x0, y0, x0 + new_w, y0 + new_h))

def process_photo(input_path: Path, output_path: Path, kind: str):
    """Traite la photo selon le type choisi. Retourne un rapport dict."""
    spec = PHOTO_SPECS.get(kind)
    if not spec:
        raise ValueError("Type de photo inconnu.")

    target_w, target_h = spec["size"]
    bg = spec["bg"]
    fmt = spec["fmt"]

    img = Image.open(input_path).convert("RGB")
    # Recadrage au ratio, de préférence centré visage
    cropped = _crop_to_aspect(img, target_w, target_h)
    # Redimension
    resized = cropped.resize((target_w, target_h), Image.LANCZOS)
    # Fond blanc (si besoin) + equalize léger
    out = ImageOps.autocontrast(resized)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path, format=fmt, quality=95)

    report = {
        "type": kind,
        "label": spec["label"],
        "target_size": {"w": target_w, "h": target_h},
        "format": fmt,
        "background": "white",
        "notes": "MVP auto-crop; détection visage approximative (Haar)."
    }
    return report
