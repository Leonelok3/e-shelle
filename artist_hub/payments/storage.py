"""Payment receipts are never published below MEDIA_URL."""
from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage

class PrivateProofStorage(FileSystemStorage):
    def __init__(self):
        root = getattr(settings, "ARTIST_HUB_PRIVATE_ROOT", Path(settings.MEDIA_ROOT).parent / "artist_hub_private")
        super().__init__(location=root, file_permissions_mode=0o600, directory_permissions_mode=0o700)
    def url(self, name):
        raise ValueError("Preuve privée : utiliser la vue staff authentifiée.")

def private_proof_storage():
    return PrivateProofStorage()
