import re
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

    value = re.sub(r"^[^\d+]+", "", value)
    value = re.sub(r"[^\d+]+$", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _normalize_phone_for_whatsapp(raw_value: str) -> str:
    value = _clean_display_phone(raw_value)
    if not value:
        return ""

    has_plus = value.startswith("+")
    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""

    if has_plus and digits.startswith("237"):
        return f"+{digits}"
    if digits.startswith("00237"):
        return f"+{digits[2:]}"
    if digits.startswith("237") and len(digits) >= 11:
        return f"+{digits}"
    if len(digits) in {8, 9}:
        return f"+237{digits}"
    if len(digits) == 10 and digits.startswith("0"):
        return f"+237{digits[1:]}"
    return ""


def extract_phone_numbers(text: str) -> list[str]:
    """Extrait les numeros visibles en gardant le format lu par OCR."""

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


def image_to_text(image_file) -> str:
    """OCR local via pytesseract. Aucune image n'est envoyee a une API externe."""

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise OCRError("Pillow n'est pas installe. Installe-le avec: pip install Pillow") from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise OCRError(
            "pytesseract n'est pas installe. Installe-le avec: pip install pytesseract puis installe Tesseract OCR sur Windows."
        ) from exc

    default_windows_cmd = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if default_windows_cmd.exists():
        pytesseract.pytesseract.tesseract_cmd = str(default_windows_cmd)

    try:
        image = Image.open(image_file)
        image = ImageOps.exif_transpose(image)
        image = image.convert("L")
        return pytesseract.image_to_string(image, lang="eng+fra")
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError(
            "Tesseract OCR est introuvable sur cette machine. Installe Tesseract puis redemarre le serveur Django."
        ) from exc
    except Exception as exc:
        raise OCRError(f"OCR impossible sur cette image: {exc}") from exc


def extract_from_image(image_file) -> OCRResult:
    text = image_to_text(image_file)
    numbers = extract_phone_numbers(text)
    return OCRResult(
        text=text,
        numbers=numbers,
        whatsapp_numbers=normalize_numbers_for_whatsapp(numbers),
    )
