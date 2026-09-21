"""Report configured providers without displaying credentials or reading user data."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_cm.settings')

import django
django.setup()

from django.conf import settings
from ai_engine.services.availability import offline_mode


if __name__ == '__main__':
    print('LLM mode:', 'offline' if offline_mode() else 'auto')
    for label, keys in (
        ('OpenAI', ('OPENAI_API_KEY',)),
        ('Google AI Studio', ('GOOGLE_API_KEY', 'GEMINI_SEARCH_API_KEY')),
    ):
        configured = any(bool(getattr(settings, key, '')) for key in keys)
        print(label + ':', 'configured' if configured else 'not configured')
    vertex_path = getattr(settings, 'GCP_VERTEX_KEY_PATH', '')
    print('Vertex AI credentials:', 'present' if vertex_path and Path(vertex_path).is_file() else 'absent')
    print('OpenAI chat model:', getattr(settings, 'OPENAI_CHAT_MODEL', 'gpt-4o'))
    print('Shared Gemini model: gemini-3.6-flash')
    print('Configuration presence does not verify credit or provider availability.')
