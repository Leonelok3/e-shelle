import logging

import requests

from ..config import get_settings
from ..utils import meta_phone


logger = logging.getLogger(__name__)


class MetaWhatsAppClient:
    def __init__(self):
        self.settings = get_settings()

    def send_text(self, phone_number_id: str, to: str, body: str) -> dict:
        if self.settings.shellbot_dry_run:
            logger.info("[DRY_RUN] %s -> %s: %s", phone_number_id, to, body)
            return {"success": True, "message_id": "dry-run"}

        if not self.settings.meta_access_token:
            return {"success": False, "error": "META_ACCESS_TOKEN is missing"}

        url = f"https://graph.facebook.com/{self.settings.meta_api_version}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": meta_phone(to),
            "type": "text",
            "text": {"body": body, "preview_url": False},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.meta_access_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        data = response.json()
        if response.ok and data.get("messages"):
            return {"success": True, "message_id": data["messages"][0]["id"]}
        return {"success": False, "error": data}

