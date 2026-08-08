import os
import re
import tempfile
from pathlib import Path
from dataclasses import dataclass


class OCRError(RuntimeError):
    pass


@dataclass
class OCRResult:
    text: str
    numbers: list[str]
    whatsapp_numbers: list[str]
    warning: str = ""


def _clean_display_phone(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""

    if value.startswith("+"):
        digits = re.sub(r"[^\d]", "", value[1:])
        return f"+{digits}" if digits else ""

    return re.sub(r"[^\d]", "", value)


def _guess_whatsapp_digits(digits: str) -> str:
    if not digits:
        return ""

    digits = digits.lstrip("+")
    digits = re.sub(r"[^\d]", "", digits)
    if digits.startswith("00"):
        digits = digits[2:]

    valid_cc = ("237", "297")

    if any(digits.startswith(cc) for cc in valid_cc) and 12 <= len(digits) <= 15:
        return digits

    for prefix in ("4", "2", "1"):
        if digits.startswith(prefix) and len(digits) > len(prefix):
            tail = digits[len(prefix):]
            if any(tail.startswith(cc) and 12 <= len(tail) <= 15 for cc in valid_cc):
                return tail

    for cc in valid_cc:
        match = re.search(fr"{cc}\d{{9}}", digits)
        if match:
            return match.group(0)

    if len(digits) == 10 and digits.startswith("0"):
        return f"237{digits[1:]}"

    if len(digits) in {7, 8, 9}:
        return f"237{digits}"

    if len(digits) > 9:
        last9 = digits[-9:]
        if last9[0] not in ("0",):
            return f"237{last9}"

    return ""


def _normalize_phone_for_whatsapp(raw_value: str) -> str:
    value = _clean_display_phone(raw_value)
    if not value:
        return ""

    digits = value[1:] if value.startswith("+") else value
    digits = _guess_whatsapp_digits(digits)
    if not digits:
        return ""

    if digits.startswith("+"):
        return digits
    return f"+{digits}"


def extract_phone_numbers(text: str) -> list[str]:
    """Extrait des numeros visibles en gardant le format lu par OCR."""

    pattern = re.compile(
        r"(?:\+?\s*\d[\d\s().-]{6,}\d)",
        flags=re.IGNORECASE,
    )
    found = []
    seen = set()
    for line in (text or "").splitlines():
        for match in pattern.finditer(line):
            display = _clean_display_phone(match.group(0))
            digits = re.sub(r"\D", "", display)
            if not display or len(digits) < 7:
                continue
            key = digits
            if key not in seen:
                seen.add(key)
                found.append(display)
    return found


def normalize_numbers_for_whatsapp(numbers: list[str]) -> list[str]:
    found = []
    seen = set()
    for number in numbers:
        normalized = _normalize_phone_for_whatsapp(number)
        if normalized and normalized not in seen:
            seen.add(normalized)
            found.append(normalized)
    return found


def _ensure_pillow_and_tesseract():
    try:
        from PIL import Image, ImageOps  # noqa: F401
    except ImportError as exc:
        raise OCRError("Pillow n'est pas installe. Installe-le avec: pip install Pillow") from exc

    try:
        import pytesseract  # noqa: F401
    except ImportError as exc:
        raise OCRError(
            "pytesseract n'est pas installe. Installe-le avec: pip install pytesseract puis installe Tesseract OCR sur Windows."
        ) from exc


def _text_from_pil_image(image) -> str:
    from PIL import ImageOps
    import pytesseract

    default_windows_cmd = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if default_windows_cmd.exists():
        pytesseract.pytesseract.tesseract_cmd = str(default_windows_cmd)

    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    return pytesseract.image_to_string(image, lang="eng+fra")


def image_to_text(image_file) -> str:
    """OCR local via pytesseract. Aucune image n'est envoyee a une API externe."""
    _ensure_pillow_and_tesseract()

    from PIL import Image

    try:
        image = Image.open(image_file)
        return _text_from_pil_image(image)
    except Exception as exc:
        if "TesseractNotFoundError" in type(exc).__name__:
            raise OCRError(
                "Tesseract OCR est introuvable sur cette machine. Installe Tesseract puis redemarre le serveur Django."
            ) from exc
        raise OCRError(f"OCR impossible sur cette image: {exc}") from exc


def video_to_text(video_file) -> str:
    """Extrait des images d'une vidéo puis applique OCR local sur les frames."""
    _ensure_pillow_and_tesseract()

    try:
        from moviepy.editor import VideoFileClip
    except ImportError as exc:
        raise OCRError(
            "MoviePy n'est pas installe. Installe-le avec: pip install moviepy[ffmpeg]"
        ) from exc

    temp_path = None
    clip = None
    try:
        suffix = os.path.splitext(getattr(video_file, "name", ""))[1] or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            for chunk in video_file.chunks():
                tmp.write(chunk)

        clip = VideoFileClip(temp_path)
        duration = float(clip.duration or 0)
        if duration <= 0:
            raise OCRError("Durée vidéo invalide ou vidéo corrompue.")

        interval = 1.0 if duration <= 30 else 2.0
        texts = []
        t = 0.0
        while t < duration:
            frame = clip.get_frame(t)
            from PIL import Image
            image = Image.fromarray(frame)
            texts.append(_text_from_pil_image(image))
            t += interval

        if duration - max(t - interval, 0) > 0.5:
            frame = clip.get_frame(max(duration - 0.5, 0))
            from PIL import Image
            image = Image.fromarray(frame)
            texts.append(_text_from_pil_image(image))

        return "\n".join(texts)
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError(
            "Impossible d'extraire le contenu de la vidéo. Vérifie que ffmpeg est installé et que le format est pris en charge."
        ) from exc
    finally:
        if clip is not None:
            clip.close()
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def extract_from_image(image_file) -> OCRResult:
    text = image_to_text(image_file)
    numbers = extract_phone_numbers(text)
    return OCRResult(
        text=text,
        numbers=numbers,
        whatsapp_numbers=normalize_numbers_for_whatsapp(numbers),
    )


def extract_from_video(video_file) -> OCRResult:
    text = video_to_text(video_file)
    numbers = extract_phone_numbers(text)
    return OCRResult(
        text=text,
        numbers=numbers,
        whatsapp_numbers=normalize_numbers_for_whatsapp(numbers),
    )
