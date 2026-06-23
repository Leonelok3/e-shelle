import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','videostory_local_ai.settings')
import django
django.setup()
from stories.models import StoryProject
qs = StoryProject.objects.order_by('-created_at')[:8]
for p in qs:
    print(p.pk, p.status, p.current_step, 'final_video=' + str(bool(p.final_video)), 'error=' + (p.error_message or '<none>'))
