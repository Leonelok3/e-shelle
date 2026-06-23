from pathlib import Path

ROOT = Path('/home/ubuntu/videostory_local_ai')

files = {
    'stories/forms.py': r'''from django import forms
from .models import StoryProject


class StoryPromptForm(forms.ModelForm):
    class Meta:
        model = StoryProject
        fields = ['prompt']
        widgets = {
            'prompt': forms.Textarea(attrs={
                'class': 'prompt-input',
                'rows': 6,
                'placeholder': 'Exemple : Raconte l’histoire d’un jeune Camerounais qui obtient un visa pour le Canada.',
            })
        }
        labels = {'prompt': 'Votre idée de vidéo'}
''',
    'stories/urls.py': r'''from django.urls import path
from . import views

app_name = 'stories'

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/<int:pk>/', views.project_detail, name='detail'),
    path('projects/<int:pk>/status/', views.project_status, name='status'),
]
''',
    'stories/views.py': r'''import threading

from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from agents.orchestrator import VideoStoryOrchestrator
from .forms import StoryPromptForm
from .models import StoryProject


def _run_generation(project_id: int) -> None:
    close_old_connections()
    project = StoryProject.objects.get(pk=project_id)
    VideoStoryOrchestrator(project).run()
    close_old_connections()


def home(request):
    if request.method == 'POST':
        form = StoryPromptForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.status = StoryProject.Status.RUNNING
            project.current_step = 'Projet créé, démarrage du workflow local'
            project.progress = 1
            project.save()
            thread = threading.Thread(target=_run_generation, args=(project.pk,), daemon=True)
            thread.start()
            return redirect(reverse('stories:detail', args=[project.pk]))
    else:
        form = StoryPromptForm()

    projects = StoryProject.objects.all()[:10]
    return render(request, 'stories/home.html', {'form': form, 'projects': projects})


def project_detail(request, pk: int):
    project = get_object_or_404(StoryProject, pk=pk)
    return render(request, 'stories/detail.html', {'project': project})


@require_GET
def project_status(request, pk: int):
    project = get_object_or_404(StoryProject, pk=pk)
    return JsonResponse({
        'id': project.pk,
        'title': project.title,
        'status': project.status,
        'progress': project.progress,
        'current_step': project.current_step,
        'error_message': project.error_message,
        'final_video_url': project.final_video.url if project.final_video else '',
    })
''',
    'templates/base.html': r'''<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}VideoStory Local AI{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/app.css">
</head>
<body>
    <header class="topbar">
        <a href="/" class="brand">VideoStory Local AI</a>
        <span class="badge">Django · Ollama · Stable Diffusion · TTS · MoviePy</span>
    </header>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
''',
    'templates/stories/home.html': r'''{% extends 'base.html' %}
{% block title %}Accueil · VideoStory Local AI{% endblock %}
{% block content %}
<section class="hero">
    <h1>Créer une vidéo narrative avec une IA locale</h1>
    <p>
        Saisissez une idée. L’application génère le scénario, les scènes, les images, la voix off,
        les sous-titres et le MP4 final sans API payante obligatoire.
    </p>
</section>

<section class="card">
    <h2>Nouveau projet vidéo</h2>
    <form method="post" class="prompt-form">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Générer la vidéo</button>
    </form>
</section>

<section class="card">
    <h2>Projets récents</h2>
    {% if projects %}
        <div class="project-list">
            {% for project in projects %}
                <a class="project-item" href="{% url 'stories:detail' project.pk %}">
                    <strong>{{ project.title|default:'Projet sans titre' }}</strong>
                    <span>{{ project.get_status_display }} · {{ project.progress }}%</span>
                </a>
            {% endfor %}
        </div>
    {% else %}
        <p>Aucun projet pour le moment.</p>
    {% endif %}
</section>
{% endblock %}
''',
    'templates/stories/detail.html': r'''{% extends 'base.html' %}
{% block title %}Projet {{ project.pk }} · VideoStory Local AI{% endblock %}
{% block content %}
<section class="card" data-status-url="{% url 'stories:status' project.pk %}">
    <h1 id="project-title">{{ project.title|default:'Génération en cours' }}</h1>
    <p class="muted">Prompt initial : {{ project.prompt }}</p>

    <div class="progress-wrap">
        <div id="progress-bar" class="progress-bar" style="width: {{ project.progress }}%"></div>
    </div>
    <p><strong>Étape :</strong> <span id="current-step">{{ project.current_step }}</span></p>
    <p><strong>Statut :</strong> <span id="status">{{ project.get_status_display }}</span></p>
    <p id="error" class="error">{{ project.error_message }}</p>

    <div id="video-zone">
        {% if project.final_video %}
            <video controls class="video-player" src="{{ project.final_video.url }}"></video>
            <p><a class="download" href="{{ project.final_video.url }}" download>Télécharger le MP4</a></p>
        {% else %}
            <p class="muted">Le lecteur vidéo apparaîtra automatiquement lorsque le rendu sera terminé.</p>
        {% endif %}
    </div>
</section>

<section class="card">
    <h2>Scènes</h2>
    {% for scene in project.scenes.all %}
        <article class="scene-card">
            <h3>Scène {{ scene.order }} · {{ scene.title }}</h3>
            <p>{{ scene.narration }}</p>
            <details>
                <summary>Prompt image</summary>
                <pre>{{ scene.image_prompt }}</pre>
            </details>
        </article>
    {% empty %}
        <p>Les scènes seront visibles après le découpage automatique.</p>
    {% endfor %}
</section>
<script src="/static/js/progress.js"></script>
{% endblock %}
''',
    'static/css/app.css': r''':root {
    --bg: #0f172a;
    --panel: #111827;
    --panel-2: #1f2937;
    --text: #f8fafc;
    --muted: #cbd5e1;
    --accent: #38bdf8;
    --accent-2: #22c55e;
    --danger: #fb7185;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    background: radial-gradient(circle at top, #1e3a8a 0, var(--bg) 38%);
    color: var(--text);
    font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
}
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 40px;
    border-bottom: 1px solid rgba(255,255,255,.08);
    background: rgba(15,23,42,.75);
    backdrop-filter: blur(12px);
}
.brand { color: var(--text); font-weight: 800; text-decoration: none; font-size: 1.2rem; }
.badge { color: var(--muted); font-size: .9rem; }
.container { max-width: 1100px; margin: 0 auto; padding: 40px 24px; }
.hero { margin-bottom: 28px; }
.hero h1 { font-size: clamp(2rem, 5vw, 4rem); margin: 0 0 12px; }
.hero p { color: var(--muted); font-size: 1.1rem; max-width: 760px; line-height: 1.7; }
.card {
    background: linear-gradient(180deg, rgba(31,41,55,.95), rgba(17,24,39,.95));
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 22px;
    padding: 26px;
    margin-bottom: 24px;
    box-shadow: 0 20px 60px rgba(0,0,0,.25);
}
.prompt-input {
    width: 100%;
    border: 1px solid rgba(255,255,255,.14);
    background: #0b1220;
    color: var(--text);
    border-radius: 14px;
    padding: 16px;
    font-size: 1rem;
    line-height: 1.6;
}
button, .download {
    display: inline-block;
    border: 0;
    color: #06111f;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    border-radius: 999px;
    padding: 13px 22px;
    font-weight: 800;
    cursor: pointer;
    text-decoration: none;
}
.project-list { display: grid; gap: 12px; }
.project-item {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 16px;
    border-radius: 14px;
    background: rgba(255,255,255,.06);
    color: var(--text);
    text-decoration: none;
}
.muted { color: var(--muted); }
.progress-wrap { height: 18px; background: #020617; border-radius: 99px; overflow: hidden; border: 1px solid rgba(255,255,255,.1); }
.progress-bar { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-2)); transition: width .4s ease; }
.video-player { width: 100%; max-height: 640px; border-radius: 18px; background: #000; }
.scene-card { border-top: 1px solid rgba(255,255,255,.08); padding: 18px 0; }
pre { white-space: pre-wrap; color: var(--muted); }
.error { color: var(--danger); font-weight: 700; }
@media (max-width: 760px) { .topbar, .project-item { flex-direction: column; align-items: flex-start; } }
''',
    'static/js/progress.js': r'''const root = document.querySelector('[data-status-url]');

function statusLabel(status) {
    return {
        draft: 'Brouillon',
        running: 'Génération en cours',
        done: 'Terminé',
        failed: 'Échec',
    }[status] || status;
}

async function pollStatus() {
    if (!root) return;
    const response = await fetch(root.dataset.statusUrl);
    const data = await response.json();

    document.getElementById('project-title').textContent = data.title || 'Génération en cours';
    document.getElementById('progress-bar').style.width = `${data.progress}%`;
    document.getElementById('current-step').textContent = data.current_step || '';
    document.getElementById('status').textContent = statusLabel(data.status);
    document.getElementById('error').textContent = data.error_message || '';

    if (data.status === 'done' && data.final_video_url) {
        const zone = document.getElementById('video-zone');
        if (!zone.querySelector('video')) {
            zone.innerHTML = `
                <video controls class="video-player" src="${data.final_video_url}"></video>
                <p><a class="download" href="${data.final_video_url}" download>Télécharger le MP4</a></p>
            `;
        }
        return;
    }
    if (data.status !== 'failed') {
        setTimeout(pollStatus, 2000);
    }
}

pollStatus();
''',
    'agents/orchestrator.py': r'''from django.core.files import File
from django.db import transaction

from images.models import GeneratedImage
from scenes.models import Scene
from stories.models import StoryProject
from voices.models import VoiceOver
from videos.models import VideoRender

from .image_agent import ImageAgent
from .image_prompt_agent import ImagePromptAgent
from .scene_agent import SceneAgent
from .story_agent import StoryAgent
from .subtitle_agent import SubtitleAgent
from .video_agent import VideoAgent
from .voice_agent import VoiceAgent


class VideoStoryOrchestrator:
    """Chef d'orchestre du workflow Prompt → Scénario → Scènes → Images → Voix → Sous-titres → MP4."""

    def __init__(self, project: StoryProject) -> None:
        self.project = project

    def _progress(self, step: str, value: int) -> None:
        self.project.mark_progress(step, value)

    def run(self) -> StoryProject:
        render = None
        try:
            self.project.status = StoryProject.Status.RUNNING
            self.project.error_message = ''
            self.project.save(update_fields=['status', 'error_message', 'updated_at'])

            story_data = StoryAgent(self._progress).run(self.project.prompt)
            self.project.title = story_data['title']
            self.project.story_text = story_data['story_text']
            self.project.save(update_fields=['title', 'story_text', 'updated_at'])

            scene_data = SceneAgent(self._progress).run(self.project.story_text)
            scene_data = ImagePromptAgent(self._progress).run(scene_data)
            self._create_scene_rows(scene_data)

            image_agent = ImageAgent(self._progress)
            voice_agent = VoiceAgent(self._progress)
            subtitle_agent = SubtitleAgent(self._progress)

            for scene in self.project.scenes.all():
                image_path = image_agent.run(scene, scene.image_prompt)
                with image_path.open('rb') as handle:
                    GeneratedImage.objects.update_or_create(
                        scene=scene,
                        defaults={'prompt': scene.image_prompt, 'image': File(handle, name=image_path.name)},
                    )

                audio_path = voice_agent.run(scene, scene.narration)
                with audio_path.open('rb') as handle:
                    VoiceOver.objects.update_or_create(
                        scene=scene,
                        defaults={'text': scene.narration, 'audio': File(handle, name=audio_path.name)},
                    )

                subtitle_agent.run(scene, scene.narration, scene.duration_seconds)

            render = VideoRender.objects.create(project=self.project)
            video_path = VideoAgent(self._progress).run(self.project)
            with video_path.open('rb') as handle:
                render.video.save(video_path.name, File(handle), save=True)
                handle.seek(0)
                self.project.final_video.save(video_path.name, File(handle), save=False)
            self.project.status = StoryProject.Status.DONE
            self.project.progress = 100
            self.project.current_step = 'Vidéo finale prête'
            self.project.save()
            render.status = VideoRender.Status.DONE
            render.save(update_fields=['status'])
            return self.project
        except Exception as exc:
            self.project.status = StoryProject.Status.FAILED
            self.project.error_message = str(exc)
            self.project.current_step = 'Erreur pendant la génération'
            self.project.save(update_fields=['status', 'error_message', 'current_step', 'updated_at'])
            if render:
                render.status = VideoRender.Status.FAILED
                render.log = str(exc)
                render.save(update_fields=['status', 'log'])
            raise

    @transaction.atomic
    def _create_scene_rows(self, scenes: list[dict]) -> None:
        self.project.scenes.all().delete()
        for data in scenes:
            Scene.objects.create(
                project=self.project,
                order=data['order'],
                title=data['title'],
                description=data['description'],
                narration=data['narration'],
                image_prompt=data.get('image_prompt', ''),
                duration_seconds=data.get('duration_seconds', 6.0),
            )
''',
}

for relative_path, content in files.items():
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

print('Interface Django écrite.')
