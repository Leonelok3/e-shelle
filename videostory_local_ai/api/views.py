from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from stories.models import StoryProject
from videos.models import RenderJob


@api_view(['GET', 'POST'])
def project_list_create(request):
    if request.method == 'GET':
        projects = StoryProject.objects.all().order_by('-created_at')
        data = [
            {
                'id': project.pk,
                'title': project.title,
                'prompt': project.prompt,
                'is_avatar_project': project.is_avatar_project,
                'status': project.status,
                'progress': project.progress,
                'current_step': project.current_step,
            }
            for project in projects
        ]
        return Response(data)

    payload = request.data
    is_avatar = str(payload.get('is_avatar_project', '')).lower() in ['true', '1'] or ('avatar_image' in request.FILES and 'script_text' in payload)

    if is_avatar:
        avatar_image = request.FILES.get('avatar_image')
        script_text = payload.get('script_text', '').strip()
        avatar_background = payload.get('avatar_background', 'office')
        title = payload.get('title', '').strip() or "Talking Avatar"

        if not script_text:
            return Response({'detail': 'script_text is required for avatar projects'}, status=status.HTTP_400_BAD_REQUEST)

        # Voice cloning logic
        cloned_voice = None
        cloned_voice_id = payload.get('cloned_voice_id')
        cloned_voice_file = request.FILES.get('cloned_voice_file')

        from voices.models import ClonedVoice
        import uuid

        if cloned_voice_file:
            cloned_voice_name = payload.get('cloned_voice_name') or f"Voix API {uuid.uuid4().hex[:6]}"
            cloned_voice = ClonedVoice.objects.create(
                name=cloned_voice_name,
                voice_file=cloned_voice_file
            )
        elif cloned_voice_id:
            try:
                cloned_voice = ClonedVoice.objects.get(pk=int(cloned_voice_id))
            except (ValueError, TypeError, ClonedVoice.DoesNotExist):
                return Response({'detail': f'Cloned voice with ID {cloned_voice_id} not found.'}, status=status.HTTP_400_BAD_REQUEST)

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
        RenderJob.objects.create(project=project, job_type='avatar', status=RenderJob.Status.RUNNING, progress=1)
        
        import threading
        from stories.views import _run_generation
        thread = threading.Thread(target=_run_generation, args=(project.pk,), daemon=True)
        thread.start()
    else:
        prompt = (payload.get('prompt') or '').strip()
        if not prompt:
            return Response({'detail': 'prompt is required'}, status=status.HTTP_400_BAD_REQUEST)

        project = StoryProject.objects.create(
            prompt=prompt,
            status=StoryProject.Status.RUNNING,
            current_step='Démarrage du workflow local...',
            progress=1
        )
        import threading
        from stories.views import _run_generation
        thread = threading.Thread(target=_run_generation, args=(project.pk,), daemon=True)
        thread.start()

    return Response(
        {
            'id': project.pk,
            'title': project.title,
            'prompt': project.prompt,
            'is_avatar_project': project.is_avatar_project,
            'status': project.status,
            'progress': project.progress,
            'current_step': project.current_step,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
def project_detail(request, pk):
    project = get_object_or_404(StoryProject, pk=pk)
    return Response(
        {
            'id': project.pk,
            'title': project.title,
            'prompt': project.prompt,
            'story_text': project.story_text,
            'status': project.status,
            'progress': project.progress,
            'current_step': project.current_step,
            'error_message': project.error_message,
            'final_video_url': project.final_video.url if project.final_video else None,
        }
    )


@api_view(['GET'])
def project_status(request, pk):
    project = get_object_or_404(StoryProject, pk=pk)
    job = project.render_jobs.first()
    return Response(
        {
            'id': project.pk,
            'status': project.status,
            'progress': project.progress,
            'current_step': project.current_step,
            'error_message': project.error_message,
            'final_video_url': project.final_video.url if project.final_video else None,
            'job': {
                'id': job.pk if job else None,
                'status': job.status if job else None,
                'progress': job.progress if job else 0,
            },
        }
    )