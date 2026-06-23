from pathlib import Path
import os
from dotenv import load_dotenv
from PIL import Image as PILImage

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Pillow 10+ has moved ANTIALIAS under Resampling.
if not hasattr(PILImage, 'ANTIALIAS'):
    PILImage.ANTIALIAS = PILImage.Resampling.LANCZOS

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-local-secret-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'e-shelle.com', 'www.e-shelle.com', 'video.e-shelle.com']
FORCE_SCRIPT_NAME = os.getenv('FORCE_SCRIPT_NAME', None)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'stories',
    'scenes',
    'images',
    'voices',
    'videos',
    'api',
    # New apps for E-Shelle Video AI
    'businesses',
    'ads',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'videostory_local_ai.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'videostory_local_ai.wsgi.application'
ASGI_APPLICATION = 'videostory_local_ai.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '180'))

IMAGE_BACKEND = os.getenv('IMAGE_BACKEND', 'comfyui')
COMFYUI_BASE_URL = os.getenv('COMFYUI_BASE_URL', 'http://127.0.0.1:8188')
SD_WEBUI_BASE_URL = os.getenv('SD_WEBUI_BASE_URL', 'http://127.0.0.1:7860')

VOICE_BACKEND = os.getenv('VOICE_BACKEND', 'coqui')
COQUI_TTS_MODEL = os.getenv('COQUI_TTS_MODEL', 'tts_models/fr/css10/vits')
PIPER_EXE = os.getenv('PIPER_EXE', 'piper')
PIPER_MODEL = os.getenv('PIPER_MODEL', 'models/fr_FR-siwis-medium.onnx')
FFMPEG_BINARY = os.getenv('FFMPEG_BINARY', 'ffmpeg')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
GCP_VERTEX_KEY_PATH = os.getenv('GCP_VERTEX_KEY_PATH', str(BASE_DIR / 'gcp_vertex_key.json'))
GOOGLE_VIDEO_MODEL = os.getenv('GOOGLE_VIDEO_MODEL', 'veo-3.1-generate-preview')

