from pathlib import Path

ROOT = Path('/home/ubuntu/videostory_local_ai')

files = {
    'manage.py': r'''#!/usr/bin/env python
"""Django management utility for VideoStory Local AI."""
import os
import sys


def main() -> None:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videostory_local_ai.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
''',
    'requirements.txt': r'''Django==5.0.6
requests==2.32.3
python-dotenv==1.0.1
moviepy==1.0.3
Pillow==10.4.0
numpy==1.26.4
TTS==0.22.0
''',
    '.env.example': r'''DJANGO_SECRET_KEY=dev-local-change-me
DJANGO_DEBUG=True
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
OLLAMA_TIMEOUT=180
IMAGE_BACKEND=comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8188
SD_WEBUI_BASE_URL=http://127.0.0.1:7860
VOICE_BACKEND=coqui
COQUI_TTS_MODEL=tts_models/fr/css10/vits
PIPER_EXE=piper
PIPER_MODEL=models/fr_FR-siwis-medium.onnx
FFMPEG_BINARY=ffmpeg
''',
    'videostory_local_ai/settings.py': r'''from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-local-secret-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'stories',
    'scenes',
    'images',
    'voices',
    'videos',
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
''',
    'videostory_local_ai/urls.py': r'''from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('stories.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
''',
    'videostory_local_ai/wsgi.py': r'''import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videostory_local_ai.settings')
application = get_wsgi_application()
''',
    'videostory_local_ai/asgi.py': r'''import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videostory_local_ai.settings')
application = get_asgi_application()
''',
    'stories/apps.py': r'''from django.apps import AppConfig


class StoriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stories'
''',
    'scenes/apps.py': r'''from django.apps import AppConfig


class ScenesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scenes'
''',
    'images/apps.py': r'''from django.apps import AppConfig


class ImagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'images'
''',
    'voices/apps.py': r'''from django.apps import AppConfig


class VoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'voices'
''',
    'videos/apps.py': r'''from django.apps import AppConfig


class VideosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'videos'
''',
    'stories/models.py': r'''from django.db import models


class StoryProject(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        RUNNING = 'running', 'Génération en cours'
        DONE = 'done', 'Terminé'
        FAILED = 'failed', 'Échec'

    title = models.CharField(max_length=220, blank=True)
    prompt = models.TextField()
    story_text = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    progress = models.PositiveSmallIntegerField(default=0)
    current_step = models.CharField(max_length=160, blank=True)
    error_message = models.TextField(blank=True)
    final_video = models.FileField(upload_to='generated/videos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title or f'Projet #{self.pk}'

    def mark_progress(self, step: str, progress: int) -> None:
        self.current_step = step
        self.progress = max(0, min(100, progress))
        self.save(update_fields=['current_step', 'progress', 'updated_at'])
''',
    'scenes/models.py': r'''from django.db import models
from stories.models import StoryProject


class Scene(models.Model):
    project = models.ForeignKey(StoryProject, on_delete=models.CASCADE, related_name='scenes')
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=220)
    description = models.TextField()
    narration = models.TextField()
    image_prompt = models.TextField(blank=True)
    duration_seconds = models.FloatField(default=6.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = [('project', 'order')]

    def __str__(self) -> str:
        return f'{self.project_id} - Scène {self.order}: {self.title}'
''',
    'images/models.py': r'''from django.db import models
from scenes.models import Scene


class GeneratedImage(models.Model):
    scene = models.OneToOneField(Scene, on_delete=models.CASCADE, related_name='generated_image')
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True)
    image = models.ImageField(upload_to='generated/images/', blank=True, null=True)
    seed = models.BigIntegerField(null=True, blank=True)
    backend = models.CharField(max_length=80, default='comfyui')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Image scène {self.scene_id}'
''',
    'voices/models.py': r'''from django.db import models
from scenes.models import Scene


class VoiceOver(models.Model):
    scene = models.OneToOneField(Scene, on_delete=models.CASCADE, related_name='voice_over')
    text = models.TextField()
    audio = models.FileField(upload_to='generated/audio/', blank=True, null=True)
    backend = models.CharField(max_length=80, default='coqui')
    duration_seconds = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Voix scène {self.scene_id}'
''',
    'videos/models.py': r'''from django.db import models
from stories.models import StoryProject


class VideoRender(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'En cours'
        DONE = 'done', 'Terminé'
        FAILED = 'failed', 'Échec'

    project = models.ForeignKey(StoryProject, on_delete=models.CASCADE, related_name='renders')
    video = models.FileField(upload_to='generated/videos/', blank=True, null=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.RUNNING)
    log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Render projet {self.project_id} - {self.status}'
''',
    'stories/admin.py': r'''from django.contrib import admin
from .models import StoryProject


@admin.register(StoryProject)
class StoryProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'progress', 'created_at')
    search_fields = ('title', 'prompt', 'story_text')
    list_filter = ('status', 'created_at')
''',
    'scenes/admin.py': r'''from django.contrib import admin
from .models import Scene


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'order', 'title', 'duration_seconds')
    list_filter = ('project',)
''',
    'images/admin.py': r'''from django.contrib import admin
from .models import GeneratedImage


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'scene', 'backend', 'seed', 'created_at')
''',
    'voices/admin.py': r'''from django.contrib import admin
from .models import VoiceOver


@admin.register(VoiceOver)
class VoiceOverAdmin(admin.ModelAdmin):
    list_display = ('id', 'scene', 'backend', 'duration_seconds', 'created_at')
''',
    'videos/admin.py': r'''from django.contrib import admin
from .models import VideoRender


@admin.register(VideoRender)
class VideoRenderAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'status', 'created_at')
''',
}

for relative_path, content in files.items():
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

print(f'Projet initial écrit dans {ROOT}')
