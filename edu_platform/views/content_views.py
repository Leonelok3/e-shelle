"""
Vues du contenu pédagogique : sujets, documents PDF, vidéos.
"""
import os
import logging
import hashlib
import time
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse, FileResponse
from django.views import View
from django.utils import timezone
from django.conf import settings

from edu_platform.models import Subject, ExamDocument, VideoLesson, AccessCode

logger = logging.getLogger('edu_platform')


class EduLoginRequiredMixin(LoginRequiredMixin):
    login_url = '/edu/login/'


class SubjectListView(EduLoginRequiredMixin, View):
    """Liste des matières filtrables par niveau."""
    template_name = 'edu_platform/content/subject_list.html'

    def get(self, request):
        level = request.GET.get('level', '')
        subject_type = request.GET.get('type', '')

        subjects = Subject.objects.filter(is_published=True)
        if level:
            subjects = subjects.filter(level=level)
        if subject_type:
            subjects = subjects.filter(subject_type=subject_type)

        subjects = subjects.order_by('level', 'order', 'title')

        context = {
            'subjects': subjects,
            'level_filter': level,
            'type_filter': subject_type,
            'level_choices': Subject.LEVEL_CHOICES,
            'type_choices': Subject.SUBJECT_TYPES,
        }
        return render(request, self.template_name, context)


class SubjectDetailView(EduLoginRequiredMixin, View):
    """Détail d'une matière avec ses documents et vidéos."""
    template_name = 'edu_platform/content/subject_detail.html'

    def get(self, request, slug):
        subject = get_object_or_404(Subject, slug=slug, is_published=True)
        user_has_access = self._check_access(request.user, subject)

        documents = subject.documents.all().order_by('doc_type')
        videos = subject.videos.all().order_by('order')

        context = {
            'subject': subject,
            'documents': documents,
            'videos': videos,
            'user_has_access': user_has_access,
        }
        return render(request, self.template_name, context)

    def _check_access(self, user, subject) -> bool:
        if not subject.is_premium:
            return True
        return AccessCode.objects.filter(
            activated_by=user,
            status='active',
            expires_at__gt=timezone.now()
        ).exists()


class DocumentView(EduLoginRequiredMixin, View):
    """
    Visionneuse PDF sécurisée.
    Sert le PDF via stream avec watermark et sans URL directe exposée.
    """
    template_name = 'edu_platform/content/document_viewer.html'

    def get(self, request, pk):
        doc = get_object_or_404(ExamDocument, pk=pk)

        if doc.subject.is_premium and not self._has_active_subscription(request.user):
            return redirect('edu:plans')

        # Générer un token signé à durée limitée (15 min) pour l'URL du fichier
        token = self._generate_doc_token(request.user, pk)

        context = {
            'doc': doc,
            'subject': doc.subject,
            'token': token,
            'watermark_text': f"{request.user.get_full_name() or request.user.username} — EduCam Pro",
        }
        return render(request, self.template_name, context)

    def _has_active_subscription(self, user) -> bool:
        return AccessCode.objects.filter(
            activated_by=user,
            status='active',
            expires_at__gt=timezone.now()
        ).exists()

    def _generate_doc_token(self, user, doc_pk: int) -> str:
        """Token HMAC signé valide 15 minutes."""
        secret = settings.SECRET_KEY
        expires = int(time.time()) + 900  # 15 min
        payload = f"{user.pk}:{doc_pk}:{expires}"
        sig = hashlib.sha256(f"{secret}:{payload}".encode()).hexdigest()[:16]
        return f"{expires}:{sig}"


class SecureDocumentServeView(EduLoginRequiredMixin, View):
    """
    Sert le fichier PDF de manière sécurisée après vérification du token.
    En production, utiliser X-Accel-Redirect (Nginx) pour les performances.
    """
    def get(self, request, pk):
        token = request.GET.get('token', '')
        if not self._verify_token(request.user, pk, token):
            raise Http404("Lien expiré ou invalide.")

        doc = get_object_or_404(ExamDocument, pk=pk)
        if not doc.file:
            raise Http404("Fichier introuvable.")

        file_path = doc.file.path

        # En production avec Nginx : utiliser X-Accel-Redirect
        if not settings.DEBUG:
            response = HttpResponse()
            response['X-Accel-Redirect'] = f"/media_protected/{doc.file.name}"
            response['Content-Type'] = 'application/pdf'
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
            return response

        # Dev : stream direct
        response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response

    def _verify_token(self, user, doc_pk: int, token: str) -> bool:
        if not token or ':' not in token:
            return False
        try:
            expires_str, sig = token.split(':', 1)
            expires = int(expires_str)
            if time.time() > expires:
                return False
            secret = settings.SECRET_KEY
            payload = f"{user.pk}:{doc_pk}:{expires}"
            expected_sig = hashlib.sha256(f"{secret}:{payload}".encode()).hexdigest()[:16]
            return sig == expected_sig
        except (ValueError, AttributeError):
            return False


class VideoPlayerView(EduLoginRequiredMixin, View):
    """Lecteur vidéo protégé avec token signé."""
    template_name = 'edu_platform/content/video_player.html'

    def get(self, request, pk):
        video = get_object_or_404(VideoLesson, pk=pk)

        if video.subject.is_premium and not video.is_preview:
            if not self._has_active_subscription(request.user):
                return redirect('edu:plans')

        # Incrémenter les vues
        video.increment_views()

        # Token pour le fichier vidéo local (si premium)
        video_token = ''
        if video.video_file:
            video_token = self._generate_video_token(request.user, pk)

        context = {
            'video': video,
            'subject': video.subject,
            'video_token': video_token,
            'related_videos': VideoLesson.objects.filter(
                subject=video.subject
            ).exclude(pk=pk).order_by('order')[:5],
        }
        return render(request, self.template_name, context)

    def _has_active_subscription(self, user) -> bool:
        return AccessCode.objects.filter(
            activated_by=user,
            status='active',
            expires_at__gt=timezone.now()
        ).exists()

    def _generate_video_token(self, user, video_pk: int) -> str:
        secret = settings.SECRET_KEY
        expires = int(time.time()) + 900
        payload = f"v:{user.pk}:{video_pk}:{expires}"
        sig = hashlib.sha256(f"{secret}:{payload}".encode()).hexdigest()[:16]
        return f"{expires}:{sig}"
