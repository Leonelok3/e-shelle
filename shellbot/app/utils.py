import re


def normalize_phone(number: str, default_country="1") -> str:
    value = (number or "").strip()
    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""
    if value.startswith("+"):
        return f"+{digits}"
    if len(digits) == 10 and default_country:
        return f"+{default_country}{digits}"
    return f"+{digits}"


def meta_phone(number: str) -> str:
    return re.sub(r"\D", "", number or "")


def detect_language(text: str, default="fr") -> str:
    t = f" {text.lower()} "
    english = [" hello ", " hi ", " quote ", " appointment ", " price ", " need ", " thanks ", " service "]
    french = [" bonjour ", " salut ", " devis ", " rendez-vous ", " prix ", " besoin ", " merci ", " service "]
    en_score = sum(1 for token in english if token in t)
    fr_score = sum(1 for token in french if token in t)
    if en_score > fr_score:
        return "en"
    if fr_score > en_score:
        return "fr"
    return default

