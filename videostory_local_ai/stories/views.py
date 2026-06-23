import threading

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
    if project.is_avatar_project:
        from agents.avatar_orchestrator import AvatarOrchestrator
        AvatarOrchestrator(project).run()
    else:
        VideoStoryOrchestrator(project).run()
    close_old_connections()



def home(request):
    from voices.models import ClonedVoice
    import uuid

    if request.method == 'POST':
        if 'is_avatar' in request.POST:
            avatar_image = request.FILES.get('avatar_image')
            script_text = request.POST.get('script_text', '').strip()
            avatar_background = request.POST.get('avatar_background', 'office')
            title = request.POST.get('title', '').strip() or "Avatar Parlant"
            
            # Voice option parsing
            voice_option = request.POST.get('voice_option', 'standard')
            cloned_voice = None
            
            if voice_option == 'new':
                cloned_voice_name = request.POST.get('cloned_voice_name', '').strip() or f"Voix {uuid.uuid4().hex[:6]}"
                cloned_voice_file = request.FILES.get('cloned_voice_file')
                if cloned_voice_file:
                    cloned_voice = ClonedVoice.objects.create(
                        name=cloned_voice_name,
                        voice_file=cloned_voice_file
                    )
            elif voice_option.isdigit():
                try:
                    cloned_voice = ClonedVoice.objects.get(pk=int(voice_option))
                except ClonedVoice.DoesNotExist:
                    pass

            if script_text:
                project = StoryProject.objects.create(
                    title=title,
                    is_avatar_project=True,
                    avatar_image=avatar_image,
                    script_text=script_text,
                    avatar_background=avatar_background,
                    cloned_voice=cloned_voice,
                    status=StoryProject.Status.RUNNING,
                    current_step="Initialisation du Talking Avatar...",
                    progress=1
                )
                thread = threading.Thread(target=_run_generation, args=(project.pk,), daemon=True)
                thread.start()
                return redirect(reverse('stories:detail', args=[project.pk]))
        else:
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
    cloned_voices = ClonedVoice.objects.all().order_by('-created_at')
    return render(request, 'stories/home.html', {
        'form': form,
        'projects': projects,
        'cloned_voices': cloned_voices
    })



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
