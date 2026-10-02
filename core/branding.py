"""Public identities for the shared application, selected per request."""
import re

IMMIGRATION97_PHONE = "237693649944"

def public_text(value, brand="E-Shelle"):
    if brand != "Immigration97":
        return value
    if isinstance(value, dict):
        return {key: public_text(item, brand) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(public_text(item, brand) for item in value)
    if not isinstance(value, str):
        return value
    value = re.sub(r"e[- ]shelle(?:\.com)?", "Immigration97", value, flags=re.I)
    value = value.replace("237680625082", IMMIGRATION97_PHONE)
    value = value.replace("+237 680 625 082", "+237 693 649 944")
    return value

def request_brand(request):
    return getattr(request, "site_brand", "E-Shelle")
